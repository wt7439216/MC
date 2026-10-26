# -*- coding: utf-8 -*-
"""客户端系统：接收补丁 -> 本地插值/特效 -> 写 HUD；并管理相机守卫。"""
from __future__ import division

import client.extraClientApi as clientApi
from mod_log import logger

from windowxScripts.modCommon import animator_core
from windowxScripts.modCommon import layout
from windowxScripts.modCommon import modConfig
from windowxScripts.modCommon import physics2d
from windowxScripts.modCommon import protocol
from windowxScripts.modClient import cameraAdapter
from windowxScripts.modClient import cameraGuard
from windowxScripts.modClient import debugSuite
from windowxScripts.modClient import hudBackend

ClientSystem = clientApi.GetClientSystemCls()

TICK = 1.0 / 30.0


class WXClientSystem(ClientSystem):
    def __init__(self, namespace, systemName):
        ClientSystem.__init__(self, namespace, systemName)
        self.player_id = clientApi.GetLocalPlayerId()
        self.level_id = clientApi.GetLevelId()
        self.windows = {}          # wid -> win（服务端镜像）
        self.anims = {}            # wid -> {'move': task} / {'fx': [task]}
        self.backend = hudBackend.HudBackend()
        self.debug = debugSuite.DebugSuite()
        self.hud = None
        self.camera = cameraAdapter.CameraAdapter(self.level_id, self.player_id)
        self.guard = cameraGuard.CameraGuard(self.camera)
        self._last_rev = 0
        self._listen()

    # ---------------- 事件 ----------------
    def _listen(self):
        eng_ns = clientApi.GetEngineNamespace()
        eng_sys = clientApi.GetEngineSystemName()
        self.ListenForEvent(eng_ns, eng_sys, 'UiInitFinished', self, self.OnUiInit)
        self.ListenForEvent(eng_ns, eng_sys, 'ScriptTickClient', self, self.OnTick)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.SERVER_SYSTEM,
                            modConfig.EV_PATCH, self, self.OnPatch)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.SERVER_SYSTEM,
                            modConfig.EV_FULL, self, self.OnFull)
        self.ListenForEvent(eng_ns, eng_sys, 'ClientPlayerInventoryCloseEvent',
                            self, self.OnRestoreCamera)
        self.ListenForEvent(eng_ns, eng_sys, 'DimensionChangeFinishClientEvent',
                            self, self.OnRestoreCamera)

    def OnUiInit(self, args):
        try:
            clientApi.RegisterUI(modConfig.MOD_NAME, modConfig.HUD_UI_NAME,
                                 modConfig.HUD_UI_CLS, modConfig.HUD_UI_DEF)
            clientApi.CreateUI(modConfig.MOD_NAME, modConfig.HUD_UI_NAME, {'isHud': 1})
        except Exception as exc:
            logger.error('[WX] CreateUI failed: %s' % exc)

    def attach_hud(self, node):
        self.hud = node
        self.backend.slots = int(getattr(node, 'slots', self.backend.slots) or 0)
        self.backend.bind_node(node)
        logger.info('[WX] HUD attached, slots=%d' % self.backend.slots)

    def OnTick(self, args=None):
        self._advance()

    # ---------------- 补丁 ----------------
    def OnFull(self, args):
        self.windows = {}
        for win in (args.get('windows') or []):
            self.windows[win['id']] = win
        self._last_rev = int(args.get('rev') or 0)

    def OnPatch(self, args):
        ok, err = protocol.validate_patch(args)
        if not ok:
            logger.warn('[WX] bad patch: %s' % err)
            return
        self._last_rev = max(self._last_rev, int(args.get('rev') or 0))
        for op in args['ops']:
            self._apply_op(op)

    def _apply_op(self, op):
        kind = op.get('op')
        wid = op.get('id')
        if kind == 'create':
            win = op.get('win') or {}
            if win.get('id'):
                self.windows[win['id']] = win
                self.anims.pop(win['id'], None)
        elif kind == 'remove':
            self.windows.pop(wid, None)
            self.anims.pop(wid, None)
            self.backend.release(wid)
        elif kind == 'set':
            win = self.windows.get(wid)
            if win is not None:
                win.update(op.get('fields') or {})
        elif kind == 'anim':
            win = self.windows.get(wid) or self.windows.get(
                (op.get('task') or {}).get('id'))
            task = op.get('task') or {}
            if win is not None and task.get('id'):
                slot = self.anims.setdefault(task['id'], {})
                slot['move'] = task
        elif kind == 'fx':
            task = op.get('task') or {}
            if task.get('id'):
                slot = self.anims.setdefault(task['id'], {})
                slot.setdefault('fx', []).append(task)
        elif kind == 'physics':
            win = self.windows.get(wid)
            params = op.get('params') or {}
            if win is not None:
                if params.get('start'):
                    win['cx'], win['cy'] = params['start']
                win['_physics'] = params
        elif kind == 'follow':
            win = self.windows.get(wid)
            if win is not None:
                win['_follow'] = op.get('params')
        elif kind == 'stop':
            if wid == 'all':
                self.anims = {}
                for w in self.windows.values():
                    w.pop('_physics', None)
                    w.pop('_follow', None)
            else:
                self.anims.pop(wid, None)
                win = self.windows.get(wid)
                if win is not None:
                    win.pop('_physics', None)
                    win.pop('_follow', None)

    # ---------------- 每帧 ----------------
    def on_hud_update(self):
        debugSuite.begin()
        entries = self._render_entries()
        self.backend.sync(entries)
        self.debug.tick(debugSuite.end_ms(), len(entries))
        if modConfig.DEV_MODE:
            self.debug.maybe_log(logger)

    def _advance(self):
        for wid in list(self.anims.keys()):
            slot = self.anims[wid]
            win = self.windows.get(wid)
            if win is None:
                self.anims.pop(wid, None)
                continue
            task = slot.get('move')
            if task:
                t = animator_core.step_task(task, TICK)
                animator_core.apply_task(win, task, t)
                if t >= 1.0:
                    slot.pop('move', None)
            fxs = slot.get('fx') or []
            keep = []
            for fx in fxs:
                t = animator_core.step_task(fx, TICK)
                if t < 1.0:
                    keep.append(fx)
            slot['fx'] = keep
            if not slot.get('move') and not slot.get('fx'):
                self.anims.pop(wid, None)

    def _render_entries(self):
        out = []
        for wid, win in self.windows.items():
            dx = dy = 0.0
            scale = 1.0
            slot = self.anims.get(wid) or {}
            for fx in (slot.get('fx') or []):
                t = animator_core.task_progress(fx)
                ox, oy, s = animator_core.fx_offsets(fx, t)
                dx += ox
                dy += oy
                scale *= s
            phys = win.get('_physics')
            if phys and not phys.get('dragging'):
                body = phys.get('_body')
                if body is None:
                    body = physics2d.Body2D(win['cx'], win['cy'], win['w'], win['h'],
                                            phys.get('gravity', 1200.0),
                                            phys.get('friction', 0.12),
                                            phys.get('elasticity', 0.45))
                    body.vx, body.vy = 0.0, 0.0
                    phys['_body'] = body
                cx, cy = body.step(TICK, modConfig.VIEW_W, modConfig.VIEW_H)
                win['cx'], win['cy'] = cx, cy
            out.append((wid, win, dx, dy, scale))
        return out

    # ---------------- 交互 ----------------
    def on_drag(self, slot, state, touch):
        wid = None
        for k, v in self.backend.slot_of.items():
            if v == slot:
                wid = k
                break
        if wid is None:
            return
        win = self.windows.get(wid)
        if win is None:
            return
        px = touch[0] * modConfig.VIEW_W if touch[0] <= 1.0 else touch[0]
        py = touch[1] * modConfig.VIEW_H if touch[1] <= 1.0 else touch[1]
        if state == 'down':
            win['_drag'] = (px - win['cx'], py - win['cy'])
        elif state == 'move':
            ox, oy = win.get('_drag') or (0.0, 0.0)
            cx, cy, w, h = layout.clamp_window(px - ox, py - oy, win['w'], win['h'],
                                               modConfig.VIEW_W, modConfig.VIEW_H)
            win['cx'], win['cy'] = cx, cy
        elif state == 'up':
            win.pop('_drag', None)
            self.NotifyToServer(modConfig.EV_CMD, {
                'owner': self.player_id, 'id': wid,
                'cx': win['cx'], 'cy': win['cy']})

    # ---------------- 相机 ----------------
    def OnRestoreCamera(self, args):
        try:
            self.guard.exit()
        except Exception as exc:
            logger.warn('[WX] camera restore failed: %s' % exc)

    def set_camera(self, pos, pitch, yaw, fov=None):
        self.guard.enter()
        self.camera.set_transform(pos, pitch, yaw)
        if fov is not None:
            self.camera.set_fov(fov)

    def reset_camera(self):
        self.guard.exit()
