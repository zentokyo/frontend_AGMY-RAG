import logging
import re
import json
from src.core.rag.deepseek_llm import DeepSeekFlashLLM
from src.core.rag.ingest import GigaChatEmbeddings
from src.core.rag.qdrant_store import QdrantKnowledgeStore

logger = logging.getLogger(__name__)

# -------------------- Настройки --------------------

# Максимальное количество символов контекста, подаваемого в LLM.
# Ограничение нужно, чтобы не превышать контекстное окно модели.
MAX_CONTEXT_CHARS = 3000


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
    prompt = f"Разбей текст на отдельные факты (по одному на строку):\n{text}"
    try:
        response = llm.invoke(prompt, max_tokens=512)
        return [line.strip() for line in response.splitlines() if line.strip()]
    except RuntimeError as e:
        logger.warning("Failed to extract assertions, using original text: %s", e)
        return [text]


def decompose_question(question: str, llm: DeepSeekFlashLLM) -> list[str]:
    """Разбивает сложный вопрос на 1-3 простых подвопроса для multi-query поиска."""
    prompt = f"Разбей сложный вопрос на 1-3 простых подвопроса:\n{question}"
    try:
        response = llm.invoke(prompt, max_tokens=256)
        return [line.strip() for line in response.splitlines() if line.strip()]
    except RuntimeError as e:
        logger.warning("Failed to decompose question, using original: %s", e)
        return [question]


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
        theme_title: Название темы для фильтрации поиска (опционально).
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
    search_queries = decompose_question(question, model) if use_query_decomposition else [question]

    # 2. Поиск с опциональной фильтрацией по теме
    search_kwargs = {"k": initial_k}
    if theme_title:
        search_kwargs["filter"] = {"source_theme": theme_title}

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

    all_chunks = collect_chunks(search_kwargs)
    if not all_chunks and theme_title:
        logger.warning(
            "Context not found for theme '%s'; retrying Qdrant search without theme filter",
            theme_title,
        )
        all_chunks = collect_chunks({"k": initial_k})

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

    for assertion in assertions:
        prompt = f"""Ты — строгий экзаменатор по эпидемиологии и санитарным нормам.

КОНТЕКСТ ИЗ БАЗЫ ЗНАНИЙ:
{context}

ВОПРОС: {question}
ОТВЕТ СТУДЕНТА: {assertion}

Оцени, верен ли ответ студента на основании контекста.
Ответ должен передавать ключевые факты правильно, дословное совпадение не требуется.
Если ответ содержит правильную суть — считай его верным.

Верни JSON одной строкой: {{"verdict": "ВЕРНО", "explanation": "..."}} или {{"verdict": "НЕВЕРНО", "explanation": "..."}}"""
        try:
            raw = model.invoke(prompt, max_tokens=128)
            m = re.search(r"\{.*\}", raw, flags=re.S)
            if m:
                data = json.loads(m.group(0))
                verdict = str(data.get("verdict", "")).upper()
                explanation = str(data.get("explanation", ""))
                if "НЕВЕРНО" in verdict:
                    logger.info("Assertion rejected: '%s' — %s", assertion[:50], explanation)
                    return False
            else:
                # Фолбэк на простой анализ текста
                if "нет" in raw.lower():
                    return False
        except (RuntimeError, json.JSONDecodeError) as e:
            logger.error("LLM assertion check failed: %s", e)
            return None  # Невозможно определить — не наказываем студента

    return True
