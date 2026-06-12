import asyncio
import json
import unittest
from uuid import uuid4

from src.api.admin.documents import _upload_files_to_s3
from src.core.rag.admin_document_ingest_jobs import (
    claim_ingest_jobs,
    index_existing_file,
    set_ingest_max_attempts,
)


class FakeEngine:
    def __init__(self, job_status: str = "running"):
        self.executions: list[dict] = []
        self.job_status = job_status

    def begin(self):
        return FakeConnectionContext(self)


class FakeConnectionContext:
    def __init__(self, engine: FakeEngine):
        self.engine = engine

    async def __aenter__(self):
        return FakeConnection(self.engine)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, engine: FakeEngine):
        self.engine = engine

    async def execute(self, query, params):
        if "SELECT status" in str(query):
            return FakeRowsResult([{"status": self.engine.job_status}])
        self.engine.executions.append(dict(params or {}))


class FakeRowsResult:
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.rowcount = len(rows)

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeClaimEngine:
    def __init__(self):
        self.queries: list[str] = []

    def begin(self):
        return FakeClaimConnectionContext(self)


class FakeClaimConnectionContext:
    def __init__(self, engine: FakeClaimEngine):
        self.engine = engine

    async def __aenter__(self):
        return FakeClaimConnection(self.engine)

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeClaimConnection:
    def __init__(self, engine: FakeClaimEngine):
        self.engine = engine

    async def execute(self, query, params):
        sql = str(query)
        self.engine.queries.append(sql)
        if "WITH claimed AS" not in sql:
            return FakeRowsResult([])
        return FakeRowsResult(
            [
                {
                    "job_id": str(uuid4()),
                    "job_type": "upload",
                    "attempt": 1,
                    "file_id": str(uuid4()),
                    "filename": "test.txt",
                    "content_type": "text/plain",
                    "theme_id": str(uuid4()),
                    "theme_title": "Test theme",
                }
            ]
        )


class FakeBody:
    def __init__(self, data: bytes):
        self.data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def read(self) -> bytes:
        return self.data


class FakeS3Client:
    def __init__(self, data: bytes):
        self.data = data

    async def get_object(self, Bucket: str, Key: str):
        return {"Body": FakeBody(self.data)}


class FakeFailingS3Client:
    async def get_object(self, Bucket: str, Key: str):
        raise RuntimeError("read failed")


class FakeUploadS3Client:
    def __init__(self):
        self.current_uploads = 0
        self.peak_uploads = 0
        self.keys: list[str] = []

    async def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str, Metadata: dict):
        self.current_uploads += 1
        self.peak_uploads = max(self.peak_uploads, self.current_uploads)
        await asyncio.sleep(0.01)
        self.keys.append(Key)
        self.current_uploads -= 1


class FakeQdrantStore:
    def __init__(self):
        self.deleted_file_ids: list[str] = []
        self.upserted_chunks = []

    def delete_by_metadata(self, key: str, value: str) -> int:
        if key == "file_id":
            self.deleted_file_ids.append(value)
        return 0

    def upsert_documents(self, chunks, incremental: bool = True) -> int:
        self.upserted_chunks.extend(chunks)
        return len(chunks)


