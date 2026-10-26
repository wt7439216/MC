# -*- coding: utf-8 -*-
"""WindowX Bedrock - netease_commands generator (single source of truth).

设计约束（v2.1）:
  * 一动作一命令，全部只用 ``args``，不启用 ``args1..args9`` 变体 -> 零歧义。
  * 三权限族: wx*(any) / wxs*(game_directors, 命令方块可用) / wxa*(admin)。
  * 带 default 的参数必须排在参数列表尾部（网易规范）。
  * enum 参数的“候选值写法”尚未在 SDK 实测，统一先用 ``str`` + description 提示，
    待 POC 通过后再切到 ``enum``（改 SCHEMA 的 type 即可，生成器自动跟随）。

用法:
    python gen_commands.py            # 生成到 behavior_packs/windowxBehavior/netease_commands
    python gen_commands.py --check    # 只校验 schema 不写盘
"""
from __future__ import print_function

import argparse
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT_DIR = os.path.join(PROJECT, 'behavior_packs', 'windowxBehavior', 'netease_commands')

ALLOWED_TYPES = set(['float', 'int', 'bool', 'str', 'target', 'pos', 'entity', 'item'])
PERMISSIONS = set(['game_directors', 'admin', 'host', 'owner', 'any'])

EASES = ('linear,quad,quadout,quadinout,cubic,cubicout,cubicinout,quart,quartout,quartinout,'
         'quint,quintout,quintinout,sine,sineout,sineinout,expo,expoout,expoinout,circ,circout,'
         'circinout,bounce,bounceout,bounceinout,elastic,elasticout,elasticinout,back,backout,'
         'backinout,spring,wave,jump,delay,rush,slowmo,faststart,stutter,glitch,packetloss,'
         'freeze,overshoot,snap,jitter,step3,step5,step8')

ANCHORS = 'center,topleft,topright,bottomleft,bottomright,left,right,top,bottom'
LAYERS = 'normal,top,solid,clickthrough'


def arg(name, typ, default=None, hint=None, desc=''):
    return {'name': name, 'type': typ, 'default': default, 'hint': hint, 'desc': desc}


