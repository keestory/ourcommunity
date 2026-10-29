"""Claude CLI result model and output parsing."""

import json
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClaudeResult:
    agent: str
    success: bool
    output: str = ""
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    session_id: str = ""
    is_error: bool = False
    num_turns: int = 0
    raw_json: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "success": self.success,
            "output": self.output[:500],
            "cost_usd": self.cost_usd,
            "duration_seconds": self.duration_seconds,
            "session_id": self.session_id,
            "num_turns": self.num_turns,
        }


def parse_claude_output(stdout: str, agent: str, duration: float) -> ClaudeResult:
    """Parse ``claude --output-format json`` output, falling back to text."""
    result = ClaudeResult(agent=agent, success=True, duration_seconds=duration)
    if not stdout.strip():
        result.output = "(빈 출력)"
        return result
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        result.output = stdout
        return result
    result.raw_json = data
    if isinstance(data, dict):
        result.output = data.get("result", str(data))
        result.cost_usd = data.get("cost_usd", 0.0)
        result.session_id = data.get("session_id", "")
        result.is_error = data.get("is_error", False)
        result.num_turns = data.get("num_turns", 0)
        result.success = not result.is_error
    else:
        result.output = str(data)
    return result
