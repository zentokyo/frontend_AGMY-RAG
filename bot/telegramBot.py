import os
import json
import asyncio
import logging
import zipfile
from io import BytesIO
from typing import Any, Dict, Optional, Tuple, Union, Iterable, Sequence

from dotenv import load_dotenv
from aiohttp import ClientSession, ClientTimeout, ClientError

from telegram import Update, ReplyKeyboardMarkup, InputFile, InputMediaDocument
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ============================================================================
# Настройка системы логирования
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# Определение состояний конечного автомата (FSM)
# ============================================================================
MAIN_MENU, EXAM_ASK_COUNT, EXAM_IN_PROGRESS, HELP_MENU, STATS_MENU, THEORY_MENU, EXAM_CHOOSE_THEME = range(7)


# ============================================================================
# Функции создания клавиатур для различных состояний бота
# ============================================================================
def kb_main():
    return ReplyKeyboardMarkup(
        [["Теория"], ["Помощь"], ["Начать экзамен"], ["Статистика"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def kb_exam_theme(themes: list):
    rows = []
    for theme in themes:
        # Выводим "---" если тема неактивна
        display_title = theme["title"] if theme.get("is_enable", True) else "---"
        rows.append([display_title])
    rows.append(["Отмена"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def kb_help():
    return ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)


def kb_stats():
    return ReplyKeyboardMarkup(
        [["Общая статистика"], ["Последний экзамен"], ["Отмена"]],
        resize_keyboard=True,
    )


def kb_in_progress():
    return ReplyKeyboardMarkup([["Получить вопрос"]], resize_keyboard=True)


def kb_theory(themes: list):
    if not themes:
        return ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)
    rows = []
    for theme in themes:
        # Выводим "---" если тема неактивна
        display_title = theme["title"] if theme.get("is_enable", True) else "---"
        rows.append([display_title])
    rows.append(["Назад"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


# ============================================================================
# Загрузка переменных окружения и конфигурация HTTP-клиента
# ============================================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_BASE_URL = os.getenv("EXAM_API_BASE_URL", "http://localhost:8000")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "15.0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не найден в .env")


def build_url(path: str) -> str:
    return f"{API_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


async def post_init(app: Application) -> None:
    app.bot_data["http_session"] = ClientSession(timeout=ClientTimeout(total=HTTP_TIMEOUT))


async def post_shutdown(app: Application) -> None:
    session: ClientSession = app.bot_data.get("http_session")
    if session and not session.closed:
        await session.close()


def get_session(context: ContextTypes.DEFAULT_TYPE) -> ClientSession:
    return context.application.bot_data["http_session"]


# ============================================================================
# API методы для взаимодействия с внешним сервисом экзаменов
# ============================================================================
async def api_get_exam_themes(session: ClientSession, user_id: int) -> Tuple[bool, Optional[list], int, str]:
    url = build_url(f"/exams/themes/users/{user_id}")
    try:
        async with session.get(url) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data if isinstance(data, list) else None, status, ""
            return False, None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_create_exam(session: ClientSession, user_id: int, question_count: int,
                          exam_theme_id: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], int, str]:
    url = build_url("/exams/")
    payload = {"user_id": user_id, "question_count": question_count}
    if exam_theme_id:
        payload["exam_theme_id"] = exam_theme_id
    try:
        async with session.post(url, json=payload) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data if isinstance(data, dict) else None, status, ""
            return False, data if isinstance(data, dict) else None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_ask_question(session: ClientSession, user_id: int) -> Tuple[bool, Optional[Dict[str, Any]], int, str]:
    url = build_url(f"/exams/users/{user_id}/questions/ask/")
    try:
        async with session.post(url, json={}) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data if isinstance(data, dict) else None, status, ""
            return False, data if isinstance(data, dict) else None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_get_unanswered_question(session: ClientSession, user_id: int) -> Tuple[
    bool, Optional[Dict[str, Any]], int, str]:
    url = build_url(f"/exams/users/{user_id}/questions/unanswered/")
    try:
        async with session.get(url) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data if isinstance(data, dict) else None, status, ""
            return False, data if isinstance(data, dict) else None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_get_questions(session: ClientSession, exam_id: Union[str, int]) -> Tuple[bool, Optional[Any], int, str]:
    url = build_url(f"/exams/{exam_id}/questions/")
    try:
        async with session.get(url) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data, status, ""
            return False, data if isinstance(data, dict) else None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_post_answer(session: ClientSession, user_id: int, answer_text: str) -> Tuple[
    bool, Optional[Dict[str, Any]], int, str]:
    url = build_url("/answers/")
    payload = {"user_id": user_id, "answer_text": answer_text}
    try:
        async with session.post(url, json=payload) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status in (200, 201):
                return True, data if isinstance(data, dict) else None, status, ""
            return False, data if isinstance(data, dict) else None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_get_stats_all(session: ClientSession, user_id: int) -> Tuple[bool, Optional[Any], int, str]:
    url = build_url(f"/stats/users/{user_id}/all/")
    try:
        async with session.get(url) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data, status, ""
            return False, data if isinstance(data, dict) else None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_get_stats_last(session: ClientSession, user_id: int) -> Tuple[bool, Optional[Any], int, str]:
    url = build_url(f"/stats/users/{user_id}/last/")
    try:
        async with session.get(url) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data, status, ""
            return False, data if isinstance(data, dict) else None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_get_themes(session: ClientSession, user_id: int) -> Tuple[bool, Optional[list], int, str]:
    url = build_url(f"/themes/users/{user_id}/")
    try:
        async with session.get(url) as resp:
            status = resp.status
            ctype = resp.headers.get("Content-Type", "")
            data = await (resp.json() if "application/json" in ctype else resp.text())
            if status == 200:
                return True, data if isinstance(data, list) else None, status, ""
            return False, None, status, str(data)
    except Exception as e:
        return False, None, 0, str(e)


async def api_get_theme_file(session: ClientSession, theme_id: str) -> Tuple[bool, Optional[bytes], str, str, int, str]:
    url = build_url(f"/themes/{theme_id}/file/")
    try:
        async with session.get(url) as resp:
            status = resp.status
            filename = resp.headers.get("Content-Disposition", "").split("filename=")[-1].strip(
                '"') if "filename=" in resp.headers.get("Content-Disposition", "") else "file.pdf"
            ctype = resp.headers.get("Content-Type", "")
            if status == 200:
                file_bytes = await resp.read()
                return True, file_bytes, filename, ctype, status, ""
            data = await resp.text()
            return False, None, "", ctype, status, data
    except Exception as e:
        return False, None, "", "", 0, str(e)


# ============================================================================
# Вспомогательные функции для извлечения и обработки данных вопросов
# ============================================================================
def _find_first_text(obj: Any, keys: Iterable[str] = ("text", "question_text")) -> Optional[str]:
    if isinstance(obj, dict):
        for k in keys:
            v = obj.get(k)
            if isinstance(v, str):
                return v
        for v in obj.values():
            found = _find_first_text(v, keys)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first_text(item, keys)
            if found:
                return found
    return None


def extract_question_text(payload: Any) -> Optional[str]:
    if isinstance(payload, dict) and "question" in payload:
        inner = payload.get("question")
        txt = _find_first_text(inner)
        if isinstance(txt, str):
            return txt
    return _find_first_text(payload)


def get_last_question_obj(data: Any) -> Any:
    if isinstance(data, list) and data:
        return data[-1]
    if isinstance(data, dict):
        for k in ("results", "questions", "items", "data"):
            v = data.get(k)
            if isinstance(v, list) and v:
                return v[-1]
    return data


# ============================================================================
# Вспомогательные функции для обработки и нормализации статистики
# ============================================================================
def _to_int_or_none(x: Any) -> Optional[int]:
    try:
        return int(x)
    except (TypeError, ValueError):
        try:
            return int(float(x))
        except (TypeError, ValueError):
            return None


def _deep_find_first_int_by_keys(data: Any, key_candidates: Sequence[str]) -> Optional[int]:
    if isinstance(data, dict):
        for k in key_candidates:
            if k in data:
                val = _to_int_or_none(data.get(k))
                if val is not None:
                    return val
        for v in data.values():
            found = _deep_find_first_int_by_keys(v, key_candidates)
            if found is not None:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _deep_find_first_int_by_keys(item, key_candidates)
            if found is not None:
                return found
    return None


def _deep_collect_sum_by_keys(data: Any, key_candidates: Sequence[str]) -> Optional[int]:
    acc = 0
    found_any = False
    if isinstance(data, dict):
        for k, v in data.items():
            if k in key_candidates:
                val = _to_int_or_none(v)
                if val is not None:
                    acc += val
                    found_any = True
            else:
                sub = _deep_collect_sum_by_keys(v, key_candidates)
                if sub is not None:
                    acc += sub
                    found_any = True
    elif isinstance(data, list):
        for item in data:
            sub = _deep_collect_sum_by_keys(item, key_candidates)
            if sub is not None:
                acc += sub
                found_any = True
    return acc if found_any else None


_TOTAL_KEYS = (
    "total_answers", "answers_total", "answers_count", "total", "count",
    "questions_total", "questions_count", "answered", "answered_total",
)
_CORRECT_KEYS = (
    "correct_answers", "answers_correct", "correct", "right_answers",
    "right", "true", "passed", "score_correct",
)


def _normalize_stats_to_pair(stats: Any) -> Optional[Tuple[int, int]]:
    total = _deep_find_first_int_by_keys(stats, _TOTAL_KEYS)
    correct = _deep_find_first_int_by_keys(stats, _CORRECT_KEYS)
    if total is not None and correct is not None:
        return correct, total
    total_sum = _deep_collect_sum_by_keys(stats, _TOTAL_KEYS)
    correct_sum = _deep_collect_sum_by_keys(stats, _CORRECT_KEYS)
    if total_sum is not None and correct_sum is not None:
        return correct_sum, total_sum
    return None


def get_answers_stat(stats: Any) -> str:
    answer_list = stats.get("answer_list", [])
    answer_stat_str = ""
    for answer in answer_list:
        answer_evaluation = "Правильный ответ!" if answer.get('is_correct') else "Неправильный ответ!"
        answer_stat_str += (
            f"Вопрос: {answer.get('question_text', '')}\n"
            f"Оценка Вашего ответа: {answer_evaluation}\n\n"
        )
    return answer_stat_str


# ============================================================================
# Функции форматирования статистики для отображения пользователю
# ============================================================================
def format_stats_minimal(stats: Any) -> str:
    total = stats.get("total_answers", 0)
    correct = stats.get("correct_answers", 0)
    accuracy = stats.get("accuracy", 0)
    accuracy = accuracy * 100
    out = [f"Всего ответов: {total}",
           f"Верных ответов: {correct}",
           f"Точность: {accuracy}%"]
    stat_by_theme = stats.get("stat_by_theme")
    if stat_by_theme and isinstance(stat_by_theme, list):
        out.append("⎯⎯⎯⎯\nПо темам:")
        for theme in stat_by_theme:
            theme_title = theme.get("theme_title", "Без названия")
            theme_total = theme.get("total_answers", 0)
            theme_correct = theme.get("correct_answers", 0)
            theme_accuracy = theme.get("accuracy", 0)
            theme_accuracy = theme_accuracy * 100
            out.append(
                f'\n— {theme_title}\n Верных ответов: {theme_correct} из {theme_total}\n Точность: {theme_accuracy}%')
    return "\n".join(out)


def format_last_stats_minimal(stats: Any) -> str:
    out = []
    theme_title = stats.get("theme_title")
    if theme_title:
        out.append(f"Тема: {theme_title}")
    total = stats.get("total_answers", 0)
    correct = stats.get("correct_answers", 0)
    accuracy = stats.get("accuracy", 0)
    accuracy = accuracy * 100
    out.append(f"Верных ответов: {correct} из {total}")
    out.append(f"Точность: {accuracy}%")
    answer_list = stats.get("answer_list", [])
    if answer_list:
        out.append("⎯⎯⎯⎯")
        for ans in answer_list:
            correctness = "✅" if ans.get("is_correct") else "❌"
            q_txt = ans.get("question_text", "")
            user_ans = ans.get("user_answer", "")
            model_ans = ans.get("model_answer", "")
            if not ans.get("is_correct"):
                pretty_model_ans = f"👀Эталонный ответ: {model_ans}\n" if model_ans else ""
            else:
                pretty_model_ans = ""
            out.append(f"{correctness} {q_txt}\n\nВаш ответ: {user_ans}\n\n{pretty_model_ans}")
    return "\n".join(out)


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
# Обработчики команд и главного меню
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


async def menu_choose_exam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await exam_theme_choose_entry(update, context)


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
    session = get_session(context)
    user_id = update.effective_user.id
    ok, themes, status, err = await api_get_exam_themes(session, user_id)
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

    # Проверка на нажатие "---"
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

    # Проверка is_enable
    if not theme_obj.get("is_enable", True):
        await update.effective_message.reply_text(
            "Вы еще не открыли эту тему.",
            reply_markup=kb_exam_theme(list(themes.values()))
        )
        return EXAM_CHOOSE_THEME

    session = get_session(context)
    user_id = update.effective_user.id
    exam_theme_id = theme_obj["exam_theme_id"]
    ok, data, status, err = await api_create_exam(session, user_id, 10, exam_theme_id)

    if not ok:
        if status == 403:
            await update.effective_message.reply_text(
                "У вас уже есть активная сессия экзамена, продолжаем без создания новой."
            )
            okq, qdata, qstatus, qerr = await api_ask_question(session, user_id)
            if not okq:
                oku, udata, ustatus, uerr = await api_get_unanswered_question(session, user_id)
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
                            "Не удалось извлечь вопрос из ответа.", reply_markup=kb_main()
                        )
                        return MAIN_MENU
                else:
                    await update.effective_message.reply_text(
                        "Ваша сессия активна, но не удалось получить неотвеченные вопросы.",
                        reply_markup=kb_main()
                    )
                    return MAIN_MENU
            else:
                question_text = extract_question_text(qdata)
                if not question_text:
                    await update.effective_message.reply_text(
                        "Сессия активна, но не удалось получить текст вопроса.", reply_markup=kb_main()
                    )
                    return MAIN_MENU
                context.user_data["current_question"] = question_text
                await update.effective_message.reply_text(
                    f"Вопрос:\n{question_text}", reply_markup=kb_in_progress()
                )
                return EXAM_IN_PROGRESS

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
    ok, qdata, qstatus, qerr = await api_ask_question(session, user_id)
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
# Обработчики процесса прохождения экзамена
# ============================================================================
async def exam_get_latest_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = get_session(context)
    user_id = update.effective_user.id

    cached_question = context.user_data.get("current_question")
    if cached_question:
        await update.effective_message.reply_text(f"Текущий вопрос:\n{cached_question}", reply_markup=kb_in_progress())
        return EXAM_IN_PROGRESS

    ok, data, status, err = await api_get_unanswered_question(session, user_id)
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
    session = get_session(context)
    user_id = update.effective_user.id
    answer_text = update.effective_message.text

    ok, _, status, err = await api_post_answer(session, user_id, answer_text)
    if not ok:
        await update.effective_message.reply_text(f"Не удалось отправить ответ (status={status}): {err}",
                                                  reply_markup=kb_in_progress())
        return EXAM_IN_PROGRESS

    ok, qdata, qstatus, qerr = await api_ask_question(session, user_id)
    if not ok:
        message_text = ""
        if isinstance(qdata, dict):
            message_text = str(qdata.get("message") or qdata.get("detail") or "")
        combined = f"{qerr} {message_text}".lower()
        finished = qstatus == 400 and ("экзаменационная сессия" in combined and "не найдена" in combined)

        if finished:
            # Очищаем кэш вопроса при завершении экзамена
            context.user_data.pop("current_question", None)
            sok, sdata, sstatus, serr = await api_get_stats_last(session, user_id)
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

    # Сохраняем новый вопрос в кэш
    context.user_data["current_question"] = question_text
    await update.effective_message.reply_text(f"Новый вопрос:\n{question_text}", reply_markup=kb_in_progress())
    return EXAM_IN_PROGRESS


# ============================================================================
# Обработчики меню помощи
# ============================================================================
async def help_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await to_main_menu(update, context)


# ============================================================================
# Обработчики меню статистики
# ============================================================================
async def stats_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = get_session(context)
    user_id = update.effective_user.id
    ok, data, status, err = await api_get_stats_all(session, user_id)
    if ok:
        summary = format_stats_minimal(data)
        await update.effective_message.reply_text("Общая статистика:\n" + summary, reply_markup=kb_main())
    else:
        await update.effective_message.reply_text(f"Не удалось получить общую статистику (status={status}): {err}",
                                                  reply_markup=kb_main())
    return MAIN_MENU


async def stats_last(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = get_session(context)
    user_id = update.effective_user.id
    ok, data, status, err = await api_get_stats_last(session, user_id)
    if ok:
        summary = format_last_stats_minimal(data)
        await update.effective_message.reply_text("Статистика за последний экзамен:\n\n" + summary,
                                                  reply_markup=kb_main())
    else:
        await update.effective_message.reply_text(
            f"Не удалось получить статистику последнего экзамена (status={status}): {err}", reply_markup=kb_main())
    return MAIN_MENU


# ============================================================================
# Обработчик отмены операции
# ============================================================================
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_message.reply_text("Диалог отменён.", reply_markup=kb_main())
    return MAIN_MENU


# ============================================================================
# Обработчики меню теории
# ============================================================================
async def theory_menu_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    session = get_session(context)
    user_id = update.effective_user.id
    ok, themes, status, err = await api_get_themes(session, user_id)
    if not ok or not themes:
        await update.effective_message.reply_text(f"Не удалось получить список тем (status={status}): {err}",
                                                  reply_markup=kb_main())
        return MAIN_MENU
    context.user_data["themes"] = {theme["title"]: theme for theme in themes}
    await update.effective_message.reply_text("Выберите тему для просмотра файла.", reply_markup=kb_theory(themes))
    return THEORY_MENU


def extract_pdf_file_list(zip_bytes: bytes) -> list[Tuple[bytes, str]]:
    """
    Извлекаем пдф-файлы из zip-архива
    """
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

    # Проверка на нажатие "---"
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

    # Проверка is_enable
    if not theme_obj.get("is_enable", True):
        await update.effective_message.reply_text(
            "Вы еще не открыли эту тему.",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    session = get_session(context)
    ok, file_bytes, filename, ctype, status, err = await api_get_theme_file(session, theme_obj["theme_id"])
    if not ok or not file_bytes:
        await update.effective_message.reply_text(
            f"Не удалось получить файл для темы (status={status}): {err}",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    pdf_list = await asyncio.to_thread(extract_pdf_file_list,file_bytes)

    await update.effective_message.reply_text(
        f"Познакомьтесь со справочной информацией по теме «{theme_obj['title']}»"
    )
    await update.effective_message.reply_media_group(
        media=[InputMediaDocument(pdf_bytes, filename=filename) for pdf_bytes, filename in pdf_list],
    )


    user_id = update.effective_user.id
    exam_theme_id = theme_obj["theme_id"]
    ok_exam, data_exam, status_exam, err_exam = await api_create_exam(session, user_id, 3, exam_theme_id)

    if not ok_exam or not data_exam:
        if status_exam == 403:
            await update.effective_message.reply_text(
                "У вас уже есть активная сессия экзамена по этой теме, продолжаем без создания новой."
            )
            okq, qdata, qstatus, qerr = await api_ask_question(session, user_id)
            if not okq:
                oku, udata, ustatus, uerr = await api_get_unanswered_question(session, user_id)
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
                            "Не удалось извлечь вопрос из ответа.", reply_markup=kb_theory(list(themes.values()))
                        )
                        return THEORY_MENU
                else:
                    await update.effective_message.reply_text(
                        "Ваша сессия активна, но не удалось получить неотвеченные вопросы.",
                        reply_markup=kb_theory(list(themes.values()))
                    )
                    return THEORY_MENU
            else:
                question_text = extract_question_text(qdata)
                if not question_text:
                    await update.effective_message.reply_text(
                        "Сессия активна, но не удалось получить текст вопроса.",
                        reply_markup=kb_theory(list(themes.values()))
                    )
                    return THEORY_MENU
                context.user_data["current_question"] = question_text
                await update.effective_message.reply_text(
                    f"Вопрос:\n{question_text}", reply_markup=kb_in_progress()
                )
                return EXAM_IN_PROGRESS
        await update.effective_message.reply_text(
            f"Экзамен по теории не удалось создать (status={status_exam}): {err_exam}",
            reply_markup=kb_theory(list(themes.values()))
        )
        return THEORY_MENU

    okq, qdata, qstatus, qerr = await api_ask_question(session, user_id)
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
# Построение и настройка приложения Telegram бота
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
# Точка входа в приложение
# ============================================================================
def main() -> None:
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
