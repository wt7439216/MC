# -*- coding: utf-8 -*-
"""CustomCommandTriggerServerEvent 真实形态解析（官方字段）。"""
from __future__ import division

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PROJECT = os.path.dirname(TOOLS)
sys.path.insert(0, os.path.join(PROJECT, 'behavior_packs', 'windowxBehavior'))

from windowxScripts.modCommon import command_event as ce  # noqa: E402
from windowxScripts.modCommon import modConfig  # noqa: E402


class NormalizeArgsTest(unittest.TestCase):
    def test_list_of_dict(self):
        raw = [{'name': 'id', 'type': 'str', 'value': 'w1'},
               {'name': 'w', 'type': 'float', 'value': 120.0}]
        self.assertEqual({'id': 'w1', 'w': 120.0}, ce.normalize_args(raw))

    def test_dict_tolerated(self):
        self.assertEqual({'id': 'w1'}, ce.normalize_args({'id': 'w1'}))

    def test_none_and_garbage(self):
        self.assertEqual({}, ce.normalize_args(None))
        self.assertEqual({}, ce.normalize_args('nope'))
        self.assertEqual({}, ce.normalize_args([1, 2, {'type': 'str'}]))

    def test_duplicate_last_wins(self):
        raw = [{'name': 'id', 'value': 'a'}, {'name': 'id', 'value': 'b'}]
        self.assertEqual('b', ce.normalize_args(raw)['id'])


class OriginTest(unittest.TestCase):
    def test_player_origin(self):
        origin = ce.normalize_origin({'entityId': 'p1', 'dimension': 0,
                                      'blockPos': (1, 64, 2)})
        self.assertFalse(origin['is_command_block'])
        actor = ce.actor_from_origin(origin, is_admin=False)
        self.assertEqual('player', actor['kind'])
        self.assertEqual('p1', actor['id'])

    def test_admin_origin(self):
        origin = ce.normalize_origin({'entityId': 'root', 'dimension': 0})
        actor = ce.actor_from_origin(origin, is_admin=True)
        self.assertEqual('admin', actor['kind'])

    def test_command_block_origin_has_no_entity(self):
        origin = ce.normalize_origin({'dimension': 0, 'blockPos': (5, 70, 5)})
        self.assertTrue(origin['is_command_block'])
        actor = ce.actor_from_origin(origin, is_admin=False)
        self.assertEqual('command_block', actor['kind'])
        self.assertEqual(modConfig.SCENE_OWNER, actor['id'])

    def test_non_dict_origin(self):
        origin = ce.normalize_origin(None)
        self.assertTrue(origin['is_command_block'])


class ParseEventTest(unittest.TestCase):
    def test_full_event(self):
        raw = {
            'command': 'wxmove',
            'args': [{'name': 'id', 'type': 'str', 'value': 'w1'},
                     {'name': 'x', 'type': 'str', 'value': 'p50'}],
            'variant': 0,
            'origin': {'entityId': 'p1', 'dimension': 0, 'blockPos': (0, 64, 0)},
        }
        ev = ce.parse_event(raw)
        self.assertEqual('wxmove', ev['command'])
        self.assertEqual({'id': 'w1', 'x': 'p50'}, ev['args'])
        self.assertFalse(ev['origin']['is_command_block'])

    def test_bad_variant_falls_back_zero(self):
        ev = ce.parse_event({'command': 'wxstop', 'args': [], 'variant': 'x'})
        self.assertEqual(0, ev['variant'])

    def test_split_command(self):
        self.assertEqual(('wx', 'move'), ce.split_command('wxmove'))
        self.assertEqual(('wxs', 'create'), ce.split_command('wxscreate'))
        self.assertEqual(('wxa', 'stop'), ce.split_command('wxastop'))
        self.assertEqual((None, None), ce.split_command('tp'))
        self.assertEqual((None, None), ce.split_command(''))

    def test_prefix_collision_regression(self):
        """wxscore/wxshake/wxsize/wxstop 以 wxs 开头，必须仍归玩家族。"""
        for name in ('wxscore', 'wxshake', 'wxsize', 'wxstop'):
            self.assertEqual(('wx', name[2:]), ce.split_command(name), name)
        self.assertEqual(('wxs', 'show'), ce.split_command('wxsshow'))


class DescribeEventTest(unittest.TestCase):
    def test_masks_identity_and_hides_position(self):
        ev = ce.parse_event({
            'command': 'wxmove',
            'args': [{'name': 'id', 'type': 'str', 'value': 'w1'},
                     {'name': 'x', 'type': 'str', 'value': 'p50'}],
            'variant': 2,
            'origin': {'entityId': 'player-abcdef', 'dimension': 0,
                       'blockPos': (123, 64, 456)},
        })
        text = ce.describe_event(ev)
        self.assertIn('command=wxmove', text)
        self.assertIn('variant=2', text)
        self.assertIn('has_entity=True', text)
        self.assertIn('pla***', text)
        self.assertNotIn('player-abcdef', text)
        self.assertNotIn('123', text)
        self.assertNotIn('456', text)

    def test_types_only_by_default(self):
        ev = ce.parse_event({'command': 'wxcreate',
                             'args': [{'name': 'id', 'value': 'secret-id'}]})
        text = ce.describe_event(ev)
        self.assertIn('id:str', text)
        self.assertNotIn('secret-id', text)


class WriteBackTest(unittest.TestCase):
    def test_failure_flag(self):
        raw = {}
        ce.write_back_failure(raw, 'bad')
        self.assertTrue(raw['return_failed'])

    def test_no_lang_key_by_default(self):
        raw = {}
        ce.write_back_failure(raw, 'bad')
        self.assertNotIn('return_msg_key', raw,
                         'return_msg_key 默认关闭，避免 lang 键缺失误导玩家')


if __name__ == '__main__':
    unittest.main()
