import unittest

from src.core.rag.main import (
    _check_response_against_context,
    _parse_assertions_response,
    build_answer_search_queries,
    check_response_against_expected,
)


class FakeLLM:
    def __init__(self, response: str):
        self.response = response

    def invoke(self, prompt: str, max_tokens: int = 256) -> str:
        return self.response


class RagAssertionsTests(unittest.TestCase):
    def test_parse_json_assertions(self):
        assertions = _parse_assertions_response(
            '["ВГВ наиболее устойчив.", "Инфицирующая доза составляет 0,0000001 мл."]'
        )

        self.assertEqual(
            assertions,
            ["ВГВ наиболее устойчив.", "Инфицирующая доза составляет 0,0000001 мл."],
        )

    def test_filters_llm_intro_from_line_fallback(self):
        assertions = _parse_assertions_response(
            """
            Вот текст, разбитый на отдельные факты (по одному на строку):
            1. ВГВ наиболее устойчив во внешней среде.
            2. ВГВ обладает высокой контагиозностью.
            """
        )

        self.assertEqual(
            assertions,
            [
                "ВГВ наиболее устойчив во внешней среде.",
                "ВГВ обладает высокой контагиозностью.",
            ],
        )

    def test_context_check_prefers_verdict_over_raw_no_word(self):
        verdict, _ = _check_response_against_context(
            question="Question",
            response_text="Answer",
            context="Context",
            model=FakeLLM('{"verdict": "ВЕРНО", "explanation": "нет прямого указания'),
            partial=True,
        )

        self.assertIs(verdict, True)

    def test_answer_search_queries_include_compact_answer_evidence_first(self):
        queries = build_answer_search_queries(
            question="Напишите схему вакцинации против вирусного гепатита B.",
            answer="0 (первые 24 часа жизни) -1-6 месяцев.",
            llm=FakeLLM(""),
            use_query_decomposition=False,
        )

        self.assertIn("0 (первые 24 часа жизни) -1-6 месяцев", queries[0])
        self.assertEqual(queries[-1], "Напишите схему вакцинации против вирусного гепатита B.")

    def test_expected_answer_check_accepts_semantic_paraphrase(self):
        verdict, explanation = check_response_against_expected(
            question="Какой вирус наиболее устойчив?",
            response_text="Самый устойчивый и заразный при контакте с кровью — вирус гепатита B.",
            expected_answer="Наиболее устойчив и контагиозен вирус гепатита В (ВГВ).",
            model=FakeLLM('{"verdict": "ВЕРНО", "explanation": "ключевые факты совпадают"}'),
        )

        self.assertIs(verdict, True)
        self.assertEqual(explanation, "ключевые факты совпадают")


if __name__ == "__main__":
    unittest.main()
