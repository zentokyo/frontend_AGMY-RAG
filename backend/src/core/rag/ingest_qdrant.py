#!/usr/bin/env python3
"""
Ingest документов в Qdrant.

Загружает .md файлы из knowledge_base, разбивает на чанки,
векторизует через GigaChat Embeddings, сохраняет в Qdrant.

Использование:
  python3 ingest_qdrant.py                         # полная переиндексация
  python3 ingest_qdrant.py --incremental            # добавить только новые

Переменные окружения:
  QDRANT_URL          — URL Qdrant (по умолч. http://localhost:6333)
  QDRANT_COLLECTION   — имя коллекции (по умолч. assistant_knowledge)
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Пути (относительно backend/) ──────────────────────────────────────────
DATA_PATH = os.getenv(
    "KB_PATH",
    os.path.join(os.path.dirname(__file__), "knowledge_base")
)

# ── Qdrant ────────────────────────────────────────────────────────────────
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333").rstrip("/")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "assistant_knowledge")
VECTOR_SIZE = 1024  # GigaChat Embeddings (EmbeddingsGigaR)

# ── GigaChat Embeddings ───────────────────────────────────────────────────
try:
    from src.core.rag.ingest import GigaChatEmbeddings
except ImportError:
    # Прямой импорт, если запускаем из директории backend/
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.core.rag.ingest import GigaChatEmbeddings


# ── HTTP-утилиты для Qdrant REST API ──────────────────────────────────────

def _qdrant_request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{QDRANT_URL}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        logger.error("Qdrant HTTP %d: %s", e.code, e.read().decode())
        raise
    except urllib.error.URLError as e:
        logger.error("Qdrant connection error: %s", e)
        raise


def ensure_collection():
    """Создать коллекцию, если не существует."""
    try:
        resp = _qdrant_request("GET", f"/collections/{QDRANT_COLLECTION}")
        logger.info("Коллекция '%s' уже существует (%d точек)",
                    QDRANT_COLLECTION, resp.get("result", {}).get("points_count", 0))
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        body = {
            "name": QDRANT_COLLECTION,
            "vectors": {
                "size": VECTOR_SIZE,
                "distance": "Cosine",
            },
        }
        _qdrant_request("PUT", f"/collections/{QDRANT_COLLECTION}", body)
        logger.info("Коллекция '%s' создана (dim=%d)", QDRANT_COLLECTION, VECTOR_SIZE)


def upsert_points(points: list[dict]):
    """Вставить/обновить точки пачками (batch by 64)."""
    BATCH = 64
    for i in range(0, len(points), BATCH):
        batch = points[i:i + BATCH]
        body = {
            "wait": True,
            "points": batch,
        }
        _qdrant_request("PUT", f"/collections/{QDRANT_COLLECTION}/points", body)
    logger.info("Загружено %d точек в Qdrant", len(points))


def get_existing_hashes() -> set[str]:
    """Получить список content_hash уже в коллекции."""
    hashes = set()
    offset = None
    while True:
        body = {
            "limit": 5000,
            "with_payload": ["content_hash"],
            "with_vector": False,
        }
        if offset:
            body["offset"] = offset
        resp = _qdrant_request("POST", f"/collections/{QDRANT_COLLECTION}/points/scroll", body)
        points = resp.get("result", {}).get("points", [])
        if not points:
            break
        for p in points:
            h = p.get("payload", {}).get("content_hash")
            if h:
                hashes.add(h)
        offset = points[-1]["id"]
    return hashes


def delete_all_points():
    """Удалить все точки из коллекции."""
    _qdrant_request("POST", f"/collections/{QDRANT_COLLECTION}/points/delete", {
        "filter": {},
    })
    logger.info("Все точки удалены из коллекции '%s'", QDRANT_COLLECTION)


# ── Обработка документов (идентично ingest.py, только таргет — Qdrant) ────

def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_documents(data_path: str = DATA_PATH):
    """Загрузить .md файлы из директории."""
    from langchain_community.document_loaders import TextLoader
    documents = []
    if not os.path.exists(data_path):
        logger.error("Директория не найдена: %s", data_path)
        return documents
    for root, _, files in os.walk(data_path):
        for file in files:
            if not file.endswith(".md"):
                continue
            file_path = os.path.join(root, file)
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                file_docs = loader.load()
                theme_name = os.path.splitext(file)[0]
                for doc in file_docs:
                    doc.metadata["source"] = file_path
                    doc.metadata["source_theme"] = theme_name
                documents.extend(file_docs)
            except Exception as e:
                logger.error("Ошибка загрузки %s: %s", file_path, e)
    logger.info("Загружено %d документов", len(documents))
    return documents


def split_text(documents, chunk_size: int = 450, chunk_overlap: int = 100):
    """Разбить на чанки с дедупликацией."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    unique = []
    seen = set()
    for chunk in chunks:
        h = _compute_hash(chunk.page_content)
        if h not in seen:
            seen.add(h)
            chunk.metadata["content_hash"] = h
            unique.append(chunk)
    logger.info("Чанков: %d уникальных из %d", len(unique), len(chunks))
    return unique


def main():
    parser = argparse.ArgumentParser(description="Ingest документов в Qdrant")
    parser.add_argument("--incremental", action="store_true",
                        help="Добавить только новые документы")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    # 1. Убедиться, что коллекция существует
    ensure_collection()

    # 2. Загрузить и разбить документы
    docs = load_documents()
    if not docs:
        logger.warning("Нет документов для обработки!")
        return
    chunks = split_text(docs)

    # 3. Получить существующие хеши (инкрементальный режим)
    existing_hashes = set()
    if args.incremental:
        try:
            existing_hashes = get_existing_hashes()
            logger.info("В коллекции уже %d уникальных хешей", len(existing_hashes))
        except Exception:
            logger.warning("Не удалось получить хеши из Qdrant (возможно, коллекция пуста)")

    new_chunks = [
        c for c in chunks
        if c.metadata.get("content_hash") not in existing_hashes
    ]

    if not new_chunks:
        logger.info("Нет новых чанков для добавления")
        return

    if args.incremental:
        logger.info("Новых чанков: %d", len(new_chunks))
    else:
        # Полная переиндексация — очищаем коллекцию
        delete_all_points()
        new_chunks = chunks

    # 4. Векторизация и загрузка
    embeddings = GigaChatEmbeddings()
    texts = [c.page_content for c in new_chunks]

    logger.info("Векторизация %d чанков через GigaChat...", len(texts))
    vectors = embeddings.embed_documents(texts)
    logger.info("Векторизация завершена")

    points = []
    for chunk, vector in zip(new_chunks, vectors):
        points.append({
            "id": chunk.metadata["content_hash"],
            "vector": vector,
            "payload": {
                "text": chunk.page_content,
                "source": chunk.metadata.get("source", ""),
                "source_theme": chunk.metadata.get("source_theme", ""),
                "content_hash": chunk.metadata["content_hash"],
            },
        })

    upsert_points(points)
    logger.info("[SUCCESS] Инжест завершён: %d точек в Qdrant", len(points))


if __name__ == "__main__":
    main()
