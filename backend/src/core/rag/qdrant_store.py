import logging
import os
import uuid
from typing import Protocol

from langchain_core.documents import Document
from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "assistant_knowledge")
VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "2560"))
UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "64"))


class Embeddings(Protocol):
    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_documents(self, texts: list[str], batch_size: int = 8) -> list[list[float]]:
        ...


class QdrantKnowledgeStore:
    """Small adapter that gives the RAG core a vector search interface."""

    def __init__(
        self,
        embeddings: Embeddings,
        url: str | None = None,
        collection_name: str | None = None,
        vector_size: int = VECTOR_SIZE,
    ):
        self.embeddings = embeddings
        self.url = (url or QDRANT_URL).rstrip("/")
        self.collection_name = collection_name or QDRANT_COLLECTION
        self.vector_size = vector_size
        self.client = QdrantClient(url=self.url)

    def ensure_collection(self) -> None:
        try:
            info = self.client.get_collection(self.collection_name)
            current_size = _collection_vector_size(info)
            if current_size and current_size != self.vector_size:
                raise RuntimeError(
                    f"Qdrant collection '{self.collection_name}' has vector size {current_size}, "
                    f"but current embedding model expects {self.vector_size}. "
                    "Run a full Qdrant reindex to recreate the collection."
                )
            return
        except RuntimeError:
            raise
        except Exception:
            logger.info(
                "Qdrant collection '%s' not found, creating it at %s",
                self.collection_name,
                self.url,
            )

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(
                size=self.vector_size,
                distance=models.Distance.COSINE,
            ),
        )

    def recreate_collection(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
            logger.info("Deleted Qdrant collection '%s'", self.collection_name)
        except Exception as exc:
            logger.info("Qdrant collection '%s' was not deleted: %s", self.collection_name, exc)
        self.ensure_collection()

    def existing_content_hashes(self) -> set[str]:
        hashes: set[str] = set()
        offset = None

        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=["content_hash"],
                with_vectors=False,
            )
            for point in points:
                content_hash = (point.payload or {}).get("content_hash")
                if content_hash:
                    hashes.add(str(content_hash))
            if offset is None:
                break

        return hashes

    def upsert_documents(self, documents: list[Document], incremental: bool = True) -> int:
        if not documents:
            return 0

        self.ensure_collection()
        existing_hashes = self.existing_content_hashes() if incremental else set()

        new_documents = []
        for document in documents:
            content_hash = str(document.metadata.get("content_hash") or _stable_text_hash(document.page_content))
            document.metadata["content_hash"] = content_hash
            if content_hash not in existing_hashes:
                new_documents.append(document)

        if not new_documents:
            logger.info("All chunks are already indexed in Qdrant")
            return 0

        texts = [document.page_content for document in new_documents]
        vectors = self.embeddings.embed_documents(texts)

        total = 0
        for start in range(0, len(new_documents), UPSERT_BATCH_SIZE):
            batch_documents = new_documents[start:start + UPSERT_BATCH_SIZE]
            batch_vectors = vectors[start:start + UPSERT_BATCH_SIZE]
            points = [
                models.PointStruct(
                    id=_point_id_for_hash(self.collection_name, str(document.metadata["content_hash"])),
                    vector=vector,
                    payload=_payload_for_document(document),
                )
                for document, vector in zip(batch_documents, batch_vectors)
            ]
            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
                wait=True,
            )
            total += len(points)

        logger.info("Upserted %d chunks into Qdrant collection '%s'", total, self.collection_name)
        return total

    def similarity_search(
        self,
        query: str,
        k: int = 10,
        filter: dict | models.Filter | None = None,
    ) -> list[Document]:
        vector = self.embeddings.embed_query(query)
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=self._build_filter(filter),
            limit=k,
            with_payload=True,
            with_vectors=False,
        )
        return [_document_for_point(point) for point in result.points]

    def delete_by_source(self, source_identifier: str) -> int:
        ids_to_delete = []
        offset = None

        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=["source"],
                with_vectors=False,
            )
            for point in points:
                source = str((point.payload or {}).get("source", ""))
                if source_identifier in source:
                    ids_to_delete.append(point.id)
            if offset is None:
                break

        if not ids_to_delete:
            return 0

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(points=ids_to_delete),
            wait=True,
        )
        return len(ids_to_delete)

    def _build_filter(self, metadata_filter: dict | models.Filter | None) -> models.Filter | None:
        if metadata_filter is None:
            return None
        if isinstance(metadata_filter, models.Filter):
            return metadata_filter

        conditions = []
        for key, value in metadata_filter.items():
            if value is None:
                continue
            conditions.append(
                models.FieldCondition(
                    key=str(key),
                    match=models.MatchValue(value=value),
                )
            )

        if not conditions:
            return None
        return models.Filter(must=conditions)


def _stable_text_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _point_id_for_hash(collection_name: str, content_hash: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection_name}:{content_hash}"))


def _payload_for_document(document: Document) -> dict:
    payload = dict(document.metadata)
    payload["text"] = document.page_content
    return payload


def _document_for_point(point) -> Document:
    payload = dict(point.payload or {})
    text = str(payload.pop("text", ""))
    metadata = payload
    metadata["qdrant_id"] = str(point.id)
    metadata["qdrant_score"] = point.score
    return Document(page_content=text, metadata=metadata)


def _collection_vector_size(info) -> int | None:
    vectors = getattr(getattr(getattr(info, "config", None), "params", None), "vectors", None)
    if isinstance(vectors, dict):
        first = next(iter(vectors.values()), None)
        return getattr(first, "size", None)
    return getattr(vectors, "size", None)
