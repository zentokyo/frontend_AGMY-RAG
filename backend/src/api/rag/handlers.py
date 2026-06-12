import asyncio
import logging

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from src.api.rag.schemas import RagEvaluateRequest, RagEvaluateResponse
from src.core.rag import DeepSeekFlashLLM, QdrantKnowledgeStore, answer_question, check_response_against_expected

logger = logging.getLogger(__name__)

rag_router = APIRouter(prefix="/rag", tags=["RAG"])


@rag_router.post("/evaluate")
@inject
async def evaluate_answer_handler(
    schema: RagEvaluateRequest,
    model: FromDishka[DeepSeekFlashLLM],
    db: FromDishka[QdrantKnowledgeStore],
) -> RagEvaluateResponse:
    """Evaluate a student's free-form answer using the Python RAG core."""
    if not schema.answer.strip():
        return RagEvaluateResponse(
            is_correct=False,
            method="python_qdrant_rag_empty",
            score=0.0,
            explanation="Empty answer",
        )

    if schema.expected_answer and _normalize(schema.answer) == _normalize(schema.expected_answer):
        return RagEvaluateResponse(
            is_correct=True,
            method="python_expected_exact",
            score=1.0,
            explanation="Answer exactly matches expected answer",
        )

    if schema.expected_answer:
        expected_verdict, expected_explanation = check_response_against_expected(
            question=schema.question,
            response_text=schema.answer,
            expected_answer=schema.expected_answer,
            model=model,
        )
        if expected_verdict is not None:
            return RagEvaluateResponse(
                is_correct=expected_verdict,
                method="python_expected_semantic",
                score=1.0 if expected_verdict else 0.0,
                explanation=expected_explanation,
            )

    result = await asyncio.to_thread(
        answer_question,
        schema.question,
        schema.answer,
        model,
        db=db,
        theme_id=schema.theme_id,
        theme_title=schema.theme_title,
        use_assertion_splitting=schema.use_assertion_splitting,
        use_query_decomposition=schema.use_query_decomposition,
        use_reranking=schema.use_reranking,
    )

    if result is None:
        logger.warning("RAG could not determine answer correctness for question: %s", schema.question[:80])
        return RagEvaluateResponse(
            is_correct=None,
            method="python_qdrant_rag_unknown",
            score=None,
            explanation="RAG could not determine correctness",
        )

    return RagEvaluateResponse(
        is_correct=result,
        method="python_qdrant_rag",
        score=1.0 if result else 0.0,
    )


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())
