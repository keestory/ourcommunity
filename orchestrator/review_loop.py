"""Claude-agent review loop with backward-compatible public imports."""

import logging
from pathlib import Path

from orchestrator.claude_runner import ClaudeRunner, ClaudeResult
from orchestrator.review_loop_models import ReviewVerdict, determine_review_level
from orchestrator.review_stages import ReviewStagesMixin

logger = logging.getLogger("harness.review")


class ReviewLoop(ReviewStagesMixin):
    """다중 레벨 리뷰 루프."""

    def __init__(self, project_root: Path, runner: ClaudeRunner = None):
        self.project_root = project_root
        self.runner = runner or ClaudeRunner(project_root)

    async def review(
        self,
        target: str,
        level: int = None,
        files_changed: list[str] = None,
        max_iterations: int = 3,
    ) -> ReviewVerdict:
        """리뷰 실행."""
        if level is None:
            level = determine_review_level(files_changed)

        logger.info(f"리뷰 시작 — Level {level}")

        dispatch = {
            1: self._level_1,
            2: self._level_2,
            3: self._level_3,
            4: self._level_4,
            5: self._level_5,
        }

        handler = dispatch.get(level, self._level_2)
        return await handler(target, files_changed)

    async def review_loop(
        self,
        task: str,
        level: int = None,
        files: list[str] = None,
        max_iterations: int = 3,
    ) -> ReviewVerdict:
        """coder → reviewer 반복 루프."""
        if level is None:
            level = determine_review_level(files)

        accumulated_feedback = ""
        all_results: list[ClaudeResult] = []

        for iteration in range(1, max_iterations + 1):
            logger.info(f"=== Ralph Wiggum Loop: 반복 {iteration}/{max_iterations} (Level {level}) ===")

            coder_prompt = f"{task}"
            if accumulated_feedback:
                coder_prompt += f"\n\n## 이전 리뷰 피드백 (반드시 반영하세요)\n{accumulated_feedback}"

            coder_result = await self.runner.run_agent(
                prompt=coder_prompt,
                agent="coder",
                max_turns=15,
                max_budget_usd=3.0,
            )
            all_results.append(coder_result)

            if not coder_result.success:
                logger.error(f"coder 실패: {coder_result.output[:200]}")
                return ReviewVerdict(
                    level=level,
                    approved=False,
                    summary=f"coder 실패 (반복 {iteration})",
                    agent_results=all_results,
                    total_cost_usd=sum(r.cost_usd for r in all_results),
                )

            verdict = await self.review(
                target=f"coder 에이전트의 작업 결과:\n\n{coder_result.output[:3000]}",
                level=level,
                files_changed=files,
            )
            all_results.extend(verdict.agent_results)

            if verdict.approved:
                logger.info(f"승인 — 반복 {iteration}, Level {level}")
                return ReviewVerdict(
                    level=level,
                    approved=True,
                    summary=f"반복 {iteration}에서 Level {level} 승인",
                    agent_results=all_results,
                    lint_passed=verdict.lint_passed,
                    test_passed=verdict.test_passed,
                    total_cost_usd=sum(r.cost_usd for r in all_results),
                )

            feedback_parts = [r.output[:500] for r in verdict.agent_results if r.output]
            accumulated_feedback = "\n\n---\n\n".join(feedback_parts)
            logger.info(f"수정 필요 — 반복 {iteration}, 피드백 {len(feedback_parts)}건")

            if verdict.escalate_to and verdict.escalate_to > level:
                level = verdict.escalate_to
                logger.info(f"에스컬레이션 → Level {level}")

        logger.warning(f"최대 반복({max_iterations}) 도달 — 사람 에스컬레이션")
        return ReviewVerdict(
            level=level,
            approved=False,
            summary=f"최대 반복 도달 — Level {level}에서 {max_iterations}회 시도",
            agent_results=all_results,
            total_cost_usd=sum(r.cost_usd for r in all_results),
        )

    async def _run_linters(self) -> tuple[bool, str]:
        """모든 린터 실행 (로컬, Claude Code 호출 없이)."""
        import subprocess
        results = []
        all_passed = True

        linters = [
            ("아키텍처", "python3 linters/architecture_linter.py ."),
            ("네이밍", "python3 linters/naming_linter.py ."),
            ("구조", "python3 linters/structure_validator.py ."),
        ]

        for name, cmd in linters:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=str(self.project_root), timeout=30,
            )
            passed = proc.returncode == 0
            if not passed:
                all_passed = False
            results.append(f"[{name}] {'통과' if passed else '위반'}: {proc.stdout[:300]}")

        return all_passed, "\n".join(results)

    def _check_approval(self, output: str) -> bool:
        """리뷰 출력에서 승인 여부 판단."""
        if not output:
            return False
        lower = output.lower()
        if any(kw in lower for kw in ["차단", "block", "critical", "위험", "수정 필요"]):
            return False
        return any(kw in lower for kw in ["승인", "approve", "lgtm", "통과", "안전"])


__all__ = ["ReviewLoop", "ReviewVerdict", "determine_review_level"]
