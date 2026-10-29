# Security policy

## Review triggers

인증·인가, 결제, 개인정보, secret, RLS, 파일 업로드, 외부 입력, 서드파티 webhook/SDK 또는 권한 경계를 바꾸면 `security_reviewer`를 추가한다. 일반 문서·스타일 변경에는 자동 호출하지 않는다.

## Baseline

- secret과 개인 데이터는 저장소, 로그, 테스트 fixture, 프롬프트에 넣지 않는다.
- 외부 입력은 경계에서 검증하고, 권한은 서버 측에서 최소 권한으로 다시 확인한다.
- shell·파일·네트워크 도구는 명시된 대상과 허용 범위 안에서만 사용한다.
- 위험한 변경은 위협, 완화책, rollback, 관측 신호와 남은 위험을 기록한다.
- 의존성 또는 플랫폼 정책은 실행 시점의 공식 자료와 실제 artifact로 확인한다.

## Known boundaries

- `ANTHROPIC_API_KEY`는 legacy 설정에서 환경변수로 읽는다. 값을 문서·로그·checkpoint에 기록하지 않는다.
- `BaseAgent.run_command()`의 문자열 차단 목록과 `shell=True` 실행은 보안 경계가 아니다. 신뢰할 수 없는 값을 shell command에 연결하지 않고, 고위험 실행은 별도 검토와 권한 확인을 거친다.
- `.harness/` 로그·checkpoint는 로컬 생성물이므로 민감정보를 포함하지 않아야 하며 Git에 커밋하지 않는다.

취약점이 의심되면 재현 가능성과 영향 범위를 검증하되 실제 사용자 데이터나 운영 시스템을 불필요하게 건드리지 않는다. 외부 공개나 수정 배포는 별도 승인 범위를 따른다.
