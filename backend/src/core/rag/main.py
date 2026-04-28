import random
import requests
import re
import json
from langchain_chroma import Chroma
from dotenv import load_dotenv
from src.core.rag.ingest import GigaChatEmbeddings  # Импорт согласно вашему проекту

# -------------------- Настройки --------------------
load_dotenv()

CHROMA_PATH = "src/core/rag/db_metadata_v5"

QUESTIONS = [
    "Что понимается под термином «гемоконтактные инфекции» в профессиональном риске медицинских работников?",
]


# -------------------- Класс для GigaChat Lite --------------------
class GigaChatLiteLLM:
    def __init__(self):
        from src.core.rag.gigachat_auth import get_gigachat_token, GigaChatAuthError
        try:
            self.token = get_gigachat_token()
        except GigaChatAuthError as e:
            raise RuntimeError(f"[GigaChatAuthError] {e}")

        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }

    def invoke(self, prompt: str, max_tokens: int = 256) -> str:
        payload = {
            "model": "GigaChat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": max_tokens
        }
        response = requests.post(self.api_url, headers=self.headers, json=payload, verify=False)
        if response.status_code != 200:
            raise RuntimeError(f"[GigaChat Error] {response.status_code}: {response.text}")
        return response.json()["choices"][0]["message"]["content"].strip()


# -------------------- Функции валидации и обработки --------------------

def is_substantive_answer(question: str, user_answer: str, llm: GigaChatLiteLLM) -> dict:
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
    except Exception:
        if candidate_answer:
            return {"ok": True, "label": "ОТВЕТ", "reason": "Фолбэк на доменную эвристику."}
        return {"ok": False, "label": "ОШИБКА", "reason": "Сбой LLM."}

    tokens = {t for t in re.split(r"[|,;\\s]+", label_text) if t}
    negative = {"ПУСТО", "МЕТА", "НЕПОТЕМЕ", "НЕ_ПО_ТЕМЕ", "OFFTOP"}
    is_answer = ("ОТВЕТ" in tokens) and tokens.isdisjoint(negative)

    if not is_answer and candidate_answer:
        return {"ok": True, "label": "ОТВЕТ", "reason": "Доменное совпадение."}

    return {"ok": is_answer, "label": label_text, "reason": explanation}


def extract_assertions(text: str, llm: GigaChatLiteLLM) -> list[str]:
    prompt = f"Разбей текст на отдельные факты (по одному на строку):\n{text}"
    response = llm.invoke(prompt, max_tokens=512)
    return [line.strip() for line in response.splitlines() if line.strip()]


def decompose_question(question: str, llm: GigaChatLiteLLM) -> list[str]:
    prompt = f"Разбей сложный вопрос на 1-3 простых подвопроса:\n{question}"
    response = llm.invoke(prompt, max_tokens=256)
    return [line.strip() for line in response.splitlines() if line.strip()]


def rerank_chunks(question: str, chunks: list, llm: GigaChatLiteLLM, top_k: int = 5) -> list:
    relevant = []
    for chunk in chunks:
        prompt = f"Вопрос: {question}\nТекст: {chunk.page_content}\nРелевантно? (да/нет)"
        if llm.invoke(prompt, max_tokens=5).lower().startswith("да"):
            relevant.append(chunk)
            if len(relevant) >= top_k: break
    return relevant


# -------------------- Основная логика проверки --------------------
def answer_question(
        question: str,
        answer: str,
        model: GigaChatLiteLLM,
        use_assertion_splitting: bool = False,
        use_query_decomposition: bool = False,
        use_reranking: bool = False,
        initial_k: int = 10,
        final_k: int = 5
) -> bool | None:
    # ИСПРАВЛЕННЫЙ ВЫЗОВ: Создаем экземпляр класса эмбеддингов
    # В новом ingest.py GigaChatEmbeddings должен наследоваться от langchain.embeddings.base.Embeddings
    embeddings = GigaChatEmbeddings()

    # Передаем объект напрямую в Chroma
    db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embeddings)

    # 1. Подготовка запросов
    search_queries = decompose_question(question, model) if use_query_decomposition else [question]

    # 2. Поиск
    all_chunks = []
    seen = set()
    for q in search_queries:
        results = db.similarity_search(q, k=initial_k)
        for doc in results:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                all_chunks.append(doc)

    # 3. Реранжирование
    if use_reranking and all_chunks:
        all_chunks = rerank_chunks(question, all_chunks, model, top_k=final_k)

    if not all_chunks:
        print("⚠️ Контекст не найден.")
        return None

    context = "\n\n".join([doc.page_content for doc in all_chunks])

    # 4. Валидация формы
    shape = is_substantive_answer(question, answer, model)
    if not shape["ok"]:
        print(f"❌ Форма ответа отклонена: {shape['label']} ({shape['reason']})")
        return False

    # 5. Проверка утверждений
    assertions = extract_assertions(answer, model) if (use_assertion_splitting and len(answer.split()) > 15) else [
        answer]

    for assertion in assertions:
        prompt = f"КОНТЕКСТ:\n{context}\n\nВОПРОС: {question}\nОТВЕТ: {assertion}\n\nВерно по контексту? (да/нет)"
        try:
            res = model.invoke(prompt, max_tokens=10).lower()
            if "нет" in res:
                return False
        except:
            return False

    return True
