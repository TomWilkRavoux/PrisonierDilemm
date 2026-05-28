import os
import time

import httpx

from src.strategies.base import Strategy

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"


class MistralAgent(Strategy):
    def __init__(self, name: str, system_prompt: str) -> None:
        self.name = name
        self._system_prompt = system_prompt
        self._api_key = os.environ.get("MISTRAL_API_KEY", "")

    def choose(self, history: list[tuple[str, str]]) -> str:
        return self._call_api(history)

    def _format_history(self, history: list[tuple[str, str]]) -> str:
        if not history:
            return "Aucun historique, c'est le premier tour."
        last_5 = history[-5:]
        lines = []
        for i, (mine, opp) in enumerate(last_5, start=max(1, len(history) - 4)):
            lines.append(f"Tour {i}: toi={mine}, adversaire={opp}")
        return "\n".join(lines)

    def _call_api(self, history: list[tuple[str, str]]) -> str:
        if not self._api_key:
            return "C"

        user_msg = (
            f"Historique des derniers tours:\n{self._format_history(history)}\n\n"
            f"Tour actuel ({len(history) + 1}). Que joues-tu ? Reponds par C ou D suivi de ta justification."
        )

        payload = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 100,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = httpx.post(MISTRAL_URL, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            choice = "C" if content.upper().startswith("C") else "D"
            self._last_reasoning = content
            time.sleep(0.5)
            return choice
        except Exception:
            self._last_reasoning = "API error, defaulting to C"
            return "C"

    def get_reasoning(self) -> str:
        return getattr(self, "_last_reasoning", "")
