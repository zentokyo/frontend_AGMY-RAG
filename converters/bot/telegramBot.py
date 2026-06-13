"""
Telegram-бот ASMU-RAG — точка входа и обработчики состояний.

Рефакторинг: клавиатуры, API-клиент и утилиты вынесены в отдельные модули.
"""
import os
import asyncio
import logging
import zipfile
from io import BytesIO
from typing import Tuple

from dotenv import load_dotenv
from aiohttp import ClientSession, ClientTimeout

from telegram import Update, InputMediaDocument
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from keyboards import kb_main, kb_exam_theme, kb_help, kb_stats, kb_in_progress, kb_theory
from api_client import APIClient
from utils import extract_question_text, format_stats_minimal, format_last_stats_minimal

# ============================================================================
# Настройка логирования
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# Состояния FSM
# ============================================================================
MAIN_MENU, EXAM_ASK_COUNT, EXAM_IN_PROGRESS, HELP_MENU, STATS_MENU, THEORY_MENU, EXAM_CHOOSE_THEME = range(7)

# ============================================================================
# Конфигурация
# ============================================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_BASE_URL = os.getenv("EXAM_API_BASE_URL", "http://127.0.0.1:8000")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "15.0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")


# ============================================================================
# Инициализация HTTP-клиента
# ============================================================================
async def post_init(app: Application) -> None:
    session = ClientSession(timeout=ClientTimeout(total=HTTP_TIMEOUT))
    app.bot_data["http_session"] = session
    app.bot_data["api"] = APIClient(session, API_BASE_URL)


async def post_shutdown(app: Application) -> None:
    session: ClientSession = app.bot_data.get("http_session")
    if session and not session.closed:
        await session.close()


def get_api(context: ContextTypes.DEFAULT_TYPE) -> APIClient:
    """Получить APIClient из контекста бота."""
    return context.application.bot_data["api"]


# ============================================================================
# Общая логика восстановления экзаменационной сессии (дедупликация)
# ============================================================================
async def _recover_exam_session(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        api: APIClient,
        user_id: int,
        fallback_state: int,
        fallback_markup,
) -> int:
    """Попытка восстановить активную экзаменационную сессию.

    Используется при status=403 (уже есть активный экзамен).
    Возвращает EXAM_IN_PROGRESS при успехе или fallback_state при ошибке.
    """
    await update.effective_message.reply_text(
        "У вас уже есть активная сессия экзамена, продолжаем без создания новой."
    )
    okq, qdata, qstatus, qerr = await api.ask_question(user_id)
    if not okq:
        oku, udata, ustatus, uerr = await api.get_unanswered_question(user_id)
        if oku and udata:
            question_text = extract_question_text(udata)
            if question_text:
                context.user_data["current_question"] = question_text
                await update.effective_message.reply_text(
                    f"Неотвеченный вопрос:\n{question_text}", reply_markup=kb_in_progress()
                )
                return EXAM_IN_PROGRESS
            else:
                await update.effective_message.reply_text(
                    "Не удалось извлечь вопрос из ответа.", reply_markup=fallback_markup
                )
                return fallback_state
        else:
            await update.effective_message.reply_text(
                "Ваша сессия активна, но не удалось получить неотвеченные вопросы.",
                reply_markup=fallback_markup
            )
            return fallback_state
    else:
        question_text = extract_question_text(qdata)
        if not question_text:
            await update.effective_message.reply_text(
                "Сессия активна, но не удалось получить текст вопроса.", reply_markup=fallback_markup
            )
            return fallback_state
        context.user_data["current_question"] = question_text
        await update.effective_message.reply_text(
            f"Вопрос:\n{question_text}", reply_markup=kb_in_progress()
        )
        return EXAM_IN_PROGRESS


# ============================================================================
# Обработчик глобальных ошибок
# ============================================================================
async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "Произошла ошибка при обработке, попробуйте ещё раз или начните заново командой /start.",
                reply_markup=kb_main(),
            )
    except Exception:
        pass


# ============================================================================
# Обработчики главного меню
# ============================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("Привет! Выберите действие:", reply_markup=kb_main())
    return MAIN_MENU


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = (
        "📚 *Помощь*\n"
        "— Для начала экзамена нажмите «Начать экзамен» и выберите тему.\n"
        "— Отвечайте на вопросы текстом в чате или используйте кнопку «Получить вопрос», чтобы повторно вывести последний вопрос на экран. *Обратите внимание*, что исправление уже отправленного боту сообщения, не позволит изменить Ваш ответ.\n"
        "\n"
        "— В разделе «Теория» доступны файлы с учебными материалами по темам. Откройте нужную тему и скачайте pdf-файл для изучения оффлайн.\n"
        "\n"
        "— Раздел «Статистика» показывает:\n"
        "   • *«Общая статистика»* — сводная информация по количеству заданных вопросов и корректности ответов по каждой теме и в целом.\n"
        "   • *«Последний экзамен»* — ваши ответы и их корректность в последней попытке.\n"
        "\n"
        "— Для возврата в главное меню используйте кнопки или команду /start\n"
        "— Доступные команды: /start (возврат в главное меню), /help (справка), /stats (статистика), /theory (Учебные материалы)"
    )
    await update.effective_message.reply_text(text, reply_markup=kb_help(), parse_mode="Markdown")
    return HELP_MENU


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("Статистика:", reply_markup=kb_stats())
    return STATS_MENU


