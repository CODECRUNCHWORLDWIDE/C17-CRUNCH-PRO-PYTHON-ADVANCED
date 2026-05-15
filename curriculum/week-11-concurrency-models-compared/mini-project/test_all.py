"""test_all.py — Verify the five implementations produce equivalent results.

Run this before benchmarking. If any test fails, the benchmark numbers are
meaningless: a "fast" implementation that returns the wrong answer is not
faster, it is broken.

Usage:
    python3 test_all.py            # full test
    python3 test_all.py --quick    # 200-doc subset (development)
    python3 -m pytest test_all.py  # via pytest if you prefer

The tests do not require a free-threaded build; they exercise the
correctness of each implementation against the serial baseline. The
benchmark.py companion script measures performance.

Compile-check: `python3 -m py_compile test_all.py`.
"""

from __future__ import annotations

import argparse
import os
import sys
import unittest
from typing import Any

# Re-import benchmark.py from the same directory so the test file is
# self-contained and does not require a package install.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import benchmark  # type: ignore[import-not-found]


def make_test_corpus(n: int = 200) -> list[tuple[str, str]]:
    """Generate a small deterministic test corpus."""
    return benchmark.generate_corpus(n)


def reference_scores(
    corpus: list[tuple[str, str]], query: list[str]
) -> dict[str, float]:
    """The ground truth: serial scoring as a dict for easy comparison."""
    return dict(benchmark.score_serial(corpus, query))


class TestSerial(unittest.TestCase):
    """v1 (serial) is the reference. The tests here check basic shape."""

    def test_returns_one_score_per_doc(self) -> None:
        corpus: list[tuple[str, str]] = make_test_corpus(50)
        results: list[tuple[str, float]] = benchmark.score_serial(corpus, benchmark.QUERY)
        self.assertEqual(len(results), 50)

    def test_doc_ids_match_input(self) -> None:
        corpus: list[tuple[str, str]] = make_test_corpus(50)
        results: list[tuple[str, float]] = benchmark.score_serial(corpus, benchmark.QUERY)
        result_ids: set[str] = {doc_id for doc_id, _ in results}
        input_ids: set[str] = {doc_id for doc_id, _ in corpus}
        self.assertEqual(result_ids, input_ids)

    def test_scores_are_normalised(self) -> None:
        """Every score is between 0.0 and 1.0 inclusive."""
        corpus: list[tuple[str, str]] = make_test_corpus(100)
        results: list[tuple[str, float]] = benchmark.score_serial(corpus, benchmark.QUERY)
        for _, score in results:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_empty_corpus_is_empty_results(self) -> None:
        self.assertEqual(benchmark.score_serial([], benchmark.QUERY), [])

    def test_deterministic_under_repeat(self) -> None:
        """The serial implementation is deterministic; same input = same output."""
        corpus: list[tuple[str, str]] = make_test_corpus(100)
        a: list[tuple[str, float]] = benchmark.score_serial(corpus, benchmark.QUERY)
        b: list[tuple[str, float]] = benchmark.score_serial(corpus, benchmark.QUERY)
        self.assertEqual(a, b)


class TestEquivalence(unittest.TestCase):
    """Each non-serial implementation must agree with the serial baseline."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus: list[tuple[str, str]] = make_test_corpus(200)  # type: ignore[attr-defined]
        cls.query: list[str] = benchmark.QUERY  # type: ignore[attr-defined]
        cls.expected: dict[str, float] = reference_scores(cls.corpus, cls.query)  # type: ignore[attr-defined]

    def _compare(self, results: list[tuple[str, float]]) -> None:
        result_dict: dict[str, float] = dict(results)
        self.assertEqual(set(result_dict.keys()), set(self.expected.keys()))
        for doc_id, expected_score in self.expected.items():
            self.assertAlmostEqual(
                result_dict[doc_id],
                expected_score,
                places=6,
                msg=f"score mismatch for {doc_id}",
            )

    def test_threads_match_serial(self) -> None:
        self._compare(benchmark.score_threads(self.corpus, self.query))

    def test_asyncio_match_serial(self) -> None:
        self._compare(benchmark.score_asyncio(self.corpus, self.query))

    def test_multiprocessing_match_serial(self) -> None:
        self._compare(benchmark.score_multiprocessing(self.corpus, self.query))

    @unittest.skipUnless(sys.version_info >= (3, 13), "subinterpreters require 3.13+")
    def test_subinterpreters_match_serial(self) -> None:
        try:
            results: list[tuple[str, float]] = benchmark.score_subinterpreters(
                self.corpus, self.query
            )
        except ImportError:
            self.skipTest("interpreters module not available")
        self._compare(results)


class TestTokenisation(unittest.TestCase):
    """Spot-check the tokenisation primitive that all implementations share."""

    def test_lowercases(self) -> None:
        self.assertEqual(benchmark.tokenise("Python Concurrency"), ["python", "concurrency"])

    def test_strips_stopwords(self) -> None:
        result: list[str] = benchmark.tokenise("the python and the model")
        self.assertNotIn("the", result)
        self.assertNotIn("and", result)
        self.assertIn("python", result)
        self.assertIn("model", result)

    def test_short_tokens_filtered(self) -> None:
        result: list[str] = benchmark.tokenise("a b cc ddd")
        # Single-character tokens are filtered (len > 1 check).
        self.assertNotIn("a", result)
        self.assertNotIn("b", result)
        self.assertIn("cc", result)
        self.assertIn("ddd", result)

    def test_empty_input(self) -> None:
        self.assertEqual(benchmark.tokenise(""), [])

    def test_whitespace_only(self) -> None:
        self.assertEqual(benchmark.tokenise("   \t\n  "), [])


class TestScoringEdgeCases(unittest.TestCase):
    """The score_one primitive: edge cases."""

    def test_empty_body_returns_zero(self) -> None:
        result: tuple[str, float] = benchmark.score_one(("doc_x", ""), benchmark.QUERY)
        self.assertEqual(result, ("doc_x", 0.0))

    def test_no_query_terms_returns_zero(self) -> None:
        result: tuple[str, float] = benchmark.score_one(
            ("doc_x", "completely unrelated words here"), benchmark.QUERY
        )
        self.assertEqual(result[1], 0.0)

    def test_all_query_terms_returns_high_score(self) -> None:
        result: tuple[str, float] = benchmark.score_one(
            ("doc_x", "python concurrency model python concurrency model"),
            benchmark.QUERY,
        )
        # After stopword/short-token filtering, all six tokens are in the query.
        self.assertAlmostEqual(result[1], 1.0, places=6)

    def test_score_independent_of_order(self) -> None:
        a: tuple[str, float] = benchmark.score_one(
            ("doc_x", "python concurrency model"), benchmark.QUERY
        )
        b: tuple[str, float] = benchmark.score_one(
            ("doc_x", "model python concurrency"), benchmark.QUERY
        )
        self.assertAlmostEqual(a[1], b[1], places=6)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="run a subset")
    args, remaining = parser.parse_known_args()
    sys.argv = [sys.argv[0]] + remaining
    if args.quick:
        # Limit to the fastest test classes for quick iteration.
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        suite.addTests(loader.loadTestsFromTestCase(TestSerial))
        suite.addTests(loader.loadTestsFromTestCase(TestTokenisation))
        suite.addTests(loader.loadTestsFromTestCase(TestScoringEdgeCases))
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
    else:
        unittest.main()


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.set_start_method("spawn", force=True)
    main()
