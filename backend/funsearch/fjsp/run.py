# -*- coding: utf-8 -*-
"""
FunSearch × FJSP 入口：合并进化工序选择与机器选择算子（get_operators）。

LLM 配置与 MA4PGO 一致，见 fjsp/config/settings.json。

用法:
  python -m fjsp.run --mock --max-samples 2
  python -m fjsp.run --max-samples 100
  python -m fjsp.experiment
"""

import argparse
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from funsearch.implementation import code_manipulation
from funsearch.implementation import config as config_lib
from funsearch.implementation import evaluator
from funsearch.implementation import funsearch
from funsearch.implementation import programs_database
from funsearch.implementation import sampler

from fjsp.config_store import load_settings, save_settings
from fjsp.llm_client import MA4PGOLLM, MockLLM, build_interface_llm
from fjsp.sandbox import FJSPSandbox


RESULTS_DIR = Path(__file__).resolve().parent / 'results'
SPEC_PATH = Path(__file__).resolve().parent / 'specification.txt'


class FJSPEvaluator(evaluator.Evaluator):
  def __init__(self, *args, timeout_seconds: int = 120, **kwargs):
    super().__init__(*args, timeout_seconds=timeout_seconds, **kwargs)
    self._sandbox = FJSPSandbox()


class FJSPSampler(sampler.Sampler):
  def __init__(
      self,
      database: programs_database.ProgramsDatabase,
      evaluators: list[FJSPEvaluator],
      llm: sampler.LLM,
  ):
    self._database = database
    self._evaluators = evaluators
    self._llm = llm

  def sample_steps(self, max_steps: int, progress_callback=None, stop_event=None) -> None:
    for step in range(max_steps):
      if stop_event is not None and stop_event.is_set():
        print('[FunSearch-FJSP] 已按请求停止')
        break
      prompt = self._database.get_prompt()
      samples = self._llm.draw_samples(prompt.code)
      for sample in samples:
        chosen = self._evaluators[step % len(self._evaluators)]
        chosen.analyse(sample, prompt.island_id, prompt.version_generated)
      print(f'[FunSearch-FJSP] 完成采样轮次 {step + 1}/{max_steps}')
      if progress_callback is not None:
        best = max(self._database._best_score_per_island)  # pylint: disable=protected-access
        progress_callback(step + 1, max_steps, best)


def load_specification() -> str:
  raw = SPEC_PATH.read_text(encoding='utf-8')
  return raw.replace('__REPO_ROOT__', REPO_ROOT.as_posix())


def save_best_program(database: programs_database.ProgramsDatabase) -> tuple[float, str]:
  best_score = -float('inf')
  best_fn = None
  for island_id, prog in enumerate(database._best_program_per_island):  # pylint: disable=protected-access
    score = database._best_score_per_island[island_id]  # pylint: disable=protected-access
    if prog is not None and score > best_score:
      best_score = score
      best_fn = prog

  RESULTS_DIR.mkdir(parents=True, exist_ok=True)
  meta_path = RESULTS_DIR / 'best_meta.json'

  if best_fn is None:
    meta = {'score': None, 'message': '尚无有效程序'}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                         encoding='utf-8')
    return best_score, ''

  out_path = RESULTS_DIR / 'best_get_operators.py'
  header = (
      '"""Best evolved get_operators from FunSearch-FJSP."""'
      f'\nimport sys\nsys.path.insert(0, {repr(str(REPO_ROOT))})\n\n'
  )
  out_path.write_text(header + str(best_fn), encoding='utf-8')

  meta = {
      'score': best_score,
      'fitness': -best_score if best_score > -1e8 else None,
      'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
      'path': str(out_path),
  }
  meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2),
                       encoding='utf-8')
  print(f'[FunSearch-FJSP] 最优 score={best_score} (fitness≈{-best_score})')
  print(f'[FunSearch-FJSP] 已保存: {out_path}')
  return best_score, out_path.read_text(encoding='utf-8')


def _merge_settings(
    cli_overrides: dict,
) -> dict:
  settings = load_settings()
  for key, value in cli_overrides.items():
    if value is not None:
      settings[key] = value
  return settings


