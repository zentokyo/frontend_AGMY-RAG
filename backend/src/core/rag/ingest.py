import hashlib
import os
import logging
import re
import requests
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

try:
    from src.core.rag.gigachat_auth import get_gigachat_token, GigaChatAuthError, GIGACHAT_VERIFY_SSL
except ImportError:
    from gigachat_auth import get_gigachat_token, GigaChatAuthError, GIGACHAT_VERIFY_SSL

load_dotenv()

logger = logging.getLogger(__name__)

CHROMA_PATH = "src/core/rag/db_metadata_v5"
DATA_PATH = "knowledge_base"


class GigaChatEmbeddings:
    """Обёртка для GigaChat Embeddings API.

    Токен обновляется автоматически через get_gigachat_token().
    Поддерживает batch-обработку для embed_documents.
    """

    def __init__(self):
        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/embeddings"

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_gigachat_token()}"
        }

    def embed_query(self, text: str) -> list[float]:
        """Получить эмбеддинг для одного текстового запроса."""
        payload = {"model": "Embeddings", "input": text}
        response = requests.post(
            self.api_url, headers=self._get_headers(),
            json=payload, verify=GIGACHAT_VERIFY_SSL, timeout=30,
        )
        if response.status_code != 200:
            logger.error("GigaChat Embeddings error: %s", response.text)
            raise RuntimeError(f"GigaChat Error: {response.text}")
        return response.json()["data"][0]["embedding"]

    def embed_documents(self, texts: list[str], batch_size: int = 8) -> list[list[float]]:
        """Получить эмбеддинги для списка документов пакетами."""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {"model": "Embeddings", "input": batch}
            response = requests.post(
                self.api_url, headers=self._get_headers(),
                json=payload, verify=GIGACHAT_VERIFY_SSL, timeout=60,
            )

            if response.status_code != 200:
                logger.error("GigaChat Embeddings batch error: %s", response.text)
                raise RuntimeError(f"GigaChat Error: {response.text}")
            all_embeddings.extend([item["embedding"] for item in response.json()["data"]])

        return all_embeddings


def _compute_hash(text: str) -> str:
    """Вычислить SHA-256 хеш текста для дедупликации."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_documents(data_path: str = DATA_PATH) -> list[Document]:
    """Загрузить все Markdown-документы из директории базы знаний.

    Для каждого документа сохраняет метаданные:
    - source: путь к исходному файлу
    - source_theme: имя файла без расширения (используется для фильтрации при поиске)
    """
    documents = []
    if not os.path.exists(data_path):
        logger.error("Директория базы знаний не найдена: %s", data_path)
        return documents

    for root, _, files in os.walk(data_path):
        for file in files:
            if not file.endswith(".md"):
                continue
            file_path = os.path.join(root, file)
            try:
                loader = TextLoader(file_path, encoding="utf-8")
                file_docs = loader.load()
                # Добавляем метаданные для фильтрации по теме
                theme_name = os.path.splitext(file)[0]
                for doc in file_docs:
                    doc.metadata["source"] = file_path
                    doc.metadata["source_theme"] = theme_name
                documents.extend(file_docs)
                logger.info("Загружен документ: %s (%d символов)", file, sum(len(d.page_content) for d in file_docs))
            except Exception as e:
                logger.error("Ошибка загрузки документа %s: %s", file_path, e)

    logger.info("Всего загружено %d документов из %s", len(documents), data_path)
    return documents


def split_text(documents: list[Document], chunk_size: int = 450, chunk_overlap: int = 100) -> list[Document]:
    """Разбить документы на чанки с помощью RecursiveCharacterTextSplitter.

    Метаданные source и source_theme наследуются от родительского документа.
    Каждому чанку добавляется уникальный hash для дедупликации.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
    )

    chunks = text_splitter.split_documents(documents)

    # Дедупликация и добавление хешей
    unique_chunks = []
    seen_hashes = set()
    for chunk in chunks:
        chunk_hash = _compute_hash(chunk.page_content)
        if chunk_hash not in seen_hashes:
            seen_hashes.add(chunk_hash)
            chunk.metadata["content_hash"] = chunk_hash
            unique_chunks.append(chunk)

    logger.info("Разбито на %d уникальных чанков (из %d до дедупликации)", len(unique_chunks), len(chunks))
    return unique_chunks


