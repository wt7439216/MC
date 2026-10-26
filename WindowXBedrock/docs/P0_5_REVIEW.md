# P0.5 修复评审（代码 + 本地测试）

> 版本：P0.5 ｜ 日期：2026-10-26 ｜ 基线：commit `805a316`
> 范围：只做 P0.5 的 9 项修复，**不进 P1**。
> **重要**：本文所有"通过"均指**本地静态检查 + 单元/ Mock 集成测试**通过；
> **未做 MCStudio 实机验证**，因此不构成"实机通过"。

---

## 0. 摘要与门禁

| # | 需求 | 状态 | 证据 |
|---|---|---|---|
| 1 | 事件 `args=list(dict)` / `origin=dict` 解析，区分玩家/管理员/命令方块 | ✅ 代码+测试 | `test_command_event` 14 项 / `test_sdk_integration` 16 项 |
| 2 | HUD 走 `GetBaseUIControl` 对象层级 + `AddTouchEventParams`/`SetButtonTouch*`；关键错误不静默 | ✅ 代码+测试 | `test_hud_layer` 16 项 |
| 3 | `OnScriptTickClient` 事件名；UI 槽位与运行时一致 | ✅ 代码+测试 | 样例 `modConfig.py` 核对；槽位改为运行时探测 |
| 4 | 客户端请求视为不可信；禁用状态写入；禁止跨 owner 伪造 | ✅ 代码+测试 | `test_client_write_rejected` / `test_ack_ignored` |
| 5 | 管理员真实权限、跨玩家补丁目标、复合键、rev/FULL 重同步 | ✅ 代码+测试 | `test_rev_registry` 8 项 / `test_sdk_integration` |
| 6 | 相机卸载/异常恢复 + 失败注入，失败不伪装成功 | ✅ 代码+测试 | `test_camera_recovery` 11 项 |
| 7 | G0 结论修订；B0 冻结、不采用未授权绕过 | ✅ 文档 | `LICENSE_SOURCE_REPORT.md` / `BRIDGE_B0_REPORT.md` / `OFFICIAL_FACTS.md` |
| 8 | 静态检查 + 回归 + Mock 集成测试，记录真实命令/数量/输出 | ✅ 已执行 | 见 §3 |
| 9 | 输出本文件；生成器仍为唯一数据源 | ✅ | `gen_commands.py` → 29 JSON + `command_index.py` |

**门禁结论**

- **代码门禁（PASS）**：静态检查 0 问题；112 项测试全绿；编译器全通过。
- **实机门禁（NOT RUN）**：`docs/P0_RUNBOOK.md` §11 的 V1–V10 尚未执行。
- **平台门禁（FROZEN）**：B0 待平台书面答复，Bridge 不实现。

---

## 1. 逐文件变更

