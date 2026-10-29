"""Single-pass and static-verified review stages."""

import json
import re

from agents.review_models import ReviewLevel, ReviewVerdict


class ReviewBasicMixin:
    async def review_level_1(self, code: str, description: str = "") -> ReviewVerdict:
        """Level 1: AI가 코드를 읽고 피드백."""
        system = """당신은 시니어 코드 리뷰어입니다.
코드를 검토하고 반드시 다음 JSON 형식으로 응답하세요:

{
  "approved": true/false,
  "confidence": 0.0~1.0,
  "summary": "한 줄 요약",
  "findings": [
    {"severity": "blocking|warning|info", "category": "카테고리", "message": "설명", "file": "파일", "line": 0, "fix": "수정 제안"}
  ]
}

리뷰 기준: 정확성, 가독성, 네이밍, 불필요한 복잡성"""

        response = await self.call_model(
            [{"role": "user", "content": f"설명: {description}\n\n```\n{code}\n```"}],
            model="claude-sonnet-4-6",
        )

        parsed = self._parse_json_response(response)
        return ReviewVerdict(
            level=ReviewLevel.AI_SINGLE_PASS,
            approved=parsed.get("approved", False),
            confidence=parsed.get("confidence", 0.5),
            summary=parsed.get("summary", "Level 1 리뷰 완료"),
            findings=parsed.get("findings", []),
        )

    async def review_level_2(self, code: str, files: list[str] = None, description: str = "") -> ReviewVerdict:
        """Level 2: 린터 + 테스트 + AI."""
        findings = []

        lint_output = self.run_command("python3 linters/architecture_linter.py .")
        lint_clean = lint_output["success"]
        if not lint_clean:
            findings.append({
                "severity": "blocking",
                "category": "아키텍처",
                "message": f"아키텍처 린트 위반 발견",
                "file": "",
                "line": 0,
                "fix": lint_output["stdout"][:500],
            })

        name_output = self.run_command("python3 linters/naming_linter.py .")
        if not name_output["success"]:
            findings.append({
                "severity": "warning",
                "category": "네이밍",
                "message": "네이밍 컨벤션 위반 발견",
                "file": "",
                "line": 0,
                "fix": name_output["stdout"][:500],
            })

        struct_output = self.run_command("python3 linters/structure_validator.py .")
        if not struct_output["success"]:
            findings.append({
                "severity": "warning",
                "category": "구조",
                "message": "프로젝트 구조 위반 발견",
                "file": "",
                "line": 0,
                "fix": struct_output["stdout"][:500],
            })

        test_output = self.run_command("python3 -m pytest --tb=short -q 2>/dev/null")
        test_passed = test_output["success"]
        test_results = {
            "passed": test_passed,
            "output": test_output["stdout"][:1000],
        }
        if not test_passed and test_output["stdout"].strip():
            findings.append({
                "severity": "blocking",
                "category": "테스트",
                "message": "테스트 실패",
                "file": "",
                "line": 0,
                "fix": f"실패 테스트를 수정하세요:\n{test_output['stdout'][:300]}",
            })

        static_context = (
            f"린터: {'통과' if lint_clean else '위반 있음'}\n"
            f"테스트: {'통과' if test_passed else '실패'}\n"
            f"발견된 이슈: {len(findings)}건"
        )

        ai_verdict = await self.review_level_1(
            code, f"{description}\n\n## 정적 검증 결과\n{static_context}"
        )

        findings.extend(ai_verdict.findings)
        has_blockers = any(f["severity"] == "blocking" for f in findings)
        return ReviewVerdict(
            level=ReviewLevel.STATIC_VERIFIED,
            approved=not has_blockers and ai_verdict.approved,
            confidence=min(ai_verdict.confidence + 0.1, 1.0) if lint_clean and test_passed else ai_verdict.confidence * 0.7,
            summary=f"정적 검증 {'통과' if lint_clean and test_passed else '실패'} + AI 리뷰",
            findings=findings,
            test_results=test_results,
            lint_results={"architecture": lint_clean, "naming": name_output["success"], "structure": struct_output["success"]},
        )

    def _parse_json_response(self, response: str) -> dict:
        """AI 응답에서 JSON 추출."""
        import re

        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        return {
            "approved": False,
            "confidence": 0.3,
            "summary": "응답 파싱 실패",
            "findings": [{"severity": "info", "category": "파싱", "message": response[:500], "file": "", "line": 0, "fix": ""}],
        }
