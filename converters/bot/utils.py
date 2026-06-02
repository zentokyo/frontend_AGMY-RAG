"""
Утилиты для обработки данных вопросов и статистики.
"""
from typing import Any, Iterable, Optional, Sequence, Tuple


# ────────────────────────────────────────────────────────────────────────
# Извлечение текста вопроса из ответа API
# ────────────────────────────────────────────────────────────────────────

def _find_first_text(obj: Any, keys: Iterable[str] = ("text", "question_text")) -> Optional[str]:
    """Рекурсивно ищет первое текстовое значение по списку ключей."""
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
    """Извлечь текст вопроса из ответа API."""
    if isinstance(payload, dict) and "question" in payload:
        inner = payload.get("question")
        txt = _find_first_text(inner)
        if isinstance(txt, str):
            return txt
    return _find_first_text(payload)


def get_last_question_obj(data: Any) -> Any:
    """Получить последний объект вопроса из данных API."""
    if isinstance(data, list) and data:
        return data[-1]
    if isinstance(data, dict):
        for k in ("results", "questions", "items", "data"):
            v = data.get(k)
            if isinstance(v, list) and v:
                return v[-1]
    return data


# ────────────────────────────────────────────────────────────────────────
# Обработка и нормализация статистики
# ────────────────────────────────────────────────────────────────────────

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


# ────────────────────────────────────────────────────────────────────────
# Форматирование статистики для отображения
# ────────────────────────────────────────────────────────────────────────

def get_answers_stat(stats: Any) -> str:
    """Форматировать статистику ответов."""
    answer_list = stats.get("answer_list", [])
    answer_stat_str = ""
    for answer in answer_list:
        answer_evaluation = "Правильный ответ!" if answer.get('is_correct') else "Неправильный ответ!"
        answer_stat_str += (
            f"Вопрос: {answer.get('question_text', '')}\n"
            f"Оценка Вашего ответа: {answer_evaluation}\n\n"
        )
    return answer_stat_str


def format_stats_minimal(stats: Any) -> str:
    """Форматировать общую статистику."""
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
    """Форматировать статистику последнего экзамена."""
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
