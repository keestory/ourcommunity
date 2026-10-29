# TIPLOOP Codex Harness

TIPLOOP의 기본 에이전트 시스템은 Codex 네이티브 멀티에이전트 설정을 사용한다. 라우팅의 핵심은 **기본 호출 0개, 조건이 맞을 때만 전문 에이전트 추가**다.

## 실행

저장소 루트에서 Codex를 시작한다.

```bash
codex
```

비대화형 작업과 독립 리뷰는 다음처럼 실행한다.

```bash
codex exec -C . "AGENTS.md의 조건부 라우팅으로 로그인 오류를 진단하고 수정해줘"
codex -C . review --uncommitted
```

Codex는 `AGENTS.md`, `.codex/config.toml`, `.codex/agents/*.toml`을 읽는다. CLI에서는 `/agent`로 실행 중인 에이전트 스레드를 확인한다.

## 모델 정책

- `gpt-5.6-luna`: 문서 정비처럼 빠르고 반복적인 좁은 작업
- `gpt-5.6-terra`: 제품 정의, 시장·사업·마케팅, 일반 리뷰, QA, 운영
- `gpt-5.6-sol`: 전략, 복잡한 구현·계획, 보안처럼 깊은 추론이 필요한 작업
- `gpt-6-astra`: UI/UX 설계 판단은 high, 비가역 출시나 전문가 충돌 에스컬레이션은 xhigh

각 커스텀 역할의 모델은 TOML에 고정한다. 저장소 탐색과 명확한 소규모 위임은 Codex 내장 `explorer`와 `worker`를 필요할 때만 사용한다.

## 신규 서비스의 표준 경로

```text
Research
  → Business Planning + Strategy
  → Product Gate
  → UX/UI Design System + Tech Architecture + Discoverability + Store impact + Measurement
  → Build-ready Gate
  → Coding → QA → Fix → Re-QA
  → Independent Review
  → Release Readiness
  → Staged Release → Live Verification → Learn
```

이 경로는 단순 waterfall이 아니다.

- Business Planning과 Strategy는 같은 시장 근거를 받아 병렬 검토한다.
- UX/UI와 Tech Architecture는 승인된 product brief를 기준으로 병렬 진행한다.
- GTM은 Product Gate 직후 초안을 시작하고, review된 실제 제품을 기준으로 최종화한다.
- QA 또는 review가 실패하면 한 명의 `engineer`에게 돌아가며, 수정 후 영향 범위 QA와 필요한 re-review를 수행한다.
- Release는 배포 버튼이 아니라 버전·대상·롤백·모니터링·live smoke까지 포함한다.
- 출시 후 `analyst`가 합의된 관측 기간과 기준으로 iterate/hold/expand/pause/rollback 판단을 만든다.
- 신규 제품·중요한 사용자 여정은 `market_researcher`의 현재 차트 근거 뒤 `competitive_pattern_researcher`가 제품·UX·디자인 패턴을 비교한다. 순위는 성공 증명이 아니며 결과는 `Adopt / Adapt / Avoid / Test`로 분류한다.
- 모든 작업은 discoverability, store compliance, competitive benchmark 적용 여부를 먼저 판정하지만 영향이 없는 S0·내부 변경에는 전문 에이전트를 호출하지 않는다.
- 공개 검색·콘텐츠·딥링크 영향이 있으면 `discoverability`, 모바일 스토어 정책 영향이 있으면 `store_compliance`를 Solution과 Release 게이트에 추가한다.

`architect`는 기술 경계·계약·ADR을, `planner`는 승인된 설계를 구현 순서와 vertical slice로 바꾸는 일을 맡는다. 둘은 책임이 다르며 복잡한 작업에서만 함께 호출한다. `gtm_lead`는 marketing·business development·analytics·ops 입력을 하나의 launch plan으로 통합한다.

## 호출 예시

단순 수정은 하위 에이전트를 요구하지 않는다.

