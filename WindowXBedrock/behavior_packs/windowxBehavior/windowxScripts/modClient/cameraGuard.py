# -*- coding: utf-8 -*-
"""摄像机状态守卫：任何退出路径都必须复原，避免玩家卡在独立相机。"""
from __future__ import division


class CameraGuard(object):
    def __init__(self, adapter):
        self.adapter = adapter
        self.snap = None
        self.active = False

    def enter(self):
        if self.active:
            return
        self.snap = self.adapter.snapshot()
        self.adapter.depart()
        self.active = True

    def exit(self):
        if not self.active:
            return
        self.adapter.restore(self.snap)
        self.snap = None
        self.active = False

    def soft_exit(self):
        """仅复原视角，不完全退出（用于切换机位）。"""
        if not self.active:
            return
        self.adapter.restore(self.snap)
        self.active = False
