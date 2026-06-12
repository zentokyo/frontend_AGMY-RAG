import unittest

from src.cli.rag_answer_eval import AnswerEvalResult, build_report, build_summary, threshold_exit_code


def _result(question_id: str, is_correct: bool | None, error: str | None = None) -> AnswerEvalResult:
    return AnswerEvalResult(
        question_id=question_id,
        question=f"Question {question_id}",
        expected_answer=f"Answer {question_id}",
        theme_id="theme-id",
        theme_title="Theme",
        is_correct=is_correct,
        passed=is_correct is True,
        elapsed_seconds=1.25,
        error=error,
    )


class RagAnswerEvalTests(unittest.TestCase):
    def test_build_summary_counts_pass_fail_unknown_and_errors(self):
        summary = build_summary(
            [
                _result("1", True),
                _result("2", False),
                _result("3", None, error="network error"),
            ]
        )

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["false_negative"], 1)
        self.assertEqual(summary["unknown"], 1)
        self.assertEqual(summary["errors"], 1)
        self.assertAlmostEqual(summary["positive_pass_rate"], 1 / 3)
        self.assertAlmostEqual(summary["unknown_rate"], 1 / 3)

    def test_build_report_includes_only_failed_results_in_failures(self):
        results = [_result("1", True), _result("2", False), _result("3", None)]
        report = build_report(
            results=results,
            summary=build_summary(results),
            settings={"limit": 3},
        )

        self.assertEqual(len(report["results"]), 3)
        self.assertEqual([failure["question_id"] for failure in report["failures"]], ["2", "3"])

    def test_threshold_exit_code_enforces_positive_and_unknown_rates(self):
        passing_summary = {"positive_pass_rate": 0.9, "unknown_rate": 0.05}
        low_pass_summary = {"positive_pass_rate": 0.7, "unknown_rate": 0.05}
        high_unknown_summary = {"positive_pass_rate": 0.9, "unknown_rate": 0.3}

        self.assertEqual(
            threshold_exit_code(
                summary=passing_summary,
                min_positive_pass_rate=0.8,
                max_unknown_rate=0.2,
            ),
            0,
        )
        self.assertEqual(
            threshold_exit_code(
                summary=low_pass_summary,
                min_positive_pass_rate=0.8,
                max_unknown_rate=0.2,
            ),
            1,
        )
        self.assertEqual(
            threshold_exit_code(
                summary=high_unknown_summary,
                min_positive_pass_rate=0.8,
                max_unknown_rate=0.2,
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
