# -*- coding: utf-8 -*-
"""客户端系统（P0.5）。

要点：
  * 引擎 tick 事件名 = OnScriptTickClient（已核对官方样例）；
  * 窗口以 (owner, id) 复合键存储，避免玩家窗口与场景窗口 id 冲突；
  * 版本号按 owner 维护，缺口只标记不猜测；
  * 客户端不向服务端写状态（EV_CMD 已禁用）；
  * 相机异常路径必须尝试恢复并如实上报。
"""
from __future__ import division

try:
    import mod.client.extraClientApi as clientApi
except ImportError:
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
        self.windows = {}      # (owner, wid) -> win
        self.revs = {}         # owner -> rev
        self.desync = {}       # owner -> bool
        self.anims = {}        # (owner, wid) -> {'move':task,'fx':[...]}
        self.backend = hudBackend.HudBackend(modConfig.HUD_SLOTS)
        self.debug = debugSuite.DebugSuite()
        self.hud = None
        self.camera = cameraAdapter.CameraAdapter(self.level_id, self.player_id)
        self.guard = cameraGuard.CameraGuard(self.camera)
        self.last_toast = ''
        self._warned = set()
        self._listen()

    # ---------------- 事件 ----------------
    def _listen(self):
        eng_ns = clientApi.GetEngineNamespace()
        eng_sys = clientApi.GetEngineSystemName()
        self.ListenForEvent(eng_ns, eng_sys, modConfig.EV_UI_INIT, self, self.OnUiInit)
        self.ListenForEvent(eng_ns, eng_sys, modConfig.EV_TICK_CLIENT, self, self.OnTick)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.SERVER_SYSTEM,
                            modConfig.EV_PATCH, self, self.OnPatch)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.SERVER_SYSTEM,
                            modConfig.EV_FULL, self, self.OnFull)
        self.ListenForEvent(modConfig.MOD_NAME, modConfig.SERVER_SYSTEM,
                            modConfig.EV_TOAST, self, self.OnToast)
        self.ListenForEvent(eng_ns, eng_sys, modConfig.EV_DIM_CHANGE_CLIENT,
                            self, self.OnRecoverCamera)
        self.ListenForEvent(eng_ns, eng_sys, modConfig.EV_LOAD_FINISH_CLIENT,
                            self, self.OnRecoverCamera)

    def OnUiInit(self, args=None):
        try:
            clientApi.RegisterUI(modConfig.MOD_NAME, modConfig.HUD_UI_NAME,
                                 modConfig.HUD_UI_CLS, modConfig.HUD_UI_DEF)
            clientApi.CreateUI(modConfig.MOD_NAME, modConfig.HUD_UI_NAME,
                               {'isHud': 1})
        except Exception as exc:
            logger.error('[WX] CreateUI failed: %r' % (exc,))

    def attach_hud(self, node):
        self.hud = node
        slots = int(getattr(node, 'slots', modConfig.HUD_SLOTS) or modConfig.HUD_SLOTS)
        self.backend.slots = slots
        if not self.backend.bind(node):
            logger.error('[WX] HUD backend unavailable: %s'
                         % self.backend.error_summary())

    def OnTick(self, args=None):
        self._advance()

    # ---------------- 全量/补丁 ----------------
    def OnFull(self, pkt):
        if not isinstance(pkt, dict):
            logger.error('[WX] bad full packet: %r' % (pkt,))
            return
        owner = str(pkt.get('owner') or '')
        if not owner:
            logger.error('[WX] full packet without owner')
            return
        for key in [k for k in self.windows if k[0] == owner]:
            self.windows.pop(key, None)
            self.anims.pop(key, None)
        for win in (pkt.get('windows') or []):
            wid = win.get('id')
            if not wid:
                continue
            self.windows[(owner, wid)] = win
        self.revs[owner] = int(pkt.get('rev') or 0)
        self.desync[owner] = False

    def OnPatch(self, pkt):
        ok, err = protocol.validate_patch(pkt)
        if not ok:
            logger.error('[WX] bad patch: %s' % err)
            return
        owner = str(pkt.get('owner') or '')
        rev = int(pkt.get('rev') or 0)
        prev = self.revs.get(owner, -1)
        if rev <= prev:
            logger.warn('[WX] stale patch dropped owner=%s rev=%s prev=%s'
                        % (owner, rev, prev))
            return
        if prev >= 0 and rev != prev + 1:
            self.desync[owner] = True
            logger.warn('[WX] rev gap owner=%s expect=%s got=%s (run /wxresync)'
                        % (owner, prev + 1, rev))
        self.revs[owner] = rev
        for op in pkt['ops']:
            self._apply_op(owner, op)

    def OnToast(self, args):
        msg = str((args or {}).get('msg') or '')
        if msg:
            self.last_toast = msg
            logger.info('[WX] toast: %s' % msg)

    def _apply_op(self, owner, op):
        kind = op.get('op')
        wid = op.get('id')
        if kind == 'create':
            win = op.get('win') or {}
            new_id = win.get('id')
            if new_id:
                key = (owner, new_id)
                self.windows[key] = win
                self.anims.pop(key, None)
            return
        key = (owner, wid)
        if kind == 'remove':
            self.windows.pop(key, None)
            self.anims.pop(key, None)
            self.backend.release(key)
        elif kind == 'set':
            win = self.windows.get(key)
            if win is not None:
                win.update(op.get('fields') or {})
        elif kind == 'anim':
            task = op.get('task') or {}
            twid = task.get('id') or wid
            if twid:
                self.anims.setdefault((owner, twid), {})['move'] = task
        elif kind == 'fx':
            task = op.get('task') or {}
            twid = task.get('id') or wid
            if twid:
                self.anims.setdefault((owner, twid), {}).setdefault('fx', []).append(task)
        elif kind == 'physics':
            win = self.windows.get(key)
            params = op.get('params') or {}
            if win is not None:
                if params.get('start'):
                    win['cx'], win['cy'] = params['start']
                win['_physics'] = params
        elif kind == 'follow':
            win = self.windows.get(key)
            if win is not None:
                win['_follow'] = op.get('params')
        elif kind == 'stop':
            if wid == 'all':
                self.anims = {}
                for w in self.windows.values():
                    w.pop('_physics', None)
                    w.pop('_follow', None)
            else:
                self.anims.pop(key, None)
                win = self.windows.get(key)
                if win is not None:
                    win.pop('_physics', None)
                    win.pop('_follow', None)

    # ---------------- 每帧 ----------------
    def _advance(self):
        for key in list(self.anims.keys()):
            slot = self.anims[key]
            win = self.windows.get(key)
            if win is None:
                self.anims.pop(key, None)
                continue
            task = slot.get('move')
            if task:
                t = animator_core.step_task(task, TICK)
                animator_core.apply_task(win, task, t)
                if t >= 1.0:
                    slot.pop('move', None)
            keep = []
            for fx in (slot.get('fx') or []):
                if animator_core.step_task(fx, TICK) < 1.0:
                    keep.append(fx)
            slot['fx'] = keep
            if not slot.get('move') and not slot.get('fx'):
                self.anims.pop(key, None)

    def on_hud_update(self):
        debugSuite.begin()
        entries = self._render_entries()
        self.backend.sync(entries)
        self.debug.tick(debugSuite.end_ms(), len(entries))
        if modConfig.DEV_MODE:
            self.debug.maybe_log(logger)

    def _render_entries(self):
        out = []
        for (owner, wid), win in self.windows.items():
            dx = dy = 0.0
            scale = 1.0
            slot = self.anims.get((owner, wid)) or {}
            for fx in (slot.get('fx') or []):
                t = animator_core.task_progress(fx)
                ox, oy, s = animator_core.fx_offsets(fx, t)
                dx += ox
                dy += oy
                scale *= s
            phys = win.get('_physics')
            if phys:
                body = phys.get('_body')
                if body is None:
                    body = physics2d.Body2D(win['cx'], win['cy'], win['w'], win['h'],
                                            phys.get('gravity', 1200.0),
                                            phys.get('friction', 0.12),
                                            phys.get('elasticity', 0.45))
                    phys['_body'] = body
                cx, cy = body.step(TICK, modConfig.VIEW_W, modConfig.VIEW_H)
                win['cx'], win['cy'] = cx, cy
            out.append((owner, wid, win, dx, dy, scale))
        return out

    # ---------------- 交互（仅本地）----------------
    def on_drag(self, slot, state, touch):
        key = None
        for k, v in self.backend.slot_of.items():
            if v == slot:
                key = k
                break
        if key is None:
            return
        win = self.windows.get(key)
        if win is None:
            return
        try:
            px = float(touch[0])
            py = float(touch[1])
        except (TypeError, ValueError, IndexError):
            return
        if px <= 1.0:
            px *= modConfig.VIEW_W
        if py <= 1.0:
            py *= modConfig.VIEW_H
        if state == 'down':
            win['_drag'] = (px - win['cx'], py - win['cy'])
        elif state == 'move':
            ox, oy = win.get('_drag') or (0.0, 0.0)
            cx, cy, w, h = layout.clamp_window(px - ox, py - oy, win['w'], win['h'],
                                               modConfig.VIEW_W, modConfig.VIEW_H)
            win['cx'], win['cy'] = cx, cy
        elif state in ('up', 'cancel'):
            win.pop('_drag', None)
            self._warn_once('drag_no_sync',
                            '拖拽仅本地生效：客户端写服务端已被禁用（等待可信身份）')

    # ---------------- 相机 ----------------
    def OnRecoverCamera(self, args=None):
        report = self.guard.exit()
        if not report.get('ok'):
            logger.error('[WX] camera recovery incomplete: %r' % (report,))

    def set_camera(self, pos, pitch, yaw, fov=None):
        if not self.guard.enter():
            logger.warn('[WX] camera enter degraded, aborting set_camera')
            return False
        ok = self.camera.set_transform(pos, pitch, yaw)
        if fov is not None:
            ok = self.camera.set_fov(fov) and ok
        if not ok:
            logger.error('[WX] camera apply failed: %r'
                         % (self.camera.failure_report(),))
            self.guard.exit()
        return ok

    def reset_camera(self):
        report = self.guard.exit()
        return bool(report.get('ok'))

    def shutdown(self):
        report = self.guard.exit()
        for key in list(self.windows.keys()):
            self.backend.release(key)
        self.windows = {}
        self.anims = {}
        return report

    def _warn_once(self, key, msg):
        if key in self._warned:
            return
        self._warned.add(key)
        logger.warn('[WX] ' + msg)
