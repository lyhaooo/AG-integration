# -*- coding: utf-8 -*-
"""本地部署 LLM：通过 local_url 调用（OpenAI 兼容接口）。"""

import requests


def _normalize_local_url(url: str) -> str:
    s = (url or "").strip().rstrip("/")
    if not s.startswith("http://") and not s.startswith("https://"):
        s = "http://" + s
    if not s.endswith("/v1"):
        s = s + "/v1"
    return s


class InterfaceLocalLLM:
    def __init__(self, llm_local_url: str):
        self.base_url = _normalize_local_url(llm_local_url)

    def get_response(self, prompt_content: str):
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": "",  # 本地常见不校验 model
            "messages": [{"role": "user", "content": prompt_content}],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=120)
            r.raise_for_status()
            data = r.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content")
        except Exception:
            return None