async def to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("Главное меню:", reply_markup=kb_main())
    return MAIN_MENU


async def main_menu_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text(
        "Неверная команда. Используйте кнопки или команды /start, /help, /stats.",
        reply_markup=kb_main(),
    )
    return MAIN_MENU


async def menu_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await cmd_help(update, context)


async def menu_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await cmd_stats(update, context)


# ============================================================================
# Обработчики выбора темы экзамена
# ============================================================================
async def exam_theme_choose_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    api = get_api(context)
    user_id = update.effective_user.id
    ok, themes, status, err = await api.get_exam_themes(user_id)
    if not ok or not themes:
        await update.effective_message.reply_text(f"Не удалось получить список тем экзамена (status={status}): {err}",
                                                  reply_markup=kb_main())
        return MAIN_MENU
    context.user_data["exam_themes"] = {theme["title"]: theme for theme in themes}
    await update.effective_message.reply_text("Выберите экзаменационную тему:", reply_markup=kb_exam_theme(themes))
    return EXAM_CHOOSE_THEME


async def exam_theme_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    themes = context.user_data.get("exam_themes", {})

    if text == "Отмена":
        return await to_main_menu(update, context)

    if text == "---":
        await update.effective_message.reply_text(
            "Вы еще не открыли эту тему.",
            reply_markup=kb_exam_theme(list(themes.values()))
        )
        return EXAM_CHOOSE_THEME

    theme_obj = themes.get(text)
    if not theme_obj:
        await update.effective_message.reply_text(
            "Тема не найдена. Попробуйте снова.",
            reply_markup=kb_exam_theme(list(themes.values()))
        )
        return EXAM_CHOOSE_THEME

    if not theme_obj.get("is_enable", True):
        await update.effective_message.reply_text(
            "Вы еще не открыли эту тему.",
            reply_markup=kb_exam_theme(list(themes.values()))
        )
        return EXAM_CHOOSE_THEME

    api = get_api(context)
    user_id = update.effective_user.id
    exam_theme_id = theme_obj["exam_theme_id"]
    ok, data, status, err = await api.create_exam(user_id, 10, exam_theme_id)

    if not ok:
        if status == 403:
            return await _recover_exam_session(
                update, context, api, user_id,
                fallback_state=MAIN_MENU, fallback_markup=kb_main(),
            )

        await update.effective_message.reply_text(
            f"Не удалось создать экзамен (status={status}): {err}",
            reply_markup=kb_main()
        )
        return MAIN_MENU

    exam_id = None
    if isinstance(data, dict):
        exam_id = data.get("exam_id") or data.get("id") or data.get("uuid")
    if not exam_id:
        await update.effective_message.reply_text(
            "Сервер не вернул exam_id — не могу продолжать.",
            reply_markup=kb_main()
        )
        return MAIN_MENU

    context.user_data["exam_id"] = str(exam_id)
    ok, qdata, qstatus, qerr = await api.ask_question(user_id)
    if not ok:
        await update.effective_message.reply_text(
            f"Не удалось получить вопрос (status={qstatus}): {qerr}",
            reply_markup=kb_main()
        )
        return MAIN_MENU

    question_text = extract_question_text(qdata)
    if not question_text:
        await update.effective_message.reply_text(
            "Ответ сервера не содержит текст вопроса.",
            reply_markup=kb_main()
        )
        return MAIN_MENU

    context.user_data["current_question"] = question_text
    await update.effective_message.reply_text(
        f"Вопрос:\n{question_text}", reply_markup=kb_in_progress()
    )
    return EXAM_IN_PROGRESS


