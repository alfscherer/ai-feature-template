from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


@lru_cache
def load_prompt_template(name: str, version: str) -> str:
    path = _PROMPTS_DIR / name / f"{version}.txt"
    return path.read_text(encoding="utf-8")
