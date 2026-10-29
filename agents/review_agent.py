"""Public review-agent API assembled from focused review modules."""

from agents.base_agent import BaseAgent
from agents.review_models import ReviewLevel, ReviewVerdict, determine_review_level
from agents.review_production import ReviewProductionMixin
from agents.review_runtime import ReviewRuntimeMixin
from agents.review_static import ReviewStaticMixin


class ReviewAgent(ReviewStaticMixin, ReviewRuntimeMixin, ReviewProductionMixin, BaseAgent):
    """다중 레벨 코드 리뷰를 수행하는 에이전트."""

    name = "reviewer"
    description = "다중 레벨 코드 리뷰를 수행하는 에이전트"

    async def review(
        self,
        code: str,
        files: list[str] = None,
        description: str = "",
        level: ReviewLevel = None,
        auto_level: bool = True,
        **kwargs,
    ) -> ReviewVerdict:
        """지정하거나 자동 선택한 깊이로 리뷰를 실행한다."""
        if level is None and auto_level:
            level = determine_review_level(
                files_changed=files or [],
                has_ui_changes=kwargs.get("has_ui_changes", False),
                has_api_changes=kwargs.get("has_api_changes", False),
                has_infra_changes=kwargs.get("has_infra_changes", False),
                has_security_changes=kwargs.get("has_security_changes", False),
                domains_affected=kwargs.get("domains_affected", 1),
                lines_added=kwargs.get("lines_added", 0),
                lines_deleted=kwargs.get("lines_deleted", 0),
            )
        elif level is None:
            level = ReviewLevel.STATIC_VERIFIED

        self.log(f"리뷰 시작 — Level {level.value}: {level.name}")

        dispatch = {
            ReviewLevel.AI_SINGLE_PASS: self.review_level_1,
            ReviewLevel.STATIC_VERIFIED: self.review_level_2,
            ReviewLevel.MULTI_SPECIALIST: self.review_level_3,
            ReviewLevel.RUNTIME_VERIFIED: self.review_level_4,
            ReviewLevel.PRODUCTION_SIMULATED: self.review_level_5,
        }

        handler = dispatch[level]
        if level == ReviewLevel.AI_SINGLE_PASS:
            verdict = await handler(code, description)
        else:
            verdict = await handler(code, files, description)

        self.log(
            f"리뷰 완료 — Level {verdict.level.value}: "
            f"{'승인' if verdict.approved else '수정 필요'} "
            f"(신뢰도: {verdict.confidence:.0%})"
        )
        return verdict

    def get_system_prompt(self) -> str:
        return "다중 레벨 리뷰 에이전트. review() 메서드를 사용하세요."

    async def execute(self, task_description: str, context: dict = None) -> str:
        verdict = await self.review(code=task_description, description=str(context or {}))
        return verdict.to_markdown()

    async def review_code(self, code: str, description: str = "") -> dict:
        verdict = await self.review(code=code, description=description)
        return {
            "approved": verdict.approved,
            "review": verdict.to_markdown(),
            "has_blocking_issues": verdict.has_blockers(),
            "verdict": verdict.to_dict(),
        }

    async def review_pr(self, diff: str, pr_description: str = "") -> dict:
        return await self.review_code(diff, pr_description)


__all__ = ["ReviewAgent", "ReviewLevel", "ReviewVerdict", "determine_review_level"]
