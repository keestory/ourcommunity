"""Review stages used by :class:`orchestrator.review_loop.ReviewLoop`."""

from orchestrator.review_loop_models import ReviewVerdict


class ReviewStagesMixin:
    async def _level_1(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """reviewer 에이전트가 코드를 읽고 피드백."""
        files_str = ", ".join(files) if files else "전체 프로젝트"

        result = await self.runner.run_agent(
            prompt=f"다음 코드/변경사항을 리뷰하세요:\n\n{target}\n\n관련 파일: {files_str}",
            agent="reviewer",
            max_turns=5,
            max_budget_usd=1.0,
        )

        approved = self._check_approval(result.output)
        return ReviewVerdict(
            level=1,
            approved=approved,
            summary=f"Level 1 — reviewer {'승인' if approved else '수정 필요'}",
            agent_results=[result],
            total_cost_usd=result.cost_usd,
        )

    async def _level_2(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """린터 실행 결과를 reviewer에 전달."""
        results = []

        lint_passed, lint_output = await self._run_linters()
        lint_context = f"린트 결과: {'통과' if lint_passed else '위반 있음'}\n{lint_output}"
        files_str = ", ".join(files) if files else "전체 프로젝트"

        result = await self.runner.run_agent(
            prompt=(
                f"다음 코드를 리뷰하세요:\n\n{target}\n\n"
                f"관련 파일: {files_str}\n\n"
                f"## 정적 검증 결과\n{lint_context}"
            ),
            agent="reviewer",
            max_turns=8,
            max_budget_usd=1.5,
        )
        results.append(result)

        approved = lint_passed and self._check_approval(result.output)
        return ReviewVerdict(
            level=2,
            approved=approved,
            summary=f"Level 2 — 린트:{'통과' if lint_passed else '위반'}, reviewer:{'승인' if self._check_approval(result.output) else '수정 필요'}",
            agent_results=results,
            lint_passed=lint_passed,
            total_cost_usd=sum(r.cost_usd for r in results),
            escalate_to=3 if not approved else None,
        )

    async def _level_3(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """reviewer + security-reviewer 병렬 실행 후 합의."""
        lint_passed, lint_output = await self._run_linters()
        files_str = ", ".join(files) if files else "전체 프로젝트"
        review_prompt = (
            f"다음 코드를 리뷰하세요:\n\n{target}\n\n"
            f"관련 파일: {files_str}\n\n"
            f"## 정적 검증 결과\n{lint_output}"
        )

        results = await self.runner.run_agents_parallel([
            {
                "prompt": review_prompt,
                "agent": "reviewer",
                "max_turns": 8,
                "max_budget_usd": 1.5,
            },
            {
                "prompt": f"다음 코드를 보안 관점에서 리뷰하세요:\n\n{target}\n\n관련 파일: {files_str}",
                "agent": "security-reviewer",
                "max_turns": 5,
                "max_budget_usd": 2.0,
            },
        ], max_concurrent=2)

        reviewer_approved = self._check_approval(results[0].output) if results[0].success else False
        security_approved = self._check_approval(results[1].output) if results[1].success else False
        approved = lint_passed and reviewer_approved and security_approved

        return ReviewVerdict(
            level=3,
            approved=approved,
            summary=(
                f"Level 3 — 린트:{'O' if lint_passed else 'X'} "
                f"reviewer:{'O' if reviewer_approved else 'X'} "
                f"security:{'O' if security_approved else 'X'}"
            ),
            agent_results=results,
            lint_passed=lint_passed,
            total_cost_usd=sum(r.cost_usd for r in results),
            escalate_to=4 if not approved else None,
        )

    async def _level_4(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """격리 환경에서 앱 구동, 테스트 실행 후 리뷰."""
        test_result = await self.runner.run_agent(
            prompt=(
                f"다음 변경사항에 대해 테스트를 실행하고 검증하세요:\n\n{target}\n\n"
                "1. 기존 테스트 실행: python3 -m pytest -v\n"
                "2. 실패 시 원인 분석\n"
                "3. 커버리지 보고"
            ),
            agent="tester",
            max_turns=10,
            max_budget_usd=1.5,
        )

        test_passed = test_result.success and "fail" not in test_result.output.lower()
        level3 = await self._level_3(target, files)
        all_results = [test_result] + level3.agent_results
        approved = test_passed and level3.approved

        return ReviewVerdict(
            level=4,
            approved=approved,
            summary=(
                f"Level 4 — 테스트:{'O' if test_passed else 'X'} "
                f"+ {level3.summary}"
            ),
            agent_results=all_results,
            lint_passed=level3.lint_passed,
            test_passed=test_passed,
            total_cost_usd=sum(r.cost_usd for r in all_results),
            escalate_to=5 if not approved else None,
        )

    async def _level_5(self, target: str, files: list[str] = None) -> ReviewVerdict:
        """Level 4 + quality-scorer + doc-gardener."""
        level4 = await self._level_4(target, files)

        extra_results = await self.runner.run_agents_parallel([
            {
                "prompt": "프로젝트 전체 품질을 평가하고 docs/QUALITY_SCORE.md를 업데이트하세요.",
                "agent": "quality-scorer",
                "max_turns": 8,
                "max_budget_usd": 1.0,
            },
            {
                "prompt": "docs/ 디렉토리를 스캔하여 코드 변경에 맞지 않는 문서를 찾고 업데이트하세요.",
                "agent": "doc-gardener",
                "max_turns": 8,
                "max_budget_usd": 1.0,
            },
        ], max_concurrent=2)

        all_results = level4.agent_results + extra_results
        approved = level4.approved

        return ReviewVerdict(
            level=5,
            approved=approved,
            summary=(
                f"Level 5 — {level4.summary} + "
                f"quality:{'O' if extra_results[0].success else 'X'} "
                f"docs:{'O' if extra_results[1].success else 'X'}"
            ),
            agent_results=all_results,
            lint_passed=level4.lint_passed,
            test_passed=level4.test_passed,
            total_cost_usd=sum(r.cost_usd for r in all_results),
        )
