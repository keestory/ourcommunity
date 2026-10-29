# AGENTS.md — TIPLOOP Codex Harness

이 파일은 TIPLOOP에서 Codex가 작업 난이도와 위험에 따라 에이전트를 선택하는 라우팅 규칙이다. 역할별 모델과 상세 지침의 단일 원본은 `.codex/agents/*.toml`이다.

## 기본 원칙

1. 메인 에이전트가 범위, 라우팅, 통합, 최종 검증을 소유한다.
2. 짧고 의존적인 작업은 메인 에이전트가 직접 처리한다. 에이전트 호출 자체를 완료 조건으로 삼지 않는다.
3. 서로 독립적인 조사·검토만 병렬화한다. 한 시점의 제품 코드 writer는 한 명으로 제한한다.
4. 하위 에이전트는 부모가 명시하지 않는 한 다른 하위 에이전트를 만들지 않는다.
5. 작업 전 `ARCHITECTURE.md`, 관련 `docs/`, 현재 작업 트리와 실제 구현을 확인한다. 문서나 배포 주장을 현재 상태의 증거로 간주하지 않는다.
6. 사용자가 요청한 산출물과 위험에 비례한 검증까지 완료한다. 계획만 전달하고 멈추지 않는다.
7. 모든 작업의 intake에서 `discoverability: required | not-applicable`, `store_compliance: required | not-applicable`, `competitive_benchmark: required | not-applicable`을 판정한다. 이는 모든 작업에 하위 에이전트를 호출한다는 뜻이 아니다. 영향이 없는 S0·내부 작업은 적용 제외 사유만 남긴다.

## 먼저 작업 등급을 정한다

| 등급 | 기준 | 기본 라우팅 |
|---|---|---|
| S0 직접 처리 | 문구, 한 파일 설정, 명확한 소규모 수정, 단순 질의 | 메인 에이전트가 직접 수행 + 최소 검증. 하위 에이전트 없음 |
| S1 제한 작업 | 소수 파일의 명확한 버그·기능, 제품 판단이 불필요 | `engineer` 1명 또는 메인 직접 수행 → 동작 변경이면 `qa` |
| S2 기능 작업 | 여러 계층·화면·데이터 흐름, 요구사항 또는 구조가 불명확 | 필요한 앞단 전문가 1~2명 → `planner`(복잡할 때만) → `engineer` → `qa`; 위험 기준 충족 시 `reviewer` |
| S3 제품/출시 | 신규 서비스, 시장 진입, 수익화, 대형 기능, 실제 출시 | 현재 시장조사 → 관련 사업 전문가만 병렬 → 제품 범위 통합 → 설계/구현/QA → 조건부 보안·운영 검토 |

등급을 올리는 신호는 인증·결제·개인정보·권한·마이그레이션·외부 공개·되돌리기 어려운 변경이다. 파일 수만으로 등급을 올리지 않는다.

## 역할과 호출 조건

