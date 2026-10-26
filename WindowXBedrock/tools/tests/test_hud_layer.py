# -*- coding: utf-8 -*-
"""HUD 对象层级与拖拽（SDK Mock）。

验证：GetBaseUIControl + asXxx 控件调用；关键 API 缺失/类型不符会记录错误；
      AddTouchEventParams + SetButtonTouch*Callback 绑定；槽位按 UI 实际数量探测。
"""
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
from windowxScripts.modClient import clientSystem  # noqa: E402
from windowxScripts.modClient import hudBackend  # noqa: E402
from windowxScripts.modClient import hudScreen  # noqa: E402


def make_win(wid='w1', title='T'):
    return {'id': wid, 'owner': 'p1', 'title': title, 'cx': 960.0, 'cy': 540.0,
            'w': 200.0, 'h': 120.0, 'color': 'black', 'layer': 'normal',
            'visible': True, 'content': {'kind': 'texture',
                                         'path': 'textures/ui/windowx/bg',
                                         'mode': 'fit'}, 'rev': 1}


class HudBackendTest(unittest.TestCase):
    def setUp(self):
        sdkmock.reset()
        STATE.ui_slots = 3
        self.node = sdkmock.FakeScreenNode('windowx', 'windowx_hud', {})

    def test_bind_resolves_all_slots(self):
        backend = hudBackend.HudBackend(3)
        self.assertTrue(backend.bind(self.node))
        self.assertEqual(3, len(backend.controls))
        self.assertEqual([], backend.errors)

    def test_sync_uses_control_methods(self):
        backend = hudBackend.HudBackend(3)
        backend.bind(self.node)
        backend.sync([('p1', 'w1', make_win(), 0.0, 0.0, 1.0)])
        names = [c[0] for c in STATE.calls]
        for expect in ('SetFullPosition', 'SetFullSize', 'SetText',
                       'SetSprite', 'SetAlpha', 'SetLayer', 'SetTouchEnable'):
            self.assertIn(expect, names, expect)
        self.assertTrue(any(c[0] == 'SetText' and c[2] == 'T' for c in STATE.calls))

    def test_release_hides_root(self):
        backend = hudBackend.HudBackend(3)
        backend.bind(self.node)
        backend.sync([('p1', 'w1', make_win(), 0, 0, 1.0)])
        backend.release(('p1', 'w1'))
        self.assertFalse(any(c[1] == '/win0' and c[0] == 'SetVisible' and c[2] is True
                             for c in STATE.calls[-3:]))

    def test_missing_part_is_reported(self):
        STATE.ui_missing = {'/win1/bg'}
        backend = hudBackend.HudBackend(3)
        self.assertTrue(backend.bind(self.node))
        self.assertEqual(2, len(backend.controls))
        self.assertTrue(any('bg' in str(e) for e in backend.errors))

    def test_type_mismatch_is_reported(self):
        STATE.ui_mismatch = {'/win0/bg'}
        backend = hudBackend.HudBackend(3)
        backend.bind(self.node)
        self.assertNotIn(0, backend.controls)
        self.assertTrue(any('asImage' in str(e) for e in backend.errors))

    def test_no_get_base_ui_control_is_critical(self):
        backend = hudBackend.HudBackend(3)
        self.assertFalse(backend.bind(object()))
        self.assertFalse(backend.critical_ok)
        self.assertFalse(backend.available)

    def test_slots_less_than_config(self):
        STATE.ui_slots = 2
        backend = hudBackend.HudBackend(5)
        backend.bind(self.node)
        self.assertEqual(2, len(backend.controls))
        self.assertTrue(any('resolved 2/5' in str(e) for e in backend.errors))


class FakeDragSystem(object):
    def __init__(self):
        self.drag_calls = []
        self.updated = 0
        self.attached = None

    def attach_hud(self, node):
        self.attached = node

    def on_drag(self, slot, state, touch):
        self.drag_calls.append((slot, state, touch))

    def on_hud_update(self):
        self.updated += 1


class HudScreenTest(unittest.TestCase):
    def setUp(self):
        sdkmock.reset()
        STATE.ui_slots = 3
        self.fake_sys = FakeDragSystem()
        sys.modules['mod.client.extraClientApi'].GetSystem = (
            lambda *a: self.fake_sys)
        self.node = hudScreen.WXHudScreen('windowx', 'windowx_hud', {})

    def test_detect_slots_matches_ui(self):
        self.node.Create()
        self.assertEqual(3, self.node.slots)
        self.assertEqual(3, self.node.touch_ready)

    def test_touch_callbacks_registered(self):
        self.node.Create()
        binds = STATE.ui_touch.get('/win0/bar_drag') or {}
        self.assertEqual(set(['down', 'move', 'up', 'cancel']), set(binds.keys()))
        self.assertTrue(any(c[0] == 'AddTouchEventParams' for c in STATE.calls))

    def test_touch_callback_forwards_to_system(self):
        self.node.Create()
        cb = STATE.ui_touch['/win0/bar_drag']['down']
        cb({'ButtonState': 'down', 'TouchPos': (10, 20)})
        self.assertEqual((0, 'down', (10, 20)), self.fake_sys.drag_calls[-1])

    def test_missing_bar_skips_slot(self):
        STATE.ui_missing = {'/win2/bar_drag'}
        self.node.Create()
        self.assertEqual(2, self.node.touch_ready)
        self.assertTrue(self.node.errors)

    def test_update_calls_system(self):
        self.node.Create()
        self.node.Update()
        self.assertEqual(1, self.fake_sys.updated)


class ClientCompositeKeyTest(unittest.TestCase):
    def setUp(self):
        sdkmock.reset()
        STATE.ui_slots = 3
        self.cs = clientSystem.WXClientSystem('windowx', modConfig.CLIENT_SYSTEM)
        self.node = sdkmock.FakeScreenNode('windowx', 'windowx_hud', {})
        self.node.slots = 3
        self.cs.attach_hud(self.node)

    def _patch(self, owner, rev, ops):
        self.cs.OnPatch({'v': 1, 'owner': owner, 'rev': rev, 'ops': ops})

    def test_same_id_different_owner(self):
        self._patch('p1', 1, [{'op': 'create', 'win': make_win('w1')}])
        self._patch('world', 1, [{'op': 'create', 'win': make_win('w1')}])
        self.assertEqual(2, len(self.cs.windows))
        self.assertIn(('p1', 'w1'), self.cs.windows)
        self.assertIn(('world', 'w1'), self.cs.windows)

    def test_stale_patch_dropped(self):
        self._patch('p1', 1, [{'op': 'create', 'win': make_win('w1')}])
        self._patch('p1', 1, [{'op': 'set', 'id': 'w1', 'fields': {'title': 'X'}}])
        self.assertEqual('T', self.cs.windows[('p1', 'w1')]['title'])

    def test_rev_gap_marks_desync(self):
        self._patch('p1', 1, [{'op': 'create', 'win': make_win('w1')}])
        self._patch('p1', 3, [{'op': 'set', 'id': 'w1', 'fields': {'title': 'Y'}}])
        self.assertTrue(self.cs.desync.get('p1'))

    def test_full_replaces_owner_only(self):
        self._patch('world', 1, [{'op': 'create', 'win': make_win('w1')}])
        self.cs.OnFull({'v': 1, 'owner': 'p1', 'rev': 2,
                        'windows': [make_win('w1'), make_win('w2')]})
        self.assertIn(('world', 'w1'), self.cs.windows)
        self.assertEqual(2, len([k for k in self.cs.windows if k[0] == 'p1']))


if __name__ == '__main__':
    unittest.main()
