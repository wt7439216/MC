# -*- coding: utf-8 -*-
"""HUD ScreenNode：承载全部伪窗口控件，并在 Update 里驱动后端。

控件路径约定与 tools/gen_ui.py 生成的一致：
    /win<i>               窗口根 panel
    /win<i>/bg            九宫格背景 image
    /win<i>/title         标题 label
    /win<i>/content       内容 image
    /win<i>/bar_drag      标题栏拖拽按钮
"""
from __future__ import division

try:
    import mod.client.extraClientApi as clientApi
except ImportError:  # 兼容旧版 SDK 的 import 路径
    import client.extraClientApi as clientApi

from windowxScripts.modCommon import modConfig

ScreenNode = clientApi.GetScreenNodeCls()


class WXHudScreen(ScreenNode):
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.system = None
        self.slots = int((param or {}).get('slots', 24))
        self._drag = {}

    # 生命周期
    def Create(self):
        for i in range(self.slots):
            root = '/win%d' % i
            self.SetVisible(root, False)
            try:
                self.AddTouchEventHandler(root + '/bar_drag',
                                          self._make_drag_cb(i), {'isSwallow': True})
            except Exception:
                pass
        sys_ = _get_client_system()
        if sys_ is not None:
            self.system = sys_
            sys_.attach_hud(self)

    def Update(self):
        if self.system is not None:
            self.system.on_hud_update()

    # 拖拽
    def _make_drag_cb(self, slot):
        def cb(args):
            if self.system is None:
                return
            state = str((args or {}).get('ButtonState') or
                        (args or {}).get('state') or '').lower()
            touch = (args or {}).get('TouchPos') or (args or {}).get('pos') or (0, 0)
            if state == 'down':
                self.system.on_drag(slot, 'down', touch)
            elif state == 'move':
                self.system.on_drag(slot, 'move', touch)
            else:
                self.system.on_drag(slot, 'up', touch)
        return cb


def _get_client_system():
    try:
        return clientApi.GetSystem(modConfig.MOD_NAME, modConfig.CLIENT_SYSTEM)
    except Exception:
        return None