```text
이 문구 오류는 S0으로 처리해줘. 메인 에이전트가 직접 최소 수정하고 관련 검증만 실행해줘.
```

여러 계층 기능도 필요한 역할만 선택한다.

```text
이 기능은 요구사항이 모호하고 UI와 API가 함께 바뀐다.
product_manager와 ui_ux의 읽기 전용 검토를 병렬로 받은 뒤 결과를 통합하고,
planner가 필요하다고 판단될 때만 계획을 추가해줘. engineer 한 명이 구현한 뒤 qa가 검증해줘.
```

신규 서비스는 최신 시장 근거가 먼저지만 모든 사업 역할을 자동 호출하지 않는다.

```text
한국 앱스토어 비즈니스 카테고리의 2026년 현재 시장을 먼저 조사해줘.
이번 결정에 필요한 strategy와 marketing만 병렬로 검토하고, 수익화·제휴 질문이 있을 때만
business_development를 추가해줘. architect와 ui_ux는 필요한 경우 병렬로 검토하고,
gtm_lead는 Product Gate 이후 launch plan을 시작해줘. 구현 후에는 위험 기준에 따라 reviewer/security/ops를 선택해줘.
```

공개 웹·앱과 모바일 제출이 함께 있는 제품은 다음처럼 요청한다.

```text
현재 한국 앱스토어 차트와 직접·인접 제품을 조사하고 competitive_pattern_researcher가
제품/온보딩/신뢰/수익화/리텐션/디자인 패턴을 비교해줘. 그대로 복제하지 말고
Adopt/Adapt/Avoid/Test로 분류해줘. discoverability가 SEO/AEO/GEO와 Universal/App Links
계약을 만들고, store_compliance가 Apple/Google requirement matrix를 만든 뒤 구현에 반영해줘.
QA 후 실제 렌더링과 제출할 IPA/AAB·현재 콘솔 상태까지 각각 재검증해줘.
```

상세 기준은 [`DISCOVERABILITY.md`](./DISCOVERABILITY.md),
네이버가 범위에 있으면 [`NAVER_DISCOVERABILITY.md`](./NAVER_DISCOVERABILITY.md),
[`STORE_COMPLIANCE.md`](./STORE_COMPLIANCE.md),
[`COMPETITIVE_RESEARCH.md`](./COMPETITIVE_RESEARCH.md)를 따른다.

## 호출하지 않는 기본값

- 문구·주석·명확한 설정 변경: PM, planner, QA, reviewer 생략 가능
- 이미 위치가 확인된 코드: `explorer` 생략
- 낮은 위험의 국소 변경: `reviewer` 생략
- 보안 경계가 없는 변경: `security_reviewer` 생략
- 실제 배포가 없는 로컬 구현: `ops` 생략
- 일반 작업: `release_council` 금지
- 내부 변경: 적용 판정은 남기되 `discoverability`, `store_compliance`, `competitive_pattern_researcher` 자동 호출 금지

상세 조건과 작업 등급은 루트 `AGENTS.md`를 따른다.

## 마이그레이션 경계

기존 Python 오케스트레이터는 `claude -p --agent` 호출을 전제로 한다. Codex 커스텀 에이전트는 부모 Codex 세션이 생성하는 설정 레이어이므로 가상의 `codex --agent` 명령으로 치환하지 않는다.

현재는 Codex 네이티브 설정이 기본이며 기존 Claude 실행 코드는 참고·호환용이다. Python 외부 오케스트레이션까지 바꾸려면 별도 단계에서 Codex App Server 또는 SDK 어댑터와 실행 동등성 테스트를 추가한다.

## 검증

새 클론에서는 먼저 테스트 환경을 만든다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

```bash
codex --version
codex --strict-config -C . doctor --summary --ascii
codex -C . debug prompt-input "라우팅 규칙과 조건부 에이전트를 요약해줘"
.venv/bin/python -m pytest -q
python3 run.py --lint
git diff --check
```