# ---------------------------------------------------------------------------
# 单一数据源：28 条命令
# ---------------------------------------------------------------------------
SCHEMA = [
    # ---------------- 玩家自用族 any ----------------
    dict(name='wxcreate', family='wx', desc='创建一个属于自己的伪窗口',
         args=[arg('id', 'str', desc='窗口 id（英文/数字/下划线）'),
               arg('w', 'float', 120.0, desc='像素宽'),
               arg('h', 'float', 80.0, desc='像素高'),
               arg('x', 'str', 'p50', desc='中心 X，支持 960 / r+20 / p50'),
               arg('y', 'str', 'p50', desc='中心 Y，支持 540 / r-20 / p50'),
               arg('title', 'str', 'Window', desc='标题栏文字')]),
    dict(name='wxremove', family='wx', desc='删除窗口（all=删除自己的全部）',
         args=[arg('id', 'str', desc='窗口 id 或 all')]),
    dict(name='wxmove', family='wx', desc='平滑移动窗口',
         args=[arg('id', 'str'),
               arg('x', 'str', desc='目标 X，绝对/r相对/p百分比'),
               arg('y', 'str', desc='目标 Y，绝对/r相对/p百分比'),
               arg('speed', 'float', 1.0, desc='速度倍率'),
               arg('ease', 'str', 'linear', hint=EASES, desc='缓动曲线')]),
    dict(name='wxsize', family='wx', desc='改变窗口单轴尺寸',
         args=[arg('id', 'str'),
               arg('axis', 'str', hint='w,h', desc='轴'),
               arg('value', 'str', desc='目标尺寸，绝对/r相对/p百分比'),
               arg('speed', 'float', 1.0),
               arg('ease', 'str', 'linear', hint=EASES)]),
    dict(name='wxzoom', family='wx', desc='双轴缩放窗口并可指定锚点',
         args=[arg('id', 'str'),
               arg('w', 'float', desc='目标宽'),
               arg('h', 'float', desc='目标高'),
               arg('speed', 'float', 1.0),
               arg('ease', 'str', 'linear', hint=EASES),
               arg('anchor', 'str', 'center', hint=ANCHORS)]),
    dict(name='wxshake', family='wx', desc='抖动',
         args=[arg('id', 'str'),
               arg('intensity', 'float', 8.0, desc='像素幅度'),
               arg('duration', 'float', 0.6, desc='秒')]),
    dict(name='wxencircle', family='wx', desc='绕中心公转',
         args=[arg('id', 'str'),
               arg('rx', 'float', 60.0),
               arg('ry', 'float', 40.0),
               arg('speed', 'float', 1.0),
               arg('deg', 'float', 360.0, desc='总角度'),
               arg('ease', 'str', 'linear', hint=EASES)]),
    dict(name='wxwobble', family='wx', desc='摇摆（正弦位移）',
         args=[arg('id', 'str'),
               arg('ix', 'float', 6.0),
               arg('iy', 'float', 6.0),
               arg('speed', 'float', 1.0),
               arg('cycles', 'int', 3)]),
    dict(name='wxbreath', family='wx', desc='呼吸式缩放',
         args=[arg('id', 'str'),
               arg('intensity', 'float', 0.06),
               arg('speed', 'float', 0.5),
               arg('cycles', 'int', 3)]),
    dict(name='wxphysics', family='wx', desc='启动物理（重力/摩擦/弹性/初速度/推力）',
         args=[arg('id', 'str'),
               arg('gravity', 'float', 1200.0),
               arg('friction', 'float', 0.12),
               arg('elasticity', 'float', 0.45),
               arg('sx', 'str', 'p50', desc='起始 X'),
               arg('sy', 'str', 'p20', desc='起始 Y'),
               arg('fx', 'float', 0.0, desc='持续推力 X'),
               arg('fy', 'float', 0.0, desc='持续推力 Y'),
               arg('fs', 'float', 0.0, desc='推力强度')]),
    dict(name='wxfollow', family='wx', desc='跟随实体或坐标',
         args=[arg('id', 'str'),
               arg('target', 'str', desc='实体 id 或 x,y,z'),
               arg('distance', 'float', 4.0),
               arg('scale', 'float', 0.0, desc='按距离缩放强度，0=不缩放')]),
    dict(name='wxcontent', family='wx', desc='设置窗口内容',
         args=[arg('id', 'str'),
               arg('kind', 'str', hint='texture,frames,text'),
               arg('path', 'str', desc='贴图/序列帧/文本'),
               arg('mode', 'str', 'fit', hint='fit,stretch,original,tile')]),
    dict(name='wxlayer', family='wx', desc='设置层级与点击行为',
         args=[arg('id', 'str'),
               arg('layer', 'str', hint=LAYERS)]),
    dict(name='wxtitle', family='wx', desc='设置/重置标题',
         args=[arg('id', 'str'),
               arg('action', 'str', hint='set,reset'),
               arg('text', 'str', '')]),
    dict(name='wxstop', family='wx', desc='停止动画（省略=自己的全部）',
         args=[arg('id', 'str', 'all')]),
    dict(name='wxget', family='wx', desc='查询窗口属性并回显',
         args=[arg('id', 'str'),
               arg('prop', 'str', hint='x,y,w,h,visible')]),
    dict(name='wxscore', family='wx', desc='把窗口属性写入记分板',
         args=[arg('id', 'str'),
               arg('objective', 'str')]),
    # 重同步：只由引擎驱动的可信入口触发（origin 由引擎提供）
    dict(name='wxresync', family='wx', desc='请求重发自己的窗口全量状态', args=[]),

    # ---------------- 演出族 game_directors（命令方块可用）----------------
    dict(name='wxscreate', family='wxs', desc='创建场景窗口（无玩家归属，命令方块可用）',
         args=[arg('id', 'str'),
               arg('w', 'float', 160.0),
               arg('h', 'float', 100.0),
               arg('x', 'str', 'p50'),
               arg('y', 'str', 'p50')]),
    dict(name='wxsmove', family='wxs', desc='移动场景窗口',
         args=[arg('id', 'str'), arg('x', 'str'), arg('y', 'str'),
               arg('speed', 'float', 1.0), arg('ease', 'str', 'linear', hint=EASES)]),
    dict(name='wxssize', family='wxs', desc='改变场景窗口单轴尺寸',
         args=[arg('id', 'str'), arg('axis', 'str', hint='w,h'), arg('value', 'str'),
               arg('speed', 'float', 1.0), arg('ease', 'str', 'linear', hint=EASES)]),
    dict(name='wxsanim', family='wxs', desc='场景窗口特效',
         args=[arg('id', 'str'),
               arg('kind', 'str', hint='shake,wobble,breath,encircle'),
               arg('a', 'float', 8.0, desc='强度/幅度'),
               arg('b', 'float', 1.0, desc='速度'),
               arg('c', 'float', 0.6, desc='时长/半径Y'),
               arg('d', 'float', 0.0, desc='角度/周期')]),
    dict(name='wxsshow', family='wxs', desc='显示场景窗口', args=[arg('id', 'str')]),
    dict(name='wxshide', family='wxs', desc='隐藏场景窗口', args=[arg('id', 'str')]),
    dict(name='wxsstop', family='wxs', desc='停止场景窗口动画',
         args=[arg('id', 'str', 'all')]),

    # ---------------- 管理族 admin ----------------
    dict(name='wxastop', family='wxa', desc='停止某玩家（或全部）窗口动画',
         args=[arg('player', 'str', 'all', desc='玩家名或 all')]),
    dict(name='wxalist', family='wxa', desc='列出某玩家（或全部）窗口',
         args=[arg('player', 'str', 'all')]),
    dict(name='wxakill', family='wxa', desc='清空某玩家全部窗口',
         args=[arg('player', 'str')]),
    dict(name='wxaquota', family='wxa', desc='设置某玩家窗口配额',
         args=[arg('player', 'str'), arg('limit', 'int')]),
]

