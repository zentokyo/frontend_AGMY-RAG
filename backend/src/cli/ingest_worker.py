import argparse
import asyncio
import logging

from src.core.rag.admin_document_ingest_jobs import (
    INGEST_STALE_AFTER_SECONDS,
    INGEST_MAX_ATTEMPTS,
    INGEST_WORKER_BATCH_SIZE,
    INGEST_WORKER_POLL_SECONDS,
    run_ingest_worker_forever,
    run_ingest_worker_once,
    set_ingest_max_attempts,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process admin document ingest jobs.")
    parser.add_argument("--once", action="store_true", help="Claim and process one batch, then exit.")
    parser.add_argument("--batch-size", type=int, default=INGEST_WORKER_BATCH_SIZE)
    parser.add_argument("--poll-seconds", type=float, default=INGEST_WORKER_POLL_SECONDS)
    parser.add_argument("--stale-after-seconds", type=int, default=INGEST_STALE_AFTER_SECONDS)
    parser.add_argument("--max-attempts", type=int, default=INGEST_MAX_ATTEMPTS)
    args = parser.parse_args()
    set_ingest_max_attempts(args.max_attempts)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if args.once:
        processed = asyncio.run(
            run_ingest_worker_once(
                batch_size=args.batch_size,
                stale_after_seconds=args.stale_after_seconds,
            )
        )
        logging.getLogger(__name__).info("Ingest worker processed %d job(s)", processed)
        return

    asyncio.run(
        run_ingest_worker_forever(
            batch_size=args.batch_size,
            poll_seconds=args.poll_seconds,
            stale_after_seconds=args.stale_after_seconds,
        )
    )


if __name__ == "__main__":
    main()
