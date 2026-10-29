"""Multi-specialist review stage."""

from agents.review_models import ReviewLevel, ReviewVerdict


class ReviewSpecialistMixin:
    async def review_level_3(self, code: str, files: list[str] = None, description: str = "") -> ReviewVerdict:
        """Level 3: 보안/아키텍처/도메인 전문 리뷰어 3인."""
        import asyncio

        security_task = self._specialist_review(code, description, "security")
        architecture_task = self._specialist_review(code, description, "architecture")
        domain_task = self._specialist_review(code, description, "domain")

        results = await asyncio.gather(security_task, architecture_task, domain_task)
        security_result, architecture_result, domain_result = results

        all_findings = []
        for name, result in [("보안", security_result), ("아키텍처", architecture_result), ("도메인", domain_result)]:
            for f in result.get("findings", []):
                f["category"] = f"{name}: {f.get('category', '일반')}"
                all_findings.append(f)

        votes = [
            security_result.get("approved", False),
            architecture_result.get("approved", False),
            domain_result.get("approved", False),
        ]
        approved = sum(votes) >= 2
        has_blockers = any(f["severity"] == "blocking" for f in all_findings)

        if has_blockers:
            approved = False

        avg_confidence = sum(r.get("confidence", 0.5) for r in results) / 3

        level2 = await self.review_level_2(code, files, description)
        all_findings.extend(level2.findings)

        return ReviewVerdict(
            level=ReviewLevel.MULTI_SPECIALIST,
            approved=approved and level2.approved,
            confidence=avg_confidence * (0.9 if level2.approved else 0.6),
            summary=(
                f"전문 리뷰어 투표: {sum(votes)}/3 승인 "
                f"(보안:{'O' if votes[0] else 'X'} "
                f"아키텍처:{'O' if votes[1] else 'X'} "
                f"도메인:{'O' if votes[2] else 'X'})"
            ),
            findings=all_findings,
            test_results=level2.test_results,
            lint_results=level2.lint_results,
            escalate_to=4 if not approved and not has_blockers else None,
        )

    async def _specialist_review(self, code: str, description: str, specialty: str) -> dict:
        """전문 리뷰어 실행."""
        prompts = {
            "security": """당신은 보안 전문 코드 리뷰어입니다.
다음을 집중적으로 검토하세요:
- 인젝션 취약점 (SQL, XSS, 커맨드 인젝션)
- 인증/인가 결함
- 민감 데이터 노출
- 하드코딩된 시크릿
- SSRF, CSRF, 경로 순회
- 의존성 취약점
반드시 JSON 형식으로 응답: {"approved": bool, "confidence": float, "findings": [...]}""",

            "architecture": """당신은 소프트웨어 아키텍처 전문 리뷰어입니다.
다음을 집중적으로 검토하세요:
- 레이어 의존성 규칙 위반 (Types→Config→Providers→Repo→Service→Runtime→UI)
- 단일 책임 원칙 위반
- 순환 의존성
- 경계 파싱 누락
- 불필요한 결합
- 추상화 수준 적절성
반드시 JSON 형식으로 응답: {"approved": bool, "confidence": float, "findings": [...]}""",

            "domain": """당신은 비즈니스 도메인 전문 리뷰어입니다.
다음을 집중적으로 검토하세요:
- 비즈니스 로직의 정확성
- 엣지 케이스 처리
- 에러 핸들링 적절성
- 데이터 무결성
- 사용자 경험에 미치는 영향
- 기존 기능과의 일관성
반드시 JSON 형식으로 응답: {"approved": bool, "confidence": float, "findings": [...]}""",
        }

        response = await self.call_model(
            [{"role": "user", "content": f"설명: {description}\n\n```\n{code}\n```"}],
            model="claude-sonnet-4-6",
        )

        return self._parse_json_response(response)
