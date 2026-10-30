# UI/UX 근거 복구와 적용 결정 — 2026-10-30

대상 코드/배포: `2c79feace2fedae0b9ea86082ada87b205e0eee8`. 이 기록은 기존 작업의 리디자인이며 기존 연구 게이트 통과를 뜻하지 않는다.

## 사용자 근거와 범위

- 8/9 원문 전달: “디자인이 항상고민인게 너무 AI적인게 많아. 좋은 예시들을 외부에서 리서치해서 어딘가에 계속 저장해놓고 발전시키고, 나의 디자인 시스템도 계속 만들어가면 어떨까”. [원문 위치](https://chatgpt.com/c/6a7852b0-e628-83ee-b0a2-84271f9edc6f?messageId=75352278-1a98-4199-afe0-fd1abb43e42d). 관리 작업의 대화 검색 결과이며 이 실행 환경에서 원문을 직접 열지는 않았다.
- 8/23 노무 앱에서 Product Design, Designly, Frontend Design Premium을 직접 요청한 기록 전달. [원문 위치](https://chatgpt.com/c/6a8aecc5-a9cc-83ee-b3c6-bf8708e5ae4d?messageId=6e0e6a8f-d67e-412b-b6cf-706a124d2c92). 특정 서비스 화면이나 스포츠 앱 색상 선택의 근거는 아니다.
- 10/30 현재 화면을 거부하고 과거 리서치/사용 자료로 바꿔 달라고 요청. 기존 따뜻한 2D 러닝 스타일은 사용자가 고른 미학이 아니다.
- Echo의 Apple 계열 AI companion/pet 비율은 다른 프로젝트 한정. 유리 orb·파스텔 카드·21st 사용을 이 앱의 취향으로 간주하지 않는다.

## 실제 이용 가능한 자료와 반영 상태

| 자료 | 확인한 내용 | 기존 적용 / 누락 |
|---|---|---|
| design-intelligence (`skill://user/6a786c9cc63c81918fbd9069eee36029/design-intelligence`) | provisional taste, source registry, Anti-AI review, evidence levels, pattern lifecycle, Community/Game/O2O recipe | 준비 문서에서 공식 기능 패턴은 구분. 실제 화면 관찰 카드, 프로젝트 취향 선택 기록, 구조가 다른 비교안과 반복 진화 기록은 없음 |
| frontend-design (`skill://plugins_6a7039f8e9708191bde88207b1919bf4/frontend-design`) | 제품 고유 정보·타이포·구성·한 가지 특징, 만든 화면의 재평가 | SVG 집이라는 특징은 있으나 반복 일러스트와 시적인 소개가 실제 참여보다 먼저 나옴 |
| frontend-design-premium (같은 패키지의 `frontend-design-premium`) | canonical UI, 토큰 원본, 복구·권한·확인창·실제 브라우저 검증 | DESIGN→tokens 생성, 공통 UI, 기능 회귀/접근성은 적용. 정적 audit 0건을 정보구조/디자인 품질 통과로 볼 수 없음 |
| root DESIGN.md / UX-CONTRACT.md / premium-ui.json | 제품 토큰·UI 소유자·동작 계약 | 유지할 행동 계약. 미확정 North Star가 시각 구현의 기본값으로 굳음. 새 근거와 동작에 맞춰 갱신 필요 |
| docs/DESIGN.md / core-beliefs | 하네스의 일반 설계 지침 | 제품 UI 원본과 구분해 보존 |
| activity-patterns.md R01–R05 | Clubhouse/Gather/Discord/Habitica/Forest의 공식 기능 설명, 10/29 부모 확인 | 기능 원리의 근거만 있음. 서비스 UI 실사용/캡처나 사용자가 선택한 시각 스타일은 아님 |

체크아웃 및 `/workspace/.agents`, `/workspace/.codex`의 관련 SKILL/taste/source-registry/pattern-card 파일 검색에서 로컬 사본은 발견되지 않았다. 이용 가능한 스킬은 위 cloud provider를 통해 읽었다. 설치 이름만으로 사용자 선호를 추정하지 않는다.

## 출처별 사용 범위

| 출처 | 근거 상태 | 가져올 원리 / 실제 적용 대상 | 제외 |
|---|---|---|---|
| [Heylo communications](https://www.heylo.com/help/communications), [event](https://www.heylo.com/help/event) | 10/29 부모의 공식 문서 확인 전달; 채팅/이벤트/RSVP/정원/대기/출석 설명. 이번 직접 조회는 프록시403 | 대화와 모임을 같은 그룹 맥락에서 연결. 홈의 최신 대화·다음 모임, 채팅의 모임 바로가기 | Heylo의 실제 화면 배치/색을 관찰·복제했다고 주장하지 않음; 기능 조합 자체가 차별점이라는 주장 제외 |
| Clubhouse / Gather / Discord | [기존 출처/권리 기록](../../product-specs/ourcommunity/activity-patterns.md), 공식 설명 전달 | 방의 맥락과 공동 귀속: 크루 중심 탐색, 공동 애셋의 상태/배치 | 공개 실시간 인원, 위치, 음성방, 유료 Boost 미도입 |
| [Apple HIG layout](https://developer.apple.com/design/human-interface-guidelines/layout), [tab bars](https://developer.apple.com/design/human-interface-guidelines/tab-bars), [Material navigation](https://m3.material.io/components/navigation-bar/overview) | 사용자 source-registry의 공식 가이드 후보. 이번 직접 조회403, 원문 최신 세부사항 미검증 | 기존 프로젝트의 터치·안전영역·포커스 계약을 적용하고 실제 viewport로 검증 | 최신 가이드를 직접 읽었다거나 특정 수치를 해당 페이지에서 인용했다는 주장 없음 |
| Mobbin / Page Flows / Carbon / Polaris / Atlassian / GOV.UK / DTCG | 사용자 스킬에 포함된 조사원 목록 | 다음 조사 시 실제 흐름, 날짜, 관찰/해석/이전 한계와 함께 저장 | 목록 존재를 사용자의 특정 화면 승인이나 접근/실사용 증거로 간주하지 않음 |

## 현행 문제와 수용 기준

부모의 fresh 공개 audit: 1180×757 채팅 입력 시작 y=844.77px(화면 밖), 안내+breadcrumb+서술 제목 약320px, 같은 집이 entry/home/memories에 반복, 공동 성장 조작 없이 설명/진행률 중심. 모바일 공개 QA는 미수행. 이 작업에서 같은 SHA를 로컬 렌더해 전후 비교한다.

1. 채팅: 페이지 전체가 아니라 메시지 목록이 스크롤한다. 1180×757, 390×844, 좁은/짧은 viewport에서 입력과 전송 버튼이 하단 탐색에 가려지지 않아야 한다.
2. 진입/홈: 역할 선택은 실제 로그인과 구분하고 우선 시작 행동을 하나로 둔다. 크루 맥락·최신 대화·다음 모임/신청이 장식 설명보다 먼저 보인다.
3. 공동 공간: 출석→해금→공간 배치가 보이는 인과관계가 있어야 한다. 최근 활기와 영구 기념물을 분리하며 실제 집계가 없는 데모에서 가짜 활기를 만들지 않는다.
4. 시각 언어: 관계를 구분하는 행·구획, 분명한 타이포 계층, 절제된 표면/강조색. 같은 둥근 카드·아이콘 상자·중복 시적 설명을 반복하지 않는다.
5. 보존: IndexedDB `ourcommunity-browser-demo-v1`, 스키마 버전1, 기존 대화/모임/출석/개별 설정을 유지. 기존 Python/PostgreSQL·서버 계약도 보존한다. 이전 기록에 새 선택 필드가 없어도 동작하도록 확장한다.

## 비교한 구조와 구현 방향

- A **클럽룸**: 대화·다음 약속이 우선, 공동 공간은 참여 결과를 확인/조작하는 영역. 재방문 동선 짧음. 이번 사용자 목표와 부모 audit에 대응하는 구현 방향으로 선택한다. 사용자에게 특정 미학을 승인받았다는 뜻은 아니다.
- B **공동 공간 우선**: 큰 공간을 탐색하며 대화/모임에 들어감. 성장 몰입 장점이 있으나 현재 입력/참가 접근 문제를 다시 만들 수 있어 이번 기본 진입으로 채택하지 않는다.

Design DNA trial: 대화 중심의 한국어 스포츠 클럽. 내용 밀도와 명확한 상태, 담백한 타이포, 단일 행동 강조색, 낮은 장식 비중. 공동 공간의 배치가 특징이며 같은 집 그림을 반복하지 않는다. 색/폰트는 이 구조를 지원하는 구현 제안으로 기록한다.

## 구현/검증 순서

1. 로컬 before 캡처와 입력창/전송 영역 측정.
2. 공통 shell·demo notice·타이포/토큰·컴포넌트 계층을 수정하고 모바일 우선 흐름 구현.
3. 클럽 홈/채팅/모임/공동 공간의 관계와 배치 피드백을 연결. 데모에만 필요한 선택 필드는 optional 확장, reset/서버 코드 유지.
4. 실제 렌더 after 비교, 키보드/대비/터치/스크롤·데이터 호환 확인. 기존 demo8+server9 회귀와 추가 변경 과업 검증.
5. 안정된 코드 독립 검토→수정→lint/type/build→기능 브랜치 push. 공개 배포는 부모가 정확한 SHA로 수행한다.

상태: reference/구조 검토와 구현 완료, 최종 검증·독립 리뷰 결과는 [결과 기록](README.md)에 별도 기록한다. [패턴 메모리](patterns.md)는 trial이며 사용자 시험 또는 adopted 패턴으로 올리지 않는다.
