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
