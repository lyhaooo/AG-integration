# -*- coding: utf-8 -*-
"""FunSearch 采样用的 LLM 封装（底层与 MA4PGO InterfaceLLM 一致）。"""

import re

from funsearch.implementation import sampler

from fjsp.llm.interface_llm import InterfaceLLM

_FUNSEARCH_PROMPT_PREFIX = (
    'Continue ONLY the function body for get_operators(): define nested '
    'select_operation(num_jobs, num_job_operations, job_current_operation, '
    'machine_process_times, machine_available_time) and '
    'select_machine(machine_process_times, machine_available_time), then '
    'return select_operation, select_machine. '
    'Do not repeat the function header or use markdown code fences.\n\n'
)


class MockLLM(sampler.LLM):
  """返回初始算子的小幅扰动，用于本地验证流水线。"""

  def __init__(self, samples_per_prompt: int, seed_body: str) -> None:
    super().__init__(samples_per_prompt)
    self._seed_body = seed_body
    self._counter = 0

  def _draw_sample(self, prompt: str) -> str:
    self._counter += 1
    delta = (self._counter % 5) + 1
    return self._seed_body.replace('remaining_ops * 10', f'remaining_ops * {delta}')


class MA4PGOLLM(sampler.LLM):
  """通过 MA4PGO 同款 InterfaceLLM 并行采样函数续写。"""

  def __init__(
      self,
      samples_per_prompt: int,
      interface_llm: InterfaceLLM,
  ) -> None:
    super().__init__(samples_per_prompt)
    self._interface = interface_llm

  def draw_samples(self, prompt: str):
    full_prompt = _FUNSEARCH_PROMPT_PREFIX + prompt
    replies = self._interface.get_responses(
        full_prompt, self._samples_per_prompt)
    samples = []
    for reply in replies:
      if reply and reply.strip():
        samples.append(_strip_markdown(reply))
    return samples


def build_interface_llm(settings: dict) -> InterfaceLLM:
  """从 settings 字典构建 MA4PGO 同款 InterfaceLLM。"""
  return InterfaceLLM(
      api_endpoint=settings.get('llm_api_endpoint'),
      api_key=settings.get('llm_api_key'),
      model_LLM=settings.get('llm_model'),
      llm_use_local=settings.get('llm_use_local', False),
      llm_local_url=settings.get('llm_local_url'),
      debug_mode=settings.get('llm_debug_mode', False),
      max_workers=settings.get('llm_max_workers', 4),
  )


def _strip_markdown(text: str) -> str:
  blocks = re.findall(r'```(?:python)?\s*([\s\S]*?)```', text)
  if blocks:
    return blocks[-1].strip()
  return text.strip()
