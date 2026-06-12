import argparse
import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import config
from src.core.rag import DeepSeekFlashLLM, answer_question
from src.core.rag.ingest import GigaChatEmbeddings
from src.core.rag.qdrant_store import QdrantKnowledgeStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnswerSample:
    question_id: str
    question: str
    expected_answer: str
    theme_id: str
    theme_title: str


@dataclass(frozen=True)
class AnswerEvalResult:
    question_id: str
    question: str
    expected_answer: str
    theme_id: str
    theme_title: str
    is_correct: bool | None
    passed: bool
    elapsed_seconds: float
    error: str | None = None


def run_answer_eval(
    *,
    limit: int = 18,
    min_positive_pass_rate: float = 0.8,
    max_unknown_rate: float = 0.2,
    use_assertion_splitting: bool = True,
    use_query_decomposition: bool = True,
    use_llm_reranking: bool = False,
    output_json: str | None = None,
    verbose: bool = False,
) -> int:
    samples = asyncio.run(_load_answer_samples(limit=limit))
    if not samples:
        logger.error("No answered questions found for answer evaluation")
        return 1

    llm = DeepSeekFlashLLM()
    store = QdrantKnowledgeStore(GigaChatEmbeddings())
    results: list[AnswerEvalResult] = []

    for index, sample in enumerate(samples, start=1):
        started_at = time.monotonic()
        is_correct = None
        error = None
        try:
            is_correct = answer_question(
                sample.question,
                sample.expected_answer,
                llm,
                db=store,
                theme_id=sample.theme_id,
                theme_title=sample.theme_title,
                use_assertion_splitting=use_assertion_splitting,
                use_query_decomposition=use_query_decomposition,
                use_reranking=use_llm_reranking,
            )
        except Exception as exc:
            error = str(exc)
            logger.exception("Answer evaluation failed for question %s", sample.question_id)

        elapsed_seconds = time.monotonic() - started_at
        passed = is_correct is True
        results.append(
            AnswerEvalResult(
                question_id=sample.question_id,
                question=sample.question,
                expected_answer=sample.expected_answer,
                theme_id=sample.theme_id,
                theme_title=sample.theme_title,
                is_correct=is_correct,
                passed=passed,
                elapsed_seconds=round(elapsed_seconds, 3),
                error=error,
            )
        )

        if verbose:
            logger.info(
                "[%d/%d] %s in %.1fs theme=%s question=%s",
                index,
                len(samples),
                "pass" if passed else f"fail({is_correct})",
                elapsed_seconds,
                sample.theme_title,
                sample.question[:120],
            )

    summary = build_summary(results)
    report = build_report(
        results=results,
        summary=summary,
        settings={
            "limit": limit,
            "use_assertion_splitting": use_assertion_splitting,
            "use_query_decomposition": use_query_decomposition,
            "use_llm_reranking": use_llm_reranking,
            "min_positive_pass_rate": min_positive_pass_rate,
            "max_unknown_rate": max_unknown_rate,
        },
    )

    logger.info(
        "Answer eval positive pass rate: %.2f (%d/%d)",
        summary["positive_pass_rate"],
        summary["passed"],
        summary["total"],
    )
    logger.info(
        "Answer eval unknown rate: %.2f (%d/%d)",
        summary["unknown_rate"],
        summary["unknown"],
        summary["total"],
    )
    logger.info("Answer eval errors: %d", summary["errors"])

    if output_json:
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Answer eval report written to %s", output_path)

    return threshold_exit_code(
        summary=summary,
        min_positive_pass_rate=min_positive_pass_rate,
        max_unknown_rate=max_unknown_rate,
    )


def build_summary(results: list[AnswerEvalResult]) -> dict:
    total = len(results)
    passed = sum(1 for result in results if result.passed)
    unknown = sum(1 for result in results if result.is_correct is None)
    false_negative = sum(1 for result in results if result.is_correct is False)
    errors = sum(1 for result in results if result.error)
    elapsed_seconds = round(sum(result.elapsed_seconds for result in results), 3)

    return {
        "total": total,
        "passed": passed,
        "false_negative": false_negative,
        "unknown": unknown,
        "errors": errors,
        "positive_pass_rate": passed / total if total else 0.0,
        "unknown_rate": unknown / total if total else 0.0,
        "elapsed_seconds": elapsed_seconds,
    }


def build_report(*, results: list[AnswerEvalResult], summary: dict, settings: dict) -> dict:
    return {
        "summary": summary,
        "settings": settings,
        "failures": [
            _result_dict(result)
            for result in results
            if not result.passed
        ],
        "results": [_result_dict(result) for result in results],
    }


def threshold_exit_code(
    *,
    summary: dict,
    min_positive_pass_rate: float,
    max_unknown_rate: float,
) -> int:
    if summary["positive_pass_rate"] < min_positive_pass_rate:
        logger.error(
            "Positive pass rate %.2f is below required %.2f",
            summary["positive_pass_rate"],
            min_positive_pass_rate,
        )
        return 1
    if summary["unknown_rate"] > max_unknown_rate:
        logger.error(
            "Unknown rate %.2f is above allowed %.2f",
            summary["unknown_rate"],
            max_unknown_rate,
        )
        return 1
    return 0


async def _load_answer_samples(limit: int) -> list[AnswerSample]:
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
                          q.answer_text AS expected_answer,
                          q.theme_id,
                          t.title AS theme_title
                        FROM question q
                        JOIN theme t ON t.theme_id = q.theme_id
                        WHERE q.answer_text IS NOT NULL
                          AND btrim(q.answer_text) <> ''
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
        AnswerSample(
            question_id=str(row["question_id"]),
            question=row["question"],
            expected_answer=row["expected_answer"],
            theme_id=str(row["theme_id"]),
            theme_title=row["theme_title"],
        )
        for row in rows
    ]


def _result_dict(result: AnswerEvalResult) -> dict:
    data = asdict(result)
    data["question_preview"] = " ".join(result.question.split())[:180]
    data["expected_answer_preview"] = " ".join(result.expected_answer.split())[:240]
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate full RAG answer judging on real SQL expected answers")
    parser.add_argument("--limit", type=int, default=18, help="How many answered questions to test; <=0 means all")
    parser.add_argument(
        "--min-positive-pass-rate",
        type=float,
        default=0.8,
        help="Required pass rate for SQL expected answers",
    )
    parser.add_argument(
        "--max-unknown-rate",
        type=float,
        default=0.2,
        help="Maximum allowed rate of None/unknown RAG verdicts",
    )
    parser.add_argument("--no-assertion-splitting", action="store_true", help="Disable answer assertion splitting")
    parser.add_argument("--no-query-decomposition", action="store_true", help="Disable question decomposition")
    parser.add_argument("--llm-reranking", action="store_true", help="Enable legacy LLM per-chunk reranking")
    parser.add_argument("--output-json", default=None, help="Write a JSON report with per-answer results")
    parser.add_argument("--verbose", action="store_true", help="Log per-answer evaluation details")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    raise SystemExit(
        run_answer_eval(
            limit=args.limit,
            min_positive_pass_rate=args.min_positive_pass_rate,
            max_unknown_rate=args.max_unknown_rate,
            use_assertion_splitting=not args.no_assertion_splitting,
            use_query_decomposition=not args.no_query_decomposition,
            use_llm_reranking=args.llm_reranking,
            output_json=args.output_json,
            verbose=args.verbose,
        )
    )


if __name__ == "__main__":
    main()
