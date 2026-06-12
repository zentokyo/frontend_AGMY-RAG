import argparse
import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import config
from src.core.rag.ingest import GigaChatEmbeddings
from src.core.rag.qdrant_store import QdrantKnowledgeStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuestionSample:
    question_id: str
    question: str
    theme_id: str
    theme_title: str


def run_retrieval_smoke(
    *,
    limit: int = 18,
    k: int = 5,
    fetch_k: int | None = None,
    rerank: bool = True,
    mmr: bool = True,
    min_filtered_hit_rate: float = 1.0,
    min_unfiltered_top1_theme_rate: float | None = None,
    min_unfiltered_topk_theme_rate: float | None = None,
    output_json: str | None = None,
    verbose: bool = False,
) -> int:
    questions = asyncio.run(_load_questions(limit=limit))
    if not questions:
        logger.error("No questions found for retrieval smoke")
        return 1

    store = QdrantKnowledgeStore(GigaChatEmbeddings())
    filtered_hits = 0
    unfiltered_top1_theme_hits = 0
    unfiltered_topk_theme_hits = 0
    results = []

    for index, sample in enumerate(questions, start=1):
        filtered = store.similarity_search(
            sample.question,
            k=k,
            filter={"theme_id": sample.theme_id},
            fetch_k=fetch_k,
            rerank=rerank,
            mmr=mmr,
        )
        unfiltered = store.similarity_search(
            sample.question,
            k=k,
            fetch_k=fetch_k,
            rerank=rerank,
            mmr=mmr,
        )

        filtered_hit = bool(filtered)
        unfiltered_top1_theme_hit = bool(
            unfiltered and str(unfiltered[0].metadata.get("theme_id")) == sample.theme_id
        )
        unfiltered_topk_theme_hit = any(str(doc.metadata.get("theme_id")) == sample.theme_id for doc in unfiltered)

        if filtered_hit:
            filtered_hits += 1
        if unfiltered_top1_theme_hit:
            unfiltered_top1_theme_hits += 1
        if unfiltered_topk_theme_hit:
            unfiltered_topk_theme_hits += 1

        results.append(
            {
                "question_id": sample.question_id,
                "question": sample.question,
                "expected_theme_id": sample.theme_id,
                "expected_theme_title": sample.theme_title,
                "filtered_hit": filtered_hit,
                "unfiltered_top1_theme_hit": unfiltered_top1_theme_hit,
                "unfiltered_topk_theme_hit": unfiltered_topk_theme_hit,
                "filtered_top": _document_summary(filtered[0]) if filtered else None,
                "unfiltered_top": [_document_summary(doc) for doc in unfiltered],
            }
        )

        if verbose:
            top = unfiltered[0] if unfiltered else None
            logger.info(
                "[%d/%d] filtered=%s top1=%s topk=%s unfiltered_top=%s score=%s question=%s",
                index,
                len(questions),
                "hit" if filtered else "miss",
                "hit" if unfiltered_top1_theme_hit else "miss",
                "hit" if unfiltered_topk_theme_hit else "miss",
                top.metadata.get("source_theme") if top else "<none>",
                top.metadata.get("retrieval_hybrid_score", top.metadata.get("qdrant_score")) if top else "<none>",
                sample.question[:120],
            )

    total = len(questions)
    filtered_hit_rate = filtered_hits / total
    unfiltered_top1_theme_rate = unfiltered_top1_theme_hits / total
    unfiltered_topk_theme_rate = unfiltered_topk_theme_hits / total

    logger.info("Retrieval smoke questions: %d", total)
    logger.info("Filtered theme hit rate: %.2f (%d/%d)", filtered_hit_rate, filtered_hits, total)
    logger.info(
        "Unfiltered top-1 theme rate: %.2f (%d/%d)",
        unfiltered_top1_theme_rate,
        unfiltered_top1_theme_hits,
        total,
    )
    logger.info(
        "Unfiltered top-%d theme rate: %.2f (%d/%d)",
        k,
        unfiltered_topk_theme_rate,
        unfiltered_topk_theme_hits,
        total,
    )

    report = {
        "summary": {
            "questions": total,
            "k": k,
            "fetch_k": fetch_k,
            "rerank": rerank,
            "mmr": mmr,
            "filtered_hit_rate": filtered_hit_rate,
            "filtered_hits": filtered_hits,
            "unfiltered_top1_theme_rate": unfiltered_top1_theme_rate,
            "unfiltered_top1_theme_hits": unfiltered_top1_theme_hits,
            "unfiltered_topk_theme_rate": unfiltered_topk_theme_rate,
            "unfiltered_topk_theme_hits": unfiltered_topk_theme_hits,
        },
        "misses": [
            result
            for result in results
            if not result["filtered_hit"] or not result["unfiltered_top1_theme_hit"]
        ],
        "results": results,
    }
    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Retrieval smoke report written to %s", output_path)

    if filtered_hit_rate < min_filtered_hit_rate:
        logger.error(
            "Filtered hit rate %.2f is below required %.2f",
            filtered_hit_rate,
            min_filtered_hit_rate,
        )
        return 1
    if (
        min_unfiltered_top1_theme_rate is not None
        and unfiltered_top1_theme_rate < min_unfiltered_top1_theme_rate
    ):
        logger.error(
            "Unfiltered top-1 theme rate %.2f is below required %.2f",
            unfiltered_top1_theme_rate,
            min_unfiltered_top1_theme_rate,
        )
        return 1
    if (
        min_unfiltered_topk_theme_rate is not None
        and unfiltered_topk_theme_rate < min_unfiltered_topk_theme_rate
    ):
        logger.error(
            "Unfiltered top-%d theme rate %.2f is below required %.2f",
            k,
            unfiltered_topk_theme_rate,
            min_unfiltered_topk_theme_rate,
        )
        return 1

    return 0


