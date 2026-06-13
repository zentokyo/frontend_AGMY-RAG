import argparse
import hashlib
import logging
import os
import re
import threading
import time

import requests
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.rag.qdrant_store import QdrantKnowledgeStore

try:
    from src.core.rag.gigachat_auth import get_gigachat_token, GigaChatAuthError, GIGACHAT_VERIFY_SSL
except ImportError:
    from gigachat_auth import get_gigachat_token, GigaChatAuthError, GIGACHAT_VERIFY_SSL

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base")
DATA_PATH = os.getenv("KB_PATH", DEFAULT_DATA_PATH)
EMBEDDINGS_MODEL = os.getenv("GIGACHAT_EMBEDDINGS_MODEL", "EmbeddingsGigaR")
DEFAULT_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "1200"))
DEFAULT_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
DEFAULT_MIN_CHUNK_CHARS = int(os.getenv("RAG_MIN_CHUNK_CHARS", "40"))
DEFAULT_EMBEDDINGS_BATCH_SIZE = int(os.getenv("GIGACHAT_EMBEDDINGS_BATCH_SIZE", "8"))
EMBEDDINGS_CONCURRENCY = max(1, int(os.getenv("GIGACHAT_EMBEDDINGS_CONCURRENCY", "1")))
EMBEDDINGS_MAX_RETRIES = max(1, int(os.getenv("GIGACHAT_EMBEDDINGS_MAX_RETRIES", "5")))
EMBEDDINGS_RETRY_BASE_SECONDS = float(os.getenv("GIGACHAT_EMBEDDINGS_RETRY_BASE_SECONDS", "1.5"))
DEFAULT_QUERY_INSTRUCTION = "Дан вопрос, необходимо найти абзац текста с ответом\nвопрос: {query}"
QUERY_INSTRUCTION = os.getenv("GIGACHAT_EMBEDDINGS_QUERY_INSTRUCTION", DEFAULT_QUERY_INSTRUCTION).replace("\\n", "\n")
_EMBEDDINGS_SEMAPHORE = threading.Semaphore(EMBEDDINGS_CONCURRENCY)


class GigaChatEmbeddings:
    """Wrapper for GigaChat Embeddings API with auto-refreshing auth token."""

    def __init__(self):
        self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/embeddings"
        self.model = EMBEDDINGS_MODEL

    def _get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {get_gigachat_token()}",
        }

    def embed_query(self, text: str) -> list[float]:
        payload = {"model": self.model, "input": self._format_query(text)}
        data = self._post_embeddings(payload, timeout=30)
        return data["data"][0]["embedding"]

    def embed_documents(self, texts: list[str], batch_size: int = DEFAULT_EMBEDDINGS_BATCH_SIZE) -> list[list[float]]:
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {"model": self.model, "input": batch}
            data = self._post_embeddings(payload, timeout=60)
            all_embeddings.extend([item["embedding"] for item in data["data"]])

        return all_embeddings

    def _format_query(self, text: str) -> str:
        if not QUERY_INSTRUCTION:
            return text
        return QUERY_INSTRUCTION.replace("{query}", text)

    def _post_embeddings(self, payload: dict, timeout: int) -> dict:
        last_response_text = ""
        for attempt in range(EMBEDDINGS_MAX_RETRIES):
            with _EMBEDDINGS_SEMAPHORE:
                response = requests.post(
                    self.api_url,
                    headers=self._get_headers(),
                    json=payload,
                    verify=GIGACHAT_VERIFY_SSL,
                    timeout=timeout,
                )

            if response.status_code == 200:
                return response.json()

            last_response_text = response.text
            if response.status_code not in {429, 500, 502, 503, 504}:
                logger.error("GigaChat Embeddings error: %s", response.text)
                raise RuntimeError(f"GigaChat Error: {response.text}")

            if attempt == EMBEDDINGS_MAX_RETRIES - 1:
                break

            delay = _retry_delay(response, attempt)
            logger.warning(
                "GigaChat Embeddings retry %d/%d after HTTP %d in %.1fs",
                attempt + 1,
                EMBEDDINGS_MAX_RETRIES,
                response.status_code,
                delay,
            )
            time.sleep(delay)

        logger.error("GigaChat Embeddings error after retries: %s", last_response_text)
        raise RuntimeError(f"GigaChat Error: {last_response_text}")


