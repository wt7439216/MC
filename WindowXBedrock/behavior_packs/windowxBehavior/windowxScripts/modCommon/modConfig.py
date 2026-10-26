# -*- coding: utf-8 -*-
"""全局配置（纯常量，不 import SDK，便于本地单测）。"""

MOD_NAME = 'windowx'
SERVER_SYSTEM = 'wxServerSystem'
CLIENT_SYSTEM = 'wxClientSystem'

SERVER_SYSTEM_CLS = 'windowxScripts.modServer.serverSystem.WXServerSystem'
CLIENT_SYSTEM_CLS = 'windowxScripts.modClient.clientSystem.WXClientSystem'

# ---- 事件名（服务端 <-> 客户端）----
EV_CMD = 'wx:cmd'          # C->S 玩家交互（当前不可信，默认禁用）
EV_PATCH = 'wx:patch'      # S->C 增量补丁
EV_FULL = 'wx:full'        # S->C 全量窗口表
EV_ACK = 'wx:ack'          # C->S rev 回执（当前不可信，仅记录）
EV_TOAST = 'wx:toast'      # S->C 提示（客户端记录/显示）
EV_DEBUG = 'wx:debug'      # S->C 调试开关

# ---- 引擎事件名（必须与官方一致，见 docs/OFFICIAL_FACTS.md）----
EV_TICK_CLIENT = 'OnScriptTickClient'
EV_TICK_SERVER = 'OnScriptTickServer'
EV_CMD_TRIGGER = 'CustomCommandTriggerServerEvent'
EV_ADD_PLAYER = 'AddServerPlayerEvent'
EV_CHAT = 'ServerChatEvent'
EV_UI_INIT = 'UiInitFinished'
EV_DIM_CHANGE_CLIENT = 'DimensionChangeFinishClientEvent'
EV_LOAD_FINISH_CLIENT = 'OnLocalPlayerStopLoading'

# ---- 虚拟画布（UI 坐标系）----
VIEW_W = 1920.0
VIEW_H = 1080.0

# ---- 配额与限流 ----
MAX_WINDOWS_PER_PLAYER = 8
MAX_WINDOWS_PER_SCENE = 24
MAX_COMMANDS_PER_SECOND = 20
MAX_TITLE_LEN = 32
MAX_CMD_NAME_LEN = 32

# ---- 动画 ----
BASE_SPEED_PX_PER_S = 900.0
MIN_DURATION = 0.05
MAX_DURATION = 20.0
DEFAULT_EASE = 'linear'

# ---- UI ----
HUD_UI_NAME = 'windowx_hud'
HUD_UI_DEF = 'windowx_hud.main'
HUD_UI_CLS = 'windowxScripts.modClient.hudScreen.WXHudScreen'
# 唯一数据源：gen_ui.py 默认从这里读槽位数；运行时按实际控件探测（见 hudScreen），
# 因此 L1–L4 用不同 --windows 生成也不会与运行时失配。
HUD_SLOTS = 24
HUD_SLOT_PROBE_LIMIT = 64

# 低配阈值：超过则自动降级（关阴影/序列帧、降低更新频率）
DEGRADE_WINDOW_COUNT = 20
LOW_PROFILE_WINDOW_COUNT = 26

# ---- 权限族 ----
FAMILY_PLAYER = 'wx'
FAMILY_SHOW = 'wxs'
FAMILY_ADMIN = 'wxa'
SCENE_OWNER = 'world'

# ---- 安全开关 ----
# 客户端事件（NotifyToServer）目前无法取得可信发送者身份，
# 因此禁止其写服务端状态；置 True 仅用于本地实验。
ALLOW_CLIENT_WRITES = False
# 未取得平台确认前，不用 return_msg_key 回显（避免 lang 键缺失导致误导）
RETURN_MSG_ENABLED = False
# 管理员兜底白名单（GetPlayerAbilities 不可用时的 fail-closed 之后的补充）
ADMIN_UIDS = frozenset()

# ---- 开发模式（性能采集、调试日志）----
DEV_MODE = True

WINDOW_ID_PATTERN = r'^[a-z0-9_]{1,16}$'
