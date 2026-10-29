"""Workflow execution engine and backward-compatible public workflow API."""

import logging
import time
from pathlib import Path

from orchestrator.claude_runner import ClaudeRunner, ClaudeResult
from orchestrator.handoff import build_handoff_prompt
from orchestrator.workflow_registry import (
    WORKFLOW_REGISTRY, workflow_analyze, workflow_bugfix, workflow_docs,
    workflow_feature, workflow_incident, workflow_refactor, workflow_review,
    workflow_small_change, workflow_spec, workflow_ui_feature,
)
from orchestrator.workflow_types import (
    Branch, Gate, GateAction, Parallel, Step, WorkflowNode, WorkflowResult,
)

logger = logging.getLogger("harness.workflow")


class WorkflowEngine:
    """병렬 실행, 게이트, 분기, 핸드오프 프로토콜을 지원."""

    def __init__(self, project_root: Path, runner: ClaudeRunner = None):
        self.project_root = project_root
        self.runner = runner or ClaudeRunner(project_root)
        self._outputs: dict[str, str] = {}
        self._results: dict[str, ClaudeResult] = {}
        self._gate_results: dict[str, str] = {}
        self._retry_counts: dict[str, int] = {}

    async def execute(
        self,
        workflow_name: str,
        nodes: list[WorkflowNode],
        prompt: str,
    ) -> WorkflowResult:
        """워크플로 실행."""
        start_time = time.time()
        self._outputs = {}
        self._results = {}
        self._gate_results = {}
        self._retry_counts = {}

        logger.info(f"워크플로 시작: {workflow_name} ({len(nodes)}개 노드)")

        i = 0
        while i < len(nodes):
            node = nodes[i]

            if isinstance(node, Step):
                result = await self._execute_step(node, prompt)
                if not result.success:
                    logger.error(f"[{node.id}] 실패 — 워크플로 중단")
                    return self._build_result(workflow_name, False, start_time)
                i += 1

            elif isinstance(node, Parallel):
                results = await self._execute_parallel(node, prompt)
                if any(not r.success for r in results):
                    failed = [r.agent for r in results if not r.success]
                    logger.error(f"[{node.id}] 병렬 실패: {failed}")
                    return self._build_result(workflow_name, False, start_time)
                i += 1

            elif isinstance(node, Gate):
                action = await self._execute_gate(node)
                if action == GateAction.PROCEED:
                    i += 1
                elif action == GateAction.RETRY:
                    retry_target = node.retry_step_id or (nodes[i-1].id if i > 0 else None)
                    if retry_target:
                        retry_idx = next(
                            (j for j, n in enumerate(nodes)
                             if hasattr(n, 'id') and n.id == retry_target),
                            max(0, i - 1)
                        )
                        i = retry_idx
                        logger.info(f"[{node.id}] 재시도 → {retry_target}")
                    else:
                        i += 1
                elif action == GateAction.ESCALATE:
                    return self._build_result(workflow_name, False, start_time, escalated=True)
                elif action == GateAction.ABORT:
                    return self._build_result(workflow_name, False, start_time, aborted=True)
                else:
                    i += 1

            elif isinstance(node, Branch):
                branch_nodes = self._evaluate_branch(node)
                nodes = nodes[:i] + branch_nodes + nodes[i+1:]

            else:
                i += 1

        return self._build_result(workflow_name, True, start_time)

    async def _execute_step(self, step: Step, base_prompt: str) -> ClaudeResult:
        """단일 에이전트 실행."""
        prompt = build_handoff_prompt(
            current_agent=step.agent,
            prompt=step.prompt_override or f"{step.label}\n\n{base_prompt}",
            previous_outputs=self._outputs,
        )

        logger.info(f"[{step.id}] {step.agent}: {step.label}")

        result = await self.runner.run_agent(
            prompt=prompt,
            agent=step.agent,
            max_turns=step.max_turns,
            max_budget_usd=step.max_budget_usd,
        )

        self._results[step.id] = result
        if result.success:
            self._outputs[step.agent] = result.output

        return result

    async def _execute_parallel(self, parallel: Parallel, base_prompt: str) -> list[ClaudeResult]:
        """병렬 에이전트 실행."""
        logger.info(f"[{parallel.id}] 병렬 실행: {[s.agent for s in parallel.steps]}")

        tasks = []
        for step in parallel.steps:
            prompt = build_handoff_prompt(
                current_agent=step.agent,
                prompt=step.prompt_override or f"{step.label}\n\n{base_prompt}",
                previous_outputs=self._outputs,
            )
            tasks.append({
                "prompt": prompt,
                "agent": step.agent,
                "max_turns": step.max_turns,
                "max_budget_usd": step.max_budget_usd,
            })

        results = await self.runner.run_agents_parallel(tasks, max_concurrent=3)

        for step, result in zip(parallel.steps, results):
            self._results[step.id] = result
            if result.success:
                self._outputs[step.agent] = result.output

        return results

    async def _execute_gate(self, gate: Gate) -> GateAction:
        """게이트 체크 실행."""
        gate_key = gate.id
        self._retry_counts.setdefault(gate_key, 0)

        if self._retry_counts[gate_key] >= gate.max_retries:
            logger.warning(f"[{gate.id}] 최대 재시도({gate.max_retries}) 도달 → 에스컬레이션")
            self._gate_results[gate.id] = "ESCALATED"
            return GateAction.ESCALATE

        passed = False
        if gate.check == "lint":
            passed = await self._gate_lint()
        elif gate.check == "test":
            passed = await self._gate_test()
        elif gate.check == "review":
            passed = self._gate_review_approved()
        elif gate.check == "budget":
            passed = self._gate_budget_ok()
        else:
            passed = True

        if passed:
            self._gate_results[gate.id] = "PASS"
            logger.info(f"[{gate.id}] 게이트 통과")
            return GateAction.PROCEED
        else:
            self._retry_counts[gate_key] += 1
            self._gate_results[gate.id] = f"FAIL (시도 {self._retry_counts[gate_key]}/{gate.max_retries})"
            logger.info(f"[{gate.id}] 게이트 실패 → {gate.on_fail.value}")
            return gate.on_fail

    def _evaluate_branch(self, branch: Branch) -> list:
        """분기 조건 평가."""
        condition = branch.condition.lower()
        all_output = " ".join(self._outputs.values()).lower()
        if condition == "has_ui":
            result = any(kw in all_output for kw in ["ui", "화면", "페이지", "컴포넌트"])
        elif condition == "has_security_concern":
            result = any(kw in all_output for kw in ["보안", "인증", "권한", "security"])
        elif condition == "needs_migration":
            result = any(kw in all_output for kw in ["마이그레이션", "migration", "스키마"])
        else:
            result = False
        return branch.if_true if result else branch.if_false

    async def _gate_lint(self) -> bool:
        """린터 통과 여부."""
        import subprocess
        for cmd in [
            "python3 linters/architecture_linter.py .",
            "python3 linters/structure_validator.py .",
        ]:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=str(self.project_root), timeout=30,
            )
            if proc.returncode != 0:
                return False
        return True

    async def _gate_test(self) -> bool:
        """테스트 통과 여부."""
        import subprocess
        proc = subprocess.run(
            "python3 -m pytest -q 2>/dev/null",
            shell=True, capture_output=True, text=True,
            cwd=str(self.project_root), timeout=120,
        )
        return proc.returncode == 0

    def _gate_review_approved(self) -> bool:
        """리뷰어 승인 여부."""
        reviewer_output = self._outputs.get("reviewer", "")
        if not reviewer_output:
            return False
        lower = reviewer_output.lower()
        if any(kw in lower for kw in ["차단", "block", "수정 필요"]):
            return False
        return any(kw in lower for kw in ["승인", "approve", "lgtm", "통과"])

    def _gate_budget_ok(self) -> bool:
        """비용 한도 내인지."""
        total = sum(r.cost_usd for r in self._results.values())
        return total < 20.0

    def _build_result(
        self, name: str, success: bool, start_time: float,
        escalated: bool = False, aborted: bool = False,
    ) -> WorkflowResult:
        return WorkflowResult(
            success=success,
            workflow_name=name,
            agent_results=dict(self._results),
            gate_results=dict(self._gate_results),
            total_cost_usd=sum(r.cost_usd for r in self._results.values()),
            total_duration=time.time() - start_time,
            escalated=escalated,
            aborted=aborted,
        )


__all__ = [
    "Branch", "Gate", "GateAction", "Parallel", "Step", "WorkflowEngine",
    "WorkflowNode", "WorkflowResult", "WORKFLOW_REGISTRY", "workflow_feature",
    "workflow_ui_feature", "workflow_bugfix", "workflow_small_change", "workflow_refactor",
    "workflow_spec", "workflow_incident", "workflow_analyze", "workflow_docs", "workflow_review",
]
