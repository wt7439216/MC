# -*- coding: utf-8 -*-
"""缓动 / 坐标 / 相机数学 / 协议 的纯逻辑测试。"""
from __future__ import division

import math
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PROJECT = os.path.dirname(TOOLS)
sys.path.insert(0, os.path.join(PROJECT, 'behavior_packs', 'windowxBehavior'))

from windowxScripts.modCommon import camera_math  # noqa: E402
from windowxScripts.modCommon import easing  # noqa: E402
from windowxScripts.modCommon import layout  # noqa: E402
from windowxScripts.modCommon import modConfig  # noqa: E402
from windowxScripts.modCommon import protocol  # noqa: E402


class EasingTest(unittest.TestCase):
    def test_endpoints(self):
        for name in easing.NAMES:
            self.assertAlmostEqual(0.0, easing.ease(name, 0.0), places=9, msg=name)
            self.assertAlmostEqual(1.0, easing.ease(name, 1.0), places=9, msg=name)

    def test_clamped_domain(self):
        for name in easing.NAMES:
            self.assertAlmostEqual(0.0, easing.ease(name, -5.0), places=9)
            self.assertAlmostEqual(1.0, easing.ease(name, 5.0), places=9)

    def test_unknown_falls_back_linear(self):
        self.assertAlmostEqual(easing.ease('nope', 0.37), 0.37, places=9)

    def test_monotonic_outs(self):
        names = ('linear', 'quadout', 'cubicout', 'quartout', 'quintout',
                 'sineout', 'expoout', 'circout')
        for name in names:
            prev = -1.0
            for i in range(21):
                v = easing.ease(name, i / 20.0)
                self.assertGreaterEqual(v + 1e-9, prev, name)
                prev = v

    def test_shape_sanity(self):
        # in/out 族在 0.5 附近的相对关系
        self.assertLess(easing.ease('quad', 0.5), 0.3)
        self.assertGreater(easing.ease('quadout', 0.5), 0.7)
        self.assertGreater(easing.ease('spring', 0.35), 0.9)  # 过冲后回落


class LayoutTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(('abs', 960.0), layout.parse_coord('960'))
        self.assertEqual(('rel', 20.0), layout.parse_coord('r+20'))
        self.assertEqual(('rel', -30.0), layout.parse_coord('r-30'))
        self.assertEqual(('pct', 50.0), layout.parse_coord('p50'))

    def test_resolve(self):
        self.assertAlmostEqual(960.0, layout.resolve_coord('p50', 0, 1920))
        self.assertAlmostEqual(600.0, layout.resolve_coord('r100', 500, 1920))
        self.assertAlmostEqual(1920.0, layout.resolve_coord('p100', 0, 1920))

    def test_resolve_clamped(self):
        self.assertAlmostEqual(0.0, layout.resolve_coord('r-9999', 100, 1920))
        self.assertAlmostEqual(1920.0, layout.resolve_coord('9999', 0, 1920))

    def test_clamp_window_keeps_partial_visible(self):
        cx, cy, w, h = layout.clamp_window(-500, -500, 120, 80, 1920, 1080)
        self.assertGreater(cx, -w)
        self.assertGreater(cy, -h)
        cx2, cy2, _, _ = layout.clamp_window(99999, 99999, 120, 80, 1920, 1080)
        self.assertLess(cx2, 1920 + 120)
        self.assertLess(cy2, 1080 + 80)

    def test_zoom_anchor(self):
        # center 锚点：中心不动
        cx, cy = layout.zoom_keep_anchor(500, 400, 100, 80, 200, 160, 'center')
        self.assertAlmostEqual(500.0, cx)
        self.assertAlmostEqual(400.0, cy)
        # topleft 锚点：左上角不动
        left = 500 - 50
        top = 400 - 40
        cx2, cy2 = layout.zoom_keep_anchor(500, 400, 100, 80, 200, 160, 'topleft')
        self.assertAlmostEqual(left, cx2 - 100)
        self.assertAlmostEqual(top, cy2 - 80)

    def test_ui_offset(self):
        ox, oy = layout.to_ui_offset(modConfig.VIEW_W / 2, modConfig.VIEW_H / 2,
                                    100, 80, modConfig.VIEW_W, modConfig.VIEW_H)
        self.assertAlmostEqual(0.0, ox)
        self.assertAlmostEqual(0.0, oy)


