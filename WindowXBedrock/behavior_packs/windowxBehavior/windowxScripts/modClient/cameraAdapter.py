# -*- coding: utf-8 -*-
"""摄像机适配层：唯一调用网易相机 API 的地方。

能力边界（官方文档 2026-10-26 核实）：
  CreateCamera(levelId) -> CameraComponentClient
    SetCameraPos / SetCameraRotation(Pitch,Yaw,Roll) / SetFov([30,110])
    SetCameraOffset(仅第三人称) / SetCameraAnchor / SetCameraBindActorId
    DepartCamera / UnDepartCamera / ResetCameraPos / LockCamera / UnLockCamera
    AddCameraTrackMotion / AddCameraAroundPointMotion / Start|StopCameraMotion
  CreatePlayerView(entityId) -> SetPerspective(0/1/2) / SetPlayerFovScale(0~100)

**没有**正交投影、没有 RTT、没有多视口。所有方法用 getattr 保护，
缺失时降级而不是崩溃。
"""
from __future__ import division

import client.extraClientApi as clientApi

from windowxScripts.modCommon import camera_math


def _safe(obj, name, *args):
    fn = getattr(obj, name, None)
    if fn is None:
        return None
    try:
        return fn(*args)
    except Exception:
        return None


class CameraAdapter(object):
    def __init__(self, level_id, player_id):
        self.level_id = level_id
        self.player_id = player_id
        self._cam = None
        self._view = None

    def _ensure(self):
        factory = clientApi.GetEngineCompFactory()
        if self._cam is None:
            self._cam = _safe(factory, 'CreateCamera', self.level_id)
        if self._view is None:
            self._view = _safe(factory, 'CreatePlayerView', self.player_id)
        return self._cam

    def available(self):
        return self._ensure() is not None

    # ---------------- 快照/恢复 ----------------
    def snapshot(self):
        cam = self._ensure()
        snap = {'fov': 70.0, 'offset': (0.0, 0.0, 0.0), 'perspective': 1,
                'departed': False, 'rotation': (0.0, 0.0, 0.0)}
        if cam is not None:
            fov = _safe(cam, 'GetFov')
            if fov is not None:
                snap['fov'] = float(fov)
            off = _safe(cam, 'GetCameraOffset')
            if off:
                snap['offset'] = tuple(off)
            rot = _safe(cam, 'GetCameraRotation')
            if rot:
                snap['rotation'] = tuple(rot)
        if self._view is not None:
            persp = _safe(self._view, 'GetPerspective')
            if persp is not None:
                snap['perspective'] = int(persp)
        return snap

    def restore(self, snap):
        snap = snap or {}
        cam = self._ensure()
        if cam is not None:
            _safe(cam, 'UnLockCamera')
            _safe(cam, 'UnDepartCamera')
            _safe(cam, 'ResetCameraPos')
            _safe(cam, 'ResetCameraBindActorId')
            if snap.get('fov') is not None:
                _safe(cam, 'SetFov', camera_math.clamp_fov(snap['fov']))
            if snap.get('offset'):
                _safe(cam, 'SetCameraOffset', tuple(snap['offset']))
        if self._view is not None and snap.get('perspective') is not None:
            _safe(self._view, 'SetPerspective', int(snap['perspective']))

    # ---------------- 应用 ----------------
    def depart(self):
        cam = self._ensure()
        if cam is not None:
            _safe(cam, 'DepartCamera')

    def set_transform(self, pos=None, pitch=None, yaw=None, roll=0.0):
        cam = self._ensure()
        if cam is None:
            return False
        if pos is not None:
            _safe(cam, 'SetCameraPos', tuple(pos))
        if pitch is not None and yaw is not None:
            native = camera_math.to_native_rotation(pitch, yaw, roll)
            _safe(cam, 'SetCameraRotation', native)
        return True

    def set_fov(self, fov):
        cam = self._ensure()
        if cam is None:
            return False
        _safe(cam, 'SetFov', camera_math.clamp_fov(fov))
        return True

    def bind_actor(self, entity_id):
        cam = self._ensure()
        if cam is not None:
            _safe(cam, 'SetCameraBindActorId', entity_id)

    def unbind_actor(self):
        cam = self._ensure()
        if cam is not None:
            _safe(cam, 'ResetCameraBindActorId')

    def set_perspective(self, mode):
        if self._view is not None:
            _safe(self._view, 'SetPerspective', int(mode))

    def set_fov_scale(self, scale):
        """0~100，仅用于变焦近似，不用于正交投影。"""
        if self._view is not None:
            _safe(self._view, 'SetPlayerFovScale', float(scale))
