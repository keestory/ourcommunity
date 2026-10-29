# CLAUDE.md — Codex 전환 안내

TIPLOOP Harness의 현재 진입점은 [`AGENTS.md`](./AGENTS.md)다.

- Codex 프로젝트 설정: [`.codex/config.toml`](./.codex/config.toml)
- 역할별 에이전트: [`.codex/agents/`](./.codex/agents/)
- 코드 아키텍처: [`ARCHITECTURE.md`](./ARCHITECTURE.md)
- 사용 가이드: [`docs/CODEX_HARNESS.md`](./docs/CODEX_HARNESS.md)

기존 `.claude/agents/`와 `orchestrator/claude_runner.py`는 이전 Claude Code 기반 실행과의 호환을 위해 남겨 두었다. 새 에이전트·모델 정책의 단일 원본으로 사용하지 않는다.