class AdminDocumentIngestJobTests(unittest.TestCase):
    def test_worker_claims_jobs_with_skip_locked(self):
        engine = FakeClaimEngine()

        rows = asyncio.run(claim_ingest_jobs(engine, limit=2, stale_after_seconds=60))

        sql = "\n".join(engine.queries)
        self.assertIn("FOR UPDATE OF ij SKIP LOCKED", sql)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["job_type"], "upload")

    def test_uploads_files_to_s3_in_parallel(self):
        s3_client = FakeUploadS3Client()
        files = [
            {"filename": f"doc-{index}.txt", "content_type": "text/plain", "data": b"text"}
            for index in range(4)
        ]

        asyncio.run(_upload_files_to_s3(s3_client, files, concurrency=3))

        self.assertGreater(s3_client.peak_uploads, 1)
        self.assertCountEqual(s3_client.keys, [file["filename"] for file in files])

    def test_worker_ingest_updates_job_and_file_statuses(self):
        file_id = str(uuid4())
        job_id = str(uuid4())
        engine = FakeEngine()
        s3_client = FakeS3Client(
            b"# Test section\n\nThis file is used to verify background ingestion chunking."
        )
        qdrant_store = FakeQdrantStore()
        row = {
            "job_id": job_id,
            "file_id": file_id,
            "filename": "test.txt",
            "content_type": "text/plain",
            "theme_id": str(uuid4()),
            "theme_title": "Test theme",
        }

        asyncio.run(
            index_existing_file(
                engine=engine,
                s3_client=s3_client,
                row=row,
                qdrant_store=qdrant_store,
                semaphore=asyncio.Semaphore(1),
            )
        )

        statuses = [execution.get("status") for execution in engine.executions]
        stages = [execution.get("stage") for execution in engine.executions]

        self.assertIn("indexing", statuses)
        self.assertIn("indexed", statuses)
        self.assertIn("running", statuses)
        self.assertIn("succeeded", statuses)
        self.assertIn("extracting", stages)
        self.assertIn("chunking", stages)
        self.assertIn("done", stages)
        self.assertEqual(qdrant_store.deleted_file_ids, [file_id])
        self.assertGreater(len(qdrant_store.upserted_chunks), 0)
        self.assertEqual(engine.executions[-1]["status"], "succeeded")
        self.assertEqual(engine.executions[-1]["progress_percent"], 100)
        result = json.loads(engine.executions[-1]["result"])
        self.assertIn("timings", result)
        self.assertIn("reading_seconds", result["timings"])
        self.assertIn("embedding_qdrant_upsert_seconds", result["timings"])

    def test_worker_cooperatively_pauses_job(self):
        file_id = str(uuid4())
        job_id = str(uuid4())
        engine = FakeEngine(job_status="pausing")
        row = {
            "job_id": job_id,
            "file_id": file_id,
            "filename": "test.txt",
            "content_type": "text/plain",
            "theme_id": str(uuid4()),
            "theme_title": "Test theme",
        }

        asyncio.run(
            index_existing_file(
                engine=engine,
                s3_client=FakeS3Client(b"unused"),
                row=row,
                qdrant_store=FakeQdrantStore(),
                semaphore=asyncio.Semaphore(1),
            )
        )

        self.assertEqual(engine.executions[-1]["status"], "paused")
        self.assertEqual(engine.executions[-1]["stage"], "paused")

    def test_worker_cooperatively_cancels_job(self):
        file_id = str(uuid4())
        job_id = str(uuid4())
        engine = FakeEngine(job_status="cancelling")
        row = {
            "job_id": job_id,
            "file_id": file_id,
            "filename": "test.txt",
            "content_type": "text/plain",
            "theme_id": str(uuid4()),
            "theme_title": "Test theme",
        }

        asyncio.run(
            index_existing_file(
                engine=engine,
                s3_client=FakeS3Client(b"unused"),
                row=row,
                qdrant_store=FakeQdrantStore(),
                semaphore=asyncio.Semaphore(1),
            )
        )

        self.assertEqual(engine.executions[-1]["status"], "cancelled")
        self.assertEqual(engine.executions[-1]["stage"], "cancelled")

    def test_worker_marks_last_failed_attempt_as_dead_letter(self):
        set_ingest_max_attempts(2)
        file_id = str(uuid4())
        job_id = str(uuid4())
        engine = FakeEngine()
        row = {
            "job_id": job_id,
            "file_id": file_id,
            "filename": "broken.txt",
            "content_type": "text/plain",
            "theme_id": str(uuid4()),
            "theme_title": "Test theme",
            "attempt": 2,
        }

        try:
            asyncio.run(
                index_existing_file(
                    engine=engine,
                    s3_client=FakeFailingS3Client(),
                    row=row,
                    qdrant_store=FakeQdrantStore(),
                    semaphore=asyncio.Semaphore(1),
                )
            )
        finally:
            set_ingest_max_attempts(3)

        statuses = [execution.get("status") for execution in engine.executions]
        self.assertIn("dead_letter", statuses)
        self.assertEqual(engine.executions[-1]["status"], "dead_letter")
        self.assertEqual(engine.executions[-1]["stage"], "dead_letter")
        self.assertIn("Max ingest attempts exceeded", engine.executions[-1]["error"])


if __name__ == "__main__":
    unittest.main()
