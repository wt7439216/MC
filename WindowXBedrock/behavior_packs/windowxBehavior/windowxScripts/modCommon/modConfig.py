# -*- coding: utf-8 -*-
"""全局配置（纯常量，不 import SDK，便于本地单测）。"""

MOD_NAME = 'windowx'
SERVER_SYSTEM = 'wxServerSystem'
CLIENT_SYSTEM = 'wxClientSystem'

SERVER_SYSTEM_CLS = 'windowxScripts.modServer.serverSystem.WXServerSystem'
CLIENT_SYSTEM_CLS = 'windowxScripts.modClient.clientSystem.WXClientSystem'

# ---- 事件名（服务端 <-> 客户端）----
EV_CMD = 'wx:cmd'          # C->S 玩家交互（拖拽结束/按钮）
EV_PATCH = 'wx:patch'      # S->C 增量补丁 + 操作指令
EV_FULL = 'wx:full'        # S->C 全量窗口表
EV_ACK = 'wx:ack'          # C->S rev 回执
EV_DEBUG = 'wx:debug'      # S->C 调试开关

# ---- 虚拟画布（UI 坐标系）----
VIEW_W = 1920.0
VIEW_H = 1080.0

# ---- 配额与限流 ----
MAX_WINDOWS_PER_PLAYER = 8
MAX_WINDOWS_PER_SCENE = 24
MAX_COMMANDS_PER_SECOND = 20
MAX_TITLE_LEN = 32

# ---- 动画 ----
BASE_SPEED_PX_PER_S = 900.0
MIN_DURATION = 0.05
MAX_DURATION = 20.0
DEFAULT_EASE = 'linear'

# ---- UI ----
HUD_UI_NAME = 'windowx_hud'
HUD_UI_DEF = 'windowx_hud.main'
HUD_UI_CLS = 'windowxScripts.modClient.hudScreen.WXHudScreen'

# 低配阈值：超过则自动降级（关阴影/序列帧、降低更新频率）
DEGRADE_WINDOW_COUNT = 20
LOW_PROFILE_WINDOW_COUNT = 26

# ---- 权限族 ----
FAMILY_PLAYER = 'wx'
FAMILY_SHOW = 'wxs'
FAMILY_ADMIN = 'wxa'
SCENE_OWNER = 'world'

# ---- 开发模式（性能采集、调试日志）----
DEV_MODE = True

WINDOW_ID_PATTERN = r'^[a-z0-9_]{1,16}$'
