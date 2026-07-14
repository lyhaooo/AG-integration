# -*- coding: utf-8 -*-
"""FJSP 评测与算子接口单元测试。"""

import os
import unittest

from fjsp.fjsp_eval import FJSPEvaluator
from fjsp.run import load_specification
from funsearch.implementation import code_manipulation


class FjspEvalTest(unittest.TestCase):

  def test_initial_operators_dauzere(self):
    spec = load_specification()
    program = code_manipulation.text_to_program(spec)
    mod = {}
    exec(str(program), mod)  # pylint: disable=exec-used
    fitness = FJSPEvaluator().evaluate_get_operators(mod['get_operators'])
    self.assertIsNotNone(fitness)
    self.assertLess(fitness, 1.0)

  def test_data_dir_exists(self):
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'Dauzere')
    self.assertTrue(os.path.isdir(data_dir))
    fjs = [f for f in os.listdir(data_dir) if f.endswith('.fjs')]
    self.assertGreaterEqual(len(fjs), 18)


if __name__ == '__main__':
  unittest.main()
