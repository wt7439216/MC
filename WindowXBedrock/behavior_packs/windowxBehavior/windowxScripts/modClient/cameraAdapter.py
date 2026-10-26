# -*- coding: utf-8 -*-
"""摄像机适配层：唯一调用网易相机 API 的地方（P0.5：失败可观测）。

官方能力（2026-10-26 核实）：
    CreateCamera(levelId) -> CameraComponentClient
      SetCameraPos / SetCameraRotation(Pitch,Yaw,Roll) / SetFov([30,110])
      SetCameraOffset(仅第三人称) / SetCameraAnchor / SetCameraBindActorId
      DepartCamera / UnDepartCamera / ResetCameraPos / LockCamera / UnLockCamera
    CreatePlayerView(entityId) -> SetPerspective(0/1/2) / SetPlayerFovScale(0~100)
    没有正交投影 / RTT / 多视口。

契约：任何 API 缺失或抛错都记入 self.failures 并返回 False，
调用方不得把 False 当成功。
"""
from __future__ import division

from mod_log import logger

try:
    import mod.client.extraClientApi as clientApi
except ImportError:
    import client.extraClientApi as clientApi

from windowxScripts.modCommon import camera_math


class CameraAdapter(object):
    def __init__(self, level_id, player_id):
        self.level_id = level_id
        self.player_id = player_id
        self._cam = None
        self._view = None
        self.failures = []
        self._factory_error = None

    # ---------------- 基础设施 ----------------
    def _factory(self):
        try:
            return clientApi.GetEngineCompFactory()
        except Exception as exc:
            self._record('GetEngineCompFactory', exc)
            self._factory_error = exc
            return None

    def _components(self):
        factory = self._factory()
        if factory is None:
            return None, None
        if self._cam is None:
            try:
                self._cam = factory.CreateCamera(self.level_id)
            except Exception as exc:
                self._record('CreateCamera', exc)
        if self._view is None:
            try:
                self._view = factory.CreatePlayerView(self.player_id)
            except Exception as exc:
                self._record('CreatePlayerView', exc)
        return self._cam, self._view

    def _record(self, name, exc):
        item = (name, repr(exc))
        if len(self.failures) < 100:
            self.failures.append(item)
        logger.error('[WX] camera api %s failed: %r' % (name, exc))

    def _call(self, comp, name, *args):
        if comp is None:
            self._record(name, 'component is None')
            return False, None
        fn = getattr(comp, name, None)
        if fn is None:
            self._record(name, 'method missing')
            return False, None
        try:
            return True, fn(*args)
        except Exception as exc:
            self._record(name, exc)
            return False, None

    def available(self):
        cam, _ = self._components()
        return cam is not None

    def healthy(self):
        return not self.failures

    # ---------------- 快照 / 恢复 ----------------
    def snapshot(self):
        cam, view = self._components()
        snap = {'fov': None, 'offset': None, 'perspective': None,
                'ok': True, 'failures': []}
        if cam is not None:
            ok, fov = self._call(cam, 'GetFov')
            if ok and fov is not None:
                snap['fov'] = float(fov)
            else:
                snap['ok'] = False
            ok, offset = self._call(cam, 'GetCameraOffset')
            if ok and offset:
                snap['offset'] = tuple(offset)
            else:
                snap['ok'] = False
        else:
            snap['ok'] = False
        if view is not None:
            ok, persp = self._call(view, 'GetPerspective')
            if ok and persp is not None:
                snap['perspective'] = int(persp)
            else:
                snap['ok'] = False
        else:
            snap['ok'] = False
        snap['failures'] = list(self.failures)
        return snap

    def restore(self, snap):
        """总是尝试全部恢复步骤；返回 {'ok','attempted','failed'}"""
        snap = snap or {}
        cam, view = self._components()
        attempted = []
        failed = []

        def step(key, comp, name, *args):
            attempted.append(name)
            ok, _ = self._call(comp, name, *args)
            if not ok:
                failed.append(name)

        step('lock', cam, 'UnLockCamera')
        step('depart', cam, 'UnDepartCamera')
        step('pos', cam, 'ResetCameraPos')
        step('bind', cam, 'ResetCameraBindActorId')
        if snap.get('fov') is not None:
            step('fov', cam, 'SetFov', camera_math.clamp_fov(snap['fov']))
        if snap.get('offset') is not None:
            step('offset', cam, 'SetCameraOffset', tuple(snap['offset']))
        if snap.get('perspective') is not None:
            step('persp', view, 'SetPerspective', int(snap['perspective']))

        ok = not failed
        if failed:
            logger.error('[WX] camera restore incomplete: %r' % (failed,))
        return {'ok': ok, 'attempted': attempted, 'failed': failed}

    # ---------------- 应用 ----------------
    def depart(self):
        cam, _ = self._components()
        ok, _ = self._call(cam, 'DepartCamera')
        return ok

    def set_transform(self, pos=None, pitch=None, yaw=None, roll=0.0):
        cam, _ = self._components()
        if cam is None:
            return False
        ok_all = True
        if pos is not None:
            ok, _ = self._call(cam, 'SetCameraPos', tuple(pos))
            ok_all = ok_all and ok
        if pitch is not None and yaw is not None:
            native = camera_math.to_native_rotation(pitch, yaw, roll)
            ok, _ = self._call(cam, 'SetCameraRotation', native)
            ok_all = ok_all and ok
        return ok_all

    def set_fov(self, fov):
        cam, _ = self._components()
        ok, _ = self._call(cam, 'SetFov', camera_math.clamp_fov(fov))
        return ok

    def bind_actor(self, entity_id):
        cam, _ = self._components()
        ok, _ = self._call(cam, 'SetCameraBindActorId', entity_id)
        return ok

    def unbind_actor(self):
        cam, _ = self._components()
        ok, _ = self._call(cam, 'ResetCameraBindActorId')
        return ok

    def set_perspective(self, mode):
        _, view = self._components()
        ok, _ = self._call(view, 'SetPerspective', int(mode))
        return ok

    def set_fov_scale(self, scale):
        _, view = self._components()
        ok, _ = self._call(view, 'SetPlayerFovScale', float(scale))
        return ok

    def failure_report(self):
        return {'ok': not self.failures,
                'failures': list(self.failures),
                'factory_error': repr(self._factory_error)}
