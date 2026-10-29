"""Review levels, verdicts, and automatic level selection."""

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class ReviewLevel(IntEnum):
    """리뷰 깊이 레벨."""

    AI_SINGLE_PASS = 1        # AI가 코드만 읽고 판단
    STATIC_VERIFIED = 2       # 린터 + 테스트 + AI
    MULTI_SPECIALIST = 3      # 전문 리뷰어 3인 합의
    RUNTIME_VERIFIED = 4      # 앱을 실제로 구동하여 확인
    PRODUCTION_SIMULATED = 5  # 관측 가능성 + 사용자 여정 재현


@dataclass
class ReviewVerdict:
    """구조화된 리뷰 판정."""

    level: ReviewLevel
    approved: bool
    confidence: float
    summary: str
    findings: list[dict] = field(default_factory=list)
    test_results: Optional[dict] = None
    lint_results: Optional[dict] = None
    runtime_results: Optional[dict] = None
    escalate_to: Optional[int] = None

    def has_blockers(self) -> bool:
        return any(f["severity"] == "blocking" for f in self.findings)

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "level_name": self.level.name,
            "approved": self.approved,
            "confidence": self.confidence,
            "summary": self.summary,
            "blockers": [f for f in self.findings if f["severity"] == "blocking"],
            "warnings": [f for f in self.findings if f["severity"] == "warning"],
            "info": [f for f in self.findings if f["severity"] == "info"],
            "test_results": self.test_results,
            "lint_results": self.lint_results,
            "runtime_results": self.runtime_results,
            "escalate_to": self.escalate_to,
        }

    def to_markdown(self) -> str:
        blockers = [f for f in self.findings if f["severity"] == "blocking"]
        warnings = [f for f in self.findings if f["severity"] == "warning"]
        infos = [f for f in self.findings if f["severity"] == "info"]

        lines = [
            f"## 리뷰 판정 (Level {self.level.value}: {self.level.name})",
            f"**결과**: {'승인' if self.approved else '수정 필요'} (신뢰도: {self.confidence:.0%})",
            f"**요약**: {self.summary}",
        ]

        if blockers:
            lines.append(f"\n### 차단 이슈 ({len(blockers)}건)")
            for f in blockers:
                lines.append(f"- **[{f.get('category', '?')}]** {f['message']}")
                if f.get("file"):
                    lines.append(f"  파일: `{f['file']}`:{f.get('line', '?')}")
                if f.get("fix"):
                    lines.append(f"  수정: {f['fix']}")

        if warnings:
            lines.append(f"\n### 경고 ({len(warnings)}건)")
            for f in warnings:
                lines.append(f"- **[{f.get('category', '?')}]** {f['message']}")

        if infos:
            lines.append(f"\n### 참고 ({len(infos)}건)")
            for f in infos:
                lines.append(f"- {f['message']}")

        if self.test_results:
            lines.append(f"\n### 테스트: {'통과' if self.test_results.get('passed') else '실패'}")

        if self.escalate_to:
            lines.append(f"\n**에스컬레이션**: Level {self.escalate_to}로 추가 검증 필요")

        return "\n".join(lines)


def determine_review_level(
    files_changed: list[str],
    lines_added: int = 0,
    lines_deleted: int = 0,
    domains_affected: int = 1,
    has_ui_changes: bool = False,
    has_api_changes: bool = False,
    has_infra_changes: bool = False,
    has_security_changes: bool = False,
) -> ReviewLevel:
    """변경 내용에 따라 적절한 리뷰 레벨을 결정한다."""
    # Level 5: 인프라/배포/보안
    if has_infra_changes or has_security_changes:
        return ReviewLevel.PRODUCTION_SIMULATED

    # Level 4: UI 또는 API 변경
    if has_ui_changes or has_api_changes:
        return ReviewLevel.RUNTIME_VERIFIED

    # Level 3: 다중 도메인 또는 대규모 변경
    if domains_affected >= 2 or (lines_added + lines_deleted) > 500:
        return ReviewLevel.MULTI_SPECIALIST

    # Level 2: 단일 도메인 로직 변경
    if any(f.endswith(".py") or f.endswith(".ts") for f in files_changed):
        return ReviewLevel.STATIC_VERIFIED

    # Level 1: 문서/설정만
    return ReviewLevel.AI_SINGLE_PASS
