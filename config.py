import os
from dataclasses import dataclass


def _as_bool(value, default=False):
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AgentConfig:
    model: str = "llama3.2:3b"
    headless: bool = False
    wait_seconds: float = 3.0
    max_source_chars: int = 18000

    @classmethod
    def from_environment(cls):
        return cls(
            model=os.getenv("OLLAMA_MODEL", cls.model),
            headless=_as_bool(os.getenv("BROWSER_HEADLESS"), cls.headless),
            wait_seconds=float(os.getenv("BROWSER_WAIT_SECONDS", cls.wait_seconds)),
            max_source_chars=int(os.getenv("MAX_SOURCE_CHARS", cls.max_source_chars)),
        )