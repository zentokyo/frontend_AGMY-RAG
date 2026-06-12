import logging
import os
import re
import json
from src.core.rag.deepseek_llm import DeepSeekFlashLLM
from src.core.rag.ingest import GigaChatEmbeddings
from src.core.rag.qdrant_store import QdrantKnowledgeStore

logger = logging.getLogger(__name__)

# -------------------- Настройки --------------------

# Максимальное количество символов контекста, подаваемого в LLM.
# Ограничение нужно, чтобы не превышать контекстное окно модели.
MAX_CONTEXT_CHARS = int(os.getenv("RAG_MAX_CONTEXT_CHARS", "8000"))


# -------------------- Класс для GigaChat Lite --------------------
class GigaChatLiteLLM:
    """Псевдоним для DeepSeekFlashLLM (обратная совместимость).

    Используется в use_cases/answer.py и ioc.py — при переходе с GigaChat на DeepSeek.
    После полной замены будет удалён.
    """

    def __init__(self):
        self._impl = DeepSeekFlashLLM()

    def invoke(self, prompt: str, max_tokens: int = 256) -> str:
        return self._impl.invoke(prompt, max_tokens=max_tokens)


# -------------------- Функции валидации и обработки --------------------

def is_substantive_answer(question: str, user_answer: str, llm: DeepSeekFlashLLM) -> dict:
    """Проверяет, является ли ответ пользователя содержательным (не мета-комментарий, не пустой)."""
    txt = (user_answer or "").strip()
    low = txt.lower()
    if not txt:
        return {"ok": False, "label": "ПУСТО", "reason": "Пустой ответ."}

    meta_phrases = {
        "я правильно ответил", "я ответил правильно", "правильно ответил",
        "повтори вопрос", "что за вопрос", "ок", "окей", "ладно",
        "как скажешь", "не уверен", "затрудняюсь", "без комментариев"
    }
    if low in meta_phrases:
        return {"ok": False, "label": "МЕТА", "reason": "Мета-комментарий вместо ответа."}
    if len(low.split()) < 3:
        return {"ok": False, "label": "МЕТА", "reason": "Слишком коротко для осмысленного ответа."}

    def to_tokens(s: str) -> set[str]:
        toks = {t for t in re.findall(r"[А-Яа-яA-Za-z0-9\-]+", s.lower()) if len(t) >= 3}
        stop = {"и", "или", "на", "по", "при", "с", "в", "о", "об", "для", "что", "как", "каков", "какие", "какой",
                "кто", "это", "тот", "так"}
        return {t for t in toks if t not in stop}

    q_tokens = to_tokens(question)
    a_tokens = to_tokens(txt)
    domain_allow = {"вирус", "гепатит", "вгв", "вгс", "вич", "контагиозн", "устойчив"}
    candidate_answer = bool((q_tokens & a_tokens) or (a_tokens & domain_allow))

    prompt = f"""Ты — строгий валидатор формы ответа.
Определи, является ли ТЕКСТ ПОЛЬЗОВАТЕЛЯ содержательным ответом на ВОПРОС.
Верни строго JSON одной строкой: {{"label":"ОТВЕТ|МЕТА|НЕ ПО ТЕМЕ|ПУСТО","explanation":"кратко почему"}}
ВОПРОС: \"\"\"{question}\"\"\"
ТЕКСТ ПОЛЬЗОВАТЕЛЯ: \"\"\"{user_answer}\"\"\""""

    try:
        raw = llm.invoke(prompt, max_tokens=128)
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if m:
            data = json.loads(m.group(0))
            label_text = str(data.get("label", "")).upper()
            explanation = str(data.get("explanation", ""))
        else:
            label_text = raw.strip().upper()
            explanation = "Формат не распознан"
    except (RuntimeError, json.JSONDecodeError) as e:
        logger.warning("LLM validation failed for answer, using heuristic fallback: %s", e)
        if candidate_answer:
            return {"ok": True, "label": "ОТВЕТ", "reason": "Фолбэк на доменную эвристику."}
        return {"ok": False, "label": "ОШИБКА", "reason": "Сбой LLM."}

    tokens = {t for t in re.split(r"[|,;\\s]+", label_text) if t}
    negative = {"ПУСТО", "МЕТА", "НЕПОТЕМЕ", "НЕ_ПО_ТЕМЕ", "OFFTOP"}
    is_answer = ("ОТВЕТ" in tokens) and tokens.isdisjoint(negative)

    if not is_answer and candidate_answer:
        return {"ok": True, "label": "ОТВЕТ", "reason": "Доменное совпадение."}

    return {"ok": is_answer, "label": label_text, "reason": explanation}