class CameraMathTest(unittest.TestCase):
    def test_wrap(self):
        self.assertAlmostEqual(0.0, camera_math.wrap_deg(360))
        self.assertAlmostEqual(180.0, camera_math.wrap_deg(180))
        # 约定区间为 (-180, 180]，-180 归一到 180
        self.assertAlmostEqual(180.0, camera_math.wrap_deg(-180))
        self.assertAlmostEqual(-90.0, camera_math.wrap_deg(270))

    def test_native_rotation_is_negated(self):
        p, y, r = camera_math.to_native_rotation(30, 45, 5)
        self.assertAlmostEqual(-30.0, p)
        self.assertAlmostEqual(-45.0, y)
        self.assertAlmostEqual(5.0, r)
        # 往返一致
        back = camera_math.from_native_rotation(p, y, r)
        self.assertAlmostEqual(30.0, back[0])
        self.assertAlmostEqual(45.0, back[1])

    def test_forward_vectors(self):
        x, y, z = camera_math.forward_vector(0, 0)
        self.assertAlmostEqual(0.0, x, places=6)
        self.assertAlmostEqual(0.0, y, places=6)
        self.assertAlmostEqual(1.0, z, places=6)
        x2, _, _ = camera_math.forward_vector(0, 90)
        self.assertAlmostEqual(-1.0, x2, places=6)
        _, y3, _ = camera_math.forward_vector(90, 0)
        self.assertAlmostEqual(-1.0, y3, places=6)

    def test_fov_clamp(self):
        self.assertAlmostEqual(30.0, camera_math.clamp_fov(5))
        self.assertAlmostEqual(110.0, camera_math.clamp_fov(500))
        self.assertAlmostEqual(70.0, camera_math.clamp_fov('bad'))
        self.assertAlmostEqual(60.0, camera_math.clamp_fov(60))

    def test_narrow_fov_plan(self):
        fov, dist, mult = camera_math.narrow_fov_plan(20, 70, 8.0)
        self.assertAlmostEqual(30.0, fov)
        self.assertGreater(mult, 1.5)
        self.assertAlmostEqual(8.0 * mult, dist)
        fov2, dist2, mult2 = camera_math.narrow_fov_plan(60, 70, 8.0)
        self.assertAlmostEqual(60.0, fov2)
        self.assertAlmostEqual(1.0, mult2)
        self.assertAlmostEqual(8.0, dist2)


class ProtocolTest(unittest.TestCase):
    def test_patch(self):
        pkt = protocol.make_patch('p1', 3, [{'op': 'stop', 'id': 'all'}])
        ok, err = protocol.validate_patch(pkt)
        self.assertTrue(ok, err)
        self.assertEqual(3, pkt['rev'])

    def test_bad_ops(self):
        pkt = {'v': protocol.PROTO_VERSION, 'owner': 'p1', 'rev': 1,
               'ops': [{'op': 'nuke'}]}
        ok, err = protocol.validate_patch(pkt)
        self.assertFalse(ok)
        self.assertIn('bad op', err)

    def test_truncate(self):
        ops = [{'op': 'stop', 'id': 'a'}] * (protocol.MAX_OPS_PER_PACKET + 5)
        pkt = protocol.make_patch('p1', 1, ops)
        self.assertEqual(protocol.MAX_OPS_PER_PACKET, len(pkt['ops']))
        self.assertTrue(pkt['truncated'])


if __name__ == '__main__':
    unittest.main()
