"""Behavioral-oracle regression tests for the module extraction."""

import tempfile
import unittest
from pathlib import Path

from agents.review_agent import ReviewAgent, ReviewLevel, ReviewVerdict
from orchestrator.claude_runner import ClaudeResult
from orchestrator.workflow_engine import (
    Gate, GateAction, Parallel, Step, WorkflowEngine,
    workflow_analyze, workflow_feature, workflow_incident,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class RecordingRunner:
    def __init__(self, parallel_results=None):
        self.agent_calls = []
        self.parallel_calls = []
        self.parallel_results = parallel_results or []

    async def run_agent(self, **kwargs):
        self.agent_calls.append(kwargs)
        return ClaudeResult(agent=kwargs["agent"], success=True, output="완료")

    async def run_agents_parallel(self, tasks, max_concurrent=3):
        self.parallel_calls.append((tasks, max_concurrent))
        return self.parallel_results


class WorkflowDefinitionBehaviorTests(unittest.TestCase):
    def test_exact_incident_prompt_and_budgets(self):
        _, nodes = workflow_incident("ignored")
        coder = next(node for node in nodes if node.id == "coder")
        postmortem = next(node for node in nodes if node.id == "postmortem")
        self.assertEqual((coder.max_turns, coder.max_budget_usd), (15, 3.0))
        self.assertEqual(postmortem.max_turns, 8)
        self.assertEqual(
            postmortem.prompt_override,
            "이번 장애에 대한 포스트모템을 작성하세요.\n"
            "포함 항목: 타임라인, 영향 범위, 근본 원인, 완화 과정, 재발 방지 액션 아이템.\n"
            "docs/exec-plans/active/ 에 postmortem-<날짜>.md로 저장하세요.",
        )

    def test_exact_analyze_and_feature_prompts(self):
        _, analyze_nodes = workflow_analyze("ignored")
        pm = next(node for node in analyze_nodes if node.id == "pm")
        self.assertEqual(
            pm.prompt_override,
            "analyst의 분석 결과를 바탕으로 다음 행동을 결정하세요:\n"
            "- 유지 (지표 개선 확인)\n"
            "- 반복 (추가 개선 필요 → 새 제품 사양 작성)\n"
            "- 롤백 (가드레일 지표 악화)\n"
            "결정과 근거를 docs/product-specs/에 기록하세요.",
        )
        _, feature_nodes = workflow_feature("ignored")
        deploy = next(node for node in feature_nodes if node.id == "deploy-parallel")
        analyst = next(step for step in deploy.steps if step.id == "analyst-verify")
        self.assertEqual(analyst.max_budget_usd, 3.0)
        self.assertEqual(
            analyst.prompt_override,
            "coder가 구현한 코드에서 analyst가 설계한 이벤트/로깅이 실제로 구현되었는지 확인하세요.",
        )


class ReviewAgentBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_user_journey_requires_success_and_ok(self):
        agent = ReviewAgent(PROJECT_ROOT)
        responses = iter([
            {"success": True, "stdout": "FAIL\n", "stderr": "", "returncode": 0},
            {"success": True, "stdout": "lint ok", "stderr": "", "returncode": 0},
            {"success": True, "stdout": "OK", "stderr": "", "returncode": 0},
        ])
        agent.run_command = lambda *args, **kwargs: next(responses)
        result = await agent._verify_user_journeys()
        self.assertNotIn({"name": "오케스트레이터 드라이런"}, result["passed"])
        self.assertEqual(result["failed"][0]["name"], "오케스트레이터 드라이런")
        self.assertEqual(result["failed"][0]["reason"], "출력 없음")

    async def test_level_dispatch_preserves_call_shape(self):
        agent = ReviewAgent(PROJECT_ROOT)
        calls = []

        async def level1(code, description):
            calls.append((1, code, description))
            return ReviewVerdict(ReviewLevel.AI_SINGLE_PASS, True, 1.0, "ok")

        async def level2(code, files, description):
            calls.append((2, code, files, description))
            return ReviewVerdict(ReviewLevel.STATIC_VERIFIED, True, 1.0, "ok")

        agent.review_level_1 = level1
        agent.review_level_2 = level2
        await agent.review("docs", description="d", level=ReviewLevel.AI_SINGLE_PASS)
        await agent.review("code", files=["a.py"], description="c", level=ReviewLevel.STATIC_VERIFIED)
        self.assertEqual(calls, [(1, "docs", "d"), (2, "code", ["a.py"], "c")])

    async def test_security_diagnostic_preserves_line_and_fix(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.py").write_text("import subprocess\nsubprocess.run('x', shell=True)\n", encoding="utf-8")
            agent = ReviewAgent(root)
            result = await agent._deep_security_scan()
        shell_finding = next(f for f in result["findings"] if f["category"] == "보안: 명령 인젝션 위험")
        self.assertEqual(shell_finding["line"], 2)
        self.assertEqual(
            shell_finding["fix"],
            "subprocess.run(cmd_list) 형식으로 변경하거나, shlex.quote()로 이스케이프하세요",
        )

    async def test_level_three_vote_summary_and_aggregation(self):
        agent = ReviewAgent(PROJECT_ROOT)
        specialist_results = iter([
            {"approved": True, "confidence": 0.9, "findings": []},
            {"approved": False, "confidence": 0.6, "findings": []},
            {"approved": True, "confidence": 0.9, "findings": []},
        ])

        async def specialist(*args):
            return next(specialist_results)

        async def level2(*args):
            return ReviewVerdict(
                ReviewLevel.STATIC_VERIFIED, True, 0.9, "static",
                findings=[{"severity": "warning", "category": "정적", "message": "warn"}],
                test_results={"passed": True}, lint_results={"architecture": True},
            )

        agent._specialist_review = specialist
        agent.review_level_2 = level2
        verdict = await agent.review_level_3("code")
        self.assertTrue(verdict.approved)
        self.assertEqual(verdict.summary, "전문 리뷰어 투표: 2/3 승인 (보안:O 아키텍처:X 도메인:O)")
        self.assertEqual(verdict.findings[-1]["category"], "정적")


class WorkflowEngineBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_retry_then_escalate(self):
        runner = RecordingRunner()
        engine = WorkflowEngine(PROJECT_ROOT, runner)

        async def fail_lint():
            return False

        engine._gate_lint = fail_lint
        nodes = [
            Step("coder", "coder", "구현"),
            Gate("lint", "lint", on_fail=GateAction.RETRY, retry_step_id="coder", max_retries=1),
        ]
        result = await engine.execute("retry", nodes, "task")
        self.assertFalse(result.success)
        self.assertTrue(result.escalated)
        self.assertEqual(len(runner.agent_calls), 2)
        self.assertEqual(result.gate_results["lint"], "ESCALATED")

    async def test_parallel_records_results_and_stops_on_failure(self):
        outputs = [
            ClaudeResult(agent="tester", success=True, output="ok"),
            ClaudeResult(agent="reviewer", success=False, output="fail"),
        ]
        runner = RecordingRunner(outputs)
        engine = WorkflowEngine(PROJECT_ROOT, runner)
        parallel = Parallel("verify", [
            Step("tester", "tester", "테스트"),
            Step("reviewer", "reviewer", "리뷰"),
        ])
        result = await engine.execute("parallel", [parallel], "task")
        self.assertFalse(result.success)
        self.assertEqual(set(result.agent_results), {"tester", "reviewer"})
        self.assertEqual(runner.parallel_calls[0][1], 3)
        self.assertEqual([task["agent"] for task in runner.parallel_calls[0][0]], ["tester", "reviewer"])


if __name__ == "__main__":
    unittest.main()
