"""CrewAI LLM adapter with a hard per-task request budget and no HTTP retries."""
from dataclasses import dataclass, field
import json
import httpx
from pydantic import PrivateAttr
from crewai import BaseLLM


@dataclass
class RequestBudget:
    limit: int = 2
    attempted: int = 0
    usage: list = field(default_factory=list)

    def claim(self):
        if self.attempted >= self.limit:
            raise RuntimeError("LLM request budget exhausted; no further requests will be made")
        self.attempted += 1


class DeepSeekLLM(BaseLLM):
    _key: str = PrivateAttr()
    _budget: RequestBudget = PrivateAttr()
    _cap: int = PrivateAttr()
    _json_mode: bool = PrivateAttr()

    def __init__(self, key, model, budget, cap, json_mode=False):
        super().__init__(model=model, temperature=0)
        self._key, self._budget, self._cap, self._json_mode = key, budget, cap, json_mode

    def call(self, messages, tools=None, callbacks=None, available_functions=None, **kwargs):
        self._budget.claim()
        if isinstance(messages, str):
            messages = [{"role": "user", "content": messages}]
        body = {"model": self.model, "messages": messages, "max_tokens": self._cap,
                "temperature": 0, "stream": False, "thinking": {"type": "disabled"}}
        if self._json_mode:
            body["response_format"] = {"type": "json_object"}
        # httpx's transport does not retry by default. Never follow redirects with a key.
        with httpx.Client(timeout=90, follow_redirects=False) as client:
            response = client.post("https://api.deepseek.com/chat/completions",
                headers={"Authorization": "Bearer " + self._key}, json=body)
        if response.status_code != 200:
            raise RuntimeError(f"DeepSeek HTTP {response.status_code}; no automatic retry")
        data = response.json()
        self._budget.usage.append({k: int(v) for k, v in data.get("usage", {}).items() if isinstance(v, (int, float))})
        message = data["choices"][0]["message"].get("content", "")
        if not message:
            raise RuntimeError("DeepSeek returned no text")
        # Explicit final marker avoids an Agent asking for an additional turn.
        return "Final Answer: " + message

    def supports_stop_words(self):
        return False