def _retry_delay(response: requests.Response, attempt: int) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return EMBEDDINGS_RETRY_BASE_SECONDS * (2 ** attempt)


def _compute_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _semantic_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def load_documents(data_path: str = DATA_PATH) -> list[Document]:
    """Load Markdown documents from the knowledge base directory."""
    documents = []
    if not os.path.exists(data_path):
        logger.error("Knowledge base directory not found: %s", data_path)
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
                logger.info(
                    "Loaded document: %s (%d chars)",
                    file,
                    sum(len(d.page_content) for d in file_docs),
                )
            except Exception as exc:
                logger.error("Failed to load document %s: %s", file_path, exc)

    logger.info("Loaded %d documents from %s", len(documents), data_path)
    return documents


def split_text(
    documents: list[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        add_start_index=True,
        separators=[
            "\n# ",
            "\n## ",
            "\n### ",
            "\n#### ",
            "\n\n",
            "\n",
            ". ",
            "; ",
            ", ",
            " ",
            "",
        ],
    )

    chunks = text_splitter.split_documents(documents)
    unique_chunks = []
    seen_hashes = set()
    source_chunk_indexes: dict[str, int] = {}
    total_semantic_chars = sum(len(_semantic_text(document.page_content)) for document in documents)

    for chunk in chunks:
        if total_semantic_chars >= DEFAULT_MIN_CHUNK_CHARS:
            if len(_semantic_text(chunk.page_content)) < DEFAULT_MIN_CHUNK_CHARS:
                continue
        source_key = str(chunk.metadata.get("file_id") or chunk.metadata.get("source") or "")
        hash_basis = f"{source_key}\n{chunk.page_content}" if source_key else chunk.page_content
        chunk_hash = _compute_hash(hash_basis)
        if chunk_hash in seen_hashes:
            continue
        seen_hashes.add(chunk_hash)
        chunk.metadata["content_hash"] = chunk_hash
        chunk.metadata["chunk_index"] = len(unique_chunks)
        chunk.metadata["source_chunk_index"] = source_chunk_indexes.get(source_key, 0)
        chunk.metadata["chunk_chars"] = len(chunk.page_content)
        if "page_start" not in chunk.metadata and "page" in chunk.metadata:
            chunk.metadata["page_start"] = chunk.metadata["page"]
        if "page_end" not in chunk.metadata and "page" in chunk.metadata:
            chunk.metadata["page_end"] = chunk.metadata["page"]
        source_chunk_indexes[source_key] = source_chunk_indexes.get(source_key, 0) + 1
        unique_chunks.append(chunk)

    logger.info("Split into %d unique chunks from %d raw chunks", len(unique_chunks), len(chunks))
    return unique_chunks


def save_to_qdrant(chunks: list[Document], incremental: bool = True) -> int:
    store = QdrantKnowledgeStore(GigaChatEmbeddings())
    if not incremental:
        store.recreate_collection()
    return store.upsert_documents(chunks, incremental=incremental)


def delete_document_chunks(source_path: str) -> int:
    store = QdrantKnowledgeStore(GigaChatEmbeddings())
    try:
        deleted = store.delete_by_source(source_path)
        logger.info("Deleted %d Qdrant chunks for source: %s", deleted, source_path)
        return deleted
    except Exception as exc:
        logger.error("Failed to delete Qdrant chunks for %s: %s", source_path, exc)
        return 0


def generate_data_store(incremental: bool = False) -> int:
    documents = load_documents()
    if not documents:
        logger.error("No documents to ingest")
        return 0

    chunks = split_text(documents)
    return save_to_qdrant(chunks, incremental=incremental)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ASMU knowledge base into Qdrant")
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only add chunks that are not already present by content_hash",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    total = generate_data_store(incremental=args.incremental)
    logger.info("[SUCCESS] Qdrant ingest finished: %d chunks written", total)


if __name__ == "__main__":
    main()
