# Reliability standard

## Runtime expectations

- timeout, retry, concurrency와 비용 한도는 명시적으로 제한한다.
- 재시도는 동일한 실패를 무한 반복하지 않으며 최대 횟수 뒤 중단 또는 에스컬레이션한다.
- 부분 실패가 성공으로 보고되지 않도록 agent, gate, artifact별 결과를 보존한다.
- 외부 CLI·네트워크·콘솔 의존성은 unavailable 상태와 복구 경로를 구분한다.

## Release evidence

실제 배포가 있으면 versioned artifact, rollback path, monitoring signal, post-release smoke를 준비한다. 로컬 테스트, 배포 완료, live availability를 별도 상태로 기록한다.

장애 대응은 증상, 영향, 임시 완화, 근본 원인, 재발 방지 action과 담당자를 포함한다. 실행 계획은 [`PLANS.md`](./PLANS.md)에 기록한다.

## Known boundaries

legacy checkpoint는 텍스트 복원을 기준으로 하며 바이너리 파일의 완전한 rollback을 보장하지 않는다. 운영 복구 수단으로 간주하기 전에 별도 round-trip 검증이 필요하다.
