from types import SimpleNamespace
import unittest

from langchain_core.documents import Document

from src.core.rag.qdrant_store import QdrantKnowledgeStore, rerank_documents


class FakeEmbeddings:
    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    def embed_documents(self, texts: list[str], batch_size: int = 8) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeQdrantClient:
    def __init__(self, points):
        self.points = points
        self.last_limit = None

    def query_points(self, **kwargs):
        self.last_limit = kwargs["limit"]
        return SimpleNamespace(points=self.points[: self.last_limit])


def _point(text: str, score: float, **metadata):
    return SimpleNamespace(
        id=metadata.pop("qdrant_id", f"point-{score}"),
        score=score,
        payload={"text": text, **metadata},
    )


class RetrievalRerankingTests(unittest.TestCase):
    def test_rerank_promotes_lexically_relevant_chunk(self):
        question = "Каковы сроки экстренной профилактики ВИЧ после аварийной ситуации?"
        weak_match = Document(
            page_content="Общие сведения о вакцинации и профессиональной безопасности.",
            metadata={"qdrant_score": 0.92, "source_theme": "Особенности вакцинации против ВГВ"},
        )
        strong_match = Document(
            page_content=(
                "Экстренная профилактика ВИЧ-инфекции после аварийной ситуации "
                "должна быть начата как можно раньше, оптимально в первые часы."
            ),
            metadata={"qdrant_score": 0.74, "source_theme": "Профилактика профессионального заражения"},
        )

        ranked = rerank_documents(
            query=question,
            documents=[weak_match, strong_match],
            k=1,
            use_mmr=False,
        )

        self.assertIs(ranked[0], strong_match)
        self.assertGreater(
            strong_match.metadata["retrieval_lexical_score"],
            weak_match.metadata["retrieval_lexical_score"],
        )

    def test_similarity_search_fetches_candidates_before_rerank(self):
        question = "Каковы сроки экстренной профилактики ВИЧ после аварийной ситуации?"
        points = [
            _point(
                "Общие сведения о вакцинации.",
                0.92,
                source_theme="Особенности вакцинации против ВГВ",
            ),
            _point(
                "Экстренная профилактика ВИЧ после аварийной ситуации начинается как можно раньше.",
                0.74,
                source_theme="Профилактика профессионального заражения",
            ),
        ]
        client = FakeQdrantClient(points)
        store = QdrantKnowledgeStore(FakeEmbeddings(), url="http://fake-qdrant")
        store.client = client

        results = store.similarity_search(question, k=1, fetch_k=2, rerank=True, mmr=False)

        self.assertEqual(client.last_limit, 2)
        self.assertEqual(results[0].metadata["source_theme"], "Профилактика профессионального заражения")
        self.assertEqual(results[0].metadata["retrieval_candidate_rank"], 2)

    def test_similarity_search_can_keep_qdrant_order_without_rerank(self):
        question = "Каковы сроки экстренной профилактики ВИЧ после аварийной ситуации?"
        points = [
            _point("Общие сведения о вакцинации.", 0.92, source_theme="Особенности вакцинации против ВГВ"),
            _point(
                "Экстренная профилактика ВИЧ после аварийной ситуации начинается как можно раньше.",
                0.74,
                source_theme="Профилактика профессионального заражения",
            ),
        ]
        client = FakeQdrantClient(points)
        store = QdrantKnowledgeStore(FakeEmbeddings(), url="http://fake-qdrant")
        store.client = client

        results = store.similarity_search(question, k=1, fetch_k=2, rerank=False)

        self.assertEqual(client.last_limit, 1)
        self.assertEqual(results[0].metadata["source_theme"], "Особенности вакцинации против ВГВ")


if __name__ == "__main__":
    unittest.main()
