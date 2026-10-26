# -*- coding: utf-8 -*-
"""权限三族矩阵 + 指令分发端到端（纯逻辑）。"""
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


class PermissionMatrixTest(unittest.TestCase):
    def test_can_run(self):
        player = permissions.make_actor_player('p1')
        admin = permissions.make_actor_player('root', is_admin=True)
        block = permissions.make_actor_command_block()

        table = {
            ('wx', 'player'): True, ('wx', 'admin'): True, ('wx', 'cb'): False,
            ('wxs', 'player'): False, ('wxs', 'admin'): True, ('wxs', 'cb'): True,
            ('wxa', 'player'): False, ('wxa', 'admin'): True, ('wxa', 'cb'): False,
        }
        actors = {'player': player, 'admin': admin, 'cb': block}
        for (fam, who), expect in table.items():
            self.assertEqual(expect, permissions.can_run(fam, actors[who]),
                             '%s / %s' % (fam, who))

    def test_can_touch(self):
        player = permissions.make_actor_player('p1')
        other = permissions.make_actor_player('p2')
        admin = permissions.make_actor_player('root', is_admin=True)
        block = permissions.make_actor_command_block()

        self.assertTrue(permissions.can_touch('wx', 'p1', player))
        self.assertFalse(permissions.can_touch('wx', 'p1', other))
        # 管理员用 wx 族时也只能操作自己名下窗口；跨玩家请走 wxa 族
        self.assertFalse(permissions.can_touch('wx', 'p1', admin))
        self.assertTrue(permissions.can_touch('wx', 'root', admin))
        self.assertTrue(permissions.can_touch('wxs', modConfig.SCENE_OWNER, block))
        self.assertFalse(permissions.can_touch('wxs', 'p1', block))
        self.assertTrue(permissions.can_touch('wxa', 'p1', admin))

    def test_scope_owner(self):
        player = permissions.make_actor_player('p1')
        block = permissions.make_actor_command_block()
        self.assertEqual('p1', permissions.scope_owner('wx', player))
        self.assertEqual(modConfig.SCENE_OWNER, permissions.scope_owner('wxs', block))


