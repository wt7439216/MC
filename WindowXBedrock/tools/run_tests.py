# -*- coding: utf-8 -*-
"""本地回归：只跑不依赖 SDK 的纯逻辑测试（py2/py3 均可）。"""
from __future__ import print_function

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'behavior_packs', 'windowxBehavior'))


def main():
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.join(HERE, 'tests'), pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
