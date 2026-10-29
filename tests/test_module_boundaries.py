"""Focused regression tests for the modular public APIs."""

import importlib
import py_compile
import tempfile
import unittest
from pathlib import Path

from agents.review_agent import ReviewAgent, ReviewLevel, ReviewVerdict, determine_review_level
from agents.review_models import ReviewLevel as ModelReviewLevel
from orchestrator.claude_result import ClaudeResult as ExtractedClaudeResult
from orchestrator.claude_runner import ClaudeResult, ClaudeRunner
from orchestrator.review_loop import (
    ReviewLoop, ReviewVerdict as LoopReviewVerdict,
    determine_review_level as determine_loop_level,
)
from orchestrator.workflow_engine import (
    WORKFLOW_REGISTRY, Branch, Gate, GateAction, Parallel, Step,
    WorkflowEngine, WorkflowResult,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PublicImportCompatibilityTests(unittest.TestCase):
    def test_review_agent_reexports_are_identical(self):
        self.assertIs(ReviewLevel, ModelReviewLevel)
        self.assertTrue(issubclass(ReviewAgent, object))
        self.assertEqual(ReviewVerdict.__module__, "agents.review_models")

    def test_orchestrator_reexports_remain_available(self):
        self.assertIs(ClaudeResult, ExtractedClaudeResult)
        for value in (ReviewLoop, LoopReviewVerdict, WorkflowEngine, WorkflowResult,
                      Step, Parallel, Gate, Branch, GateAction):
            self.assertIsNotNone(value)


class ReviewBoundaryTests(unittest.TestCase):
    def test_agent_review_level_boundaries(self):
        self.assertEqual(determine_review_level(["README.md"]), ReviewLevel.AI_SINGLE_PASS)
        self.assertEqual(determine_review_level(["app.py"]), ReviewLevel.STATIC_VERIFIED)
        self.assertEqual(determine_review_level([], lines_added=251, lines_deleted=250), ReviewLevel.MULTI_SPECIALIST)
        self.assertEqual(determine_review_level([], has_ui_changes=True), ReviewLevel.RUNTIME_VERIFIED)
        self.assertEqual(determine_review_level([], has_security_changes=True), ReviewLevel.PRODUCTION_SIMULATED)

    def test_review_verdict_model(self):
        verdict = ReviewVerdict(
            level=ReviewLevel.STATIC_VERIFIED, approved=False, confidence=0.8,
            summary="검토", findings=[{"severity": "blocking", "message": "문제"}],
        )
        self.assertTrue(verdict.has_blockers())
        self.assertEqual(verdict.to_dict()["level_name"], "STATIC_VERIFIED")
        self.assertIn("수정 필요", verdict.to_markdown())

    def test_loop_review_level_boundaries(self):
        self.assertEqual(determine_loop_level(["README.md"]), 1)
        self.assertEqual(determine_loop_level(["module.py"]), 2)
        self.assertEqual(determine_loop_level([], lines_changed=501), 3)
        self.assertEqual(determine_loop_level(["api/routes.py"]), 4)
        self.assertEqual(determine_loop_level(["auth/service.py"]), 5)


class WorkflowRegistryTests(unittest.TestCase):
    def test_registry_shape_and_unique_node_ids(self):
        expected = {"feature", "ui-feature", "bugfix", "small-change", "refactor",
                    "spec", "incident", "analyze", "docs", "review"}
        self.assertEqual(set(WORKFLOW_REGISTRY), expected)
        for key, factory in WORKFLOW_REGISTRY.items():
            name, nodes = factory("test")
            self.assertEqual(name, key)
            self.assertTrue(nodes)
            ids = [node.id for node in nodes]
            self.assertEqual(len(ids), len(set(ids)), key)
            self.assertTrue(all(isinstance(node, (Step, Parallel, Gate, Branch)) for node in nodes))


class ClaudeRunnerTests(unittest.TestCase):
    def test_command_shape(self):
        runner = ClaudeRunner(PROJECT_ROOT, max_budget_usd=7.0)
        command = runner._build_command(
            "hello", agent="reviewer", model="sonnet", max_turns=4,
            allowed_tools=["Read", "Grep"], max_budget_usd=2.5,
        )
        self.assertEqual(command[:4], ["claude", "-p", "--output-format", "json"])
        self.assertEqual(command[-1], "hello")
        self.assertIn("reviewer", command)
        self.assertIn("Read,Grep", command)
        self.assertIn("2.5", command)

    def test_json_and_text_output_parsing(self):
        runner = ClaudeRunner(PROJECT_ROOT, max_budget_usd=7.0)
        result = runner._parse_output(
            '{"result":"done","cost_usd":0.25,"session_id":"s1","num_turns":2,"is_error":false}',
            "reviewer", 1.5,
        )
        self.assertTrue(result.success)
        self.assertEqual((result.output, result.cost_usd, result.session_id), ("done", 0.25, "s1"))
        fallback = runner._parse_output("plain output", "coder", 0.1)
        self.assertEqual(fallback.output, "plain output")
        self.assertIsNone(fallback.raw_json)


class ImportCompileSmokeTests(unittest.TestCase):
    def test_public_modules_import(self):
        modules = (
            "agents.review_agent", "agents.review_models", "agents.review_basic",
            "agents.review_specialist", "agents.review_static",
            "agents.review_runtime", "agents.review_production",
            "orchestrator.claude_runner", "orchestrator.claude_result",
            "orchestrator.review_loop", "orchestrator.review_loop_models",
            "orchestrator.review_stages", "orchestrator.workflow_engine",
            "orchestrator.workflow_registry", "orchestrator.workflow_types",
        )
        for module in modules:
            self.assertIsNotNone(importlib.import_module(module))

    def test_project_python_files_compile(self):
        with tempfile.TemporaryDirectory() as cache_dir:
            for directory in ("agents", "orchestrator", "linters", "tests"):
                for source in (PROJECT_ROOT / directory).glob("*.py"):
                    target = Path(cache_dir) / f"{directory}-{source.stem}.pyc"
                    py_compile.compile(str(source), cfile=str(target), doraise=True)


if __name__ == "__main__":
    unittest.main()
