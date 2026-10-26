# -*- coding: utf-8 -*-
"""HUD ScreenNode（P0.5：控件对象 + 官方触摸回调）。

官方能力（2026-10-26 核实）：
    GetBaseUIControl(path).asButton() -> 按钮控件
    按钮必须先 AddTouchEventParams()，再 SetButtonTouchDown/Move/Up/CancelCallback
    Update() 由引擎每帧调用（约 30fps）

控件路径与 tools/gen_ui.py 生成结果一致：
    /win<i> /bg /title /content /bar_drag
"""
from __future__ import division

from mod_log import logger

try:
    import mod.client.extraClientApi as clientApi
except ImportError:  # 兼容旧版 SDK
    import client.extraClientApi as clientApi

from windowxScripts.modCommon import modConfig

ScreenNode = clientApi.GetScreenNodeCls()

TOUCH_BINDINGS = (
    ('SetButtonTouchDownCallback', 'down'),
    ('SetButtonTouchMoveCallback', 'move'),
    ('SetButtonTouchUpCallback', 'up'),
    ('SetButtonTouchCancelCallback', 'cancel'),
)


class WXHudScreen(ScreenNode):
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.system = None
        self.slots = int(modConfig.HUD_SLOTS)
        self.touch_ready = 0
        self.errors = []

    # ---------------- 生命周期 ----------------
    def Create(self):
        # 顺序很重要：先探测 UI 实际槽位，再让客户端系统按该数量绑定后端，
        # 最后注册触摸回调。反过来会让 backend 用默认 24 绑定，导致槽位错配。
        self.slots = self._detect_slots()
        self._attach_system()
        for i in range(self.slots):
            if self._bind_drag(i):
                self.touch_ready += 1
        logger.info('[WX] HUD Create: slots=%d touch_ready=%d errors=%d'
                    % (self.slots, self.touch_ready, len(self.errors)))

    def _detect_slots(self):
        """按 UI JSON 实际生成的 /win<i> 数量探测，避免与常量 24 失配。"""
        count = 0
        limit = int(modConfig.HUD_SLOT_PROBE_LIMIT)
        while count < limit:
            if self._probe_control('/win%d' % count) is None:
                break
            count += 1
        if count == 0:
            self._error('<screen>', '_detect_slots',
                        'no /win<i> found, fallback to HUD_SLOTS=%d'
                        % modConfig.HUD_SLOTS)
            return int(modConfig.HUD_SLOTS)
        if count != int(modConfig.HUD_SLOTS):
            logger.warn('[WX] UI slots=%d differs from HUD_SLOTS=%d (runtime follows UI)'
                        % (count, modConfig.HUD_SLOTS))
        return count

    def Update(self):
        if self.system is not None:
            self.system.on_hud_update()

    # ---------------- 系统绑定 ----------------
    def _attach_system(self):
        try:
            self.system = clientApi.GetSystem(modConfig.MOD_NAME,
                                              modConfig.CLIENT_SYSTEM)
        except Exception as exc:
            self._error('GetSystem', repr(exc))
            self.system = None
            return
        if self.system is None:
            self._error('GetSystem', 'returned None')
            return
        try:
            self.system.attach_hud(self)
        except Exception as exc:
            self._error('attach_hud', repr(exc))

    # ---------------- 拖拽 ----------------
    def _bind_drag(self, slot):
        path = '/win%d/bar_drag' % slot
        base = self._control(path)
        if base is None:
            return False
        button = self._as(base, 'asButton', path)
        if button is None:
            return False
        if not self._enable_touch(button, path):
            return False
        ok = True
        for method, state in TOUCH_BINDINGS:
            fn = getattr(button, method, None)
            if fn is None:
                self._error(path, method, 'missing')
                ok = False
                continue
            try:
                fn(self._make_cb(slot, state))
            except Exception as exc:
                self._error(path, method, repr(exc))
                ok = False
        return ok

    def _probe_control(self, path):
        """探测用：不记录错误（避免把"最后一个不存在的槽位"当成异常）。"""
        getter = getattr(self, 'GetBaseUIControl', None)
        if getter is None:
            return None
        try:
            return getter(path)
        except Exception:
            return None

    def _control(self, path):
        getter = getattr(self, 'GetBaseUIControl', None)
        if getter is None:
            self._error(path, 'GetBaseUIControl', 'missing')
            return None
        try:
            ctrl = getter(path)
        except Exception as exc:
            self._error(path, 'GetBaseUIControl', repr(exc))
            return None
        if ctrl is None:
            self._error(path, 'GetBaseUIControl', 'None')
        return ctrl

    def _as(self, base, caster_name, path):
        caster = getattr(base, caster_name, None)
        if caster is None:
            return base          # 老 SDK 可能直接返回具体控件
        try:
            ctrl = caster()
        except Exception as exc:
            self._error(path, caster_name, repr(exc))
            return None
        if ctrl is None:
            self._error(path, caster_name, 'type mismatch')
        return ctrl

    def _enable_touch(self, button, path):
        fn = getattr(button, 'AddTouchEventParams', None)
        if fn is None:
            self._error(path, 'AddTouchEventParams', 'missing')
            return False
        try:
            fn()
            return True
        except TypeError:
            pass
        except Exception as exc:
            self._error(path, 'AddTouchEventParams', repr(exc))
            return False
        try:
            fn({'isSwallow': True})
            return True
        except Exception as exc:
            self._error(path, 'AddTouchEventParams(dict)', repr(exc))
            return False

    def _make_cb(self, slot, state):
        def cb(args):
            if self.system is None:
                return
            payload = args if isinstance(args, dict) else {}
            touch = (payload.get('TouchPos') or payload.get('pos')
                     or payload.get('position') or (0, 0))
            try:
                self.system.on_drag(slot, state, touch)
            except Exception as exc:
                self._error('/win%d/bar_drag' % slot, 'on_drag', repr(exc))
        return cb

    # ---------------- 错误 ----------------
    def _error(self, path, method, detail):
        if len(self.errors) < 200:
            self.errors.append((path, method, detail))
        logger.error('[WX] hud api error %s.%s: %s' % (path, method, detail))
