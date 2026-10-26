# -*- coding: utf-8 -*-
"""CustomCommandTriggerServerEvent 真实形态解析（纯逻辑）。

官方字段（2026-10-26 核实，见 docs/OFFICIAL_FACTS.md）：
    command : str                     自定义命令名（对应 json 的 name）
    args    : list(dict)              每项含 name / type / value
    variant : int                     变体号 [0,9]
    origin  : dict                    entityId(命令方块无) / dimension / blockPos
    return_failed : bool              可写，True 时以红色显示失败
    return_msg_key: str               可写，回显信息（支持 lang 键）

关键点：
  * args 是**列表**，直接 args.get() 会抛异常 -> 必须归一化；
  * origin 里**没有**玩家名/权限等级，管理员身份需另查（GetPlayerAbilities）；
  * 命令方块触发时 origin 不含 entityId -> 据此区分"玩家"与"命令方块"。
"""
from __future__ import division

from . import command_index
from . import modConfig


def normalize_args(raw_args):
    """把 list(dict) / dict / None 统一成 {name: value}。

    重复 name 后者覆盖前者（保守：以引擎给出的顺序为准）。
    """
    out = {}
    if isinstance(raw_args, dict):
        for k in raw_args:
            out[str(k)] = raw_args[k]
        return out
    if isinstance(raw_args, (list, tuple)):
        for item in raw_args:
            if not isinstance(item, dict):
                continue
            name = item.get('name')
            if name is None:
                continue
            out[str(name)] = item.get('value')
    return out


def normalize_origin(raw_origin):
    origin = raw_origin if isinstance(raw_origin, dict) else {}
    data = {
        'entityId': str(origin.get('entityId') or ''),
        'dimension': origin.get('dimension'),
        'blockPos': origin.get('blockPos'),
    }
    data['is_command_block'] = not data['entityId']
    return data


def parse_event(raw):
    """返回 {'command','variant','args','origin','return_failed'}"""
    raw = raw if isinstance(raw, dict) else {}
    try:
        variant = int(raw.get('variant') or 0)
    except (TypeError, ValueError):
        variant = 0
    return {
        'command': str(raw.get('command') or ''),
        'variant': variant,
        'args': normalize_args(raw.get('args')),
        'origin': normalize_origin(raw.get('origin')),
        'return_failed': bool(raw.get('return_failed', False)),
    }


def split_command(name):
    """按自动生成的索引精确分发，**不做前缀猜测**。

    反例：`wxscore` / `wxshake` / `wxsize` / `wxstop` 都以 `wxs` 开头，
    前缀匹配会把玩家族指令误判为演出族（wxs）。
    """
    name = str(name or '')
    hit = command_index.COMMANDS.get(name)
    if hit is None:
        return None, None
    return hit[0], hit[1]


def actor_from_origin(origin, is_admin=False):
    """把 origin 转成权限层使用的 actor。

    命令方块 -> actor.kind='command_block'，id='world'；
    玩家     -> id=entityId，is_admin 决定 admin/player（必须由调用方查证）。
    """
    origin = origin or {}
    if origin.get('is_command_block') or not origin.get('entityId'):
        actor = {'kind': 'command_block', 'id': modConfig.SCENE_OWNER,
                 'dimension': origin.get('dimension'), 'pos': origin.get('blockPos')}
        return actor
    actor = {'kind': 'admin' if is_admin else 'player',
             'id': str(origin.get('entityId')),
             'dimension': origin.get('dimension'), 'pos': origin.get('blockPos')}
    return actor


def describe_event(ev, keep_values=False):
    """给调试日志用的事件摘要：**不输出完整实体 id，也不输出坐标**。"""
    origin = ev.get('origin') or {}
    eid = str(origin.get('entityId') or '')
    masked = (eid[:3] + '***') if eid else '<none>'
    parts = []
    for name in sorted((ev.get('args') or {}).keys()):
        if keep_values:
            parts.append('%s=%s' % (name, repr(ev['args'][name])[:24]))
        else:
            parts.append('%s:%s' % (name, type(ev['args'][name]).__name__))
    return ('command=%s variant=%d args=[%s] origin=%s dim=%r has_entity=%s'
            % (ev.get('command'), int(ev.get('variant') or 0), ','.join(parts),
               masked, origin.get('dimension'), bool(eid)))


def write_back_failure(raw, message):
    """按官方字段把失败写回事件，让引擎以红色提示（不依赖 lang 键）。"""
    if not isinstance(raw, dict):
        return
    raw['return_failed'] = True
    if modConfig.RETURN_MSG_ENABLED:
        raw['return_msg_key'] = message