| 文件 | 变更 | 原因 |
|---|---|---|
| `modCommon/command_event.py` **新增** | `normalize_args`（list(dict)/dict）、`normalize_origin`、`parse_event`、`split_command`、`actor_from_origin`、`write_back_failure` | 官方事件是 `args=list(dict)`、`origin=dict`；不能 `args.get()`；命令方块无 `entityId` |
| `modCommon/command_index.py` **新增（生成物）** | `COMMANDS = {name: (family, action)}` | 前缀匹配会把 `wxscore/wxshake/wxsize/wxstop` 误判为 `wxs*`（实测 bug），改为显式索引 |
| `modCommon/rev_store.py` **新增** | 按 owner 的 rev：`current/next/set/reset/needs_full` | 支持跨 owner 独立版本与"缺口"判定 |
| `modCommon/modConfig.py` | 新增 `EV_TICK_CLIENT/SERVER`、`EV_CMD_TRIGGER`、`EV_ADD_PLAYER`、`HUD_SLOTS`、`HUD_SLOT_PROBE_LIMIT`、`ALLOW_CLIENT_WRITES=False`、`RETURN_MSG_ENABLED=False`、`ADMIN_UIDS` | 事件名集中管理；安全开关默认关闭；槽位单一数据源 |
| `modServer/serverSystem.py` **重写** | 用 `parse_event` 解析；`origin.entityId` 查 `GetPlayerAbilities().op`；失败写 `return_failed`；按 owner 分组发补丁；`OnPlayerJoin` 发 FULL（p1 + world）；`wxresync`；`OnClientCmd/OnAck` 一律拒绝/忽略 | 事件形态、权限、跨玩家路由、不可信客户端 |
| `modServer/permissions_service.py` **新增** | `is_admin`（GetPlayerAbilities → 白名单 → False）、`resolve_player`、`player_ids` | 管理员真实判定，fail-closed |
| `modClient/clientSystem.py` **重写** | tick 改 `OnScriptTickClient`；`(owner,id)` 复合键；按 owner 的 rev + 缺口标记；`EV_TOAST`；拖拽仅本地；`shutdown()`；相机失败上报 | 事件名错误、id 冲突、rev 语义、安全边界 |
| `modClient/hudBackend.py` **重写** | `GetBaseUIControl(path)` + `asPanel/asImage/asLabel/asButton`；每个槽位 5 个控件对象；错误列表 + 关键失败标记；不再静默吞异常 | 官方是"控件对象"而非 path 调用；`SetAlpha` 仅 image/label |
| `modClient/hudScreen.py` **重写** | 槽位探测；`AddTouchEventParams()` + 四个 `SetButtonTouch*Callback`；触摸回调转发；错误上报 | 官方触摸流程；避免 24 固定值 |
| `modClient/cameraAdapter.py` **重写** | 失败账本 `failures`；`_call` 统一捕获；`restore()` 返回 `{ok,attempted,failed}`；`set_fov/set_transform` 返回 bool | 失败可观测、不伪装成功 |
| `modClient/cameraGuard.py` | `enter/exit` 返回真实结果；`exit` 必尝试全部恢复；快照失败 → 结论必为失败 | 异常路径恢复 |
| `modMain.py` | `DestroyClient` 调 `shutdown()`（归还相机/槽位） | 卸载恢复 |
| `tools/gen_commands.py` | 新增 `wxresync`；允许空 `args`；生成 `command_index.py` | 重同步入口 + 消除前缀歧义 |
| `tools/gen_ui.py` | 默认读 `modConfig.HUD_SLOTS`；`--windows` 仅用于分级测试并给出警告；范围校验 | 与运行时一致 |
| `tools/tests/sdkmock.py` **新增** | SDK Mock：Server/ClientSystem、组件工厂、`GetPlayerAbilities`、Camera/PlayerView、`ScreenNode` + 控件 + 触摸登记、失败注入 | 无实机条件下的集成测试 |
| `tools/tests/test_command_event.py` **新增** | 14 项 | 事件解析 |
| `tools/tests/test_sdk_integration.py` **新增** | 16 项 | 服务端链路/权限/路由/安全 |
| `tools/tests/test_hud_layer.py` **新增** | 16 项 | HUD 层级/触摸/复合键 |
| `tools/tests/test_camera_recovery.py` **新增** | 11 项 | 相机失败注入 |
| `tools/tests/test_rev_registry.py` **新增** | 8 项 | rev 与复合键 |
| `docs/OFFICIAL_FACTS.md` **新增** | 官方事实清单（带来源） | 所有"按官方"说法的锚点 |
| `docs/LICENSE_SOURCE_REPORT.md` | 修订 G0 结论：类名包含 ≠ 字节码/来源已证明 | 防止过度推断 |
| `docs/BRIDGE_B0_REPORT.md` | 剪贴板路径改为**否决**；B0 冻结；禁止任何绕过 | 合规 |
| `docs/P0_RUNBOOK.md` | 前置 112 项；29 指令；新增 §11 实机验证 V1–V10 | 实机门禁 |
| `README.md` / `SOURCE_INVENTORY.md` | 数量与状态同步 | 一致性 |

---

## 2. 关键实现说明

### 2.1 事件解析（需求 1）

```python
ev = command_event.parse_event(raw)
# raw: {'command': 'wxmove', 'args': [{'name':'id','type':'str','value':'w1'}],
#       'variant': 0, 'origin': {'entityId': 'p1', 'dimension': 0, 'blockPos': (0,64,0)}}
# ev['args'] -> {'id': 'w1'}
# ev['origin']['is_command_block'] -> False
```
- `args` 为 `dict` 时也兼容（旧样例/自定义调用）。
- 失败：`raw['return_failed'] = True`；`return_msg_key` 默认不写（避免 lang 键缺失误导）。

### 2.2 权限（需求 1/5）

