import argparse
import asyncio
from dataclasses import dataclass
import logging
import os
import time
import uuid
from typing import Any

from aiobotocore.session import get_session
from botocore.client import Config as ClientConfig
from qdrant_client import models
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import config
from src.core.rag.document_ingestion import (
    DocumentExtractionError,
    extract_documents,
    index_knowledge_file,
    prepare_documents_for_chunking,
)
from src.core.rag.ingest import GigaChatEmbeddings
from src.core.rag.ingest import split_text
from src.core.rag.qdrant_store import QdrantKnowledgeStore

logger = logging.getLogger(__name__)

DEFAULT_REINDEX_CONCURRENCY = int(os.getenv("RAG_ADMIN_REINDEX_CONCURRENCY", "2"))


@dataclass(frozen=True)
class FileIndexResult:
    file_id: str
    chunks: int
    failed: bool


async def reindex_admin_documents(
    recreate_qdrant: bool = False,
    concurrency: int = DEFAULT_REINDEX_CONCURRENCY,
    blue_green: bool = False,
    dry_run: bool = False,
) -> int:
    concurrency = max(1, concurrency)
    engine = create_async_engine(config.postgres.db_url, echo=False)
    staging_collection: str | None = None
    cleanup_store: QdrantKnowledgeStore | None = None
    switched_collection = False

    try:
        async with engine.begin() as connection:
            rows = (
                await connection.execute(
                    text(
                        """
                        SELECT
                          f.file_id,
                          f.filename,
                          f.content_type,
                          t.theme_id,
                          t.title AS theme_title
                        FROM file f
                        JOIN theme_file tf ON tf.file_id = f.file_id
                        JOIN theme t ON t.theme_id = tf.theme_id
                        ORDER BY t.theme_order ASC, f.filename ASC
                        """
                    )
                )
            ).mappings().all()

        if not rows:
            logger.info("No admin documents found for reindex")
            return 0

        store: QdrantKnowledgeStore | None = None
        live_collection = None
        if not dry_run:
            embeddings = GigaChatEmbeddings()
            live_store = QdrantKnowledgeStore(embeddings)
            live_collection = live_store.collection_name
            store = live_store
            cleanup_store = store
        elif blue_green or recreate_qdrant:
            logger.info("Ignoring Qdrant publish/recreate flags because --dry-run is enabled")

        if blue_green and store and live_collection:
            staging_collection = _staging_collection_name(live_collection)
            store = QdrantKnowledgeStore(
                store.embeddings,
                url=store.url,
                collection_name=staging_collection,
                vector_size=store.vector_size,
            )
            cleanup_store = store
            store.recreate_collection()
            logger.info(
                "Blue-green reindex enabled: indexing into staging collection '%s' before publishing '%s'",
                staging_collection,
                live_collection,
            )
        elif recreate_qdrant and store:
            store.recreate_collection()

        indexed_total = 0
        failed_total = 0
        indexed_files: list[FileIndexResult] = []
        s3_session = get_session()
        semaphore = asyncio.Semaphore(concurrency)
        logger.info("Reindexing %d admin documents with concurrency=%d", len(rows), concurrency)
        async with s3_session.create_client(
            "s3",
            endpoint_url=config.minio.s3_url,
            aws_access_key_id=config.minio.user,
            aws_secret_access_key=config.minio.password,
            region_name="us-east-1",
            config=ClientConfig(connect_timeout=50, read_timeout=120),
        ) as s3_client:
            tasks = [
                asyncio.create_task(
                    _index_row(
                        engine,
                        s3_client,
                        row,
                        store,
                        semaphore,
                        defer_status_updates=blue_green or dry_run,
                        delete_existing=not blue_green and not dry_run,
                        dry_run=dry_run,
                    )
                )
                for row in rows
            ]
            for task in asyncio.as_completed(tasks):
                result = await task
                indexed_total += result.chunks
                failed_total += 1 if result.failed else 0
                if not result.failed:
                    indexed_files.append(result)

        if failed_total:
            logger.error(
                "Admin document reindex finished with %d failed files and %d chunks indexed",
                failed_total,
                indexed_total,
            )
            raise RuntimeError(f"{failed_total} admin document(s) failed to index")

        if blue_green and store and live_collection:
            assert staging_collection is not None
            points_count = _collection_points_count(store, staging_collection)
            if points_count is not None and points_count != indexed_total:
                raise RuntimeError(
                    f"Staging collection '{staging_collection}' contains {points_count} points, "
                    f"but {indexed_total} chunks were indexed"
                )
            previous_collection = _publish_staging_collection(store, live_collection, staging_collection)
            switched_collection = True
            for indexed_file in indexed_files:
                await _update_file_status(
                    engine,
                    indexed_file.file_id,
                    "indexed",
                    indexed_chunks=indexed_file.chunks,
                )
            _delete_previous_staging_collection(
                store,
                previous_collection,
                live_collection=live_collection,
                current_staging_collection=staging_collection,
            )

        if dry_run:
            logger.info("Admin document dry-run finished: %d chunks would be indexed", indexed_total)
        else:
            logger.info("Admin document reindex finished: %d chunks indexed", indexed_total)
        return indexed_total
    except Exception:
        if blue_green and staging_collection and cleanup_store and not switched_collection:
            _delete_collection_if_exists(cleanup_store, staging_collection)
        raise
    finally:
        await engine.dispose()


