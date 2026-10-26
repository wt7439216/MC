# -*- coding: utf-8 -*-
"""HUD 后端：**对象层级**调用（P0.5 重构）。

官方层级（2026-10-26 核实）：
    ScreenNode.GetBaseUIControl(path) -> BaseUIControl
    BaseUIControl.asImage() / asLabel() / asButton() / asPanel() -> 具体控件（类型不符返回 None）
    位置/尺寸/贴图/透明度/层级都在**控件**上调用（SetFullPosition / SetFullSize /
    SetSprite / SetAlpha / SetLayer / SetVisible）。
    SetAlpha 仅对 image / label 生效。

错误策略：关键 API 缺失或类型不符 → 记录到 self.errors 并 log.error，
**不静默当成成功**；槽位不可用则跳过该槽位并标记 critical_ok=False。
"""
from __future__ import division

from mod_log import logger

from windowxScripts.modCommon import modConfig

PARTS = (
    ('root', 'Panel', ''),
    ('bg', 'Image', 'bg'),
    ('title', 'Label', 'title'),
    ('content', 'Image', 'content'),
    ('bar', 'Button', 'bar_drag'),
)


class HudBackend(object):
    def __init__(self, slots=None):
        self.slots = int(slots or modConfig.HUD_SLOTS)
        self.node = None
        self.controls = {}       # slot -> {part: control}
        self.slot_of = {}        # (owner, wid) -> slot
        self.used = set()
        self.errors = []         # [(path, method, detail)]
        self.critical_ok = True
        self.available = False

    # ---------------- 绑定 ----------------
    def bind(self, node):
        self.node = node
        self.controls = {}
        self.slot_of = {}
        self.used = set()
        self.errors = []
        self.critical_ok = True
        resolved = 0
        if node is None:
            self._error('<screen>', 'bind', 'ScreenNode is None')
            self.available = False
            return False
        if not hasattr(node, 'GetBaseUIControl'):
            self._critical('<screen>', 'GetBaseUIControl', 'method missing')
            self.available = False
            return False

        for i in range(self.slots):
            base = '/win%d' % i
            ctrls = {}
            ok = True
            for part, kind, segment in PARTS:
                path = base if not segment else base + '/' + segment
                ctrl = self._get(path, kind)
                if ctrl is None:
                    ok = False
                ctrls[part] = ctrl
            if not ok:
                # 槽位不完整：保留已取到的部分，但不参与分配
                self._error(base, 'bind', 'incomplete slot (missing part)')
                continue
            self.controls[i] = ctrls
            resolved += 1

        if resolved == 0:
            self._critical('<screen>', 'bind', 'no usable slot resolved')
        elif resolved < self.slots:
            self._error('<screen>', 'bind',
                        'resolved %d/%d slots' % (resolved, self.slots))
        self.available = resolved > 0 and self.critical_ok
        logger.info('[WX] HUD backend bound: %d/%d slots, errors=%d'
                    % (resolved, self.slots, len(self.errors)))
        return self.available

    # ---------------- 取控件 ----------------
    def _get(self, path, kind):
        getter = getattr(self.node, 'GetBaseUIControl', None)
        if getter is None:
            self._critical(path, 'GetBaseUIControl', 'method missing')
            return None
        try:
            base = getter(path)
        except Exception as exc:
            self._critical(path, 'GetBaseUIControl', repr(exc))
            return None
        if base is None:
            self._error(path, 'GetBaseUIControl', 'returned None')
            return None

        caster = getattr(base, 'as' + kind, None)
        if caster is None:
            # 部分 SDK 直接返回具体控件；退化为 base 本身
            return base
        try:
            ctrl = caster()
        except Exception as exc:
            self._error(path, 'as' + kind, repr(exc))
            return None
        if ctrl is None:
            self._error(path, 'as' + kind, 'type mismatch (None)')
            return None
        return ctrl

    # ---------------- 分配 ----------------
    def _alloc(self, key):
        if key in self.slot_of:
            return self.slot_of[key]
        for i in sorted(self.controls.keys()):
            if i not in self.used:
                self.used.add(i)
                self.slot_of[key] = i
                return i
        return None

    def release(self, key):
        slot = self.slot_of.pop(key, None)
        if slot is None:
            return
        self.used.discard(slot)
        root = self.controls.get(slot, {}).get('root')
        self._call(slot, 'root', root, 'SetVisible', False)

    # ---------------- 同步 ----------------
    def sync(self, entries):
        """entries: [(owner, wid, win, dx, dy, scale)]"""
        alive = set()
        for owner, wid, win, dx, dy, scale in entries:
            key = (owner, wid)
            alive.add(key)
            slot = self._alloc(key)
            if slot is None:
                self._error('<slots>', '_alloc', 'no free slot for %s' % (key,))
                continue
            c = self.controls.get(slot) or {}
            cx = win['cx'] + dx
            cy = win['cy'] + dy
            w = max(16.0, win['w'] * scale)
            h = max(16.0, win['h'] * scale)
            ox = (cx - modConfig.VIEW_W * 0.5) / modConfig.VIEW_W * 100.0
            oy = (cy - modConfig.VIEW_H * 0.5) / modConfig.VIEW_H * 100.0

            self._call(slot, 'root', c.get('root'), 'SetVisible',
                       bool(win.get('visible', True)))
            self._call(slot, 'root', c.get('root'), 'SetFullPosition',
                       ('%+.4f%%' % ox, '%+.4f%%' % oy))
            self._call(slot, 'root', c.get('root'), 'SetFullSize',
                       ('%.4f%%' % (w / modConfig.VIEW_W * 100.0),
                        '%.4f%%' % (h / modConfig.VIEW_H * 100.0)))
            self._call(slot, 'root', c.get('root'), 'SetLayer',
                       10 if win.get('layer') == 'top' else 0)
            self._call(slot, 'title', c.get('title'), 'SetText',
                       str(win.get('title') or ''))

            content = win.get('content') or {}
            if content.get('kind') == 'texture' and content.get('path'):
                self._call(slot, 'content', c.get('content'), 'SetVisible', True)
                self._call(slot, 'content', c.get('content'), 'SetSprite',
                           content['path'])
            else:
                self._call(slot, 'content', c.get('content'), 'SetVisible', False)

            alpha = 0.85 if win.get('layer') == 'clickthrough' else 1.0
            self._call(slot, 'bg', c.get('bg'), 'SetAlpha', alpha)
            self._call(slot, 'bar', c.get('bar'), 'SetTouchEnable',
                       win.get('layer') != 'clickthrough')

        for key in list(self.slot_of.keys()):
            if key not in alive:
                self.release(key)

    # ---------------- 调用包装 ----------------
    def _call(self, slot, part, ctrl, method, *args):
        if ctrl is None:
            self._error('/win%s/%s' % (slot, part), method, 'control is None')
            return False
        fn = getattr(ctrl, method, None)
        if fn is None:
            self._error('/win%s/%s' % (slot, part), method, 'method missing')
            return False
        try:
            fn(*args)
            return True
        except Exception as exc:
            self._error('/win%s/%s' % (slot, part), method, repr(exc))
            return False

    # ---------------- 错误记录 ----------------
    def _error(self, path, method, detail):
        item = (path, method, detail)
        if len(self.errors) < 200:
            self.errors.append(item)
        logger.error('[WX] ui api error %s.%s: %s' % (path, method, detail))

    def _critical(self, path, method, detail):
        self.critical_ok = False
        self._error(path, method, detail)

    def error_summary(self):
        if not self.errors:
            return 'no errors'
        return '%d errors, first: %r' % (len(self.errors), self.errors[0])