class DispatchTest(unittest.TestCase):
    def setUp(self):
        self.store = registry_core.Store()
        self.p1 = permissions.make_actor_player('p1')
        self.p2 = permissions.make_actor_player('p2')
        self.admin = permissions.make_actor_player('root', is_admin=True)
        self.block = permissions.make_actor_command_block()

    def _create(self, wid='w1', actor=None, family='wx'):
        actor = actor or self.p1
        return dc.handle(self.store, family, 'create',
                         {'id': wid, 'w': '200', 'h': '120',
                          'x': 'p50', 'y': 'p50', 'title': 'T'}, actor)

    def test_create_and_get(self):
        r = self._create()
        self.assertTrue(r['ok'], r['msg'])
        self.assertEqual(1, len(r['ops']))
        self.assertEqual('create', r['ops'][0]['op'])
        win = self.store.get('p1', 'w1')
        self.assertIsNotNone(win)
        self.assertAlmostEqual(modConfig.VIEW_W / 2, win['cx'])
        self.assertAlmostEqual(modConfig.VIEW_H / 2, win['cy'])

    def test_duplicate_id(self):
        self.assertTrue(self._create()['ok'])
        self.assertFalse(self._create()['ok'])

    def test_invalid_id(self):
        self.assertFalse(self._create('Bad-ID')['ok'])
        self.assertFalse(self._create('')['ok'])

    def test_quota(self):
        for i in range(modConfig.MAX_WINDOWS_PER_PLAYER):
            self.assertTrue(self._create('w%d' % i)['ok'], i)
        over = self._create('overflow')
        self.assertFalse(over['ok'])
        self.assertIn('配额', over['msg'])

    def test_move_updates_state_and_emits_anim(self):
        self._create()
        r = dc.handle(self.store, 'wx', 'move',
                      {'id': 'w1', 'x': 'p25', 'y': 'p75', 'speed': '2', 'ease': 'quadout'},
                      self.p1)
        self.assertTrue(r['ok'], r['msg'])
        task = r['ops'][0]['task']
        self.assertEqual('move', task['kind'])
        self.assertGreater(task['dur'], 0.0)
        win = self.store.get('p1', 'w1')
        self.assertAlmostEqual(modConfig.VIEW_W * 0.25, win['cx'])
        self.assertAlmostEqual(modConfig.VIEW_H * 0.75, win['cy'])

    def test_relative_move(self):
        self._create()
        win = self.store.get('p1', 'w1')
        before = win['cx']
        r = dc.handle(self.store, 'wx', 'move',
                      {'id': 'w1', 'x': 'r+100', 'y': 'r+0'}, self.p1)
        self.assertTrue(r['ok'], r['msg'])
        self.assertAlmostEqual(before + 100, self.store.get('p1', 'w1')['cx'])

    def test_ownership_denied(self):
        self._create()
        r = dc.handle(self.store, 'wx', 'move',
                      {'id': 'w1', 'x': '100', 'y': '100'}, self.p2)
        self.assertFalse(r['ok'])

    def test_size_axis(self):
        self._create()
        r = dc.handle(self.store, 'wx', 'size',
                      {'id': 'w1', 'axis': 'w', 'value': '300'}, self.p1)
        self.assertTrue(r['ok'], r['msg'])
        self.assertAlmostEqual(300.0, self.store.get('p1', 'w1')['w'])
        bad = dc.handle(self.store, 'wx', 'size',
                        {'id': 'w1', 'axis': 'z', 'value': '300'}, self.p1)
        self.assertFalse(bad['ok'])

    def test_zoom_anchor_center(self):
        self._create()
        win = self.store.get('p1', 'w1')
        cx0, cy0 = win['cx'], win['cy']
        r = dc.handle(self.store, 'wx', 'zoom',
                      {'id': 'w1', 'w': '400', 'h': '300', 'anchor': 'center'}, self.p1)
        self.assertTrue(r['ok'], r['msg'])
        win = self.store.get('p1', 'w1')
        self.assertAlmostEqual(cx0, win['cx'])
        self.assertAlmostEqual(cy0, win['cy'])

    def test_fx_ops(self):
        self._create()
        for kind, args in (('shake', {'intensity': '12', 'duration': '0.5'}),
                           ('encircle', {'rx': '80', 'ry': '40', 'speed': '1.5'}),
                           ('wobble', {'ix': '5', 'iy': '5', 'speed': '1', 'cycles': '2'}),
                           ('breath', {'intensity': '0.1', 'speed': '0.5', 'cycles': '2'})):
            args['id'] = 'w1'
            r = dc.handle(self.store, 'wx', kind, args, self.p1)
            self.assertTrue(r['ok'], r['msg'])
            self.assertEqual('fx', r['ops'][0]['op'])
            self.assertEqual(kind, r['ops'][0]['task']['fx'])

    def test_content_validation(self):
        self._create()
        ok = dc.handle(self.store, 'wx', 'content',
                       {'id': 'w1', 'kind': 'texture',
                        'path': 'textures/ui/windowx/bg', 'mode': 'fit'}, self.p1)
        self.assertTrue(ok['ok'], ok['msg'])
        self.assertEqual('texture', self.store.get('p1', 'w1')['content']['kind'])
        bad = dc.handle(self.store, 'wx', 'content',
                        {'id': 'w1', 'kind': 'web', 'path': 'x'}, self.p1)
        self.assertFalse(bad['ok'])

    def test_layer_and_title(self):
        self._create()
        self.assertTrue(dc.handle(self.store, 'wx', 'layer',
                                  {'id': 'w1', 'layer': 'top'}, self.p1)['ok'])
        self.assertEqual('top', self.store.get('p1', 'w1')['layer'])
        self.assertFalse(dc.handle(self.store, 'wx', 'layer',
                                   {'id': 'w1', 'layer': 'ghost'}, self.p1)['ok'])
        self.assertTrue(dc.handle(self.store, 'wx', 'title',
                                  {'id': 'w1', 'action': 'set', 'text': 'Hi'}, self.p1)['ok'])
        self.assertEqual('Hi', self.store.get('p1', 'w1')['title'])
        self.assertTrue(dc.handle(self.store, 'wx', 'title',
                                  {'id': 'w1', 'action': 'reset'}, self.p1)['ok'])
        self.assertEqual('', self.store.get('p1', 'w1')['title'])

    def test_stop_and_remove_all(self):
        self._create('w1')
        self._create('w2')
        r = dc.handle(self.store, 'wx', 'stop', {'id': 'all'}, self.p1)
        self.assertTrue(r['ok'])
        r = dc.handle(self.store, 'wx', 'remove', {'id': 'all'}, self.p1)
        self.assertTrue(r['ok'])
        self.assertEqual(2, r['data']['count'])
        self.assertEqual(0, self.store.count('p1'))

    def test_get_and_score(self):
        self._create()
        r = dc.handle(self.store, 'wx', 'get', {'id': 'w1', 'prop': 'x'}, self.p1)
        self.assertTrue(r['ok'])
        self.assertAlmostEqual(modConfig.VIEW_W / 2, r['data']['value'])
        r = dc.handle(self.store, 'wx', 'score',
                      {'id': 'w1', 'objective': 'wxobj'}, self.p1)
        self.assertTrue(r['ok'])
        self.assertEqual('wxobj', r['data']['objective'])

    def test_scene_family(self):
        r = self._create('scene1', actor=self.block, family='wxs')
        self.assertTrue(r['ok'], r['msg'])
        self.assertIsNotNone(self.store.get(modConfig.SCENE_OWNER, 'scene1'))
        # 普通玩家不能操作场景窗口
        r2 = dc.handle(self.store, 'wxs', 'move',
                       {'id': 'scene1', 'x': '100', 'y': '100'}, self.p1)
        self.assertFalse(r2['ok'])
        # 命令方块可以
        r3 = dc.handle(self.store, 'wxs', 'move',
                       {'id': 'scene1', 'x': '100', 'y': '100'}, self.block)
        self.assertTrue(r3['ok'], r3['msg'])

    def test_scene_anim(self):
        self._create('scene1', actor=self.block, family='wxs')
        r = dc.handle(self.store, 'wxs', 'anim',
                      {'id': 'scene1', 'kind': 'shake', 'a': '10', 'b': '1', 'c': '0.5'},
                      self.block)
        self.assertTrue(r['ok'], r['msg'])
        self.assertEqual('shake', r['ops'][0]['task']['fx'])

    def test_admin(self):
        self._create('w1')
        self._create('w2')
        r = dc.handle(self.store, 'wxa', 'list', {'player': 'all'}, self.admin)
        self.assertTrue(r['ok'])
        self.assertEqual(2, r['data']['owners'][0]['count'])
        r = dc.handle(self.store, 'wxa', 'kill', {'player': 'p1'}, self.admin)
        self.assertTrue(r['ok'])
        self.assertEqual(0, self.store.count('p1'))
        r = dc.handle(self.store, 'wxa', 'quota', {'player': 'p1', 'limit': '3'}, self.admin)
        self.assertTrue(r['ok'])
        self.assertEqual(3, self.store.quota_of('p1'))
        # 玩家不能用管理族
        self.assertFalse(dc.handle(self.store, 'wxa', 'kill',
                                   {'player': 'p1'}, self.p1)['ok'])

    def test_unknown_action(self):
        r = dc.handle(self.store, 'wx', 'nuke', {}, self.p1)
        self.assertFalse(r['ok'])
        self.assertIn('未知动作', r['msg'])


if __name__ == '__main__':
    unittest.main()
