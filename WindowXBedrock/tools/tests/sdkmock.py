# -*- coding: utf-8 -*-
"""最小 SDK Mock：用于本地集成测试（**不代表 MCStudio 实机通过**）。

覆盖：
  mod.server.extraServerApi / mod.client.extraClientApi / mod_log / mod.common.mod
  引擎组件：CreatePlayer(GetPlayerAbilities) / CreateGame / CreateCamera / CreatePlayerView / CreateName
  UI：ScreenNode.GetBaseUIControl -> 控件 asXxx() + 触摸回调登记
"""
from __future__ import division

import sys
import types


class State(object):
    def __init__(self):
        self.reset()

    def reset(self):
        self.players = ['p1']
        self.admins = set()
        self.sent = []            # (target_kind, player_id, event, payload)
        self.commands = []        # SetCommand
        self.notify = []
        self.calls = []           # UI/相机调用记录
        self.ui_slots = 3
        self.ui_missing = set()   # 缺失控件路径
        self.ui_mismatch = set()  # 类型不匹配路径
        self.ui_touch = {}        # path -> {state: cb}
        self.camera_fail = set()  # 方法名 -> 抛异常
        self.factory_fail = set() # CreateCamera / CreatePlayerView / CreatePlayer
        self.controls = {}
        self.screen = None

    def sent_events(self, event=None):
        if event is None:
            return list(self.sent)
        return [s for s in self.sent if s[2] == event]


STATE = State()


# ---------------------------------------------------------------- UI controls
class FakeControl(object):
    def __init__(self, path, kind):
        self.path = path
        self.kind = kind

    def _cast(self, want):
        # ui_mismatch 用于注入"类型不匹配"（官方此时返回 None）
        if self.path in STATE.ui_mismatch:
            return None
        return self if want == self.kind else None

    def asPanel(self):
        return self._cast('panel')

    def asImage(self):
        return self._cast('image')

    def asLabel(self):
        return self._cast('label')

    def asButton(self):
        return self._cast('button')

    # ---- 通用 ----
    def SetVisible(self, v):
        STATE.calls.append(('SetVisible', self.path, v))

    def SetFullPosition(self, v):
        STATE.calls.append(('SetFullPosition', self.path, v))

    def SetFullSize(self, v):
        STATE.calls.append(('SetFullSize', self.path, v))

    def SetLayer(self, v):
        STATE.calls.append(('SetLayer', self.path, v))

    # ---- image ----
    def SetAlpha(self, v):
        STATE.calls.append(('SetAlpha', self.path, v))

    def SetSprite(self, v):
        STATE.calls.append(('SetSprite', self.path, v))

    # ---- label ----
    def SetText(self, v):
        STATE.calls.append(('SetText', self.path, v))

    # ---- button ----
    def SetTouchEnable(self, v):
        STATE.calls.append(('SetTouchEnable', self.path, v))

    def AddTouchEventParams(self, params=None):
        STATE.calls.append(('AddTouchEventParams', self.path, params))

    def _bind(self, state, cb):
        STATE.ui_touch.setdefault(self.path, {})[state] = cb
        STATE.calls.append(('bind:' + state, self.path, None))

    def SetButtonTouchDownCallback(self, cb):
        self._bind('down', cb)

    def SetButtonTouchMoveCallback(self, cb):
        self._bind('move', cb)

    def SetButtonTouchUpCallback(self, cb):
        self._bind('up', cb)

    def SetButtonTouchCancelCallback(self, cb):
        self._bind('cancel', cb)


def _kind_of(path):
    if path.endswith('/bg') or path.endswith('/content'):
        return 'image'
    if path.endswith('/title'):
        return 'label'
    if path.endswith('/bar_drag'):
        return 'button'
    return 'panel'


class FakeScreenNode(object):
    def __init__(self, namespace, name, param):
        self.namespace = namespace
        self.name = name
        self.param = param or {}
        self.slots = None

    def GetBaseUIControl(self, path):
        idx = None
        first = path.strip('/').split('/')[0]
        if first.startswith('win'):
            try:
                idx = int(first[3:])
            except ValueError:
                idx = None
        if idx is not None and idx >= STATE.ui_slots:
            return None
        if path in STATE.ui_missing:
            return None
        key = path
        if key not in STATE.controls:
            STATE.controls[key] = FakeControl(path, _kind_of(path))
        return STATE.controls[key]

    def Update(self):
        pass


