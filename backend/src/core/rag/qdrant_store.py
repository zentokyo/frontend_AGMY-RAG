import logging
import math
import os
import re
import uuid
from typing import Protocol

from langchain_core.documents import Document
from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

QDRANT_URL = os.getenv("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "assistant_knowledge")
VECTOR_SIZE = int(os.getenv("QDRANT_VECTOR_SIZE", "2560"))
UPSERT_BATCH_SIZE = int(os.getenv("QDRANT_UPSERT_BATCH_SIZE", "64"))
DEFAULT_RETRIEVAL_FETCH_K = max(1, int(os.getenv("RAG_RETRIEVAL_FETCH_K", "30")))
HYBRID_RERANK_ENABLED = os.getenv("RAG_HYBRID_RERANK_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
HYBRID_VECTOR_WEIGHT = float(os.getenv("RAG_HYBRID_VECTOR_WEIGHT", "0.78"))
HYBRID_LEXICAL_WEIGHT = float(os.getenv("RAG_HYBRID_LEXICAL_WEIGHT", "0.22"))
MMR_ENABLED = os.getenv("RAG_MMR_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
MMR_LAMBDA = min(1.0, max(0.0, float(os.getenv("RAG_MMR_LAMBDA", "0.82"))))

_TOKEN_RE = re.compile(r"[a-zа-яё0-9]+", flags=re.IGNORECASE)
_STOPWORDS = {
    "а",
    "без",
    "бы",
    "в",
    "во",
    "для",
    "до",
    "его",
    "ее",
    "если",
    "и",
    "или",
    "их",
    "как",
    "какая",
    "какие",
    "какой",
    "каков",
    "когда",
    "кто",
    "на",
    "над",
    "не",
    "но",
    "о",
    "об",
    "от",
    "по",
    "под",
    "при",
    "с",
    "со",
    "так",
    "такое",
    "такой",
    "то",
    "что",
    "the",
    "and",
    "for",
    "from",
    "with",
}
_RUSSIAN_SUFFIXES = (
    "ыми",
    "ими",
    "ого",
    "его",
    "ому",
    "ему",
    "ами",
    "ями",
    "иях",
    "ах",
    "ях",
    "ая",
    "яя",
    "ые",
    "ие",
    "ой",
    "ей",
    "ую",
    "юю",
    "ом",
    "ем",
    "ым",
    "им",
    "ых",
    "их",
    "ов",
    "ев",
    "ия",
    "ий",
    "ый",
    "ой",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "у",
    "ю",
)
_METADATA_TEXT_FIELDS = (
    "source_theme",
    "theme_title",
    "section_title",
    "filename",
    "pdf_title",
    "source",
)


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
        fetch_k: int | None = None,
        rerank: bool | None = None,
        mmr: bool | None = None,
    ) -> list[Document]:
        if k <= 0:
            return []

        use_rerank = HYBRID_RERANK_ENABLED if rerank is None else rerank
        candidate_limit = max(k, fetch_k or DEFAULT_RETRIEVAL_FETCH_K) if use_rerank else k
        vector = self.embeddings.embed_query(query)
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=self._build_filter(filter),
            limit=candidate_limit,
            with_payload=True,
            with_vectors=False,
        )
        documents = [_document_for_point(point) for point in result.points]
        for index, document in enumerate(documents, start=1):
            document.metadata["retrieval_qdrant_rank"] = index

        if not use_rerank:
            return documents[:k]

        return rerank_documents(
            query=query,
            documents=documents,
            k=k,
            use_mmr=MMR_ENABLED if mmr is None else mmr,
        )

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

    def delete_by_metadata(self, key: str, value: str) -> int:
        ids_to_delete = []
        offset = None

        self.ensure_collection()
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                offset=offset,
                with_payload=[key],
                with_vectors=False,
            )
            for point in points:
                payload_value = str((point.payload or {}).get(key, ""))
                if payload_value == str(value):
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


