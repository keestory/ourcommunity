# kee_agent architecture

`kee_agent`는 Codex 네이티브 설정을 기본으로 사용하고, 기존 Claude/Python 실행 계층을 호환용으로 유지하는 에이전트 하네스다.

## Source of truth

- [`AGENTS.md`](./AGENTS.md): 작업 등급, 역할 선택, 게이트와 handoff 규칙
- [`.codex/config.toml`](./.codex/config.toml): 프로젝트 범위의 멀티에이전트 설정
- [`.codex/agents/`](./.codex/agents/): Codex 역할별 실행 정책
- [`docs/CODEX_HARNESS.md`](./docs/CODEX_HARNESS.md): 실행과 검증 방법

`.claude/`, `agents/`, `orchestrator/`, `run.py`는 이전 Claude Code 기반 실행과 로컬 린터 호환 계층이다. 신규 역할과 모델 정책을 이 계층에 먼저 추가하지 않는다.

## Runtime boundaries

```text
AGENTS.md + .codex/config.toml + .codex/agents/*.toml
                         ↓
                Codex parent session
                         ↓
              conditional sub-agents

run.py → orchestrator/ → ClaudeRunner → Claude Code CLI
  └── linters/                     (legacy/local compatibility)
```

Codex 경로와 legacy 경로는 실행 계약이 다르다. 가상의 `codex --agent` 명령을 만들거나, Claude 전용 Python runner를 Codex 런타임으로 간주하지 않는다.

## Dependency direction

린터가 검사하는 애플리케이션 레이어의 허용 방향은 다음과 같다.

```text
types → config → providers → repo → service → runtime → ui
```

현재 `architecture_linter.py`는 파일·import 경로에 이 레이어 이름이 나타날 때만 방향을 검사한다. 모든 Python 의존성을 완전하게 증명하는 검사가 아니므로 import smoke와 관련 테스트를 함께 실행한다.

하네스 내부에서는 진입점이 orchestration과 agent interface에 의존하고, agent 구현은 공통 base와 작은 도메인별 모델·helper에 의존한다. 순환 import를 만들지 않고 공개 import 경로는 가능한 한 유지한다.

## Change rules

- 한 시점에 제품 코드 writer는 한 명만 둔다.
- read-only 전문가가 근거와 계약을 만들고, 구현 후 QA가 실제 동작을 검증한다.
- 테스트, 배포, 스토어 제출, 승인, 공개 상태는 별도 증거로 다룬다.
- 새 구조를 추가하면 이 문서와 관련 index를 같은 변경에서 갱신한다.

## ourcommunity 제품 준비 문서

스포츠 커뮤니티의 준비 자료는 [`docs/product-specs/ourcommunity/`](./docs/product-specs/ourcommunity/README.md), 진행 상태는 [`docs/product-state.yaml`](./docs/product-state.yaml)에 있다. 준비 문서는 연구 단계의 제안과 근거를 보존한다. 이후 사용자의 명시적 개발 요청에 따라 아래 로컬 제품을 별도로 구현한다. 고객 검증이나 출시 게이트 통과를 뜻하지 않는다.

## ourcommunity 로컬 제품 경계

```text
web/ (React + TypeScript + Vite)
  → /api (개발 프록시)
    → community/ (FastAPI)
      → .harness/community.sqlite3 (SQLite, 추적 제외)
```

`community/app.py`가 로컬 Origin/Host 경계와 API를 조립한다. `security.py`는 세션·CSRF·현재 멤버십을 검사하며 모든 비공개 리소스에서 재사용한다. `database.py`의 트랜잭션은 메시지 재시도, 정원·대기 제안, 출석 전환을 직렬화한다. `event_logic.py`는 좌석과 기여 규칙을, `growth.py`는 공동 애셋과 보호된 집계를 소유한다. 외부 인증·푸시·운영 플랫폼과 연결하지 않는다.

`DESIGN.md`가 화면 토큰의 원본이고 `UX-CONTRACT.md`가 공통 컴포넌트·탐색·오류·권한 동작을 정의한다. 화면은 API 성공 이후 상태를 갱신하며 서버 권한 검사를 대체하지 않는다. 채팅은 폴링으로 갱신한다. 원래 하네스 런타임과 소비자 앱은 import나 데이터베이스를 공유하지 않는다.

실행과 한계는 [`README.md`](./README.md), 설계 가정과 검증 상태는 [`로컬 제품 기록`](./docs/implementation/local-product.md)을 따른다. 배포·실제 사용자 데이터·보관 정책·계정 삭제는 별도 준비가 필요하다.
