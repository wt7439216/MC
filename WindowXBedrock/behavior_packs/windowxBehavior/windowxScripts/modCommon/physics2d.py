# -*- coding: utf-8 -*-
"""2D 刚体（窗口物理）：重力 / 摩擦 / 弹性 / 拖拽甩出。

与源项目同名参数：gravity(px/s^2) friction(0~1 每秒衰减) elasticity(0~1)
纯逻辑，固定步长积分，可单测。
"""
from __future__ import division


class Body2D(object):
    def __init__(self, cx, cy, w, h, gravity=1200.0, friction=0.12, elasticity=0.45):
        self.cx = float(cx)
        self.cy = float(cy)
        self.w = float(w)
        self.h = float(h)
        self.vx = 0.0
        self.vy = 0.0
        self.gravity = float(gravity)
        self.friction = max(0.0, min(1.0, float(friction)))
        self.elasticity = max(0.0, min(1.0, float(elasticity)))
        self.dragging = False
        self._drag_x = 0.0
        self._drag_y = 0.0
        self._drag_t = 0.0

    # ---- 拖拽 ----
    def drag_start(self, x, y, now):
        self.dragging = True
        self._drag_x = float(x)
        self._drag_y = float(y)
        self._drag_t = float(now)
        self.vx = 0.0
        self.vy = 0.0

    def drag_to(self, x, y, now):
        if not self.dragging:
            return
        dt = max(1e-4, float(now) - self._drag_t)
        self.vx = (float(x) - self._drag_x) / dt
        self.vy = (float(y) - self._drag_y) / dt
        self.cx = float(x)
        self.cy = float(y)
        self._drag_x = float(x)
        self._drag_y = float(y)
        self._drag_t = float(now)

    def drag_end(self):
        self.dragging = False
        # 甩出速度限幅，避免飞出画布
        limit = 4000.0
        self.vx = max(-limit, min(limit, self.vx))
        self.vy = max(-limit, min(limit, self.vy))

    # ---- 积分 ----
    def step(self, dt, view_w, view_h, floor_friction=0.9):
        dt = max(0.0, min(0.05, float(dt)))
        if self.dragging or dt <= 0.0:
            return self.cx, self.cy

        self.vy += self.gravity * dt
        damp = max(0.0, 1.0 - self.friction * dt * 60.0)
        self.vx *= damp
        self.vy *= damp

        self.cx += self.vx * dt
        self.cy += self.vy * dt

        half_w = self.w / 2.0
        half_h = self.h / 2.0
        # 左右边界
        if self.cx < half_w:
            self.cx = half_w
            self.vx = abs(self.vx) * self.elasticity
        elif self.cx > view_w - half_w:
            self.cx = view_w - half_w
            self.vx = -abs(self.vx) * self.elasticity
        # 上下边界
        if self.cy < half_h:
            self.cy = half_h
            self.vy = abs(self.vy) * self.elasticity
        elif self.cy > view_h - half_h:
            self.cy = view_h - half_h
            self.vy = -abs(self.vy) * self.elasticity
            self.vx *= floor_friction
            if abs(self.vy) < 40.0:
                self.vy = 0.0
                self.vx *= 0.85
        return self.cx, self.cy

    def at_rest(self):
        return abs(self.vx) < 1.0 and abs(self.vy) < 1.0 and self.cy >= 0.0