def _document_summary(document) -> dict:
    metadata = document.metadata
    return {
        "theme_id": str(metadata.get("theme_id") or ""),
        "source_theme": metadata.get("source_theme"),
        "section_title": metadata.get("section_title"),
        "filename": metadata.get("filename"),
        "page_start": metadata.get("page_start") or metadata.get("page"),
        "page_end": metadata.get("page_end") or metadata.get("page"),
        "qdrant_score": metadata.get("qdrant_score"),
        "retrieval_qdrant_rank": metadata.get("retrieval_qdrant_rank"),
        "retrieval_candidate_rank": metadata.get("retrieval_candidate_rank"),
        "retrieval_vector_score": metadata.get("retrieval_vector_score"),
        "retrieval_lexical_score": metadata.get("retrieval_lexical_score"),
        "retrieval_hybrid_score": metadata.get("retrieval_hybrid_score"),
        "retrieval_mmr_score": metadata.get("retrieval_mmr_score"),
        "text_preview": " ".join(document.page_content.split())[:240],
    }


async def _load_questions(limit: int) -> list[QuestionSample]:
    engine = create_async_engine(config.postgres.db_url, echo=False)
    try:
        async with engine.begin() as connection:
            rows = (
                await connection.execute(
                    text(
                        """
                        SELECT
                          q.question_id,
                          q.text AS question,
                          q.theme_id,
                          t.title AS theme_title
                        FROM question q
                        JOIN theme t ON t.theme_id = q.theme_id
                        ORDER BY t.theme_order ASC, q.text ASC
                        """
                    )
                )
            ).mappings().all()
    finally:
        await engine.dispose()

    if limit > 0:
        rows = rows[:limit]

    return [
        QuestionSample(
            question_id=str(row["question_id"]),
            question=row["question"],
            theme_id=str(row["theme_id"]),
            theme_title=row["theme_title"],
        )
        for row in rows
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test Qdrant retrieval on real SQL questions")
    parser.add_argument("--limit", type=int, default=18, help="How many questions to test; <=0 means all")
    parser.add_argument("--k", type=int, default=5, help="How many chunks to retrieve per query")
    parser.add_argument("--fetch-k", type=int, default=None, help="How many Qdrant candidates to fetch before rerank")
    parser.add_argument("--no-rerank", action="store_true", help="Disable hybrid lexical/vector reranking")
    parser.add_argument("--no-mmr", action="store_true", help="Disable MMR diversity step after reranking")
    parser.add_argument(
        "--min-filtered-hit-rate",
        type=float,
        default=1.0,
        help="Required hit rate for retrieval filtered by question theme_id",
    )
    parser.add_argument(
        "--min-unfiltered-top1-theme-rate",
        type=float,
        default=None,
        help="Optional required rate for unfiltered top-1 matching the question theme",
    )
    parser.add_argument(
        "--min-unfiltered-topk-theme-rate",
        type=float,
        default=None,
        help="Optional required rate for unfiltered top-k containing the question theme",
    )
    parser.add_argument("--output-json", default=None, help="Write a JSON report with per-question results")
    parser.add_argument("--verbose", action="store_true", help="Log per-question retrieval details")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    raise SystemExit(
        run_retrieval_smoke(
            limit=args.limit,
            k=args.k,
            fetch_k=args.fetch_k,
            rerank=not args.no_rerank,
            mmr=not args.no_mmr,
            min_filtered_hit_rate=args.min_filtered_hit_rate,
            min_unfiltered_top1_theme_rate=args.min_unfiltered_top1_theme_rate,
            min_unfiltered_topk_theme_rate=args.min_unfiltered_topk_theme_rate,
            output_json=args.output_json,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
