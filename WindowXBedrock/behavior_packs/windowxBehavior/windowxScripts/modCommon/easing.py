# -*- coding: utf-8 -*-
"""缓动曲线库（对应 WindowX 的 EaseFunctions）。

约定：所有函数定义域 [0,1]，且 e(0)=0、e(1)=1。
纯数学、无 SDK 依赖，可在本地 py2/py3 直接单测。
"""
from __future__ import division

import math

__all__ = ['ease', 'has_ease', 'NAMES']


def _clamp01(t):
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return float(t)


# ---------------- 标准族 ----------------
def _linear(t):
    return t


def _quad(t):
    return t * t


def _cubic(t):
    return t * t * t


def _quart(t):
    return t * t * t * t


def _quint(t):
    return t * t * t * t * t


def _sine(t):
    return 1.0 - math.cos(t * math.pi / 2.0)


def _expo(t):
    if t <= 0.0:
        return 0.0
    return 2.0 ** (10.0 * (t - 1.0))


def _circ(t):
    return 1.0 - math.sqrt(max(0.0, 1.0 - t * t))


def _bounce_out(t):
    n1 = 7.5625
    d1 = 2.75
    if t < 1.0 / d1:
        return n1 * t * t
    if t < 2.0 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    if t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    t -= 2.625 / d1
    return n1 * t * t + 0.984375


def _elastic_out(t):
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    c4 = (2.0 * math.pi) / 3.0
    return 2.0 ** (-10.0 * t) * math.sin((t * 10.0 - 0.75) * c4) + 1.0


def _back_out(t):
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def _make_out(fn):
    def inner(t):
        return 1.0 - fn(1.0 - t)
    return inner


def _make_inout(fn):
    def inner(t):
        if t < 0.5:
            return fn(t * 2.0) / 2.0
        return 1.0 - fn((1.0 - t) * 2.0) / 2.0
    return inner


# ---------------- 特殊族（WindowX 的整活曲线）----------------
def _spring(t):
    if t >= 1.0:
        return 1.0
    return 1.0 - math.exp(-6.0 * t) * math.cos(12.0 * t)


def _wave(t):
    return t + math.sin(3.0 * math.pi * t) * 0.12 * (1.0 - t)


def _jump(t):
    """先冲到 1.18 再落回 1.0。"""
    if t < 0.62:
        u = t / 0.62
        return 1.18 * (1.0 - (1.0 - u) ** 2)
    u = (t - 0.62) / 0.38
    return 1.18 + (1.0 - 1.18) * (u * u * (3.0 - 2.0 * u))


def _delay(t):
    if t < 0.3:
        return 0.0
    u = (t - 0.3) / 0.7
    return 1.0 - (1.0 - u) ** 2


def _rush(t):
    return 1.0 - (1.0 - t) ** 2


def _slowmo(t):
    return t * t


def _faststart(t):
    return 1.0 - (1.0 - t) ** 5


def _stutter(t):
    steps = 8
    q = math.floor(t * steps) / float(steps)
    return 1.0 - (1.0 - q) ** 2


def _glitch(t):
    jitter = 0.03 * math.sin(97.0 * t) if t < 0.9 else 0.0
    return t + jitter


def _packetloss(t):
    marks = (0.15, 0.32, 0.48, 0.66, 0.84)
    v = t
    for m in marks:
        if t >= m:
            v = m
    if t >= 0.99:
        return 1.0
    return v


def _freeze(t):
    if t < 0.75:
        return 0.0
    u = (t - 0.75) / 0.25
    return 1.0 - (1.0 - u) ** 2


def _overshoot(t):
    c1 = 2.4
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def _snap(t):
    return 0.0 if t < 0.08 else 1.0


def _jitter(t):
    return t + 0.02 * math.sin(60.0 * t) * (1.0 - t)


def _step(n):
    def inner(t):
        if t >= 1.0:
            return 1.0
        return math.floor(t * n) / float(n)
    return inner


def _finalize(fn):
    """保证端点精确，避免浮点误差导致首尾跳变。"""
    def inner(t):
        t = _clamp01(t)
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        return fn(t)
    inner.__name__ = getattr(fn, '__name__', 'ease')
    return inner


_IN = {
    'quad': _quad, 'cubic': _cubic, 'quart': _quart, 'quint': _quint,
    'sine': _sine, 'expo': _expo, 'circ': _circ,
    'elastic': _elastic_out, 'back': _back_out,
}

REGISTRY = {}


def _register(name, fn):
    REGISTRY[name] = _finalize(fn)


for _name, _fn in _IN.items():
    _register(_name, _fn)
    _register(_name + 'out', _make_out(_fn))
    _register(_name + 'inout', _make_inout(_fn))

_register('linear', _linear)
_register('bounce', lambda t: 1.0 - _bounce_out(1.0 - t))
_register('bounceout', _bounce_out)
_register('bounceinout', _make_inout(lambda t: 1.0 - _bounce_out(1.0 - t)))

for _n, _f in (('spring', _spring), ('wave', _wave), ('jump', _jump), ('delay', _delay),
               ('rush', _rush), ('slowmo', _slowmo), ('faststart', _faststart),
               ('stutter', _stutter), ('glitch', _glitch), ('packetloss', _packetloss),
               ('freeze', _freeze), ('overshoot', _overshoot), ('snap', _snap),
               ('jitter', _jitter)):
    _register(_n, _f)

_register('step3', _step(3))
_register('step5', _step(5))
_register('step8', _step(8))

NAMES = tuple(sorted(REGISTRY.keys()))


def has_ease(name):
    return name in REGISTRY


def ease(name, t):
    """按名字取样；未知名字回退 linear。"""
    fn = REGISTRY.get(name)
    if fn is None:
        fn = REGISTRY['linear']
    return fn(t)
