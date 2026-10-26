# -*- coding: utf-8 -*-
from __future__ import division

import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
PROJECT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import gen_commands as gc  # noqa: E402


class CommandSchemaTest(unittest.TestCase):
    def test_schema_valid(self):
        self.assertEqual([], gc.validate())

    def test_counts(self):
        self.assertEqual(28, len(gc.SCHEMA))
        fam = {}
        for c in gc.SCHEMA:
            fam[c['family']] = fam.get(c['family'], 0) + 1
        self.assertEqual(17, fam['wx'])
        self.assertEqual(7, fam['wxs'])
        self.assertEqual(4, fam['wxa'])

    def test_permission_mapping(self):
        expect = {'wx': 'any', 'wxs': 'game_directors', 'wxa': 'admin'}
        for c in gc.SCHEMA:
            self.assertEqual(expect[c['family']], gc.build_json(c)['permission_level'])

    def test_no_variants(self):
        for c in gc.SCHEMA:
            pkt = gc.build_json(c)
            self.assertEqual(['format_version', 'name', 'description',
                              'permission_level', 'args'], list(pkt.keys()))
            self.assertNotIn('args1', pkt)

    def test_defaults_at_tail(self):
        for c in gc.SCHEMA:
            seen = False
            for a in c['args']:
                if a['default'] is not None:
                    seen = True
                else:
                    self.assertFalse(seen, '%s.%s' % (c['name'], a['name']))

    def test_generated_files_match_schema(self):
        out_dir = os.path.join(PROJECT, 'behavior_packs', 'windowxBehavior',
                               'netease_commands')
        self.assertTrue(os.path.isdir(out_dir), 'run gen_commands.py first')
        files = [f for f in os.listdir(out_dir) if f.endswith('.json')]
        self.assertEqual(28, len(files))
        for c in gc.SCHEMA:
            path = os.path.join(out_dir, gc.file_name(c))
            self.assertTrue(os.path.exists(path), path)
            data = json.loads(io.open(path, encoding='utf-8').read())
            self.assertEqual(c['name'], data['name'])
            self.assertEqual(len(c['args']), len(data['args']))

    def test_file_name_rule(self):
        for c in gc.SCHEMA:
            fn = gc.file_name(c)
            self.assertTrue(fn.startswith('wxb_'), fn)
            self.assertTrue(fn.endswith('.json'), fn)
            self.assertNotIn('-', fn)


if __name__ == '__main__':
    unittest.main()
