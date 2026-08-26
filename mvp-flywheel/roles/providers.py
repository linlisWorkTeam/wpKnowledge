"""模型 provider：生产 codeagent/GLM 与显式实验 DeepSeek。"""

import json
import os
import subprocess
import urllib.request
from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    pass


class ChatProvider(ABC):
    name = "unknown"

    @abstractmethod
    def chat(self, messages: list, temperature: float, max_tokens: int, timeout: int) -> str:
        ...


class CodeAgentProvider(ChatProvider):
    """通过批准的 codeagent CLI 调用公司 GLM 5.1。"""

    name = "codeagent"

    def __init__(self, command: list, model_id: str = "GLM-5.1"):
        self.command = list(command)
        self.model_id = model_id

    def chat(self, messages: list, temperature: float = 0.2,
             max_tokens: int = 8192, timeout: int = 180) -> str:
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            proc = subprocess.run(
                self.command,
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ProviderError(f"codeagent 调用失败: {exc}") from exc
        if proc.returncode != 0:
            raise ProviderError(f"codeagent 返回 {proc.returncode}: {proc.stderr[:1000]}")
        output = proc.stdout.strip()
        if not output:
            return ""
        # 兼容单个 JSON、JSONL 最后一行和纯文本输出。
        for candidate in (output, output.splitlines()[-1]):
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                if isinstance(data.get("content"), str):
                    return data["content"]
                if isinstance(data.get("output"), str):
                    return data["output"]
                message = data.get("message")
                if isinstance(message, dict) and isinstance(message.get("content"), str):
                    return message["content"]
        return output


class DeepSeekProvider(ChatProvider):
    """仅用于 experimental 模式的外部 API provider。"""

    name = "deepseek"

    def __init__(self, model: str = "deepseek-v4-flash",
                 base_url: str = "https://api.deepseek.com/v1", api_key: str | None = None):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def chat(self, messages: list, temperature: float = 0.2,
             max_tokens: int = 8192, timeout: int = 180) -> str:
        key = self.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        if not key:
            raise ProviderError("DEEPSEEK_API_KEY 未配置")
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]
