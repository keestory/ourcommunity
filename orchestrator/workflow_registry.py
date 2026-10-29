"""Built-in workflow definitions extracted from the workflow engine."""

from orchestrator.workflow_types import Branch, Gate, GateAction, Parallel, Step, WorkflowNode


def workflow_feature(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """풀사이클 기능 구현."""
    return "feature", [
        Parallel(id="plan-parallel", label="기획", steps=[
            Step(id="pm", agent="pm", label="제품 사양 및 수용 기준 정의", max_turns=10),
            Step(id="analyst-metrics", agent="analyst", label="성공 지표 설계", max_turns=8),
        ]),
        Step(id="designer", agent="designer", label="UI/UX 설계", max_turns=10),
        Step(id="planner", agent="planner", label="실행 계획 수립 (AC 체크리스트 포함)", max_turns=10),
        Step(id="coder", agent="coder", label="코드 구현 (AC 체크리스트 하나씩 확인)", max_turns=20, max_budget_usd=5.0),
        Gate(id="lint-gate", check="lint", label="린트 게이트",
             on_fail=GateAction.RETRY, retry_step_id="coder", max_retries=2),
        Parallel(id="verify-parallel", label="검증", steps=[
            Step(id="tester", agent="tester", label="테스트 작성 및 실행", max_turns=10),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰 + AC 검증", max_turns=10),
        ]),
        Gate(id="review-gate", check="review", label="리뷰 게이트",
             on_fail=GateAction.RETRY, retry_step_id="coder", max_retries=2),
        Parallel(id="deploy-parallel", label="배포 준비", steps=[
            Step(id="ops", agent="ops", label="배포 검토", max_turns=5),
            Step(id="analyst-verify", agent="analyst",
                 label="텔레메트리 구현 검증",
                 prompt_override="coder가 구현한 코드에서 analyst가 설계한 이벤트/로깅이 실제로 구현되었는지 확인하세요.",
                 max_turns=5),
        ]),
    ]


def workflow_ui_feature(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """UI 중심 기능 — 디자이너가 설계와 검증 모두 수행."""
    return "ui-feature", [
        Parallel(id="plan-parallel", label="기획", steps=[
            Step(id="pm", agent="pm", label="제품 사양 정의", max_turns=8),
            Step(id="analyst-metrics", agent="analyst", label="성공 지표 설계", max_turns=6),
        ]),
        Step(id="designer-design", agent="designer", label="화면 설계 및 인터랙션 정의", max_turns=12),
        Step(id="planner", agent="planner", label="구현 계획", max_turns=8),
        Step(id="coder", agent="coder", label="UI 구현", max_turns=20, max_budget_usd=5.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
        Parallel(id="review-parallel", label="리뷰", steps=[
            Step(id="designer-review", agent="designer", label="UX 리뷰 및 접근성 검증", max_turns=8),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=8),
        ]),
        Gate(id="review-gate", check="review", on_fail=GateAction.RETRY, retry_step_id="coder"),
    ]


def workflow_bugfix(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """버그 수정 — 빠르게, 하지만 검증은 철저히."""
    return "bugfix", [
        Step(id="coder", agent="coder", label="버그 재현 및 수정", max_turns=15, max_budget_usd=3.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
        Parallel(id="verify-parallel", label="검증", steps=[
            Step(id="tester", agent="tester", label="수정 검증 + 회귀 테스트", max_turns=10),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=8),
        ]),
        Gate(id="review-gate", check="review", on_fail=GateAction.RETRY, retry_step_id="coder"),
    ]


def workflow_small_change(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """설정, 문구, 스타일 등 작은 변경."""
    return "small-change", [
        Step(id="coder", agent="coder", label="변경 구현", max_turns=8, max_budget_usd=1.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
    ]


def workflow_refactor(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """리팩터링."""
    return "refactor", [
        Step(id="quality", agent="quality-scorer", label="현재 품질 평가", max_turns=8),
        Step(id="planner", agent="planner", label="리팩터링 계획", max_turns=10),
        Step(id="coder", agent="coder", label="리팩터링 실행", max_turns=20, max_budget_usd=5.0),
        Gate(id="lint-gate", check="lint", on_fail=GateAction.RETRY, retry_step_id="coder"),
        Parallel(id="verify-parallel", label="검증", steps=[
            Step(id="tester", agent="tester", label="회귀 테스트", max_turns=10),
            Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=8),
        ]),
        Gate(id="review-gate", check="review", on_fail=GateAction.RETRY, retry_step_id="coder"),
        Step(id="quality-after", agent="quality-scorer", label="리팩터링 후 품질 재평가", max_turns=5),
    ]


def workflow_spec(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """제품 기획만 (구현 없이)."""
    return "spec", [
        Step(id="pm", agent="pm", label="제품 사양 작성", max_turns=12),
        Step(id="analyst", agent="analyst", label="성공 지표 설계", max_turns=8),
        Step(id="designer", agent="designer", label="UI/UX 설계", max_turns=10),
    ]


def workflow_incident(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """장애 대응 — 완화 → 수정 → 검증 → 포스트모템."""
    return "incident", [
        Step(id="ops-analyze", agent="ops", label="장애 분석 및 완화 판단", max_turns=10),
        Step(id="coder", agent="coder", label="핫픽스 구현", max_turns=15, max_budget_usd=3.0),
        Parallel(id="verify-parallel", label="핫픽스 검증", steps=[
            Step(id="tester", agent="tester", label="핫픽스 검증", max_turns=8),
            Step(id="reviewer", agent="reviewer", label="핫픽스 리뷰", max_turns=5),
        ]),
        Step(id="ops-deploy", agent="ops", label="배포 및 모니터링 포인트 정의", max_turns=5),
        Step(id="postmortem", agent="planner",
             label="포스트모템 작성",
             prompt_override=(
                 "이번 장애에 대한 포스트모템을 작성하세요.\n"
                 "포함 항목: 타임라인, 영향 범위, 근본 원인, 완화 과정, "
                 "재발 방지 액션 아이템.\n"
                 "docs/exec-plans/active/ 에 postmortem-<날짜>.md로 저장하세요."
             ),
             max_turns=8),
    ]


def workflow_analyze(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """출시 후 효과 분석."""
    return "analyze", [
        Step(id="analyst", agent="analyst", label="지표 분석 및 결론", max_turns=10),
        Step(id="pm", agent="pm",
             label="분석 결과 기반 다음 행동 결정",
             prompt_override=(
                 "analyst의 분석 결과를 바탕으로 다음 행동을 결정하세요:\n"
                 "- 유지 (지표 개선 확인)\n"
                 "- 반복 (추가 개선 필요 → 새 제품 사양 작성)\n"
                 "- 롤백 (가드레일 지표 악화)\n"
                 "결정과 근거를 docs/product-specs/에 기록하세요."
             ),
             max_turns=8),
    ]


def workflow_docs(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """문서 관리."""
    return "docs", [
        Step(id="doc-gardener", agent="doc-gardener", label="문서 스캔 및 업데이트", max_turns=10),
        Gate(id="struct-gate", check="lint", label="구조 검증"),
    ]


def workflow_review(prompt: str) -> tuple[str, list[WorkflowNode]]:
    """코드 리뷰만."""
    return "review", [
        Step(id="reviewer", agent="reviewer", label="코드 리뷰", max_turns=10),
        Branch(id="security-branch", condition="has_security_concern",
               if_true=[Step(id="security", agent="security-reviewer", label="보안 리뷰", max_turns=8)],
               if_false=[]),
    ]


WORKFLOW_REGISTRY = {
    "feature": workflow_feature,
    "ui-feature": workflow_ui_feature,
    "bugfix": workflow_bugfix,
    "small-change": workflow_small_change,
    "refactor": workflow_refactor,
    "spec": workflow_spec,
    "incident": workflow_incident,
    "analyze": workflow_analyze,
    "docs": workflow_docs,
    "review": workflow_review,
}
