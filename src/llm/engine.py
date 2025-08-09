"""LlmEngine: tenká vrstva nad llama-cpp pro generování odpovědí.

Závislosti jsou volitelné; pokud nejsou k dispozici, engine vrátí
deterministickou zprávu o nedostupnosti.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any


try:
    from llama_cpp import Llama  # type: ignore
except ImportError:  # pragma: no cover - volitelná závislost
    Llama = None  # type: ignore


@dataclass
class LlmConfig:
    model_path: str
    n_ctx: int = 4096
    n_threads: int = 4
    max_tokens: int = 200
    temperature: float = 0.2
    top_p: float = 0.9
    repeat_penalty: float = 1.1


class LlmEngine:
    def __init__(self, cfg: LlmConfig):
        self.cfg = cfg
        self._llm = None
        if Llama is not None:
            try:
                self._llm = Llama(
                    model_path=self.cfg.model_path,
                    n_ctx=self.cfg.n_ctx,
                    n_threads=self.cfg.n_threads,
                    verbose=False,
                )
            except (OSError, RuntimeError, ValueError):  # pragma: no cover
                self._llm = None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if self._llm is None:
            return "LLM není dostupný"
        full_prompt = (system_prompt + "\n\n" if system_prompt else "") + prompt
        try:
            res: Dict[str, Any] = self._llm(
                full_prompt,
                max_tokens=self.cfg.max_tokens,
                temperature=self.cfg.temperature,
                top_p=self.cfg.top_p,
                repeat_penalty=self.cfg.repeat_penalty,
                stop=["\n\n", "Otázka:", "Pokyny:"],
            )
            text = (res.get("choices", [{}])[0] or {}).get("text", "").strip()
            return text or "Nevím"
        except (OSError, RuntimeError, ValueError):  # pragma: no cover
            return "Promiňte, momentálně nemohu odpovědět"
