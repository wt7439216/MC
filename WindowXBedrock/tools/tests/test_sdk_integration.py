# -*- coding: utf-8 -*-
"""SDK Mock 集成测试（服务端）。

注意：这是**本地 Mock**，不代表 MCStudio 实机通过。
覆盖：list(dict) 参数、origin 区分玩家/命令方块、管理员判定、
      return_failed、补丁路由、拒绝不可信客户端写入、FULL 重同步。
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
from windowxScripts.modServer import serverSystem  # noqa: E402


def a(name, value):
    return {'name': name, 'type': 'str', 'value': value}


def raw_cmd(name, args=None, entity='p1', block=(0, 64, 0), variant=0):
    origin = {'dimension': 0, 'blockPos': block}
    if entity:
        origin['entityId'] = entity
    return {'command': name, 'args': args or [], 'variant': variant,
            'origin': origin}


class ServerIntegrationTest(unittest.TestCase):
    def setUp(self):
        sdkmock.reset()
        STATE.players = ['p1', 'root']
        self.sys = serverSystem.WXServerSystem('windowx', modConfig.SERVER_SYSTEM)

    # ---------------- 基本链路 ----------------
    def test_player_create_uses_list_args(self):
        raw = raw_cmd('wxcreate', [a('id', 'w1'), a('w', '200'), a('h', '120'),
                                   a('x', 'p50'), a('y', 'p50')])
        self.sys.OnCustomCommand(raw)
        self.assertIsNotNone(self.sys.store.get('p1', 'w1'))
        self.assertFalse(raw.get('return_failed', False))
        patches = STATE.sent_events(modConfig.EV_PATCH)
        self.assertTrue(any(p[1] == 'p1' for p in patches), patches)

    def test_dict_style_args_tolerated(self):
        raw = raw_cmd('wxcreate', {'id': 'w2'})
        self.sys.OnCustomCommand(raw)
        self.assertIsNotNone(self.sys.store.get('p1', 'w2'))

    def test_duplicate_id_sets_return_failed(self):
        raw1 = raw_cmd('wxcreate', [a('id', 'w1')])
        self.sys.OnCustomCommand(raw1)
        raw2 = raw_cmd('wxcreate', [a('id', 'w1')])
        self.sys.OnCustomCommand(raw2)
        self.assertTrue(raw2.get('return_failed'))
        toasts = STATE.sent_events(modConfig.EV_TOAST)
        self.assertTrue(any('已存在' in str(t[3]) for t in toasts), toasts)

    def test_command_block_origin_writes_scene(self):
        raw = raw_cmd('wxscreate', [a('id', 's1')], entity=None)
        self.sys.OnCustomCommand(raw)
        self.assertIsNotNone(self.sys.store.get(modConfig.SCENE_OWNER, 's1'))
        self.assertTrue(any(p[0] == 'all' for p in STATE.sent_events(modConfig.EV_PATCH)))

    # ---------------- 管理员 ----------------
    def test_admin_detected_by_player_abilities(self):
        STATE.admins = {'root'}
        raw = raw_cmd('wxaquota', [a('player', 'p1'), a('limit', '3')], entity='root')
        self.sys.OnCustomCommand(raw)
        self.assertEqual(3, self.sys.store.quota_of('p1'))
        self.assertFalse(raw.get('return_failed', False))

    def test_non_admin_rejected(self):
        raw = raw_cmd('wxaquota', [a('player', 'p1'), a('limit', '3')], entity='p1')
        self.sys.OnCustomCommand(raw)
        self.assertTrue(raw.get('return_failed'))
        self.assertEqual(modConfig.MAX_WINDOWS_PER_PLAYER, self.sys.store.quota_of('p1'))

    def test_admin_check_fail_closed(self):
        STATE.admins = {'root'}
        STATE.factory_fail = {'CreatePlayer'}
        raw = raw_cmd('wxastop', [a('player', 'all')], entity='root')
        self.sys.OnCustomCommand(raw)
        self.assertTrue(raw.get('return_failed'), '权限查不到时必须拒绝')

    # ---------------- 不可信客户端 ----------------
    def test_client_write_rejected(self):
        self.sys.OnCustomCommand(raw_cmd('wxcreate', [a('id', 'w1')]))
        before = len(STATE.sent)
        self.sys.OnClientCmd({'owner': 'p2', 'id': 'w1', 'cx': 1.0, 'cy': 2.0})
        self.assertEqual(before, len(STATE.sent))
        self.assertAlmostEqual(modConfig.VIEW_W / 2, self.sys.store.get('p1', 'w1')['cx'])

    def test_ack_ignored(self):
        self.sys.OnCustomCommand(raw_cmd('wxcreate', [a('id', 'w1')]))
        before = [s for s in STATE.sent_events(modConfig.EV_FULL)]
        self.sys.OnAck({'owner': 'p1', 'rev': 0})
        after = [s for s in STATE.sent_events(modConfig.EV_FULL)]
        self.assertEqual(len(before), len(after))

    # ---------------- 重同步 ----------------
    def test_player_join_sends_full_bundle(self):
        self.sys.OnPlayerJoin({'id': 'p1'})
        fulls = STATE.sent_events(modConfig.EV_FULL)
        owners = sorted(f[3]['owner'] for f in fulls)
        self.assertEqual(sorted([modConfig.SCENE_OWNER, 'p1']), owners)

    def test_resync_command_sends_full(self):
        raw = raw_cmd('wxresync', entity='p1')
        self.sys.OnCustomCommand(raw)
        fulls = STATE.sent_events(modConfig.EV_FULL)
        self.assertEqual(2, len(fulls))
        self.assertFalse(raw.get('return_failed', False))

    # ---------------- rev / 路由 ----------------
    def test_rev_increments_per_owner(self):
        self.sys.OnCustomCommand(raw_cmd('wxcreate', [a('id', 'w1')]))
        self.sys.OnCustomCommand(raw_cmd('wxmove', [a('id', 'w1'), a('x', 'p30'), a('y', 'p30')]))
        self.sys.OnCustomCommand(raw_cmd('wxmove', [a('id', 'w1'), a('x', 'p40'), a('y', 'p40')]))
        revs = [p[3]['rev'] for p in STATE.sent_events(modConfig.EV_PATCH)
                if p[3]['owner'] == 'p1']
        self.assertEqual([1, 2, 3], revs)

    def test_admin_kill_routes_patch_to_target(self):
        self.sys.OnCustomCommand(raw_cmd('wxcreate', [a('id', 'w1')]))
        STATE.admins = {'root'}
        before = len(STATE.sent_events(modConfig.EV_PATCH))
        raw = raw_cmd('wxakill', [a('player', 'p1')], entity='root')
        self.sys.OnCustomCommand(raw)
        self.assertEqual(0, self.sys.store.count('p1'))
        new = STATE.sent_events(modConfig.EV_PATCH)[before:]
        self.assertTrue(new)
        self.assertTrue(all(p[1] == 'p1' and p[3]['owner'] == 'p1' for p in new), new)

    def test_score_writes_command(self):
        self.sys.OnCustomCommand(raw_cmd('wxcreate', [a('id', 'w1')]))
        self.sys.OnCustomCommand(raw_cmd('wxscore', [a('id', 'w1'), a('objective', 'wxobj')]))
        self.assertTrue(any('scoreboard players set' in c for c in STATE.commands))

    # ---------------- 限流 ----------------
    def test_rate_limit(self):
        ok = [self.sys._rate_ok('p1') for _ in range(modConfig.MAX_COMMANDS_PER_SECOND)]
        self.assertTrue(all(ok))
        self.assertFalse(self.sys._rate_ok('p1'))

    # ---------------- 未知指令 ----------------
    def test_unknown_command_ignored(self):
        raw = raw_cmd('tp', [a('x', '1')])
        self.sys.OnCustomCommand(raw)
        self.assertEqual([], STATE.sent)
        self.assertFalse(raw.get('return_failed', False))


if __name__ == '__main__':
    unittest.main()