# ---------------------------------------------------------------- components
class FakePlayer(object):
    def __init__(self, eid):
        self.eid = eid

    def GetPlayerAbilities(self):
        if 'CreatePlayer' in STATE.factory_fail:
            raise RuntimeError('inject: CreatePlayer')
        return {'op': self.eid in STATE.admins}


class FakeGame(object):
    def SetCommand(self, cmd):
        STATE.commands.append(cmd)
        return True

    def SetNotifyMsg(self, msg):
        STATE.notify.append(msg)
        return True


class FakeCamera(object):
    def __init__(self):
        self.fov = 70.0
        self.pos = (0.0, 0.0, 0.0)

    def _do(self, name, *args):
        if name in STATE.camera_fail:
            raise RuntimeError('inject: %s' % name)
        STATE.calls.append((name, args))

    def DepartCamera(self):
        self._do('DepartCamera')

    def UnDepartCamera(self):
        self._do('UnDepartCamera')

    def ResetCameraPos(self):
        self._do('ResetCameraPos')

    def ResetCameraBindActorId(self):
        self._do('ResetCameraBindActorId')

    def UnLockCamera(self):
        self._do('UnLockCamera')

    def GetFov(self):
        self._do('GetFov')
        return self.fov

    def GetCameraOffset(self):
        self._do('GetCameraOffset')
        return (0.0, 0.0, 0.0)

    def SetFov(self, fov):
        self._do('SetFov', fov)
        self.fov = fov

    def SetCameraPos(self, pos):
        self._do('SetCameraPos', pos)
        self.pos = pos

    def SetCameraRotation(self, rot):
        self._do('SetCameraRotation', rot)

    def SetCameraOffset(self, offset):
        self._do('SetCameraOffset', offset)

    def SetCameraBindActorId(self, eid):
        self._do('SetCameraBindActorId', eid)


class FakeView(object):
    def _do(self, name, *args):
        if name in STATE.camera_fail:
            raise RuntimeError('inject: %s' % name)
        STATE.calls.append((name, args))

    def GetPerspective(self):
        self._do('GetPerspective')
        return 1

    def SetPerspective(self, mode):
        self._do('SetPerspective', mode)

    def SetPlayerFovScale(self, scale):
        self._do('SetPlayerFovScale', scale)


class FakeName(object):
    def __init__(self, eid):
        self.eid = eid

    def GetName(self):
        return 'name_' + str(self.eid)


class FakeFactory(object):
    def CreatePlayer(self, eid):
        return FakePlayer(eid)

    def CreateGame(self, level_id=None):
        return FakeGame()

    def CreateCamera(self, level_id=None):
        if 'CreateCamera' in STATE.factory_fail:
            raise RuntimeError('inject: CreateCamera')
        return FakeCamera()

    def CreatePlayerView(self, eid=None):
        if 'CreatePlayerView' in STATE.factory_fail:
            raise RuntimeError('inject: CreatePlayerView')
        return FakeView()

    def CreateName(self, eid):
        return FakeName(eid)


# ---------------------------------------------------------------- systems
class FakeServerSystem(object):
    def __init__(self, namespace, systemName):
        self.namespace = namespace
        self.systemName = systemName
        self.listeners = {}

    def ListenForEvent(self, ns, sysname, event, obj, cb):
        self.listeners[(ns, sysname, event)] = cb

    def UnListenForEvent(self, ns, sysname, event, obj, cb):
        self.listeners.pop((ns, sysname, event), None)

    def NotifyToClient(self, pid, event, payload):
        STATE.sent.append(('client', pid, event, payload))

    def NotifyToMultiClients(self, pids, event, payload):
        for pid in pids:
            STATE.sent.append(('client', pid, event, payload))

    def BroadcastToAllClient(self, event, payload):
        STATE.sent.append(('all', None, event, payload))