# ============================================================================
# Обработчики экзамена
# ============================================================================
async def exam_get_latest_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    api = get_api(context)
    user_id = update.effective_user.id

    cached_question = context.user_data.get("current_question")
    if cached_question:
        await update.effective_message.reply_text(f"Текущий вопрос:\n{cached_question}", reply_markup=kb_in_progress())
        return EXAM_IN_PROGRESS

    ok, data, status, err = await api.get_unanswered_question(user_id)
    if not ok:
        await update.effective_message.reply_text(
            f"Не удалось получить текущий вопрос (status={status}): {err}",
            reply_markup=kb_in_progress()
        )
        return EXAM_IN_PROGRESS

    question_text = extract_question_text(data)
    if question_text:
        context.user_data["current_question"] = question_text
        await update.effective_message.reply_text(f"Текущий вопрос:\n{question_text}", reply_markup=kb_in_progress())
    else:
        await update.effective_message.reply_text(
            "Не удалось извлечь текст вопроса из ответа.",
            reply_markup=kb_in_progress()
        )
    return EXAM_IN_PROGRESS


async def exam_submit_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    api = get_api(context)
    user_id = update.effective_user.id
    answer_text = update.effective_message.text

    ok, _, status, err = await api.post_answer(user_id, answer_text)
    if not ok:
        await update.effective_message.reply_text(f"Не удалось отправить ответ (status={status}): {err}",
                                                  reply_markup=kb_in_progress())
        return EXAM_IN_PROGRESS

    ok, qdata, qstatus, qerr = await api.ask_question(user_id)
    if not ok:
        message_text = ""
        if isinstance(qdata, dict):
            message_text = str(qdata.get("message") or qdata.get("detail") or "")
        combined = f"{qerr} {message_text}".lower()
        finished = qstatus == 400 and ("экзаменационная сессия" in combined and "не найдена" in combined)

        if finished:
            context.user_data.pop("current_question", None)
            sok, sdata, sstatus, serr = await api.get_stats_last(user_id)
            if sok:
                summary = format_last_stats_minimal(sdata)
                await update.effective_message.reply_text(
                    "Экзамен завершён.\nСтатистика последнего экзамена:\n\n" + summary,
                    reply_markup=kb_main(),
                )
            else:
                await update.effective_message.reply_text(
                    f"Экзамен завершён, но статистику получить не удалось (status={sstatus}): {serr}",
                    reply_markup=kb_main(),
                )
            context.user_data.pop("exam_id", None)
            return MAIN_MENU

        await update.effective_message.reply_text(f"Не удалось получить новый вопрос (status={qstatus}): {qerr}",
                                                  reply_markup=kb_in_progress())
        return EXAM_IN_PROGRESS

    question_text = extract_question_text(qdata)
    if not question_text:
        await update.effective_message.reply_text("Ответ сервера не содержит текст следующего вопроса.",
                                                  reply_markup=kb_in_progress())
        return EXAM_IN_PROGRESS

    context.user_data["current_question"] = question_text
    await update.effective_message.reply_text(f"Новый вопрос:\n{question_text}", reply_markup=kb_in_progress())
    return EXAM_IN_PROGRESS


# ============================================================================
# Обработчики помощи и статистики
# ============================================================================
async def help_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await to_main_menu(update, context)


async def stats_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    api = get_api(context)
    user_id = update.effective_user.id
    ok, data, status, err = await api.get_stats_all(user_id)
    if ok:
        summary = format_stats_minimal(data)
        await update.effective_message.reply_text("Общая статистика:\n" + summary, reply_markup=kb_main())
    else:
        await update.effective_message.reply_text(f"Не удалось получить общую статистику (status={status}): {err}",
                                                  reply_markup=kb_main())
    return MAIN_MENU


