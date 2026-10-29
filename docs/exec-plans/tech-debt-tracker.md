# Technical debt tracker

검증된 기술 부채만 기록한다. 단순 아이디어나 재현되지 않은 의심은 추가하지 않는다.

| ID | 영역 | 증거 | 영향 | 다음 행동 | 담당 | 상태 |
|---|---|---|---|---|---|---|
| TD-001 | Binary checkpoint rollback | 바이너리를 hex 문자열로 저장하지만 rollback은 텍스트로 기록 | 바이너리 복원이 원본과 다를 수 있음 | binary round-trip 형식과 테스트 설계 | maintainer | open |

## Verified in this cleanup

- 개발 의존성은 `requirements-dev.txt`, pytest 수집 범위와 marker는 `pytest.ini`에 고정했다.
- 대형 review/workflow/runner 모듈은 공개 import를 유지한 작은 모듈로 분리하고 경계 회귀 테스트를 추가했다.

상태는 `open | planned | in-progress | verified | accepted` 중 하나를 사용한다. 해결 시 관련 검증 명령과 commit을 남긴다.
