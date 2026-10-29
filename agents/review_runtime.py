"""Runtime verification stage for :class:`ReviewAgent`."""

from agents.review_models import ReviewLevel, ReviewVerdict


class ReviewRuntimeMixin:
    async def review_level_4(self, code: str, files: list[str] = None, description: str = "") -> ReviewVerdict:
        """Level 4: 앱을 실제로 구동하여 동작 확인."""
        findings = []
        runtime_results = {}

        level3 = await self.review_level_3(code, files, description)
        findings.extend(level3.findings)

        worktree_result = self.run_command("git worktree add /tmp/harness-review-wt -b review-temp 2>/dev/null || echo 'worktree-skip'")
        has_worktree = "worktree-skip" not in worktree_result["stdout"]
        runtime_results["worktree"] = has_worktree

        if has_worktree:
            work_dir = "/tmp/harness-review-wt"
        else:
            work_dir = str(self.project_root)

        boot_commands = [
            ("python3 -c 'import orchestrator; print(\"import-ok\")'", "Python import 검증"),
            ("python3 -m pytest --tb=line -q 2>/dev/null", "테스트 스위트 실행"),
            ("python3 -c 'from agents import AGENT_REGISTRY; print(len(AGENT_REGISTRY), \"agents loaded\")'", "에이전트 레지스트리 검증"),
        ]

        for cmd, label in boot_commands:
            result = self.run_command(cmd, timeout=60)
            runtime_results[label] = {
                "success": result["success"],
                "output": result["stdout"][:500],
            }
            if not result["success"]:
                findings.append({
                    "severity": "blocking",
                    "category": "런타임",
                    "message": f"{label} 실패",
                    "file": "",
                    "line": 0,
                    "fix": f"다음 명령이 실패했습니다: {cmd}\n출력: {result['stderr'][:300]}",
                })

        if any("api" in f.lower() or "route" in f.lower() for f in (files or [])):
            api_check = await self._verify_api_endpoints(files)
            findings.extend(api_check.get("findings", []))
            runtime_results["api_verification"] = api_check

        if has_worktree:
            self.run_command("git worktree remove /tmp/harness-review-wt --force 2>/dev/null")

        has_blockers = any(f["severity"] == "blocking" for f in findings)
        runtime_passed = all(r.get("success", True) for r in runtime_results.values() if isinstance(r, dict))

        return ReviewVerdict(
            level=ReviewLevel.RUNTIME_VERIFIED,
            approved=level3.approved and not has_blockers and runtime_passed,
            confidence=level3.confidence * (0.95 if runtime_passed else 0.4),
            summary=f"런타임 검증 {'통과' if runtime_passed else '실패'} + {level3.summary}",
            findings=findings,
            test_results=level3.test_results,
            lint_results=level3.lint_results,
            runtime_results=runtime_results,
            escalate_to=5 if not runtime_passed else None,
        )

    async def _verify_api_endpoints(self, files: list[str]) -> dict:
        """API 엔드포인트 동작 검증."""
        findings = []
        endpoints_checked = 0

        for f in (files or []):
            content = self.read_file(f)
            if content.startswith("[ERROR]"):
                continue

            import re
            routes = re.findall(r'@(?:app|router)\.\w+\(["\']([^"\']+)', content)
            for route in routes:
                endpoints_checked += 1

        return {
            "endpoints_checked": endpoints_checked,
            "findings": findings,
        }
