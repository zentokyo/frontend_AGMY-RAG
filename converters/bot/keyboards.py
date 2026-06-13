"""
Клавиатуры для Telegram-бота ASMU-RAG.
"""
from telegram import ReplyKeyboardMarkup


def kb_main():
    """Клавиатура главного меню."""
    return ReplyKeyboardMarkup(
        [["Теория"], ["Помощь"], ["Начать экзамен"], ["Статистика"]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def kb_exam_theme(themes: list):
    """Клавиатура выбора темы экзамена."""
    rows = []
    for theme in themes:
        display_title = theme["title"] if theme.get("is_enable", True) else "---"
        rows.append([display_title])
    rows.append(["Отмена"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


def kb_help():
    """Клавиатура меню помощи."""
    return ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)


def kb_stats():
    """Клавиатура меню статистики."""
    return ReplyKeyboardMarkup(
        [["Общая статистика"], ["Последний экзамен"], ["Отмена"]],
        resize_keyboard=True,
    )


def kb_in_progress():
    """Клавиатура во время экзамена."""
    return ReplyKeyboardMarkup([["Получить вопрос"]], resize_keyboard=True)


def kb_theory(themes: list):
    """Клавиатура выбора темы для просмотра теории."""
    if not themes:
        return ReplyKeyboardMarkup([["Назад"]], resize_keyboard=True)
    rows = []
    for theme in themes:
        display_title = theme["title"] if theme.get("is_enable", True) else "---"
        rows.append([display_title])
    rows.append(["Назад"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)
