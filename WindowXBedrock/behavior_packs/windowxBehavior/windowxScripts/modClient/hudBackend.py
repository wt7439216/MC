# -*- coding: utf-8 -*-
"""HUD 后端：把窗口状态写到网易自定义 UI 的控件上。

约束（官方文档核实）：
  * 控件级有 SetPosition/SetFullPosition/SetSize/SetFullSize/SetAlpha/SetSprite；
  * SetAlpha 只对 image / label 生效 -> 皮肤全部用 image；
  * 每帧驱动来自 ScreenNode.Update（约 30fps）。

所有 SDK 调用都做了 hasattr/getattr 保护：某接口缺失时只降级并记一次日志，
不抛异常打断整帧。
"""
from __future__ import division

from windowxScripts.modCommon import modConfig


def _fmt_pct(v):
    return '%+.4f%%' % v


class HudBackend(object):
    def __init__(self, node=None, slots=0):
        self.node = node
        self.slots = int(slots)
        self.slot_of = {}      # wid -> slot
        self.used = set()
        self.missing = set()
        self.low_profile = False

    # ---------------- 绑定 ----------------
    def bind_node(self, node):
        self.node = node
        if node is not None:
            self.used.clear()
            self.slot_of.clear()

    def _call(self, name, *a):
        if self.node is None:
            return False
        fn = getattr(self.node, name, None)
        if fn is None:
            if name not in self.missing:
                self.missing.add(name)
            return False
        try:
            fn(*a)
            return True
        except Exception:
            if name not in self.missing:
                self.missing.add(name)
            return False

    # ---------------- 槽位 ----------------
    def _alloc(self, wid):
        if wid in self.slot_of:
            return self.slot_of[wid]
        for i in range(self.slots):
            if i not in self.used:
                self.used.add(i)
                self.slot_of[wid] = i
                return i
        return None

    def release(self, wid):
        slot = self.slot_of.pop(wid, None)
        if slot is not None:
            self.used.discard(slot)
            self._call('SetVisible', '/win%d' % slot, False)

    def sync(self, entries):
        """entries: [(wid, win, dx, dy, scale), ...]"""
        self.low_profile = len(entries) >= modConfig.DEGRADE_WINDOW_COUNT
        alive = set()
        for wid, win, dx, dy, scale in entries:
            alive.add(wid)
            slot = self._alloc(wid)
            if slot is None:
                continue
            root = '/win%d' % slot
            cx = win['cx'] + dx
            cy = win['cy'] + dy
            w = max(16.0, win['w'] * scale)
            h = max(16.0, win['h'] * scale)
            # 中心坐标 -> anchor=center 的偏移百分比
            ox = (cx - modConfig.VIEW_W * 0.5) / modConfig.VIEW_W * 100.0
            oy = (cy - modConfig.VIEW_H * 0.5) / modConfig.VIEW_H * 100.0
            self._call('SetVisible', root, bool(win.get('visible', True)))
            self._call('SetFullPosition', root, (_fmt_pct(ox), _fmt_pct(oy)))
            self._call('SetFullSize', root, (_fmt_pct(w / modConfig.VIEW_W * 100.0),
                                            _fmt_pct(h / modConfig.VIEW_H * 100.0)))
            self._call('SetLayer', root, 10 if win.get('layer') == 'top' else 0)
            self._call('SetText', root + '/title', str(win.get('title') or ''))
            content = win.get('content') or {}
            if content.get('kind') == 'texture' and content.get('path'):
                self._call('SetSprite', root + '/content', content['path'])
                self._call('SetVisible', root + '/content', True)
            elif content.get('kind') == 'text':
                self._call('SetVisible', root + '/content', False)
            # 点击穿透（界面级 SetIsSwallow 由 HUD 屏统一控制，这里只切触摸）
            self._call('SetTouchEnable', root + '/bar_drag',
                       win.get('layer') != 'clickthrough')
        for wid in list(self.slot_of.keys()):
            if wid not in alive:
                self.release(wid)

    def available(self):
        return self.node is not None and not self.missing
