"""Data types shared by workflow execution and workflow definitions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from orchestrator.claude_runner import ClaudeResult


class GateAction(Enum):
    PROCEED = "proceed"
    RETRY = "retry"
    LOOP_BACK = "loop_back"
    ESCALATE = "escalate"
    ABORT = "abort"


@dataclass
class Step:
    id: str
    agent: str
    label: str
    max_turns: int = 10
    max_budget_usd: float = 3.0
    prompt_override: str = ""


@dataclass
class Parallel:
    id: str
    steps: list[Step]
    label: str = ""


@dataclass
class Gate:
    id: str
    check: str
    label: str = ""
    on_fail: GateAction = GateAction.RETRY
    retry_step_id: str = ""
    max_retries: int = 2


@dataclass
class Branch:
    id: str
    condition: str
    if_true: list = field(default_factory=list)
    if_false: list = field(default_factory=list)


WorkflowNode = Union[Step, Parallel, Gate, Branch]


@dataclass
class WorkflowResult:
    success: bool
    workflow_name: str
    agent_results: dict[str, ClaudeResult] = field(default_factory=dict)
    gate_results: dict[str, str] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    total_duration: float = 0.0
    aborted: bool = False
    escalated: bool = False

    def to_markdown(self) -> str:
        lines = [
            f"# 워크플로 결과: {self.workflow_name}",
            f"**결과**: {'성공' if self.success else '실패'}",
            f"**비용**: ${self.total_cost_usd:.4f}",
            f"**소요**: {self.total_duration:.1f}초",
        ]
        if self.escalated:
            lines.append("**에스컬레이션**: 사람 검토 필요")

        lines.append("\n## 단계별 결과")
        for step_id, result in self.agent_results.items():
            status = "성공" if result.success else "실패"
            lines.append(f"- **{step_id}** [{result.agent}] {status} ({result.duration_seconds:.1f}s)")

        if self.gate_results:
            lines.append("\n## 게이트")
            for gate_id, verdict in self.gate_results.items():
                lines.append(f"- **{gate_id}**: {verdict}")

        return "\n".join(lines)
