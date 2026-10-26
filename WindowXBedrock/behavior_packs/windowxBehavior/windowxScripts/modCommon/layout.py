# -*- coding: utf-8 -*-
"""坐标与锚点换算（对应 WindowX 的绝对 / r 相对 / p 百分比 语义）。

约定：位置是"窗口中心"在虚拟画布中的像素坐标；尺寸是像素。
纯数学，无 SDK 依赖。
"""
from __future__ import division

ANCHORS = {
    'topleft': (0.0, 0.0),
    'top': (0.5, 0.0),
    'topright': (1.0, 0.0),
    'left': (0.0, 0.5),
    'center': (0.5, 0.5),
    'right': (1.0, 0.5),
    'bottomleft': (0.0, 1.0),
    'bottom': (0.5, 1.0),
    'bottomright': (1.0, 1.0),
}


def parse_coord(text):
    """'960' -> ('abs', 960.0); 'r+20' -> ('rel', 20.0); 'p50' -> ('pct', 50.0)"""
    s = str(text).strip().lower().replace(' ', '')
    if not s:
        raise ValueError('empty coord')
    if s[0] == 'r':
        rest = s[1:]
        return ('rel', float(rest) if rest not in ('', '+', '-') else 0.0)
    if s[0] == 'p':
        return ('pct', float(s[1:]))
    return ('abs', float(s))


def resolve_coord(text, base, total, lo=None, hi=None):
    """把坐标字符串解析为像素值，并按 [lo, hi] 夹取。"""
    kind, val = parse_coord(text)
    if kind == 'abs':
        out = val
    elif kind == 'rel':
        out = float(base) + val
    else:
        out = float(total) * val / 100.0
    if lo is None:
        lo = 0.0
    if hi is None:
        hi = float(total)
    if out < lo:
        out = lo
    if out > hi:
        out = hi
    return out


def anchor_ratio(name):
    return ANCHORS.get(str(name).strip().lower(), ANCHORS['center'])


def clamp_window(cx, cy, w, h, view_w, view_h):
    """窗口不得整体跑出画布：至少保留 24px 可见。"""
    margin = 24.0
    w = max(16.0, min(float(w), float(view_w) - margin))
    h = max(16.0, min(float(h), float(view_h) - margin))
    half_w = w / 2.0
    half_h = h / 2.0
    cx = max(half_w - w + margin, min(float(cx), view_w - half_w + w - margin))
    cy = max(half_h - h + margin, min(float(cy), view_h - half_h + h - margin))
    return cx, cy, w, h


def zoom_keep_anchor(cx, cy, w, h, new_w, new_h, anchor):
    """缩放时保持锚点在屏幕上的位置不变，返回新的中心点。"""
    ax, ay = anchor_ratio(anchor)
    left = cx - w * 0.5
    top = cy - h * 0.5
    new_left = left + w * ax - new_w * ax
    new_top = top + h * ay - new_h * ay
    return new_left + new_w * 0.5, new_top + new_h * 0.5


def to_ui_offset(cx, cy, w, h, view_w, view_h):
    """中心坐标 -> 网易 UI 的 anchor=center 偏移（百分比, 百分比）。

    UI 的 offset 支持 "百分比+px" 字符串；这里统一输出百分比，
    由后端拼成 '%+.4f%%' 形式。
    """
    return ((cx - view_w * 0.5) / view_w * 100.0,
            (cy - view_h * 0.5) / view_h * 100.0)
