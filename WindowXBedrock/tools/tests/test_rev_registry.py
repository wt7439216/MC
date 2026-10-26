# -*- coding: utf-8 -*-
"""rev 存储与 (owner,id) 复合键注册表。"""
from __future__ import division

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PROJECT = os.path.dirname(TOOLS)
sys.path.insert(0, os.path.join(PROJECT, 'behavior_packs', 'windowxBehavior'))

from windowxScripts.modCommon import dispatch_core as dc  # noqa: E402
from windowxScripts.modCommon import modConfig  # noqa: E402
from windowxScripts.modCommon import permissions  # noqa: E402
from windowxScripts.modCommon import registry_core  # noqa: E402
from windowxScripts.modCommon import rev_store  # noqa: E402
from windowxScripts.modCommon import window_def  # noqa: E402


class RevStoreTest(unittest.TestCase):
    def test_monotonic(self):
        store = rev_store.RevStore()
        self.assertEqual(0, store.current('p1'))
        self.assertEqual(1, store.next('p1'))
        self.assertEqual(2, store.next('p1'))
        self.assertEqual(0, store.current('p2'))
        self.assertEqual(1, store.next('p2'))

    def test_needs_full(self):
        store = rev_store.RevStore()
        store.next('p1')
        store.next('p1')
        self.assertFalse(store.needs_full('p1', 2))
        self.assertTrue(store.needs_full('p1', 1))

    def test_reset(self):
        store = rev_store.RevStore()
        store.next('p1')
        store.reset('p1')
        self.assertEqual(0, store.current('p1'))


class CompositeKeyTest(unittest.TestCase):
    def setUp(self):
        self.store = registry_core.Store()

    def _win(self, wid, owner):
        return window_def.new_window(wid, owner, 100, 60, 500, 400)

    def test_same_id_different_owner(self):
        ok1, _ = self.store.add(self._win('w1', 'p1'))
        ok2, _ = self.store.add(self._win('w1', 'p2'))
        self.assertTrue(ok1 and ok2)
        self.assertIsNotNone(self.store.get('p1', 'w1'))
        self.assertIsNotNone(self.store.get('p2', 'w1'))
        self.assertEqual(1, self.store.count('p1'))

    def test_duplicate_within_owner(self):
        self.store.add(self._win('w1', 'p1'))
        ok, msg = self.store.add(self._win('w1', 'p1'))
        self.assertFalse(ok)
        self.assertIn('已存在', msg)

    def test_scene_quota_separate(self):
        for i in range(modConfig.MAX_WINDOWS_PER_SCENE):
            ok, _ = self.store.add(self._win('s%d' % i, modConfig.SCENE_OWNER))
            self.assertTrue(ok, i)
        ok, msg = self.store.add(self._win('overflow', modConfig.SCENE_OWNER))
        self.assertFalse(ok)
        self.assertIn('配额', msg)
        # 玩家配额不受影响
        ok2, _ = self.store.add(self._win('w1', 'p1'))
        self.assertTrue(ok2)

    def test_admin_ops_carry_owner(self):
        self.store.add(self._win('w1', 'p1'))
        self.store.add(self._win('w2', 'p2'))
        admin = permissions.make_actor_player('root', is_admin=True)
        r = dc.handle(self.store, 'wxa', 'kill', {'player': 'p1'}, admin)
        self.assertTrue(r['ok'])
        owners = [op.get('owner') for op in r['ops']]
        self.assertEqual(['p1'], sorted(owners))

    def test_admin_stop_all_tags_each_owner(self):
        self.store.add(self._win('w1', 'p1'))
        self.store.add(self._win('s1', modConfig.SCENE_OWNER))
        admin = permissions.make_actor_player('root', is_admin=True)
        r = dc.handle(self.store, 'wxa', 'stop', {'player': 'all'}, admin)
        self.assertTrue(r['ok'])
        owners = sorted(op.get('owner') for op in r['ops'])
        self.assertEqual(sorted(['p1', modConfig.SCENE_OWNER]), owners)


if __name__ == '__main__':
    unittest.main()
