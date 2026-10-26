# -*- coding: utf-8 -*-
"""摄像机数学：坐标约定转换 + FOV 夹取 + 窄视场补偿。

网易文档事实（2026-10-26 核实）：
  * SetCameraRotation(rot) 顺序为 (Pitch, Yaw, Roll)，且与 F3 显示**相反**；
  * SetFov 有效范围 [30, 110]，越界会被钳制；
  * SetPlayerFovScale 是"视场角比例（变焦）"，不是正交投影。

因此本模块只提供：符号与顺序的显式转换、FOV 夹取、以及
"远机位 + 30° 窄视场"的**视觉压缩技巧**参数计算（不是正交相机）。
"""
from __future__ import division

import math

FOV_MIN = 30.0
FOV_MAX = 110.0


def wrap_deg(v):
    """归一化到 (-180, 180]。"""
    v = float(v)
    v = math.fmod(v + 180.0, 360.0)
    if v <= 0:
        v += 360.0
    return v - 180.0


def clamp_fov(v, fallback=70.0):
    try:
        f = float(v)
    except (TypeError, ValueError):
        f = fallback
    return max(FOV_MIN, min(FOV_MAX, f))


def to_native_rotation(pitch, yaw, roll=0.0):
    """游戏内(F3 语义) -> 网易 SetCameraRotation 参数。

    依据文档"参数与 F3 显示相反"，统一取反。roll 原样透传。
    该映射需在 POC 中实测校准（见 docs/P0_RUNBOOK.md 的 camera 用例）。
    """
    return (wrap_deg(-float(pitch)), wrap_deg(-float(yaw)), float(roll))


def from_native_rotation(native_pitch, native_yaw, roll=0.0):
    return (wrap_deg(-float(native_pitch)), wrap_deg(-float(native_yaw)), float(roll))


def forward_vector(pitch, yaw):
    """游戏内朝向向量（yaw 0 = +Z，yaw 90 = -X）。"""
    p = math.radians(float(pitch))
    y = math.radians(float(yaw))
    return (-math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p))


def narrow_fov_plan(target_fov, base_fov=70.0, base_distance=8.0):
    """用"更远机位 + 30° 窄视场"压缩透视，返回 (fov, distance, multiplier)。

    target_fov >= 30 时无需补偿，返回 (clamp(target), base_distance, 1.0)。
    这是**视觉近似技巧**，不是正交投影；只在场景允许拉远机位时使用。
    """
    try:
        raw = float(target_fov)
    except (TypeError, ValueError):
        raw = float(base_fov)
    t = clamp_fov(raw, base_fov)
    if raw >= FOV_MIN:
        return t, base_distance, 1.0
    mult = perspective_compensation(FOV_MIN, base_fov)
    return FOV_MIN, base_distance * mult, mult


def perspective_compensation(target_fov, base_fov=70.0):
    """把 target_fov 换算成等效的机位拉远倍数（<30° 时用于估算）。"""
    t = max(1.0, float(target_fov))
    b = clamp_fov(base_fov)
    return math.tan(math.radians(b) * 0.5) / math.tan(math.radians(t) * 0.5)
