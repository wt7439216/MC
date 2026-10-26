# -*- coding: utf-8 -*-
"""服务端系统：自定义指令 -> 纯逻辑分发 -> 下发补丁。

本文件只做"适配"：解析网易事件、限流、发通知；所有业务判定在
modCommon/dispatch_core.py（可在本地单测）。
"""
from __future__ import division

import time

import mod.server.extraServerApi as serverApi

from windowxScripts.modCommon import dispatch_core
from windowxScripts.modCommon import modConfig
from windowxScripts.modCommon import permissions
from windowxScripts.modCommon import protocol
from windowxScripts.modCommon import registry_core

ServerSystem = serverApi.GetServerSystemCls()

# 建议在部署时改为真实 UID 白名单；JSON 的 permission_level 只是第一道闸。
ADMIN_UIDS = set()


def _log(msg):
    try:
        serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId()).SetNotifyMsg(msg)
    except Exception:
        pass


class WXServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        self.store = registry_core.Store()
        self._last_cmd = {}   # playerId -> [timestamps]
        self._rev = {}        # owner -> rev
        self._listen()

    # ---------------- 事件 ----------------
    def _listen(self):
        eng_ns = serverApi.GetEngineNamespace()
        eng_sys = serverApi.GetEngineSystemName()
        self.ListenForEvent(eng_ns, eng_sys, 'CustomCommandTriggerServerEvent',
                            self, self.OnCustomCommand)
        # 开发期兜底：聊天栏 "!wx ..." 也能触发（正式版可关）
        self.ListenForEvent(eng_ns, eng_sys, 'ServerChatEvent', self, self.OnChat)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.CLIENT_SYSTEM,
                            modConfig.EV_ACK, self, self.OnAck)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.CLIENT_SYSTEM,
                            modConfig.EV_CMD, self, self.OnClientCmd)

    # ---------------- 指令入口 ----------------
    def OnCustomCommand(self, args):
        name = str(args.get('command') or args.get('cmd') or '')
        argd = args.get('args') or {}
        player_id = args.get('entityId') or args.get('playerId') or ''
        block_pos = args.get('blockPos')
        family, action = self._split_command(name)
        if not family:
            return
        actor = self._make_actor(player_id, block_pos)
        if not self._rate_ok(actor.get('id')):
            self._notify(actor, '操作太快，请稍后再试')
            return
        result = dispatch_core.handle(self.store, family, action, argd, actor)
        self._after(family, action, actor, result)

    def OnChat(self, args):
        """!wxwin move mywin p50 p40 —— 仅开发期使用。"""
        msg = str(args.get('message') or '')
        if not msg.startswith('!wx'):
            return
        parts = msg[3:].split()
        if not parts:
            return
        player_id = args.get('playerId') or ''
        name = parts[0]
        family, action = self._split_command(name)
        if not family:
            return
        argd = {}
        for pair in parts[1:]:
            if '=' in pair:
                k, v = pair.split('=', 1)
                argd[k] = v
        actor = self._make_actor(player_id, None)
        result = dispatch_core.handle(self.store, family, action, argd, actor)
        self._after(family, action, actor, result)

    # ---------------- 核心后续处理 ----------------
    def _after(self, family, action, actor, result):
        owner = permissions.scope_owner(family, actor) or ''
        rev = self._rev.get(owner, 0) + 1
        self._rev[owner] = rev

        if not result['ok']:
            self._notify(actor, '§c' + result['msg'])
            return

        if actor.get('kind') == 'player' or actor.get('kind') == 'admin':
            self._notify(actor, '§a' + result['msg'])

        if result['ops']:
            pkt = protocol.make_patch(owner, rev, result['ops'])
            self._send_ops(owner, pkt)

        data = result.get('data') or {}
        if action == 'score' and data.get('objective'):
            self._write_score(owner, data)

    def _send_ops(self, owner, pkt):
        if owner == modConfig.SCENE_OWNER:
            try:
                self.BroadcastToAllClient(modConfig.EV_PATCH, pkt)
            except Exception:
                pass
            return
        try:
            self.NotifyToClient(owner, modConfig.EV_PATCH, pkt)
        except Exception:
            pass

    def _write_score(self, owner, data):
        obj = data.get('objective')
        try:
            comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            comp.SetCommand('scoreboard players set %s %s %d'
                            % (data['id'] + '_x', obj, int(data['x'])))
            comp.SetCommand('scoreboard players set %s %s %d'
                            % (data['id'] + '_y', obj, int(data['y'])))
            comp.SetCommand('scoreboard players set %s %s %d'
                            % (data['id'] + '_w', obj, int(data['w'])))
            comp.SetCommand('scoreboard players set %s %s %d'
                            % (data['id'] + '_h', obj, int(data['h'])))
        except Exception:
            pass

    # ---------------- 客户端回执 ----------------
    def OnAck(self, args):
        owner = args.get('owner') or ''
        rev = int(args.get('rev') or 0)
        if rev < self._rev.get(owner, 0):
            pkt = protocol.make_full(owner, self._rev.get(owner, 0),
                                     self.store.list(owner))
            try:
                self.NotifyToClient(owner, modConfig.EV_FULL, pkt)
            except Exception:
                pass

    def OnClientCmd(self, args):
        """客户端交互（拖拽结束/按钮）——当前仅同步目标坐标。"""
        owner = args.get('owner') or ''
        wid = args.get('id') or ''
        win = self.store.get(owner, wid)
        if win is None:
            return
        for key in ('cx', 'cy', 'w', 'h'):
            if key in args:
                try:
                    win[key] = float(args[key])
                except (TypeError, ValueError):
                    pass

    # ---------------- 工具 ----------------
    def _split_command(self, name):
        if name.startswith('wxs'):
            return modConfig.FAMILY_SHOW, name[3:]
        if name.startswith('wxa'):
            return modConfig.FAMILY_ADMIN, name[3:]
        if name.startswith('wx'):
            return modConfig.FAMILY_PLAYER, name[2:]
        return None, None

    def _make_actor(self, player_id, block_pos):
        if player_id:
            is_admin = (player_id in ADMIN_UIDS)
            return permissions.make_actor_player(player_id, is_admin)
        return permissions.make_actor_command_block(block_pos)

    def _notify(self, actor, msg):
        target = (actor or {}).get('id') or ''
        if target and target != modConfig.SCENE_OWNER:
            try:
                self.NotifyToClient(target, 'wx:toast', {'msg': msg})
            except Exception:
                pass

    def _rate_ok(self, key):
        now = time.time()
        bucket = self._last_cmd.setdefault(key, [])
        bucket[:] = [t for t in bucket if now - t < 1.0]
        if len(bucket) >= modConfig.MAX_COMMANDS_PER_SECOND:
            return False
        bucket.append(now)
        return True