| 에이전트 | 모델 / effort | 호출해야 할 때 | 호출하지 않을 때 |
|---|---|---|---|
| `market_researcher` | `gpt-5.6-terra` / high | 신규 제품·시장·가격·경쟁·ASO·앱스토어 순위 판단 | 내부 버그, 이미 확정된 기능 구현 |
| `competitive_pattern_researcher` | `gpt-5.6-terra` / high | 신규 제품·핵심 플로우의 현재 상위 제품, 패턴, 디자인, 리뷰 근거를 비교할 때 | 작은 수정, 경쟁 근거가 제품 결정을 바꾸지 않는 작업 |
| `strategy` | `gpt-5.6-sol` / high | 큰 제품 선택, 포지셔닝, 우선순위 충돌 | 수용 기준이 명확한 기능 |
| `business_development` | `gpt-5.6-terra` / high | 수익화, 파트너십, 유통, B2B, 단위경제 | 사업모델과 무관한 제품 수정 |
| `marketing` | `gpt-5.6-terra` / high | 출시 메시지, ASO, 획득 채널, 캠페인 실험 | 백엔드·인프라 단독 변경 |
| `discoverability` | `gpt-5.6-terra` / high | 신규 제품, 공개 URL·콘텐츠·렌더링·canonical·structured data·검색 랜딩·Universal/App Links 변경 | 인증 뒤 전용 화면, 순수 내부 API·리팩터링, 검색·딥링크 영향이 없는 수정 |
| `store_compliance` | `gpt-5.6-sol` / high | 모바일 앱 신규 개발, 로그인·데이터·권한·결제·SDK·UGC 변경, App Store/Google Play 제출 | 모바일 스토어와 무관한 웹·백엔드 작업 |
| `gtm_lead` | `gpt-5.6-sol` / high | 실제 출시의 타깃·포지셔닝·채널·가격·준비도·측정을 하나로 통합 | 출시가 없는 내부 구현, 작은 패치 |
| `product_manager` | `gpt-5.6-terra` / high | 사용자·범위·수용 기준이 모호한 기능 | 요구와 수용 기준이 이미 명확한 작업 |
| `ui_ux` | `gpt-6-astra` / high | 사용자 흐름, 화면 상태, 디자인 토큰·컴포넌트, 접근성, 시각 계층 변경 | UI에 영향 없는 코드 변경 |
| `architect` | `gpt-5.6-sol` / high | 신규 서비스, 시스템 경계, API·데이터 계약, NFR, 통합, 마이그레이션 | 기존 구조 안의 국소 구현 |
| `planner` | `gpt-5.6-sol` / high | 여러 계층, 마이그레이션, 순서 의존성, 롤백 설계 | 한두 단계로 바로 구현 가능한 작업 |
| `engineer` | `gpt-5.6-sol` / high | 복잡하거나 독립 위임 가치가 있는 구현 | S0이거나 메인이 이미 구현 중인 작업 |
| `qa` | `gpt-5.6-terra` / high | 사용자 동작, 데이터, API, 회귀 가능성이 바뀜 | 문구·주석·문서만 바뀌고 기계 검증으로 충분함 |
| `reviewer` | `gpt-5.6-terra` / high | S2/S3, 핵심 경계, 회귀 폭이 큰 diff, 출시 전 독립 검토 | 낮은 위험의 국소 변경을 QA가 충분히 검증함 |
| `security_reviewer` | `gpt-5.6-sol` / xhigh | 인증·인가·결제·PII·시크릿·RLS·업로드·외부 입력 | 보안 경계를 건드리지 않는 변경 |
| `ops` | `gpt-5.6-terra` / high | 실제 배포, 환경변수, 마이그레이션, 장애, 롤백·관측성 | 로컬 구현·테스트만 요청된 작업 |
| `analyst` | `gpt-5.6-terra` / high | KPI, 이벤트, 퍼널, 실험, 출시 후 의사결정 | 측정·데이터 판단이 없는 구현 |
| `doc_gardener` | `gpt-5.6-luna` / medium | 명시적 문서 정비 또는 동작 변경으로 문서 동기화가 큼 | 코드와 무관한 작은 문서 한 줄 수정 |
| `release_council` | `gpt-6-astra` / xhigh | 되돌리기 어려운 출시, 다중 시스템 마이그레이션, 전문가 간 미해결 충돌 | 일반 개발·리뷰·출시 체크리스트 |

저장소 탐색은 Codex 내장 `explorer`, 명확한 소규모 위임은 내장 `worker`를 필요할 때만 사용한다. 이 둘을 같은 이름의 커스텀 에이전트로 중복 정의하지 않는다.

## 서비스 개발 표준 수명주기

요청한 `Research → Business Planning → Strategy → UX/UI Design System → Tech Architecture → Coding → QA → Coding → Review → GTM → Release`의 책임은 모두 포함한다. 다만 이를 긴 직렬 waterfall로 실행하지 않고, 아래처럼 의사결정 게이트와 병렬 트랙으로 운영한다.

```text
Intake / task grading
        ↓
Current market + benchmark research ──→ Opportunity Gate
        ↓
Business Planning + Product Strategy ──→ Product Gate
        ↓
UX/UI & Design System  ║  Tech Architecture  ║  Discoverability / Store impact / Measurement
        └────────────── Solution Gate ──────────────┘
                               ↓
                    Incremental Coding
                               ↓
                   QA ──fail──→ Coding fix
                    ↑              │
                    └────retest────┘
                               ↓ pass
                  Independent Review
                               ↓
GTM track (starts after Product Gate) ──→ Release Readiness Gate
                                               ↓
                                      Staged Release
                                               ↓
                                      Measure / Learn
```