| 来源 | actor.kind | 可执行族 |
|---|---|---|
| `origin.entityId` 且 `GetPlayerAbilities().op == True` | `admin` | `wx` / `wxs` / `wxa` |
| `origin.entityId` 且非 op | `player` | 仅 `wx`（且仅本人窗口） |
| 无 `entityId`（命令方块） | `command_block` | 仅 `wxs`（仅 `owner=world`） |
| 权限查不到（API 异常） | 按 player | 拒绝 `wxa`（fail-closed） |

### 2.3 补丁路由（需求 5）

`_deliver` 先按 `op['owner']` 分组，再对每个 owner 单独 `rev=next(owner)` 并发送：
- `owner == world` → `BroadcastToAllClient`
- 否则 → `NotifyToClient(owner)`

因此管理员 `wxakill p1` 的删除补丁发给 **p1**，不会误改管理员自己的状态。

### 2.4 不可信客户端（需求 4）

- `OnClientCmd`：**永不写状态**（`ALLOW_CLIENT_WRITES=False` 且即便为 True 也因无可信身份拒绝），只记录一次 warn。
- `OnAck`：忽略，不触发 FULL（否则可被用于探测他人窗口）。
- 重同步仅两条可信路径：玩家加入（引擎事件）/ `wxresync` 指令（引擎给 origin）。

### 2.5 UI 层级（需求 2）

```
ScreenNode.GetBaseUIControl('/win0')      -> asPanel()
ScreenNode.GetBaseUIControl('/win0/bg')   -> asImage()  -> SetAlpha/SetSprite
ScreenNode.GetBaseUIControl('/win0/title')-> asLabel()  -> SetText
ScreenNode.GetBaseUIControl('/win0/bar_drag')-> asButton()
    -> AddTouchEventParams()
    -> SetButtonTouchDownCallback / Move / Up / Cancel
```
- 任一环节返回 `None` 或抛异常 → `errors` + `logger.error`，该槽位不分配；全部失败 → `available=False`。
- **不**用 `ScreenNode.SetVisible(path,...)` 之类的路径式便捷方法作为主路径（仅作历史兼容）。

### 2.6 槽位一致性（需求 3）

- `gen_ui.py` 默认 `modConfig.HUD_SLOTS`；
- `hudScreen.Create()` 调 `_detect_slots()`，按 `/win0..N` 实际存在数量决定运行时槽位；
- 生成数量与常量不同只 warn，不再造成越界/失配。

---

## 3. 实际执行命令与输出

```powershell
PS> cd WindowXBedrock
PS> ruff check --select E9,F --target-version py39 --output-format concise .
All checks passed!

PS> python -c "import compileall; print('OK' if compileall.compile_dir('.', quiet=1, force=True) else 'FAIL')"
OK

PS> cd tools
PS> python gen_commands.py
[OK] schema valid: 29 commands (18 wx / 7 wxs / 4 wxa)
[OK] wrote 29 files -> ...\netease_commands
[OK] command index -> ...\modCommon\command_index.py

PS> python run_tests.py
Ran 112 tests in 0.010s
OK
```

> 说明：`ruff` 仅做语法/未定义名/未使用变量类检查（`E9,F`），不代表运行时正确；
> 上述 `OK` 来自 **Mock 环境**，不是 MCStudio。

---

## 4. 测试明细（112）

| 文件 | 数量 | 覆盖 |
|---|---|---|
| `test_command_event.py` | 14 | list(dict)/dict 归一化、origin 三类、变体容错、前缀冲突回归 |
| `test_commands_schema.py` | 7 | 29 条 schema、权限映射、无变体、默认值靠后、文件名规则 |
| `test_core_logic.py` | 19 | 缓动端点/单调、坐标解析、锚点缩放、相机数学、协议 |
| `test_permissions_dispatch.py` | 21 | 三族权限矩阵、创建/移动/缩放/特效/内容/层级/标题、配额、场景族 |
| `test_rev_registry.py` | 8 | rev 单调/needs_full、同 id 不同 owner、场景配额、管理族 owner 标记 |
| `test_sdk_integration.py` | 16 | 真实事件形态、管理员 op、命令方块、return_failed、补丁路由、拒绝客户端写、FULL、限流 |
| `test_hud_layer.py` | 16 | 控件层级、缺失/类型不符报错、触摸注册、槽位探测、复合键、rev 缺口 |
| `test_camera_recovery.py` | 11 | 方法失败注入、CreateCamera 失败、restore 结果、快照失败、异常不外泄、关服恢复 |