FAMILY_PERMISSION = {'wx': 'any', 'wxs': 'game_directors', 'wxa': 'admin'}
FAMILY_LABEL = {'wx': '玩家自用', 'wxs': '演出/命令方块', 'wxa': '管理'}

NAME_RE = re.compile(r'^[a-z][a-z0-9_]{1,31}$')
ARG_RE = re.compile(r'^[a-z][a-z0-9_]{0,31}$')


def validate():
    """返回错误列表，空列表表示通过。"""
    errors = []
    seen = set()
    for cmd in SCHEMA:
        name = cmd['name']
        if name in seen:
            errors.append('duplicate command: %s' % name)
        seen.add(name)
        if not NAME_RE.match(name):
            errors.append('bad name: %s' % name)
        if cmd['family'] not in FAMILY_PERMISSION:
            errors.append('bad family: %s' % name)
        args = cmd['args']
        seen_default = False
        for a in args:
            if a['type'] not in ALLOWED_TYPES:
                errors.append('%s: bad type %s' % (name, a['type']))
            if not ARG_RE.match(a['name']):
                errors.append('%s: bad arg name %s' % (name, a['name']))
            if a['default'] is not None:
                seen_default = True
            elif seen_default:
                errors.append('%s: arg %s without default after default' % (name, a['name']))
        # 参数类型与默认值一致性
        for a in args:
            if a['default'] is None:
                continue
            t, v = a['type'], a['default']
            if t == 'float' and not isinstance(v, float):
                errors.append('%s.%s: default must be float' % (name, a['name']))
            if t == 'int' and (isinstance(v, bool) or not isinstance(v, int)):
                errors.append('%s.%s: default must be int' % (name, a['name']))
            if t == 'bool' and not isinstance(v, bool):
                errors.append('%s.%s: default must be bool' % (name, a['name']))
            if t == 'str' and not isinstance(v, str):
                errors.append('%s.%s: default must be str' % (name, a['name']))
    return errors


def build_json(cmd):
    permission = FAMILY_PERMISSION[cmd['family']]
    args = []
    for a in cmd['args']:
        item = {'name': a['name'], 'type': a['type']}
        desc = a.get('desc') or ''
        if a.get('hint'):
            desc = (desc + ' | 可选: ' + a['hint']).strip(' |')
        if desc:
            item['description'] = desc
        if a['default'] is not None:
            item['default'] = a['default']
        args.append(item)
    return {
        'format_version': '0.0.1',
        'name': cmd['name'],
        'description': '[WindowX/%s] %s' % (FAMILY_LABEL[cmd['family']], cmd['desc']),
        'permission_level': permission,
        'args': args,
    }


def file_name(cmd):
    return 'wxb_wx_%s.json' % cmd['name'][2:] if cmd['family'] == 'wx' else \
        'wxb_%s_%s.json' % (cmd['family'], cmd['name'][3:])


def emit_index(cmds, out_dir):
    """生成 name -> (family, action) 索引，供服务端精确分发。

    必须用显式索引而不是前缀猜测：`wxscore`/`wxshake`/`wxsize`/`wxstop`
    都以 `wxs` 开头，前缀匹配会把它们误判成演出族。
    """
    lines = [
        '# -*- coding: utf-8 -*-',
        '"""自动生成，请勿手改。由 tools/gen_commands.py 输出。"""',
        '',
        'COMMANDS = {',
    ]
    for cmd in sorted(cmds, key=lambda c: c['name']):
        family = cmd['family']
        action = cmd['name'][len(family):]
        lines.append('    %r: (%r, %r),' % (cmd['name'], family, action))
    lines.append('}')
    lines.append('')
    path = os.path.join(out_dir, 'command_index.py')
    with io.open(path, 'w', encoding='utf-8') as fh:
        fh.write(u'\n'.join(lines))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ns = ap.parse_args()

    errors = validate()
    if errors:
        print('[FAIL] schema invalid:')
        for e in errors:
            print('  -', e)
        return 1
    print('[OK] schema valid: %d commands (%d wx / %d wxs / %d wxa)'
          % (len(SCHEMA),
             len([c for c in SCHEMA if c['family'] == 'wx']),
             len([c for c in SCHEMA if c['family'] == 'wxs']),
             len([c for c in SCHEMA if c['family'] == 'wxa'])))

    if ns.check:
        return 0

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    written = 0
    for cmd in SCHEMA:
        path = os.path.join(OUT_DIR, file_name(cmd))
        with io.open(path, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(build_json(cmd), ensure_ascii=False, indent=2, sort_keys=False))
            fh.write(u'\n')
        written += 1
    print('[OK] wrote %d files -> %s' % (written, OUT_DIR))
    index_path = emit_index(SCHEMA, os.path.join(PROJECT, 'behavior_packs',
                                                 'windowxBehavior', 'windowxScripts',
                                                 'modCommon'))
    print('[OK] command index -> %s' % index_path)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