async def stats_last(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    api = get_api(context)
    user_id = update.effective_user.id
    ok, data, status, err = await api.get_stats_last(user_id)
    if ok:
        summary = format_last_stats_minimal(data)
        await update.effective_message.reply_text("Статистика за последний экзамен:\n\n" + summary,
                                                  reply_markup=kb_main())
    else:
        await update.effective_message.reply_text(
            f"Не удалось получить статистику последнего экзамена (status={status}): {err}", reply_markup=kb_main())
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("Диалог отменён.", reply_markup=kb_main())
    return MAIN_MENU


# ============================================================================
# Обработчики меню теории
# ============================================================================
async def theory_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    api = get_api(context)
    user_id = update.effective_user.id
    ok, themes, status, err = await api.get_themes(user_id)
    if not ok or not themes:
        await update.effective_message.reply_text(f"Не удалось получить список тем (status={status}): {err}",
                                                  reply_markup=kb_main())
        return MAIN_MENU
    context.user_data["themes"] = {theme["title"]: theme for theme in themes}
    await update.effective_message.reply_text("Выберите тему для просмотра файла.", reply_markup=kb_theory(themes))
    return THEORY_MENU


def extract_pdf_file_list(zip_bytes: bytes) -> list[Tuple[bytes, str]]:
    """Извлечь PDF-файлы из zip-архива."""
    with zipfile.ZipFile(BytesIO(zip_bytes), 'r') as zip_buffer:
        file_list = [
            (zip_buffer.read(filename), filename)
            for filename in zip_buffer.namelist()
            if filename.lower().endswith(".pdf")
        ]
    return file_list


async def theory_select_theme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text.strip()
    themes = context.user_data.get("themes", {})
    if text == "Назад":
        return await to_main_menu(update, context)

    if text == "---":
        await update.effective_message.reply_text(
            "Вы еще не открыли эту тему.",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    theme_obj = themes.get(text)
    if not theme_obj:
        await update.effective_message.reply_text(
            "Тема не найдена. Попробуйте снова.",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    if not theme_obj.get("is_enable", True):
        await update.effective_message.reply_text(
            "Вы еще не открыли эту тему.",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    api = get_api(context)
    user_id = update.effective_user.id

    ok, file_bytes, filename, ctype, status, err = await api.get_theme_file(theme_obj["theme_id"])
    if not ok or not file_bytes:
        await update.effective_message.reply_text(
            f"Не удалось получить файл для темы (status={status}): {err}",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    pdf_list = await asyncio.to_thread(extract_pdf_file_list, file_bytes)

    await update.effective_message.reply_text(
        f"Познакомьтесь со справочной информацией по теме «{theme_obj['title']}»"
    )
    await update.effective_message.reply_media_group(
        media=[InputMediaDocument(pdf_bytes, filename=filename) for pdf_bytes, filename in pdf_list],
    )

    exam_theme_id = theme_obj["theme_id"]
    ok_exam, data_exam, status_exam, err_exam = await api.create_exam(user_id, 3, exam_theme_id)

    if not ok_exam or not data_exam:
        if status_exam == 403:
            return await _recover_exam_session(
                update, context, api, user_id,
                fallback_state=THEORY_MENU,
                fallback_markup=kb_theory(list(themes.values())),
            )
        await update.effective_message.reply_text(
            f"Экзамен по теории не удалось создать (status={status_exam}): {err_exam}",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    okq, qdata, qstatus, qerr = await api.ask_question(user_id)
    if not okq or not qdata:
        await update.effective_message.reply_text(
            f"Вопрос от сервера не удалось получить (status={qstatus}): {qerr}",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    question_text = extract_question_text(qdata)
    if question_text:
        context.user_data["current_question"] = question_text
        await update.effective_message.reply_text(
            f"Вопрос по теме:\n{question_text}", reply_markup=kb_in_progress()
        )
    else:
        await update.effective_message.reply_text(
            "Не удалось извлечь текст вопроса из ответа.", reply_markup=kb_in_progress()
        )
    return EXAM_IN_PROGRESS


# ============================================================================
# Сборка приложения
# ============================================================================
def build_application() -> Application:
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_error_handler(on_error)

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("help", cmd_help),
            CommandHandler("stats", cmd_stats),
            CommandHandler("theory", theory_menu_entry),
        ],
        states={
            MAIN_MENU: [
                CommandHandler("help", cmd_help),
                CommandHandler("stats", cmd_stats),
                CommandHandler("theory", theory_menu_entry),
                MessageHandler(filters.Regex(r"^Теория$"), theory_menu_entry),
                MessageHandler(filters.Regex(r"^Помощь$"), menu_help),
                MessageHandler(filters.Regex(r"^Начать экзамен$"), exam_theme_choose_entry),
                MessageHandler(filters.Regex(r"^Статистика$"), menu_stats),
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu_unknown),
            ],
            EXAM_CHOOSE_THEME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, exam_theme_selected),
            ],
            EXAM_IN_PROGRESS: [
                CommandHandler("help", cmd_help),
                CommandHandler("stats", cmd_stats),
                CommandHandler("theory", theory_menu_entry),
                MessageHandler(filters.Regex(r"^Получить вопрос$"), exam_get_latest_question),
                MessageHandler(filters.TEXT & ~filters.COMMAND, exam_submit_answer),
            ],
            HELP_MENU: [
                CommandHandler("help", cmd_help),
                CommandHandler("stats", cmd_stats),
                CommandHandler("theory", theory_menu_entry),
                MessageHandler(filters.Regex(r"^Назад$"), help_back),
            ],
            STATS_MENU: [
                CommandHandler("help", cmd_help),
                CommandHandler("stats", cmd_stats),
                CommandHandler("theory", theory_menu_entry),
                MessageHandler(filters.Regex(r"^Общая статистика$"), stats_all),
                MessageHandler(filters.Regex(r"^Последний экзамен$"), stats_last),
                MessageHandler(filters.Regex(r"^Отмена$"), to_main_menu),
            ],
            THEORY_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, theory_select_theme),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
            CommandHandler("theory", theory_menu_entry),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv)
    return app


# ============================================================================
# Точка входа
# ============================================================================
def main() -> None:
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