def extract_assertions(text: str, llm: DeepSeekFlashLLM) -> list[str]:
    """Разбивает ответ пользователя на отдельные утверждения (факты)."""
    prompt = f"""Разбей текст на отдельные проверяемые факты.
Верни строго JSON-массив строк без пояснений и без Markdown.
Если текст содержит один факт, верни массив из одной строки.

ТЕКСТ:
{text}"""
    try:
        response = llm.invoke(prompt, max_tokens=512)
        assertions = _parse_assertions_response(response)
        return assertions or [text]
    except (RuntimeError, json.JSONDecodeError) as e:
        logger.warning("Failed to extract assertions, using original text: %s", e)
        return [text]


def _parse_assertions_response(response: str) -> list[str]:
    raw = response.strip()
    parsed = None
    if raw.startswith("["):
        parsed = json.loads(raw)
    else:
        match = re.search(r"\[[\s\S]*\]", raw)
        if match:
            parsed = json.loads(match.group(0))

    if isinstance(parsed, list):
        return _clean_assertion_lines(str(item) for item in parsed)
    return _clean_assertion_lines(raw.splitlines())


def _clean_assertion_lines(lines) -> list[str]:
    assertions = []
    service_prefixes = (
        "вот текст",
        "разбитый на",
        "отдельные факты",
        "факты:",
        "json",
    )
    for line in lines:
        value = str(line).strip()
        value = re.sub(r"^\s*[-*•]\s*", "", value)
        value = re.sub(r"^\s*\d+[.)]\s*", "", value)
        value = value.strip(" \t\r\n\"'")
        if not value:
            continue
        lowered = value.lower()
        if any(lowered.startswith(prefix) for prefix in service_prefixes):
            continue
        if lowered in {"[", "]"}:
            continue
        assertions.append(value)
    return assertions


def _check_response_against_context(
    *,
    question: str,
    response_text: str,
    context: str,
    model: DeepSeekFlashLLM,
    partial: bool = False,
) -> tuple[bool | None, str]:
    if partial:
        assessment_instruction = """Оцени только фактическую корректность ФРАГМЕНТА ответа.
Фрагмент не обязан полностью отвечать на вопрос, если он является частью перечисления или частью более длинного ответа.
Если фрагмент является неполной, но верной частью ответа и не противоречит контексту — считай его верным.
Считай фрагмент неверным только если он противоречит контексту, содержит существенную неподтвержденную информацию или не относится к вопросу."""
        answer_label = "ФРАГМЕНТ ОТВЕТА СТУДЕНТА"
    else:
        assessment_instruction = """Оцени, верен ли ответ студента на основании контекста.
Ответ должен передавать ключевые факты правильно, дословное совпадение не требуется.
Учитывай условия, уже заданные в формулировке вопроса: ответ не обязан повторять группу риска, сценарий или объект, если они явно названы в вопросе.
Для вопросов, где просят написать схему цифрами, достаточно корректной цифровой последовательности.
Если ответ содержит правильную суть — считай его верным."""
        answer_label = "ОТВЕТ СТУДЕНТА"

    prompt = f"""Ты — строгий экзаменатор по эпидемиологии и санитарным нормам.

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{context}

ВОПРОС: {question}
{answer_label}: {response_text}

{assessment_instruction}

    Верни JSON одной строкой: {{"verdict": "ВЕРНО", "explanation": "..."}} или {{"verdict": "НЕВЕРНО", "explanation": "..."}}"""
    try:
        raw = model.invoke(prompt, max_tokens=256)
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if m:
            try:
                data = json.loads(m.group(0))
                verdict = str(data.get("verdict", "")).upper()
                explanation = str(data.get("explanation", ""))
                if "НЕВЕРНО" in verdict:
                    return False, explanation
                if "ВЕРНО" in verdict:
                    return True, explanation
                return None, explanation or raw
            except json.JSONDecodeError:
                pass
        raw_upper = raw.upper()
        if "НЕВЕРНО" in raw_upper:
            return False, raw
        if "ВЕРНО" in raw_upper:
            return True, raw
        if "нет" in raw.lower():
            return False, raw
        return True, raw
    except RuntimeError as e:
        logger.error("LLM context check failed: %s", e)
        return None, str(e)