### Gate 1 — Opportunity

- `market_researcher`가 최신 시장, 고객 문제, 앱스토어 비즈니스 순위, 경쟁·가격 근거를 수집한다.
- `competitive_pattern_researcher`는 신규 제품과 핵심 사용자 플로우에서 대상 국가·플랫폼·카테고리·관측일이 명시된 비교군을 만들고, 상위권·직접 경쟁·인접 우수 제품의 제품 패턴과 디자인 패턴을 분리해 분석한다.
- 순위는 발견 신호일 뿐 품질·매출·유지율의 증거가 아니다. 스크린샷, 실제 플로우, 리뷰, 공식 상품 설명 등 서로 다른 근거를 교차 확인하고 사실·해석·가설을 구분한다.
- 신규 서비스와 시장 진입에서는 필수다. 기존 제품의 명확한 구현에서는 생략한다.
- 산출물: 날짜가 있는 evidence pack, 고객 문제, 비교 행렬, 패턴·반패턴, 우리 제품에 적용할 원칙과 적용하지 않을 복제 요소, 기회 크기 가설, 사실/가설 구분, 중단 조건.

### Gate 2 — Product and Business

- 같은 evidence pack을 사용해 `business_development`와 `strategy`가 독립적으로 검토하고, 필요할 때 병렬 실행한다.
- `product_manager`가 고객, 가치제안, 사업모델, 범위, 수용 기준, 비목표를 하나의 product brief로 통합한다.
- 통과 조건: 타깃 고객, 해결할 문제, 차별점, 사업 가설, 성공지표, 중단 기준이 명확하다.
- 근거가 약하면 설계로 진행하지 않고 research로 되돌린다.

### Gate 3 — Solution

- 사용자 화면이 있으면 `ui_ux`, 새로운 경계·계약·데이터 모델이 있으면 `architect`, 측정이 필요하면 `analyst`를 최대 3개까지 병렬 실행한다.
- `ui_ux`는 화면만 그리지 않고 흐름, 정보구조, 모든 상태, 접근성, 토큰, 재사용 컴포넌트와 interaction contract를 정의한다.
- `architect`는 시스템 경계, API·데이터 계약, NFR, 보안 가정, 관측성, 마이그레이션과 롤백을 정의한다.
- 공개 웹·앱 surface가 있으면 `discoverability`가 SEO·AEO·GEO 관점의 URL, crawl/index, answerability, structured data, Universal/App Links, web fallback과 측정 계약을 정의한다. `AEG`는 사용자 입력 별칭으로만 인식하고 표준명으로 발명하지 않는다.
- 모바일 앱 신규 개발이나 스토어 영향 변경이면 `store_compliance`가 개인정보, 계정 삭제, 결제, 권한, SDK, 연령·콘텐츠, 리뷰어 접근과 플랫폼 차이를 `store requirement matrix`로 만든다.
- `planner`는 승인된 product brief, UX contract, architecture decision을 구현 가능한 vertical slice로 바꿀 때만 호출한다.
- 통과 조건: 수용 기준, 디자인 시스템 delta, 계약·ADR, 테스트 전략, 계측, rollout 제약이 서로 모순되지 않는다.

### Build–Verify Loop

1. `engineer` 한 명이 가장 작은 vertical slice를 구현하고 자체 검증한다.
2. 구현이 멈춘 뒤 `qa`가 수용 기준, 회귀, 실패·경계·접근성·통합 케이스를 검증한다.
3. 실패 시 `qa`는 재현·기대/실제·심각도·증거가 있는 defect packet을 반환한다.
4. 같은 `engineer`가 최소 수정하고 `qa`가 영향 범위를 재검증한다.
5. QA가 통과한 안정된 diff만 `reviewer`가 correctness·architecture·regression 관점에서 검토한다.
6. review blocker는 `engineer → qa → reviewer`의 좁은 루프로 되돌린다. 스타일 의견만으로 전체 루프를 반복하지 않는다.