class FakeClientSystem(object):
    def __init__(self, namespace, systemName):
        self.namespace = namespace
        self.systemName = systemName
        self.listeners = {}

    def ListenForEvent(self, ns, sysname, event, obj, cb):
        self.listeners[(ns, sysname, event)] = cb

    def UnListenForEvent(self, ns, sysname, event, obj, cb):
        self.listeners.pop((ns, sysname, event), None)

    def NotifyToServer(self, event, payload):
        STATE.sent.append(('server', None, event, payload))


class FakeLogger(object):
    def __init__(self):
        self.lines = []

    def _log(self, level, msg):
        self.lines.append((level, msg))

    def info(self, msg, *a):
        self._log('info', msg % a if a else msg)

    def warn(self, msg, *a):
        self._log('warn', msg % a if a else msg)

    def error(self, msg, *a):
        self._log('error', msg % a if a else msg)

    def debug(self, msg, *a):
        self._log('debug', msg % a if a else msg)


LOGGER = FakeLogger()


# ---------------------------------------------------------------- install
def _module(name, **attrs):
    mod = types.ModuleType(name)
    mod.__path__ = []
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def install():
    """安装 mock 模块到 sys.modules（幂等）。"""
    if getattr(install, '_done', False):
        return STATE

    factory = FakeFactory()

    server_api = _module(
        'mod.server.extraServerApi',
        GetServerSystemCls=lambda: FakeServerSystem,
        GetEngineNamespace=lambda: 'Minecraft',
        GetEngineSystemName=lambda: 'ServerEngine',
        GetLevelId=lambda: 'level1',
        GetEngineCompFactory=lambda: factory,
        GetPlayerList=lambda: list(STATE.players),
    )
    client_api = _module(
        'mod.client.extraClientApi',
        GetClientSystemCls=lambda: FakeClientSystem,
        GetScreenNodeCls=lambda: FakeScreenNode,
        GetEngineNamespace=lambda: 'Minecraft',
        GetEngineSystemName=lambda: 'ClientEngine',
        GetLocalPlayerId=lambda: 'p1',
        GetLevelId=lambda: 'level1',
        GetEngineCompFactory=lambda: factory,
        RegisterSystem=lambda *a: None,
        RegisterUI=lambda *a: None,
        CreateUI=lambda *a: None,
        GetSystem=lambda *a: None,
        GetUI=lambda *a: None,
    )

    mod = _module('mod')
    mod_server = _module('mod.server')
    mod_client = _module('mod.client')
    mod_common = _module('mod.common')
    mod_common_mod = _module('mod.common.mod')

    class _Mod(object):
        @staticmethod
        def Binding(**kw):
            def deco(cls):
                return cls
            return deco

        @staticmethod
        def InitServer():
            return lambda fn: fn

        @staticmethod
        def InitClient():
            return lambda fn: fn

        @staticmethod
        def DestroyServer():
            return lambda fn: fn

        @staticmethod
        def DestroyClient():
            return lambda fn: fn

    mod_common_mod.Mod = _Mod

    legacy_client = _module('client')
    legacy_client_api = _module('client.extraClientApi',
                                **dict((k, v) for k, v in vars(client_api).items()
                                       if not k.startswith('__')))
    mod_log = _module('mod_log', logger=LOGGER)

    setattr(mod, 'server', mod_server)
    setattr(mod, 'client', mod_client)
    setattr(mod, 'common', mod_common)
    setattr(mod_server, 'extraServerApi', server_api)
    setattr(mod_client, 'extraClientApi', client_api)
    setattr(mod_common, 'mod', mod_common_mod)
    setattr(legacy_client, 'extraClientApi', legacy_client_api)

    sys.modules.update({
        'mod': mod,
        'mod.server': mod_server,
        'mod.server.extraServerApi': server_api,
        'mod.client': mod_client,
        'mod.client.extraClientApi': client_api,
        'mod.common': mod_common,
        'mod.common.mod': mod_common_mod,
        'mod_log': mod_log,
        'client': legacy_client,
        'client.extraClientApi': legacy_client_api,
    })
    install._done = True
    return STATE


def reset():
    STATE.reset()
    LOGGER.lines = []
