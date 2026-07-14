# -*- coding: utf-8 -*-
"""远程 OpenAI 兼容 API：通过 endpoint + key + model 调用。"""

import requests


def _normalize_endpoint(endpoint: str) -> str:
  s = (endpoint or '').strip()
  if not s:
    return ''
  if not s.startswith('http://') and not s.startswith('https://'):
    s = 'https://' + s
  s = s.rstrip('/')
  if not s.endswith('/v1'):
    s = s + '/v1'
  return s


class InterfaceAPI:
  def __init__(
      self,
      api_endpoint: str,
      api_key: str,
      model_LLM: str,
      debug_mode: bool = False,
  ):
    self.base_url = _normalize_endpoint(api_endpoint)
    self.api_key = api_key
    self.model_LLM = model_LLM
    self.debug_mode = debug_mode
    self.last_response_headers = None

  def get_response(self, prompt_content: str):
    url = f'{self.base_url}/chat/completions'
    headers = {
        'Authorization': f'Bearer {self.api_key}',
        'Content-Type': 'application/json',
    }
    payload = {
        'model': self.model_LLM,
        'messages': [{'role': 'user', 'content': prompt_content}],
        'temperature': 0.7,
        'max_tokens': 4096,
    }
    try:
      r = requests.post(url, json=payload, headers=headers, timeout=120)
      self.last_response_headers = dict(r.headers) if r is not None else None
      r.raise_for_status()
      data = r.json()
      content = data.get('choices', [{}])[0].get('message', {}).get('content')
      if self.debug_mode and content:
        print('[InterfaceAPI] response length:', len(content or ''))
      return content
    except Exception as e:
      try:
        self.last_response_headers = (
            dict(getattr(r, 'headers', None)) if 'r' in locals() else None)
      except Exception:
        self.last_response_headers = None
      if self.debug_mode:
        print('[InterfaceAPI] Error:', e)
      return None