def check_response_against_expected(
    *,
    question: str,
    response_text: str,
    expected_answer: str,
    model: DeepSeekFlashLLM,
) -> tuple[bool | None, str]:
    prompt = f"""Ты — строгий экзаменатор по эпидемиологии.
Сравни ОТВЕТ СТУДЕНТА с ЭТАЛОННЫМ ОТВЕТОМ на конкретный вопрос.
Дословное совпадение не требуется: принимай переформулировки, синонимы и другой порядок фактов.
Считай ответ верным, если он передает все ключевые факты эталона без существенных ошибок.
Считай ответ неверным, если отсутствует важный факт, есть противоречие или ответ уходит от вопроса.

ВОПРОС: {question}
ЭТАЛОННЫЙ ОТВЕТ: {expected_answer}
ОТВЕТ СТУДЕНТА: {response_text}

Верни JSON одной строкой: {{"verdict": "ВЕРНО", "explanation": "..."}} или {{"verdict": "НЕВЕРНО", "explanation": "..."}}"""
    try:
        raw = model.invoke(prompt, max_tokens=256)
        m = re.search(r"\{.*\}", raw, flags=re.S)
        if m:
            try:
                data = json.loads(m.group(0))
                verdict = str(data.get("verdict", "")).upper()
                explanation = str(data.get("explanation", ""))
                if "НЕВЕРНО" in verdict:
                    return False, explanation
                if "ВЕРНО" in verdict:
                    return True, explanation
                return None, explanation or raw
            except json.JSONDecodeError:
                pass
        raw_upper = raw.upper()
        if "НЕВЕРНО" in raw_upper:
            return False, raw
        if "ВЕРНО" in raw_upper:
            return True, raw
        return None, raw
    except RuntimeError as e:
        logger.error("LLM expected-answer check failed: %s", e)
        return None, str(e)


def decompose_question(question: str, llm: DeepSeekFlashLLM) -> list[str]:
    """Разбивает сложный вопрос на 1-3 простых подвопроса для multi-query поиска."""
    prompt = f"Разбей сложный вопрос на 1-3 простых подвопроса:\n{question}"
    try:
        response = llm.invoke(prompt, max_tokens=256)
        return [line.strip() for line in response.splitlines() if line.strip()]
    except RuntimeError as e:
        logger.warning("Failed to decompose question, using original: %s", e)
        return [question]


def build_answer_search_queries(
    question: str,
    answer: str,
    llm: DeepSeekFlashLLM,
    use_query_decomposition: bool,
) -> list[str]:
    """Build retrieval queries for answer validation.

    The answer can contain compact evidence terms that are absent from the
    question itself, for example vaccination schedules like "0-1-6".
    """
    queries = [
        _compact_search_text(f"{question}\n{answer}", limit=700),
        _compact_search_text(answer, limit=500),
    ]
    if use_query_decomposition:
        queries.extend(decompose_question(question, llm))
    else:
        queries.append(question)
    return _dedupe_queries(queries)


def _compact_search_text(text: str, limit: int) -> str:
    value = " ".join((text or "").split())
    return value[:limit].strip()


def _dedupe_queries(queries: list[str]) -> list[str]:
    result = []
    seen = set()
    for query in queries:
        normalized = query.strip()
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def rerank_chunks(question: str, chunks: list, llm: DeepSeekFlashLLM, top_k: int = 5) -> list:
    """Реранжирование чанков по релевантности вопросу.

    Для каждого чанка запрашиваем у LLM оценку релевантности.
    Фильтруем только релевантные чанки.
    """
    relevant = []
    for chunk in chunks:
        prompt = f"Вопрос: {question}\nТекст: {chunk.page_content}\nРелевантно? (да/нет)"
        try:
            if llm.invoke(prompt, max_tokens=5).lower().startswith("да"):
                relevant.append(chunk)
                if len(relevant) >= top_k:
                    break
        except RuntimeError as e:
            logger.warning("Reranking failed for chunk, skipping: %s", e)
            continue
    return relevant


