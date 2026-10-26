# -*- coding: utf-8 -*-
"""三权限族的判定规则（服务端二次校验，不依赖 permission_level 单点）。

actor 结构: {'kind': 'player'|'admin'|'command_block', 'id': <playerId or 'world'>}

对应 v2.1 §3.2：
  wx*  any            只能操作自己的窗口
  wxs* game_directors 只能操作场景窗口（owner = 'world'），命令方块可用
  wxa* admin          可跨玩家
"""
from . import modConfig

F_ANY = modConfig.FAMILY_PLAYER
F_SHOW = modConfig.FAMILY_SHOW
F_ADMIN = modConfig.FAMILY_ADMIN


def can_run(family, actor):
    """该 actor 是否有资格使用该族指令。"""
    kind = (actor or {}).get('kind')
    if family == F_ANY:
        return kind in ('player', 'admin')
    if family == F_SHOW:
        # 命令方块与管理员可用；普通玩家不可（避免绕过 owner 校验）
        return kind in ('command_block', 'admin')
    if family == F_ADMIN:
        return kind == 'admin'
    return False


def can_touch(family, owner, actor):
    """该 actor 是否能操作 owner 名下的窗口。"""
    kind = (actor or {}).get('kind')
    actor_id = (actor or {}).get('id')
    if family == F_ADMIN:
        return kind == 'admin'
    if family == F_SHOW:
        return owner == modConfig.SCENE_OWNER and kind in ('command_block', 'admin')
    if family == F_ANY:
        return owner == actor_id and kind in ('player', 'admin')
    return False


def make_actor_player(player_id, is_admin=False):
    return {'kind': 'admin' if is_admin else 'player', 'id': player_id}


def make_actor_command_block(block_pos=None):
    return {'kind': 'command_block', 'id': modConfig.SCENE_OWNER, 'pos': block_pos}


def scope_owner(family, actor):
    """该族指令写入/读取的 owner 命名空间。"""
    if family == F_SHOW:
        return modConfig.SCENE_OWNER
    return (actor or {}).get('id')
