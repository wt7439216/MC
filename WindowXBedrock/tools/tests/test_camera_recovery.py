# -*- coding: utf-8 -*-
"""相机 API 失败注入与恢复路径（SDK Mock）。"""
from __future__ import division

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PROJECT = os.path.dirname(TOOLS)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(PROJECT, 'behavior_packs', 'windowxBehavior'))

import sdkmock  # noqa: E402

STATE = sdkmock.install()

from windowxScripts.modCommon import modConfig  # noqa: E402
from windowxScripts.modClient import cameraAdapter  # noqa: E402
from windowxScripts.modClient import cameraGuard  # noqa: E402
from windowxScripts.modClient import clientSystem  # noqa: E402


class CameraAdapterTest(unittest.TestCase):
    def setUp(self):
        sdkmock.reset()

    def test_normal_calls_succeed(self):
        adapter = cameraAdapter.CameraAdapter('level1', 'p1')
        self.assertTrue(adapter.available())
        self.assertTrue(adapter.set_fov(70))
        self.assertTrue(adapter.set_transform((1, 2, 3), 10, 20))
        self.assertTrue(adapter.healthy())

    def test_missing_method_reports_failure(self):
        STATE.camera_fail = {'SetFov'}
        adapter = cameraAdapter.CameraAdapter('level1', 'p1')
        self.assertFalse(adapter.set_fov(70))
        self.assertFalse(adapter.healthy())
        self.assertTrue(any(f[0] == 'SetFov' for f in adapter.failures))

    def test_create_camera_failure(self):
        STATE.factory_fail = {'CreateCamera'}
        adapter = cameraAdapter.CameraAdapter('level1', 'p1')
        self.assertFalse(adapter.available())
        self.assertFalse(adapter.set_fov(60))
        report = adapter.failure_report()
        self.assertFalse(report['ok'])

    def test_restore_returns_real_result(self):
        adapter = cameraAdapter.CameraAdapter('level1', 'p1')
        snap = adapter.snapshot()
        STATE.camera_fail = {'UnDepartCamera'}
        report = adapter.restore(snap)
        self.assertFalse(report['ok'])
        self.assertIn('UnDepartCamera', report['failed'])
        self.assertIn('ResetCameraPos', report['attempted'])


class CameraGuardTest(unittest.TestCase):
    def setUp(self):
        sdkmock.reset()

    def test_normal_enter_exit(self):
        guard = cameraGuard.CameraGuard(cameraAdapter.CameraAdapter('level1', 'p1'))
        self.assertTrue(guard.enter())
        report = guard.exit()
        self.assertTrue(report['ok'], report)
        self.assertFalse(guard.active)

    def test_snapshot_failure_never_claims_success(self):
        STATE.camera_fail = {'GetFov'}
        guard = cameraGuard.CameraGuard(cameraAdapter.CameraAdapter('level1', 'p1'))
        self.assertFalse(guard.enter())
        report = guard.exit()
        self.assertFalse(report['ok'])
        self.assertIn('snapshot', report['failed'])

    def test_restore_failure_is_reported(self):
        guard = cameraGuard.CameraGuard(cameraAdapter.CameraAdapter('level1', 'p1'))
        guard.enter()
        STATE.camera_fail = {'SetFov'}
        report = guard.exit()
        self.assertFalse(report['ok'])
        self.assertIn('SetFov', report['failed'])
        self.assertFalse(guard.active)

    def test_adapter_exception_does_not_escape(self):
        class Boom(object):
            def snapshot(self):
                return {'ok': True, 'fov': 70.0, 'offset': None, 'perspective': None}

            def depart(self):
                return True

            def restore(self, snap):
                raise RuntimeError('boom')

        guard = cameraGuard.CameraGuard(Boom())
        guard.enter()
        report = guard.exit()          # 不得抛异常
        self.assertFalse(report['ok'])
        self.assertFalse(guard.active)


class ClientCameraTest(unittest.TestCase):
    def setUp(self):
        sdkmock.reset()
        STATE.ui_slots = 2
        self.cs = clientSystem.WXClientSystem('windowx', modConfig.CLIENT_SYSTEM)

    def test_set_camera_failure_exits_guard(self):
        STATE.camera_fail = {'SetFov'}
        ok = self.cs.set_camera((0, 64, 0), 0, 0, fov=90)
        self.assertFalse(ok)
        self.assertFalse(self.cs.guard.active)
        self.assertFalse(self.cs.camera.healthy())

    def test_set_camera_success(self):
        ok = self.cs.set_camera((0, 64, 0), 0, 90, fov=70)
        self.assertTrue(ok)
        self.assertTrue(self.cs.reset_camera())

    def test_shutdown_restores(self):
        self.cs.set_camera((0, 64, 0), 0, 0, fov=70)
        report = self.cs.shutdown()
        self.assertTrue(report['ok'], report)


if __name__ == '__main__':
    unittest.main()