# -------------------- Основная логика проверки --------------------
def answer_question(
        question: str,
        answer: str,
        model: DeepSeekFlashLLM,
        db: QdrantKnowledgeStore | None = None,
        theme_id: str | None = None,
        theme_title: str | None = None,
        use_assertion_splitting: bool = False,
        use_query_decomposition: bool = False,
        use_reranking: bool = False,
        initial_k: int = 10,
        final_k: int = 5
) -> bool | None:
    """Основная функция проверки ответа студента по базе знаний.

    Args:
        question: Текст вопроса экзамена.
        answer: Текст ответа студента.
        model: Экземпляр DeepSeekFlashLLM для вызовов LLM.
        db: Экземпляр QdrantKnowledgeStore (если None — создаётся локально).
        theme_id: UUID темы для точной фильтрации поиска (опционально).
        theme_title: Название темы для fallback-фильтрации поиска (опционально).
        use_assertion_splitting: Разбивать ли ответ на отдельные утверждения.
        use_query_decomposition: Разбивать ли вопрос на подвопросы.
        use_reranking: Включить ли LLM-реранжирование чанков.
        initial_k: Количество чанков при первичном поиске.
        final_k: Количество чанков после реранжирования.

    Returns:
        True — ответ верный, False — ответ неверный, None — невозможно определить.
    """
    if db is None:
        logger.warning("Qdrant store не передан через DI, создаётся локально. "
                       "Рекомендуется использовать IoC-контейнер.")
        embeddings = GigaChatEmbeddings()
        db = QdrantKnowledgeStore(embeddings)

    # 1. Подготовка запросов
    search_queries = build_answer_search_queries(
        question=question,
        answer=answer,
        llm=model,
        use_query_decomposition=use_query_decomposition,
    )

    # 2. Поиск с опциональной фильтрацией по теме
    search_attempts = []
    if theme_id:
        search_attempts.append(("theme_id", {"k": initial_k, "filter": {"theme_id": str(theme_id)}}))
    if theme_title:
        search_attempts.append(("source_theme", {"k": initial_k, "filter": {"source_theme": theme_title}}))
    search_attempts.append(("unfiltered", {"k": initial_k}))

    def collect_chunks(kwargs: dict) -> list:
        chunks = []
        seen = set()
        for q in search_queries:
            try:
                results = db.similarity_search(q, **kwargs)
            except Exception as e:
                logger.warning("Similarity search failed for query '%s': %s", q, e)
                continue
            for doc in results:
                key = doc.metadata.get("content_hash") or doc.page_content
                if key not in seen:
                    seen.add(key)
                    chunks.append(doc)
        return chunks

    all_chunks = []
    for attempt_name, search_kwargs in search_attempts:
        all_chunks = collect_chunks(search_kwargs)
        if all_chunks:
            if attempt_name != "theme_id" and theme_id:
                logger.warning(
                    "Context not found for theme_id '%s'; using %s Qdrant search fallback",
                    theme_id,
                    attempt_name,
                )
            break
        if attempt_name != "unfiltered":
            logger.warning("Context not found using %s filter; retrying next search strategy", attempt_name)

    # 3. Реранжирование
    if use_reranking and all_chunks:
        all_chunks = rerank_chunks(question, all_chunks, model, top_k=final_k)

    if not all_chunks:
        logger.warning("Контекст не найден для вопроса: %s", question[:80])
        return None

    # 4. Формируем контекст с ограничением размера
    context = "\n\n".join([doc.page_content for doc in all_chunks])
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS]
        logger.debug("Контекст обрезан до %d символов", MAX_CONTEXT_CHARS)

    # 5. Валидация формы ответа
    shape = is_substantive_answer(question, answer, model)
    if not shape["ok"]:
        logger.info("Форма ответа отклонена: %s (%s)", shape['label'], shape['reason'])
        return False

    # 6. Проверка утверждений по контексту с улучшенным промптом
    assertions = extract_assertions(answer, model) if (use_assertion_splitting and len(answer.split()) > 15) else [
        answer]

    check_partial_assertions = len(assertions) > 1
    if check_partial_assertions:
        whole_verdict, whole_explanation = _check_response_against_context(
            question=question,
            response_text=answer,
            context=context,
            model=model,
            partial=False,
        )
        if whole_verdict is True:
            return True
        if whole_verdict is None:
            logger.error("LLM whole-answer check failed: %s", whole_explanation)
            return None  # Невозможно определить — не наказываем студента
        logger.info("Whole answer rejected, checking assertions: %s", whole_explanation)

    for assertion in assertions:
        verdict, explanation = _check_response_against_context(
            question=question,
            response_text=assertion,
            context=context,
            model=model,
            partial=check_partial_assertions,
        )
        if verdict is False:
            logger.info("Assertion rejected: '%s' — %s", assertion[:50], explanation)
            return False
        if verdict is None:
            logger.error("LLM assertion check failed: %s", explanation)
            return None  # Невозможно определить — не наказываем студента

    return True