---

## 5. 剩余风险

| 级别 | 风险 | 说明 / 缓解 |
|---|---|---|
| **高** | 事件真实字段可能随版本变化 | 已按官方核对，但仍需 V1 打印一次真实 `args`；解析层容错 list/dict，未知指令直接忽略 |
| **高** | `GetPlayerAbilities()` 在联机房间/命令方块场景的可用性 | 失败即 fail-closed；必要时改用服务器命令白名单（需平台确认） |
| **中** | UI 触摸回调参数名（`TouchPos`/`ButtonState`）可能不同 | 回调里做了多键兜底；V7 验证 |
| **中** | `AddTouchEventParams()` 是否接受空参 | 先空参、失败再传 `{'isSwallow': True}`；V7 验证 |
| **中** | 拖拽仅本地（不同步服务端） | 明确取舍：无可信身份前不写服务端；P1 需设计"拖动结束由服务端校验后落库"的可信路径 |
| **中** | `SetIsSwallow` 为界面级，逐窗口点击穿透未实现 | 已标注为 P1；当前用 `SetTouchEnable` 做降级 |
| **低** | Mock 与真实引擎行为差异 | Mock 只覆盖契约，不覆盖渲染/网络时序；以 V1–V10 为准 |
| **低** | 29 条指令的 Tab 补全与参数提示 | 需实机确认 `str` + description 的提示效果 |

---

## 6. MCStudio 最小实机步骤（门禁）

前置：`docs/P0_RUNBOOK.md` §2 导入 pack，进图看到 `[WX] HUD backend bound: N/N slots`。

| # | 操作 | 期望 | 结果 |
|---|---|---|---|
| V1 | 打印一次 `repr(args)` 后触发任意指令 | 字段与 `OFFICIAL_FACTS.md` §1 一致 | ☐ |
| V2 | 普通玩家 `/wxcreate a 120 80`；再 `/wxastop all` | 前者成功，后者被拒 | ☐ |
| V3 | op 玩家 `/wxalist all` | 正常列出 | ☐ |
| V4 | 命令方块触发 `wxscreate scene1` | 成功，owner=world，广播 | ☐ |
| V5 | 客户端侧改坐标（临时脚本） | 日志出现"拒绝客户端写请求" | ☐ |
| V6 | 断线重连 | 收到 2 个 `wx:full`，窗口复原 | ☐ |
| V7 | 删掉一个 `/winN/bar_drag` | 日志 error；该槽位不可拖；其余正常 | ☐ |
| V8 | `set_camera(fov=5)` | 钳到 30，不崩 | ☐ |
| V9 | 切维度/退出世界 | 视角/FOV/透视全复原 | ☐ |
| V10 | 故意改错 `SetFov` 名 | `set_camera` 返回 False，日志 error | ☐ |

总耗时预估：**30–45 分钟**（不含首次下载 SDK/引擎）。

---

## 7. 门禁判定

| 门禁 | 判定 | 说明 |
|---|---|---|
| G-P0.5-A 代码正确性 | **PASS** | ruff / compileall / 112 项测试通过 |
| G-P0.5-B 安全边界 | **PASS（代码级）** | 客户端写全拒绝、跨 owner 伪造无效、ACK 不触发 FULL |
| G-P0.5-C 事件兼容 | **PASS（按文档）** / **待 V1** | 已按官方字段实现，实机仍需打印确认 |
| G-P0.5-D UI 可用 | **待 V7** | 控件层级/触摸已按官方文档实现，Mock 通过 |
| G-P0.5-E 相机恢复 | **待 V8–V10** | 失败注入测试通过，实机未验 |
| G-P0.5-F 来源与授权 | **CONDITIONAL** | 类名包含只证明"同源可能"，授权未闭环 → clean-room |
| G-P0.5-G Bridge | **FROZEN** | 无官方通道；剪贴板等绕过已否决 |

---

## 8. 明确未做（防止误读）

1. 未在 MCStudio/真机运行过任何一条指令；未截取实机日志。
2. 未实现拖拽的服务端落库（因无可信身份）。
3. 未实现逐窗口点击穿透（界面级限制，P1）。
4. 未实现机位方块/实体、红石、生成器 UI、多人同步配额（P1 范围）。
5. 未做任何 Bridge/桌面程序相关代码。