공개 discovery contract가 있는 변경은 구현 후 `discoverability`가 실제 렌더링, 대표 URL, 구조화 데이터, association file과 fallback을 읽기 전용으로 확인한다. 모바일 store requirement matrix가 있는 변경은 실제 코드·SDK·네트워크 동작과 개인정보처리방침, Apple App Privacy, Google Data safety, 권한 설명, 계정 삭제, 결제와 스토어 메타데이터가 일치하는지 `qa`와 `store_compliance`가 검증한다. 실패는 좁은 `engineer → qa → 전문 재검증` 루프로 되돌린다.

`security_reviewer`는 보안 트리거가 있을 때 Build–Verify 또는 Release Readiness에 추가한다. 여러 coding agent가 같은 작업 트리를 동시에 수정하지 않는다.

### GTM 병렬 트랙과 Release Readiness

- GTM은 review 뒤에 처음 시작하지 않는다. Product Gate가 통과하면 `marketing`, 필요한 경우 `business_development`와 `analyst`가 입력을 만들고 `gtm_lead`가 병렬로 초안을 시작한다.
- `gtm_lead`는 타깃, 포지셔닝, 채널 순서, 가격·파트너 의존성, 출시 자산, 지원 준비, KPI·guardrail, 중단 기준과 담당자를 하나의 launch plan으로 통합한다.
- 안정된 review 결과를 반영해 약속·메시지·스크린샷·지원 문서를 실제 제품과 다시 맞춘다.
- 출시 게이트는 QA 통과, blocker 없는 review, 필요한 security 승인, `ops`의 버전·롤백·모니터링·smoke plan, GTM 자산과 계측 준비를 모두 요구한다.
- 검색·딥링크 영향이 있으면 대표 URL, crawl/index 정책, canonical, sitemap, structured data, Universal/App Links, web fallback과 계측을 확인한다. 등록 요청 성공을 색인·순위·AI 인용 성공으로 간주하지 않는다.
- App Store·Google Play 제출 직전에는 `store_compliance`가 제출할 실제 IPA/AAB(정확한 version/build/signing)와 현재 콘솔 상태를 기준으로 Pre-submission Hard Gate를 수행한다. 콘솔 전용 항목을 직접 확인하지 못하면 GO가 아니라 CONDITIONAL GO 또는 NO-GO다. 어떤 체크리스트도 승인을 보장하지 않는다.
- `ops`는 read-only로 release readiness를 검증한다. 실제 외부 배포·제출은 메인 에이전트가 사용자의 대상·계정·권한을 다시 확인한 후 수행한다. `release_council`은 비가역 고위험 판단에만 사용한다.
- release 후 `analyst`가 KPI와 guardrail을 읽고 `product_manager`·`strategy`에 학습을 돌려준다.

## 오케스트레이션 패턴

### S0 — 단순 작업

메인 에이전트가 직접 수정하고 가장 작은 관련 검증을 실행한다. 시장조사, PM, planner, reviewer를 자동 호출하지 않는다.

### S1 — 제한된 버그·기능

코드 위치가 불명확할 때만 내장 `explorer`를 호출한다. 메인 또는 `engineer` 한 명이 구현하고, 동작이 바뀌면 `qa`가 회귀를 확인한다. 낮은 위험이면 별도 reviewer는 생략한다.

### S2 — 여러 계층의 기능

요구가 모호하면 `product_manager`, 사용자 화면이 바뀌면 `ui_ux`, 기술 경계가 바뀌면 `architect`, 공개 검색·딥링크에 영향이 있으면 `discoverability`, 모바일 정책 영향이 있으면 `store_compliance`, 구현 순서가 복잡하면 `planner`를 선택적으로 호출한다. 읽기 전용 결과는 최대 3개까지 병렬화할 수 있다. 메인 에이전트가 결론을 통합한 후 `engineer` 한 명이 구현하고 `qa`가 검증한다. 핵심 경계 또는 큰 diff일 때만 `reviewer`를 추가한다.

### S3 — 신규 서비스·시장·수익화·출시

