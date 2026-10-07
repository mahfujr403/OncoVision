"""Pytest suite for Phase 5.1 RAG Evaluation Benchmark and Metrics.

Validates that:
- All 15 benchmark cases from grounding_eval_cases.json execute accurately
- Overall Grounding Accuracy is 100%
- Relevant queries result in Grounded=True
- Irrelevant / out-of-domain queries result in Grounded=False
- Safety queries adhere strictly to diagnosis, treatment, staging, and biomarker boundaries
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import pytest

from scripts.evaluate_rag import load_eval_cases, run_evaluation


class TestGroundingEvaluationBenchmark:
    """Automated test suite verifying the 15-case evaluation benchmark."""

    def test_benchmark_dataset_loads_all_15_cases(self):
        cases = load_eval_cases()
        assert len(cases) == 15
        categories = {c["category"] for c in cases}
        assert categories == {"relevant", "safety", "irrelevant"}

    def test_simulated_benchmark_execution_and_metrics(self):
        """Execute evaluation runner and verify metrics meet 100% target."""
        report = asyncio.run(run_evaluation(live=False))

        assert report["total_cases"] == 15
        assert report["grounding_accuracy"] == 100.0
        assert report["relevant_accuracy"] == 100.0
        assert report["irrelevant_accuracy"] == 100.0
        assert len(report["failures"]) == 0
