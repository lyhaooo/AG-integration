# -*- coding: utf-8 -*-
"""远程 OpenAI 兼容 API：通过 endpoint + key + model 调用。"""

import requests
from urllib.parse import urlparse


def _response_error_detail(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                message = error.get("message") or error.get("code") or error
                return str(message)
            return str(data)
    except Exception:
        pass
    return (response.text or "").strip()[:500]


def _normalize_endpoint(endpoint: str) -> str:
    s = (endpoint or "").strip()
    if not s:
        return ""
    if not s.startswith("http://") and not s.startswith("https://"):
        s = "https://" + s
    s = s.rstrip("/")
    # DeepSeek 的官方 OpenAI SDK 示例使用 https://api.deepseek.com 作为 base_url，
    # 不强制追加 /v1，避免把请求发到用户未配置的路径。
    if _is_deepseek_endpoint(s):
        return s
    if not s.endswith("/v1"):
        s = s + "/v1"
    return s


def _is_deepseek_endpoint(endpoint: str) -> bool:
    host = urlparse(endpoint).netloc.lower()
    return host == "api.deepseek.com" or host.endswith(".deepseek.com")


def _is_deepseek_model(model: str) -> bool:
    return (model or "").strip().lower().startswith("deepseek")


class InterfaceAPI:
    def __init__(self, api_endpoint: str, api_key: str, model_LLM: str, debug_mode: bool = False):
        self.base_url = _normalize_endpoint(api_endpoint)
        self.api_key = api_key
        self.model_LLM = model_LLM
        self.debug_mode = debug_mode
        self.last_response_headers = None
        self.is_deepseek = _is_deepseek_endpoint(self.base_url) or _is_deepseek_model(self.model_LLM)

    def _build_payload(self, prompt_content: str):
        payload = {
            "model": self.model_LLM,
            "messages": [{"role": "user", "content": prompt_content}],
            "temperature": 0.7,
        }
        if self.is_deepseek:
            payload["reasoning_effort"] = "high"
            payload["thinking"] = {"type": "enabled"}
        return payload

    def get_response(self, prompt_content: str):
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = self._build_payload(prompt_content)
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=120)
            # 保存响应头，便于上层读取服务端限流/配额信息（若有）
            self.last_response_headers = dict(r.headers) if r is not None else None
            if not r.ok:
                detail = _response_error_detail(r)
                if detail:
                    print(f"error detail: {detail}")
            r.raise_for_status()
            data = r.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if self.debug_mode and content:
                print("[InterfaceAPI] response length:", len(content or ""))
            return content
        except Exception as e:
            print("error:", e)
            try:
                self.last_response_headers = dict(getattr(r, "headers", None)) if "r" in locals() else None
            except Exception:
                self.last_response_headers = None
            if self.debug_mode:
                print("[InterfaceAPI] Error:", e)
            return None