1. `market_researcher`가 2026년 현재 대상 국가의 앱스토어 비즈니스 순위, 경쟁 제품, 가격, 공식 자료를 조사하고 `competitive_pattern_researcher`가 상위·직접·인접 제품의 제품/UX/디자인 패턴을 비교한다.
2. `strategy`와 `business_development` 중 문제에 해당하는 역할을 호출하고 `product_manager`가 product brief로 통합한다.
3. `ui_ux`, `architect`, `analyst`, `discoverability`, `store_compliance` 중 영향 판정상 필요한 읽기 역할만 최대 3개씩 호출하고, 복잡한 delivery면 `planner`가 vertical slice를 만든다.
4. Product Gate 이후 실제 출시가 예정됐으면 `gtm_lead`가 GTM 병렬 트랙을 시작한다. `marketing`, `business_development`, `analyst`는 필요한 입력만 제공한다.
5. `engineer → qa ↔ engineer` 루프로 수용 기준을 통과시킨 뒤 안정된 diff를 `reviewer`가 독립 검토한다.
6. 보안 트리거가 있을 때만 `security_reviewer`를 추가한다.
7. 실제 배포가 범위일 때만 `ops`가 release readiness와 rollback을 검토한다. 모바일 스토어 제출이면 `store_compliance`의 Pre-submission Hard Gate를 추가한다.
8. 출시 후 `analyst`가 결과를 측정한다. 남은 고위험 충돌이 있을 때만 `release_council`로 에스컬레이션한다.

## 병렬화와 handoff 계약

- 기본 동시 fan-out은 3 이하로 유지한다.
- 병렬화하기 좋은 일: 시장조사, 코드 위치 탐색, 독립 리뷰, 테스트 결과 분석.
- 병렬화하지 않을 일: 같은 파일 수정, 앞 단계 결정에 의존하는 구현, 연속 마이그레이션.
- 모든 하위 에이전트는 `결론 / 근거 / 가정 / 산출물 또는 영향 파일 / 검증 / 남은 위험 / 다음 담당자` 순서로 반환한다.
- 메인 에이전트는 상충하는 제안을 통합하고 사용자 요구와 다른 결정을 임의로 확대하지 않는다.

## 품질 게이트

- 아키텍처 의존성: Types → Config → Providers → Repo → Service → Runtime → UI.
- 변경 후 관련 테스트와 필요한 경우 `python3 run.py --lint`를 실행한다.
- 테스트 통과, 배포 완료, 공개 확인을 서로 구분한다. 로컬·시뮬레이터 성공은 출시 승인이 아니다.
- 벤치마크는 관측일·국가·플랫폼·카테고리·출처를 남긴다. 상위 순위를 제품 품질이나 성과의 인과 증거로 해석하거나 경쟁 UI를 그대로 복제하지 않는다.
- SEO·AEO·GEO는 현재 공식 검색엔진 지침과 렌더된 결과로 검증하고 순위·색인·AI 인용을 보장하지 않는다.
- GitHub 별 수와 커뮤니티 문서는 발견 신호일 뿐 정책 근거가 아니다. 관측일·검색 cohort·누적 별과 기간 내 증가를 구분해 기록하고, 공식 원문과 실제 렌더링이 우선한다.
- 스토어 정책은 제출 시점에 공식 원문을 다시 확인한다. 저장소 검사, release artifact, 콘솔 선언, 제출, 승인, 공개 상태를 서로 구분한다.
- 실패·미검증 항목을 숨기지 않는다.
- 외부 게시, 배포, 결제, 제출처럼 되돌리기 어려운 행동은 대상 계정과 현재 상태를 확인한 뒤 수행한다.

## 구조

```text
.codex/config.toml       Codex 멀티에이전트 기본값
.codex/agents/*.toml     조건부 전문 역할의 모델·effort·sandbox·지침
ARCHITECTURE.md          코드 경계와 의존성
docs/                    제품·설계·운영 기록
linters/                 기계적 구조 검증
```

기존 `.claude/`와 Python Claude 오케스트레이터는 마이그레이션 호환 자료다. 새 작업의 에이전트 선택과 모델 정책은 이 파일과 `.codex/`를 기준으로 한다.