async def _index_row(
    engine,
    s3_client: Any,
    row: Any,
    store_template: QdrantKnowledgeStore | None,
    semaphore: asyncio.Semaphore,
    defer_status_updates: bool,
    delete_existing: bool,
    dry_run: bool,
) -> FileIndexResult:
    async with semaphore:
        file_id = str(row["file_id"])
        filename = row["filename"]
        logger.info("Indexing %s (%s)", filename, file_id)

        if not defer_status_updates:
            await _update_file_status(engine, file_id, "indexing")
        try:
            data = await _read_s3_file(s3_client, filename)
            prepared_file = {
                "file_id": file_id,
                "filename": filename,
                "content_type": row["content_type"] or "application/octet-stream",
                "data": data,
            }
            if dry_run:
                chunks = await asyncio.to_thread(
                    _dry_run_file_sync,
                    prepared_file,
                    str(row["theme_id"]),
                    row["theme_title"],
                )
            else:
                if store_template is None:
                    raise RuntimeError("Qdrant store is required for non-dry-run indexing")
                chunks = await asyncio.to_thread(
                    _index_file_sync,
                    prepared_file,
                    str(row["theme_id"]),
                    row["theme_title"],
                    store_template,
                    delete_existing,
                )
        except Exception as exc:
            logger.exception("Failed to index %s", filename)
            if not defer_status_updates:
                await _update_file_status(engine, file_id, "failed", error=_truncate_error(exc))
            return FileIndexResult(file_id=file_id, chunks=0, failed=True)

        if not defer_status_updates:
            await _update_file_status(engine, file_id, "indexed", indexed_chunks=chunks)
    return FileIndexResult(file_id=file_id, chunks=chunks, failed=False)


def _dry_run_file_sync(
    prepared_file: dict[str, Any],
    theme_id: str,
    theme_title: str,
) -> int:
    documents = extract_documents(
        data=prepared_file["data"],
        filename=prepared_file["filename"],
        content_type=prepared_file["content_type"],
        file_id=str(prepared_file["file_id"]),
        theme_id=theme_id,
        theme_title=theme_title,
    )
    prepared_documents = prepare_documents_for_chunking(documents, fallback_section=theme_title)
    chunks = split_text(prepared_documents)
    if not chunks:
        raise DocumentExtractionError("No chunks were produced from the uploaded file")

    section_keys = {
        (chunk.metadata.get("section_index"), chunk.metadata.get("section_title"))
        for chunk in chunks
    }
    chunk_lengths = [len(chunk.page_content) for chunk in chunks]
    missing_section_titles = sum(1 for chunk in chunks if not chunk.metadata.get("section_title"))
    logger.info(
        "Dry-run parsed %s: extracted_docs=%d sections=%d chunks=%d chunk_chars=%d..%d missing_section_titles=%d",
        prepared_file["filename"],
        len(documents),
        len(section_keys),
        len(chunks),
        min(chunk_lengths),
        max(chunk_lengths),
        missing_section_titles,
    )
    return len(chunks)


def _index_file_sync(
    prepared_file: dict[str, Any],
    theme_id: str,
    theme_title: str,
    store_template: QdrantKnowledgeStore,
    delete_existing: bool,
) -> int:
    store = _clone_store(store_template)
    if delete_existing:
        store.delete_by_metadata("file_id", str(prepared_file["file_id"]))
    return index_knowledge_file(prepared_file, theme_id, theme_title, store)


def _clone_store(store: QdrantKnowledgeStore) -> QdrantKnowledgeStore:
    return QdrantKnowledgeStore(
        store.embeddings,
        url=store.url,
        collection_name=store.collection_name,
        vector_size=store.vector_size,
    )


async def _read_s3_file(s3_client: Any, filename: str) -> bytes:
    response = await s3_client.get_object(Bucket=config.minio.bucket, Key=filename)
    async with response["Body"] as stream:
        return await stream.read()


