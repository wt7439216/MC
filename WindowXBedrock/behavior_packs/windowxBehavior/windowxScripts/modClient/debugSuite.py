# -*- coding: utf-8 -*-
"""性能采集（S1 / L1-L4 用）：记录每帧 UI 同步耗时与窗口数，输出 P95。"""
from __future__ import division

import time


class DebugSuite(object):
    def __init__(self, limit=600):
        self.limit = int(limit)
        self.cost = []
        self.frames = 0
        self.window_peak = 0
        self.last_report = 0.0

    def tick(self, cost_ms, window_count):
        self.frames += 1
        self.window_peak = max(self.window_peak, int(window_count))
        self.cost.append(float(cost_ms))
        if len(self.cost) > self.limit:
            del self.cost[0:self.limit // 2]

    def p95(self):
        if not self.cost:
            return 0.0
        data = sorted(self.cost)
        idx = int(len(data) * 0.95)
        if idx >= len(data):
            idx = len(data) - 1
        return data[idx]

    def avg(self):
        if not self.cost:
            return 0.0
        return sum(self.cost) / float(len(self.cost))

    def report(self):
        return ('frames=%d peak_windows=%d avg=%.2fms p95=%.2fms'
                % (self.frames, self.window_peak, self.avg(), self.p95()))

    def maybe_log(self, logger, tag='[WX-PERF]', every=150):
        now = time.time()
        if self.frames % every == 0 and now - self.last_report > 2.0:
            self.last_report = now
            try:
                logger.info('%s %s' % (tag, self.report()))
            except Exception:
                pass


_START = [0.0]


def begin():
    _START[0] = time.time()


def end_ms():
    return (time.time() - _START[0]) * 1000.0
