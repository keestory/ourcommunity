# Execution plans

여러 단계·계층·마이그레이션·rollback이 있는 작업만 실행 계획을 만든다. 명확한 S0/S1 변경에는 별도 계획 문서를 강제하지 않는다.

## Lifecycle

- 진행 중: [`exec-plans/active/`](./exec-plans/active/README.md)
- 완료: [`exec-plans/completed/`](./exec-plans/completed/README.md)
- 기술 부채: [`exec-plans/tech-debt-tracker.md`](./exec-plans/tech-debt-tracker.md)

계획에는 목적, 범위와 비목표, 의존성, vertical slice, 수용 기준, 검증, rollout/rollback, 결정과 미해결 위험을 포함한다. 완료 시 실제 결과와 검증 증거를 갱신한 뒤 completed로 이동한다.