def rerank_documents(
    *,
    query: str,
    documents: list[Document],
    k: int,
    use_mmr: bool = MMR_ENABLED,
) -> list[Document]:
    """Blend Qdrant score with lexical evidence and optionally diversify results."""
    if k <= 0 or not documents:
        return []

    query_tokens = _tokens(query)
    scored = []
    for index, document in enumerate(documents):
        lexical_score = _lexical_score(query_tokens, document)
        vector_score = _vector_score(document)
        hybrid_score = (HYBRID_VECTOR_WEIGHT * vector_score) + (HYBRID_LEXICAL_WEIGHT * lexical_score)
        document.metadata["retrieval_vector_score"] = vector_score
        document.metadata["retrieval_lexical_score"] = lexical_score
        document.metadata["retrieval_hybrid_score"] = hybrid_score
        document.metadata["retrieval_candidate_rank"] = index + 1
        scored.append((document, hybrid_score, _document_tokens(document)))

    scored.sort(key=lambda item: item[1], reverse=True)
    if not use_mmr:
        return [document for document, _, _ in scored[:k]]

    selected: list[tuple[Document, float, set[str]]] = []
    remaining = scored[:]
    while remaining and len(selected) < k:
        best_index = 0
        best_score = -math.inf
        for index, (document, hybrid_score, doc_tokens) in enumerate(remaining):
            redundancy = max(
                (_jaccard(doc_tokens, selected_tokens) for _, _, selected_tokens in selected),
                default=0.0,
            )
            mmr_score = (MMR_LAMBDA * hybrid_score) - ((1.0 - MMR_LAMBDA) * redundancy)
            if mmr_score > best_score:
                best_score = mmr_score
                best_index = index
        document, hybrid_score, doc_tokens = remaining.pop(best_index)
        document.metadata["retrieval_mmr_score"] = best_score
        selected.append((document, hybrid_score, doc_tokens))

    return [document for document, _, _ in selected]


def _collection_vector_size(info) -> int | None:
    vectors = getattr(getattr(getattr(info, "config", None), "params", None), "vectors", None)
    if isinstance(vectors, dict):
        first = next(iter(vectors.values()), None)
        return getattr(first, "size", None)
    return getattr(vectors, "size", None)


def _vector_score(document: Document) -> float:
    try:
        return float(document.metadata.get("qdrant_score") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _lexical_score(query_tokens: set[str], document: Document) -> float:
    if not query_tokens:
        return 0.0

    text_tokens = _document_tokens(document)
    if not text_tokens:
        return 0.0

    overlap = len(query_tokens & text_tokens)
    recall = overlap / len(query_tokens)
    precision = overlap / min(len(text_tokens), 80)

    metadata_tokens = _metadata_tokens(document)
    metadata_recall = len(query_tokens & metadata_tokens) / len(query_tokens) if metadata_tokens else 0.0
    return min(1.0, (0.82 * recall) + (0.08 * precision) + (0.10 * metadata_recall))


def _document_tokens(document: Document) -> set[str]:
    metadata_text = " ".join(str(document.metadata.get(field) or "") for field in _METADATA_TEXT_FIELDS)
    return _tokens(f"{document.page_content}\n{metadata_text}")


def _metadata_tokens(document: Document) -> set[str]:
    metadata_text = " ".join(str(document.metadata.get(field) or "") for field in _METADATA_TEXT_FIELDS)
    return _tokens(metadata_text)


def _tokens(text: str) -> set[str]:
    result = set()
    for raw_token in _TOKEN_RE.findall(text.lower().replace("ё", "е")):
        if raw_token in _STOPWORDS:
            continue
        if len(raw_token) < 3 and not raw_token.isdigit():
            continue
        token = _light_stem(raw_token)
        if token and token not in _STOPWORDS:
            result.add(token)
    return result


def _light_stem(token: str) -> str:
    if token.isdigit() or len(token) <= 5:
        return token
    for suffix in _RUSSIAN_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
