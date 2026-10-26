# -*- coding: utf-8 -*-
"""服务端权限/身份查询（唯一调用 SDK 的地方，便于 Mock 测试）。

管理员判定顺序：
  1) CreatePlayer(entityId).GetPlayerAbilities() -> {'op': bool}
  2) 配置 ADMIN_UIDS 白名单
  3) 都不可用 -> False（fail-closed，绝不默认放行）
"""
from __future__ import division

import time

import mod.server.extraServerApi as serverApi

from windowxScripts.modCommon import modConfig

CACHE_TTL = 3.0


class PermissionService(object):
    def __init__(self, logger=None):
        self._cache = {}
        self._logger = logger
        self._warned = False

    def _log(self, msg):
        if self._logger is not None:
            try:
                self._logger.warn('[WX] ' + msg)
            except Exception:
                pass

    def is_admin(self, entity_id):
        entity_id = str(entity_id or '')
        if not entity_id:
            return False
        now = time.time()
        cached = self._cache.get(entity_id)
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]

        result = False
        try:
            comp = serverApi.GetEngineCompFactory().CreatePlayer(entity_id)
            abilities = comp.GetPlayerAbilities()
            if isinstance(abilities, dict) and 'op' in abilities:
                result = bool(abilities.get('op'))
                self._cache[entity_id] = (now, result)
                return result
        except Exception as exc:
            if not self._warned:
                self._warned = True
                self._log('GetPlayerAbilities unavailable: %r' % (exc,))

        result = entity_id in modConfig.ADMIN_UIDS
        self._cache[entity_id] = (now, result)
        return result

    def resolve_player(self, who):
        """把用户名/ID 统一成 entityId；找不到返回空串。"""
        who = str(who or '').strip()
        if not who:
            return ''
        try:
            ids = serverApi.GetPlayerList() or []
        except Exception:
            ids = []
        if who in ids:
            return who
        for pid in ids:
            try:
                name_comp = serverApi.GetEngineCompFactory().CreateName(pid)
                if name_comp and name_comp.GetName() == who:
                    return pid
            except Exception:
                continue
        return ''

    def player_ids(self):
        try:
            return list(serverApi.GetPlayerList() or [])
        except Exception:
            return []
