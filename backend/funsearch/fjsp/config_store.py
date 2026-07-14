# -*- coding: utf-8 -*-
"""配置持久化（字段与 MA4PGO backend/config_store 对齐）。"""

import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
SETTINGS_PATH = os.path.join(CONFIG_DIR, 'settings.json')

DEFAULT_SETTINGS = {
    'max_samples': 50,
    'num_islands': 4,
    'samples_per_prompt': 2,
    'llm_api_endpoint': 'one.ocoolai.com',
    'llm_api_key': '',
    'llm_model': 'gpt-3.5-turbo',
    'llm_use_local': False,
    'llm_local_url': 'xxx',
    'llm_debug_mode': False,
    'llm_max_workers': 4,
}


def _ensure_config_dir():
  os.makedirs(CONFIG_DIR, exist_ok=True)


def load_settings() -> dict:
  _ensure_config_dir()
  if os.path.isfile(SETTINGS_PATH):
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
      stored = json.load(f)
    return {**DEFAULT_SETTINGS, **stored}
  return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> dict:
  _ensure_config_dir()
  merged = {**DEFAULT_SETTINGS, **settings}
  with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
    json.dump(merged, f, ensure_ascii=False, indent=2)
  return merged
