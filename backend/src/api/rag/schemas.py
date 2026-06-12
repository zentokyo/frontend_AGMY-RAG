from pydantic import BaseModel


class RagEvaluateRequest(BaseModel):
    question: str
    answer: str
    expected_answer: str | None = None
    theme_id: str | None = None
    theme_title: str | None = None
    use_assertion_splitting: bool = True
    use_query_decomposition: bool = True
    use_reranking: bool = False


class RagEvaluateResponse(BaseModel):
    is_correct: bool | None
    method: str = "python_qdrant_rag"
    score: float | None = None
    explanation: str | None = None
