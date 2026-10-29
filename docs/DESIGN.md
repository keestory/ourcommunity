# Design system guidance

이 저장소 자체는 제품 UI를 제공하지 않는다. 이 문서는 `ui_ux` 에이전트가 대상 프로젝트의 UI를 설계·검토할 때 지켜야 할 최소 계약을 정의한다.

## Required outputs

- 사용자 목표, 진입점, 주요 흐름과 정보 구조
- default, loading, empty, error, offline, permission-denied 상태
- 색상·타이포·spacing·radius 등 최소 token delta
- 재사용 component, variant, state와 interaction contract
- keyboard, screen reader, contrast, dynamic type와 responsive 동작
- 구현 결과를 비교할 수 있는 수용 기준과 시각 검증 증거

기존 primitive를 우선 재사용하고 경쟁 제품의 고유 자산·문구·화면 배치를 복제하지 않는다. 상세 설계 기록은 [`design-docs/`](./design-docs/index.md)에 남긴다.
