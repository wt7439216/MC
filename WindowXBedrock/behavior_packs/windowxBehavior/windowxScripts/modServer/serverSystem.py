# -*- coding: utf-8 -*-
"""服务端系统：事件适配 + 可信来源解析 + 补丁路由。

安全边界（P0.5）：
  * 自定义指令的 origin 由引擎给出，可信；据此区分玩家/命令方块；
  * 管理员身份通过 GetPlayerAbilities().op 查证，失败则 fail-closed；
  * 客户端 NotifyToServer 事件（EV_CMD / EV_ACK）无可靠发送者身份，
    **不写服务端状态**，仅记录并拒绝；
  * 重同步只能由引擎驱动的入口触发：玩家加入 / `wxresync` 指令。
"""
from __future__ import division

import time

import mod.server.extraServerApi as serverApi
from mod_log import logger

from windowxScripts.modCommon import command_event
from windowxScripts.modCommon import dispatch_core
from windowxScripts.modCommon import modConfig
from windowxScripts.modCommon import permissions
from windowxScripts.modCommon import protocol
from windowxScripts.modCommon import registry_core
from windowxScripts.modCommon import rev_store
from windowxScripts.modServer import permissions_service

ServerSystem = serverApi.GetServerSystemCls()


class WXServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        self.store = registry_core.Store()
        self.revs = rev_store.RevStore()
        self.perms = permissions_service.PermissionService(logger)
        self._rate = {}
        self._warned = set()
        self._listen()

    # ---------------- 事件注册 ----------------
    def _listen(self):
        eng_ns = serverApi.GetEngineNamespace()
        eng_sys = serverApi.GetEngineSystemName()
        self.ListenForEvent(eng_ns, eng_sys, modConfig.EV_CMD_TRIGGER,
                            self, self.OnCustomCommand)
        self.ListenForEvent(eng_ns, eng_sys, modConfig.EV_ADD_PLAYER,
                            self, self.OnPlayerJoin)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.CLIENT_SYSTEM,
                            modConfig.EV_ACK, self, self.OnAck)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.CLIENT_SYSTEM,
                            modConfig.EV_CMD, self, self.OnClientCmd)
        if modConfig.DEV_MODE:
            self.ListenForEvent(eng_ns, eng_sys, modConfig.EV_CHAT,
                                self, self.OnChat)

    # ---------------- 指令入口（可信 origin）----------------
    def OnCustomCommand(self, raw):
        ev = command_event.parse_event(raw)
        family, action = command_event.split_command(ev['command'])
        if family is None:
            return

        entity_id = ev['origin']['entityId']
        is_admin = self.perms.is_admin(entity_id) if entity_id else False
        actor = command_event.actor_from_origin(ev['origin'], is_admin)
        if not self._rate_ok(actor.get('id')):
            self._fail(raw, actor, '操作过快，请稍后再试')
            return

        if family == modConfig.FAMILY_PLAYER and action == 'resync':
            self._send_full_bundle(actor.get('id'))
            self._chat(actor, '§a[WindowX] 已重发窗口状态')
            return

        args = ev['args']
        if family == modConfig.FAMILY_ADMIN and action in ('stop', 'list', 'kill', 'quota'):
            who = str(args.get('player') or 'all')
            if who and who != 'all':
                resolved = self.perms.resolve_player(who)
                if not resolved:
                    self._fail(raw, actor, '找不到玩家: %s' % who)
                    return
                args = dict(args)
                args['player'] = resolved

        result = dispatch_core.handle(self.store, family, action, args, actor)
        if not result['ok']:
            self._fail(raw, actor, result['msg'])
            return

        self._deliver(actor, family, result)
        self._chat(actor, '§a[WindowX] ' + result['msg'])
        data = result.get('data') or {}
        if action == 'score' and data.get('objective'):
            self._write_score(actor, data)

    # ---------------- 引擎驱动的重同步 ----------------
    def OnPlayerJoin(self, raw):
        pid = ''
        for key in ('id', 'playerId', 'entityId'):
            if isinstance(raw, dict) and raw.get(key):
                pid = str(raw.get(key))
                break
        if pid:
            self._send_full_bundle(pid)

    def _send_full_bundle(self, pid):
        if not pid:
            return
        self._send_full(pid, pid)
        self._send_full(modConfig.SCENE_OWNER, pid)

    def _send_full(self, owner, target):
        pkt = protocol.make_full(owner, self.revs.current(owner),
                                 self.store.list(owner))
        try:
            self.NotifyToClient(target, modConfig.EV_FULL, pkt)
        except Exception as exc:
            self._log_error('send full failed: %r' % (exc,))

    # ---------------- 补丁路由 ----------------
    def _deliver(self, actor, family, result):
        ops = result.get('ops') or []
        if not ops:
            return
        default_owner = permissions.scope_owner(family, actor) or ''
        groups = {}
        for op in ops:
            owner = op.get('owner') or default_owner
            groups.setdefault(owner, []).append(op)
        for owner in groups:
            rev = self.revs.next(owner)
            pkt = protocol.make_patch(owner, rev, groups[owner])
            if owner == modConfig.SCENE_OWNER:
                try:
                    self.BroadcastToAllClient(modConfig.EV_PATCH, pkt)
                except Exception as exc:
                    self._log_error('broadcast patch failed: %r' % (exc,))
            else:
                try:
                    self.NotifyToClient(owner, modConfig.EV_PATCH, pkt)
                except Exception as exc:
                    self._log_error('send patch failed: %r' % (exc,))

    # ---------------- 客户端写请求：一律拒绝 ----------------
    def OnClientCmd(self, raw):
        self._warn_once('client_write',
                        '拒绝客户端写请求 EV_CMD：无法验证发送者身份（payload=%r）' % (raw,))

    def OnAck(self, raw):
        self._warn_once('client_ack',
                        '忽略客户端 ACK：无法验证发送者身份（payload=%r）' % (raw,))

    # ---------------- 开发期聊天兜底 ----------------
    def OnChat(self, raw):
        msg = str((raw or {}).get('message') or '')
        if not msg.startswith('!wx'):
            return
        parts = msg[3:].split()
        if not parts:
            return
        pid = str((raw or {}).get('playerId') or '')
        actor = permissions.make_actor_player(pid, self.perms.is_admin(pid))
        family, action = command_event.split_command(parts[0])
        if family is None:
            return
        args = {}
        for pair in parts[1:]:
            if '=' in pair:
                k, v = pair.split('=', 1)
                args[k] = v
        result = dispatch_core.handle(self.store, family, action, args, actor)
        if result['ok']:
            self._deliver(actor, family, result)
        self._chat(actor, ('§a' if result['ok'] else '§c') + result['msg'])

    # ---------------- 工具 ----------------
    def _fail(self, raw, actor, message):
        command_event.write_back_failure(raw, message)
        self._chat(actor, '§c[WindowX] ' + message)
        logger.warn('[WX] cmd failed: %s' % message)

    def _chat(self, actor, msg):
        target = (actor or {}).get('id') or ''
        if not target or target == modConfig.SCENE_OWNER:
            return
        try:
            self.NotifyToClient(target, modConfig.EV_TOAST, {'msg': msg})
        except Exception as exc:
            self._log_error('toast failed: %r' % (exc,))

    def _rate_ok(self, key):
        key = str(key or '?')
        now = time.time()
        bucket = self._rate.setdefault(key, [])
        bucket[:] = [t for t in bucket if now - t < 1.0]
        if len(bucket) >= modConfig.MAX_COMMANDS_PER_SECOND:
            return False
        bucket.append(now)
        return True

    def _write_score(self, actor, data):
        try:
            comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            for key in ('x', 'y', 'w', 'h'):
                comp.SetCommand('scoreboard players set %s_%s %s %d'
                                % (data.get('id'), key, data.get('objective'),
                                   int(data.get(key, 0))))
        except Exception as exc:
            self._log_error('scoreboard write failed: %r' % (exc,))

    def _warn_once(self, key, msg):
        if key in self._warned:
            return
        self._warned.add(key)
        logger.warn('[WX] ' + msg)

    def _log_error(self, msg):
        logger.error('[WX] ' + msg)
