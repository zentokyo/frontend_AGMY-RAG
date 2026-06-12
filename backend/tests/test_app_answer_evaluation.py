import asyncio
import unittest

from src.api.app.answers import _evaluate_answer


class FakeLLM:
    def invoke(self, prompt: str, max_tokens: int = 256) -> str:
        return '{"verdict": "ВЕРНО", "explanation": "ответ является корректной переформулировкой"}'


class AppAnswerEvaluationTests(unittest.TestCase):
    def test_uses_expected_answer_semantic_check_before_rag(self):
        result = asyncio.run(
            _evaluate_answer(
                question="Какой вирус наиболее устойчив?",
                answer="Самый устойчивый и заразный при контакте с кровью — вирус гепатита B.",
                expected_answer="Наиболее устойчив и контагиозен вирус гепатита В (ВГВ).",
                theme_id="theme-id",
                theme_title="Theme",
                model=FakeLLM(),
                db=object(),
            )
        )

        self.assertEqual(result["method"], "python_expected_semantic")
        self.assertIs(result["is_correct"], True)


if __name__ == "__main__":
    unittest.main()
