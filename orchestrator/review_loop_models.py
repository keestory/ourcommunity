"""Models and boundary rules for the Claude-based review loop."""

from dataclasses import dataclass, field
from typing import Optional

from orchestrator.claude_runner import ClaudeResult


@dataclass
class ReviewVerdict:
    level: int
    approved: bool
    summary: str
    agent_results: list[ClaudeResult] = field(default_factory=list)
    lint_passed: bool = True
    test_passed: bool = True
    total_cost_usd: float = 0.0
    escalate_to: Optional[int] = None

    def to_markdown(self) -> str:
        lines = [
            f"## 리뷰 판정 (Level {self.level})",
            f"**결과**: {'승인' if self.approved else '수정 필요'}",
            f"**린트**: {'통과' if self.lint_passed else '위반'}",
            f"**테스트**: {'통과' if self.test_passed else '실패'}",
            f"**비용**: ${self.total_cost_usd:.4f}",
            f"**요약**: {self.summary}",
        ]
        for r in self.agent_results:
            status = "성공" if r.success else "실패"
            lines.append(f"\n### [{r.agent}] {status} ({r.duration_seconds:.1f}s)")
            lines.append(r.output[:1000] if r.output else "(출력 없음)")
        return "\n".join(lines)


def determine_review_level(
    files_changed: list[str] = None,
    lines_changed: int = 0,
    domains_affected: int = 1,
) -> int:
    """변경 내용에 따라 리뷰 레벨 자동 결정."""
    files = files_changed or []

    infra_patterns = ["deploy", "docker", "ci", "security", "auth", "permission"]
    if any(any(p in f.lower() for p in infra_patterns) for f in files):
        return 5

    ui_api_patterns = ["ui/", "api/", "route", "endpoint", "app.py", "server"]
    if any(any(p in f.lower() for p in ui_api_patterns) for f in files):
        return 4

    if domains_affected >= 2 or lines_changed > 500:
        return 3

    if any(f.endswith((".py", ".ts", ".js")) for f in files):
        return 2

    return 1