def save_to_chroma(chunks: list[Document], incremental: bool = True):
    """Сохранить чанки в ChromaDB.

    Args:
        chunks: Список документов-чанков для сохранения.
        incremental: Если True — добавляет только новые чанки (по hash).
                     Если False — полностью пересоздаёт базу.
    """
    os.makedirs(os.path.dirname(CHROMA_PATH) or ".", exist_ok=True)

    try:
        embedding_function = GigaChatEmbeddings()

        if incremental and os.path.exists(CHROMA_PATH):
            db = Chroma(
                persist_directory=CHROMA_PATH,
                embedding_function=embedding_function,
                collection_metadata={"hnsw:space": "cosine"},
            )

            # Получаем существующие хеши
            existing = db.get(include=[])
            existing_ids = set(existing.get("ids", []))

            # Фильтруем только новые чанки
            new_chunks = []
            for chunk in chunks:
                chunk_id = chunk.metadata.get("content_hash", _compute_hash(chunk.page_content))
                if chunk_id not in existing_ids:
                    new_chunks.append(chunk)

            if not new_chunks:
                logger.info("Все чанки уже в базе, нечего добавлять.")
                return

            # Добавляем новые чанки с хешами как IDs
            db.add_documents(
                new_chunks,
                ids=[c.metadata.get("content_hash", _compute_hash(c.page_content)) for c in new_chunks],
            )
            logger.info("[SUCCESS] Добавлено %d новых чанков в %s (инкрементально)", len(new_chunks), CHROMA_PATH)
        else:
            # Полное пересоздание базы
            import shutil
            if os.path.exists(CHROMA_PATH):
                shutil.rmtree(CHROMA_PATH)

            chunk_ids = [c.metadata.get("content_hash", _compute_hash(c.page_content)) for c in chunks]
            db = Chroma.from_documents(
                documents=chunks,
                embedding=embedding_function,
                persist_directory=CHROMA_PATH,
                ids=chunk_ids,
                collection_metadata={"hnsw:space": "cosine"},
            )
            logger.info("[SUCCESS] Сохранено %d чанков в %s (полное пересоздание)", len(chunks), CHROMA_PATH)
    except Exception as e:
        logger.error("[ERROR] Ошибка Chroma: %s", e)
        raise


def delete_document_chunks(source_path: str):
    """Удалить все чанки, связанные с конкретным документом.

    Args:
        source_path: Путь к исходному файлу или его часть для поиска в metadata.source.
    """
    if not os.path.exists(CHROMA_PATH):
        logger.warning("ChromaDB не найдена: %s", CHROMA_PATH)
        return 0

    try:
        embedding_function = GigaChatEmbeddings()
        db = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_function)

        # Получаем все документы и фильтруем по source
        results = db.get(include=["metadatas"])
        ids_to_delete = []
        for doc_id, metadata in zip(results["ids"], results["metadatas"]):
            source = metadata.get("source", "")
            if source_path in source:
                ids_to_delete.append(doc_id)

        if ids_to_delete:
            db._collection.delete(ids=ids_to_delete)
            logger.info("Удалено %d чанков для документа: %s", len(ids_to_delete), source_path)
        else:
            logger.info("Чанки для документа не найдены: %s", source_path)

        return len(ids_to_delete)
    except Exception as e:
        logger.error("Ошибка удаления чанков: %s", e)
        return 0


def generate_data_store():
    """Полный пайплайн: загрузка → разбиение → сохранение в ChromaDB."""
    documents = load_documents()
    if not documents:
        logger.error("Нет документов для обработки!")
        return
    chunks = split_text(documents)
    save_to_chroma(chunks, incremental=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    generate_data_store()
