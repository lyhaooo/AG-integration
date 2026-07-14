# -*- coding: utf-8 -*-
"""FunSearch 沙箱：在隔离命名空间中执行生成的程序。"""

import multiprocessing
import types
from typing import Any

from funsearch.implementation import evaluator as evaluator_lib


class FJSPSandbox(evaluator_lib.Sandbox):
  """执行 specification 程序并调用 @funsearch.run 标注的 evaluate 函数。"""

  def run(
      self,
      program: str,
      function_to_run: str,
      test_input: Any,
      timeout_seconds: int,
  ) -> tuple[Any, bool]:
    # Web 后端在线程中启动迭代；fork 可避免 spawn 重新导入 uvicorn/__main__ 导致失败。
    # Windows 不支持 fork 时再回退到 spawn。
    methods = multiprocessing.get_all_start_methods()
    ctx = multiprocessing.get_context('fork' if 'fork' in methods else 'spawn')
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    proc = ctx.Process(
        target=_sandbox_worker,
        args=(program, function_to_run, test_input, child_conn),
    )
    proc.start()
    proc.join(timeout_seconds)
    if proc.is_alive():
      proc.kill()
      proc.join()
      return None, False
    if not parent_conn.poll():
      return None, False
    result, ok = parent_conn.recv()
    return result, ok


def _sandbox_worker(
    program: str,
    function_to_run: str,
    test_input: Any,
    conn,
) -> None:
  try:
    mod = types.ModuleType('fjsp_program')
    exec(program, mod.__dict__)  # pylint: disable=exec-used
    if function_to_run not in mod.__dict__:
      conn.send((None, False))
      return
    result = mod.__dict__[function_to_run](test_input)
    conn.send((result, True))
  except Exception:
    conn.send((None, False))
  finally:
    conn.close()