def run_evolution(settings: dict, mock: bool = False, progress_callback=None, stop_event=None) -> tuple[float, str]:
  specification = load_specification()
  function_to_evolve, function_to_run = funsearch._extract_function_names(
      specification)

  template = code_manipulation.text_to_program(specification)
  num_islands = int(settings.get('num_islands', 4))
  samples_per_prompt = int(settings.get('samples_per_prompt', 2))
  max_samples = int(settings.get('max_samples', 50))

  db_config = config_lib.ProgramsDatabaseConfig(
      functions_per_prompt=2,
      num_islands=num_islands,
      reset_period=24 * 60 * 60,
  )
  cfg = config_lib.Config(
      programs_database=db_config,
      num_samplers=1,
      num_evaluators=1,
      samples_per_prompt=samples_per_prompt,
  )

  database = programs_database.ProgramsDatabase(
      cfg.programs_database, template, function_to_evolve)

  inputs = ['Dauzere']
  evaluators_list = [
      FJSPEvaluator(
          database,
          template,
          function_to_evolve,
          function_to_run,
          inputs,
          timeout_seconds=180,
      )
  ]

  initial_body = template.get_function(function_to_evolve).body
  evaluators_list[0].analyse(initial_body, island_id=None, version_generated=None)

  if mock:
    llm: sampler.LLM = MockLLM(samples_per_prompt, initial_body)
    print('[FunSearch-FJSP] Mock LLM 模式')
  else:
    interface = build_interface_llm(settings)
    llm = MA4PGOLLM(samples_per_prompt, interface)
    print(
        f'[FunSearch-FJSP] MA4PGO LLM: model={settings.get("llm_model")}, '
        f'endpoint={settings.get("llm_api_endpoint")}, '
        f'local={settings.get("llm_use_local")}'
    )

  fjsp_sampler = FJSPSampler(database, evaluators_list, llm)
  fjsp_sampler.sample_steps(max_samples, progress_callback, stop_event)
  return save_best_program(database)


def main() -> None:
  parser = argparse.ArgumentParser(description='FunSearch FJSP 算子进化')
  parser.add_argument('--mock', action='store_true', help='使用 Mock LLM 冒烟测试')
  parser.add_argument('--max-samples', type=int, default=None)
  parser.add_argument('--num-islands', type=int, default=None)
  parser.add_argument('--samples-per-prompt', type=int, default=None)
  parser.add_argument(
      '--llm-api-endpoint', default=None, help='同 MA4PGO llm_api_endpoint')
  parser.add_argument('--llm-api-key', default=None, help='同 MA4PGO llm_api_key')
  parser.add_argument('--llm-model', default=None, help='同 MA4PGO llm_model')
  parser.add_argument(
      '--llm-use-local', action='store_true', help='同 MA4PGO llm_use_local')
  parser.add_argument('--llm-local-url', default=None)
  parser.add_argument('--llm-debug-mode', action='store_true')
  parser.add_argument('--llm-max-workers', type=int, default=None)
  parser.add_argument(
      '--save-settings', action='store_true',
      help='将本次 CLI 覆盖项写回 fjsp/config/settings.json')
  args = parser.parse_args()

  cli_overrides = {
      'max_samples': args.max_samples,
      'num_islands': args.num_islands,
      'samples_per_prompt': args.samples_per_prompt,
      'llm_api_endpoint': args.llm_api_endpoint,
      'llm_api_key': args.llm_api_key,
      'llm_model': args.llm_model,
      'llm_local_url': args.llm_local_url,
      'llm_max_workers': args.llm_max_workers,
  }
  if args.llm_use_local:
    cli_overrides['llm_use_local'] = True
  if args.llm_debug_mode:
    cli_overrides['llm_debug_mode'] = True

  settings = _merge_settings(cli_overrides)
  if args.save_settings:
    save_settings(settings)
    print('[FunSearch-FJSP] 已更新 fjsp/config/settings.json')

  run_evolution(settings, mock=args.mock)


if __name__ == '__main__':
  main()