async def _update_file_status(
    engine,
    file_id: str,
    status: str,
    error: str | None = None,
    indexed_chunks: int = 0,
) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                UPDATE file
                SET ingest_status = :status,
                    ingest_error = :error,
                    indexed_chunks = :indexed_chunks,
                    indexed_at = CASE WHEN :set_indexed_at THEN NOW() ELSE indexed_at END
                WHERE file_id = CAST(:file_id AS uuid)
                """
            ),
            {
                "file_id": file_id,
                "status": status,
                "error": error,
                "indexed_chunks": indexed_chunks,
                "set_indexed_at": status == "indexed",
            },
        )


def _truncate_error(exc: Exception) -> str:
    return str(exc)[:1000] or exc.__class__.__name__


def _staging_collection_name(live_collection: str) -> str:
    return f"{live_collection}__staging__{time.strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"


def _collection_points_count(store: QdrantKnowledgeStore, collection_name: str) -> int | None:
    try:
        return int(store.client.count(collection_name=collection_name, exact=True).count)
    except Exception as exc:
        logger.warning("Could not count points in Qdrant collection '%s': %s", collection_name, exc)
        return None


def _publish_staging_collection(
    store: QdrantKnowledgeStore,
    live_collection: str,
    staging_collection: str,
) -> str | None:
    previous_collection = _alias_target(store, live_collection)
    if previous_collection:
        store.client.update_collection_aliases(
            change_aliases_operations=[
                models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=live_collection)),
                models.CreateAliasOperation(
                    create_alias=models.CreateAlias(
                        collection_name=staging_collection,
                        alias_name=live_collection,
                    )
                ),
            ]
        )
        logger.info(
            "Switched Qdrant alias '%s' from '%s' to '%s'",
            live_collection,
            previous_collection,
            staging_collection,
        )
        return previous_collection

    if _collection_exists(store, live_collection):
        logger.warning(
            "Qdrant name '%s' is a collection, not an alias. Deleting it after staging succeeded "
            "and recreating the name as an alias.",
            live_collection,
        )
        store.client.delete_collection(live_collection)

    store.client.update_collection_aliases(
        change_aliases_operations=[
            models.CreateAliasOperation(
                create_alias=models.CreateAlias(
                    collection_name=staging_collection,
                    alias_name=live_collection,
                )
            )
        ]
    )
    logger.info("Created Qdrant alias '%s' -> '%s'", live_collection, staging_collection)
    return None


def _alias_target(store: QdrantKnowledgeStore, alias_name: str) -> str | None:
    aliases = getattr(store.client.get_aliases(), "aliases", [])
    for alias in aliases:
        if getattr(alias, "alias_name", None) == alias_name:
            return getattr(alias, "collection_name", None)
    return None


def _collection_exists(store: QdrantKnowledgeStore, collection_name: str) -> bool:
    try:
        store.client.get_collection(collection_name)
        return True
    except Exception:
        return False


def _delete_previous_staging_collection(
    store: QdrantKnowledgeStore,
    collection_name: str | None,
    live_collection: str,
    current_staging_collection: str,
) -> None:
    if not collection_name or collection_name in {live_collection, current_staging_collection}:
        return
    if not collection_name.startswith(f"{live_collection}__staging__"):
        logger.info(
            "Leaving previous Qdrant collection '%s' untouched because it was not created by blue-green reindex",
            collection_name,
        )
        return
    _delete_collection_if_exists(store, collection_name)


def _delete_collection_if_exists(store: QdrantKnowledgeStore, collection_name: str) -> None:
    try:
        store.client.delete_collection(collection_name)
        logger.info("Deleted Qdrant collection '%s'", collection_name)
    except Exception as exc:
        logger.warning("Could not delete Qdrant collection '%s': %s", collection_name, exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindex admin-uploaded documents into Qdrant")
    parser.add_argument(
        "--recreate-qdrant",
        action="store_true",
        help="Delete and recreate the Qdrant collection before indexing",
    )
    parser.add_argument(
        "--blue-green",
        action="store_true",
        help="Index into a staging collection and publish it through the live Qdrant alias after success",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and chunk admin documents without calling embeddings API, writing Qdrant, or changing SQL statuses",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_REINDEX_CONCURRENCY,
        help="Maximum number of files to extract/embed/index in parallel",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    total = asyncio.run(
        reindex_admin_documents(
            recreate_qdrant=args.recreate_qdrant,
            concurrency=args.concurrency,
            blue_green=args.blue_green,
            dry_run=args.dry_run,
        )
    )
    if args.dry_run:
        logger.info("[SUCCESS] Dry-run finished: %d chunks would be indexed", total)
    else:
        logger.info("[SUCCESS] Reindex finished: %d chunks indexed", total)


if __name__ == "__main__":
    main()
