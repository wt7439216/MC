# -*- coding: utf-8 -*-
"""动画任务与特效采样（对应 WindowX 的 WindowAnimator / AnimationTask）。

全部以"归一化时间 t∈[0,1]"为输入，返回该时刻的几何量，
客户端每 tick 调用一次即可。纯逻辑、可单测。
"""
from __future__ import division

import math

from . import easing
from . import layout
from . import modConfig


# ---------------- 时长 ----------------
def move_duration(distance, speed=1.0):
    speed = max(0.05, float(speed or 1.0))
    dur = abs(float(distance)) / (modConfig.BASE_SPEED_PX_PER_S * speed)
    return max(modConfig.MIN_DURATION, min(modConfig.MAX_DURATION, dur))


def lerp(a, b, t):
    return a + (b - a) * t


def sample_move(fr, to, t, ease_name):
    k = easing.ease(ease_name, t)
    return (lerp(fr[0], to[0], k), lerp(fr[1], to[1], k))


def sample_zoom(fr_wh, to_wh, fr_c, to_c, t, ease_name):
    k = easing.ease(ease_name, t)
    w = lerp(fr_wh[0], to_wh[0], k)
    h = lerp(fr_wh[1], to_wh[1], k)
    cx = lerp(fr_c[0], to_c[0], k)
    cy = lerp(fr_c[1], to_c[1], k)
    return w, h, cx, cy


# ---------------- 特效 ----------------
def shake_offset(t, intensity):
    """衰减正弦抖动；t∈[0,1]，端点归零。"""
    amp = float(intensity) * (1.0 - t)
    phase = t * math.pi * 18.0
    return (math.sin(phase) * amp, math.cos(phase * 1.7) * amp * 0.6)


def encircle_offset(t, rx, ry, total_deg, start_deg=0.0):
    """绕中心公转：返回 (dx, dy, 当前角度)。"""
    deg = start_deg + float(total_deg) * t
    rad = math.radians(deg)
    return (math.cos(rad) * float(rx), math.sin(rad) * float(ry), deg)


def wobble_offset(t, ix, iy, speed=1.0, cycles=3):
    """正弦摇摆，按 cycles 完整周期数。"""
    phase = 2.0 * math.pi * float(cycles) * t * max(0.05, float(speed))
    return (math.sin(phase) * float(ix), math.sin(phase * 0.7) * float(iy))


def breath_scale(t, intensity=0.06, speed=1.0, cycles=3):
    """呼吸式缩放系数（1.0 附近振荡，端点回到 1.0）。"""
    phase = 2.0 * math.pi * float(cycles) * t * max(0.05, float(speed))
    wave = math.sin(phase) * float(intensity)
    return 1.0 + wave * (1.0 - t)


# ---------------- 任务 ----------------
def make_move_task(window, to_cx, to_cy, speed, ease_name):
    dist = math.hypot(to_cx - window['cx'], to_cy - window['cy'])
    return {
        'kind': 'move', 'id': window['id'], 'elapsed': 0.0,
        'dur': move_duration(dist, speed), 'ease': ease_name,
        'from': (window['cx'], window['cy']), 'to': (to_cx, to_cy),
    }


def make_zoom_task(window, new_w, new_h, new_cx, new_cy, speed, ease_name):
    dist = math.hypot(new_w - window['w'], new_h - window['h'])
    dist += math.hypot(new_cx - window['cx'], new_cy - window['cy'])
    return {
        'kind': 'zoom', 'id': window['id'], 'elapsed': 0.0,
        'dur': move_duration(dist, speed), 'ease': ease_name,
        'from_wh': (window['w'], window['h']), 'to_wh': (new_w, new_h),
        'from_c': (window['cx'], window['cy']), 'to_c': (new_cx, new_cy),
    }


def make_fx_task(window, kind, dur, params):
    task = {'kind': 'fx', 'fx': kind, 'id': window['id'],
            'elapsed': 0.0, 'dur': max(0.05, float(dur))}
    task.update(params or {})
    return task


def task_progress(task):
    dur = float(task.get('dur') or 0.0)
    if dur <= 0.0:
        return 1.0
    return max(0.0, min(1.0, float(task.get('elapsed', 0.0)) / dur))


def step_task(task, dt):
    task['elapsed'] = float(task.get('elapsed', 0.0)) + max(0.0, float(dt))
    return task_progress(task)


def apply_task(window, task, t):
    """把任务在 t 时刻的结果写回 window（就地修改），返回变化的字段名集合。"""
    changed = set()
    if task['kind'] == 'move':
        cx, cy = sample_move(task['from'], task['to'], t, task['ease'])
        cx, cy, w, h = layout.clamp_window(cx, cy, window['w'], window['h'],
                                           modConfig.VIEW_W, modConfig.VIEW_H)
        window['cx'], window['cy'] = cx, cy
        changed.update(('cx', 'cy'))
    elif task['kind'] == 'zoom':
        w, h, cx, cy = sample_zoom(task['from_wh'], task['to_wh'],
                                   task['from_c'], task['to_c'], t, task['ease'])
        cx, cy, w, h = layout.clamp_window(cx, cy, w, h,
                                           modConfig.VIEW_W, modConfig.VIEW_H)
        window['w'], window['h'], window['cx'], window['cy'] = w, h, cx, cy
        changed.update(('w', 'h', 'cx', 'cy'))
    return changed


def fx_offsets(task, t):
    """特效任务在 t 时刻的偏移/缩放，客户端叠加到基础坐标上。"""
    kind = task.get('fx')
    if kind == 'shake':
        dx, dy = shake_offset(t, task.get('intensity', 8.0))
        return dx, dy, 1.0
    if kind == 'encircle':
        dx, dy, _ = encircle_offset(t, task.get('rx', 60.0), task.get('ry', 40.0),
                                    task.get('deg', 360.0), task.get('start', 0.0))
        return dx, dy, 1.0
    if kind == 'wobble':
        dx, dy = wobble_offset(t, task.get('ix', 6.0), task.get('iy', 6.0),
                               task.get('speed', 1.0), task.get('cycles', 3))
        return dx, dy, 1.0
    if kind == 'breath':
        s = breath_scale(t, task.get('intensity', 0.06),
                         task.get('speed', 0.5), task.get('cycles', 3))
        return 0.0, 0.0, s
    return 0.0, 0.0, 1.0
