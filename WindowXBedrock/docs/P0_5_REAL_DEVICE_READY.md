# P0.5 实机测试准备（REAL-DEVICE READY）

> 日期：2026-10-26 ｜ 基线：`main@0587d35` 之后的 P0.5b
> **状态声明**：本轮只做"上机前的准备与修复"。
> 下表中 **Mock = 本地 SDK 模拟**；**实机 = MCStudio 真实客户端**。
> **实机测试一项都还没跑**，因此本文不包含任何"实机通过"的结论。

---

## 0. 本轮 6 项修复与证据

| # | 问题 | 修复 | 证据（Mock 测试） |
|---|---|---|---|
| 1 | `hudScreen.Create()` **先 attach 系统、后探测槽位**，导致 backend 按默认 24 绑定 | 改为 **探测 → attach → 注册触摸**；`clientSystem.attach_hud` 使用 `node.slots` | `test_hud_layer.FullLifecycleTest.test_create_detects_before_attach`、`test_detect_slots_matches_ui` |
| 2 | `CameraGuard.enter()` 快照失败仍 `depart()`，修改了相机状态 | 快照失败 → **直接返回 False、不 depart、不 set**；depart 失败 → 回滚快照 | `test_snapshot_failure_does_not_touch_camera`、`test_depart_failure_rolls_back` |
| 3 | `wxresync` 未校验真实玩家身份（命令方块也可触发） | 必须有 `origin.entityId` **且**在当前在线列表；否则 `return_failed` | `test_resync_rejected_for_command_block`、`test_resync_rejected_for_unknown_entity` |
| 4 | V5 只写"客户端改位置"，无法主动构造越权请求 | 新增 `clientSystem.debug_send_unauthorized_write()`（仅 `DEV_MODE`），主动发 `EV_CMD` | `test_debug_unauthorized_write_is_emitted` + 服务端 `test_client_write_rejected` |
| 5 | V1 需打印完整 `repr(args)`，会泄露身份/坐标 | 新增开关 `modConfig.DEBUG_LOG_COMMAND_EVENT` + `command_event.describe_event()`（id 打码、不输出坐标） | `test_debug_log_masks_identity`、`describe_event` 两项 |
| 6 | V1–V10 步骤过粗 | `P0_RUNBOOK.md §11` 重写：操作 / 日志关键词 / 预期 / 失败处理 | —（文档） |

> 另外保持：**Bridge 冻结**；未新增任何外部通信代码。

---

## 1. 本轮逐文件变更

| 文件 | 变更 |
|---|---|
| `modClient/hudScreen.py` | `Create()` 顺序改为 探测 → attach → 绑定触摸 |
| `modClient/cameraGuard.py` | 重写 `enter()`：快照失败不改状态；depart 失败回滚；`exit()` 报告 `enter_failed` |
| `modServer/serverSystem.py` | `wxresync` 增加玩家身份 + 在线校验；`OnCustomCommand` 增加脱敏调试日志 |
| `modCommon/command_event.py` | 新增 `describe_event()`（id 打码、不输出 blockPos） |
| `modCommon/modConfig.py` | 新增 `DEBUG_LOG_COMMAND_EVENT = False` |
| `modClient/clientSystem.py` | 新增 `debug_send_unauthorized_write()`（仅 DEV_MODE） |
| `tools/tests/test_hud_layer.py` | +4 项：完整生命周期（探测顺序/Update/卸载/调试写） |
| `tools/tests/test_camera_recovery.py` | +2 项：快照失败不 depart；depart 失败回滚 |
| `tools/tests/test_sdk_integration.py` | +3 项：resync 两种拒绝 + 调试日志脱敏 |
| `tools/tests/test_command_event.py` | +2 项：`describe_event` 脱敏与类型模式 |
| `docs/P0_RUNBOOK.md` | §11 重写为 V1–V10 细化版 |

---

## 2. 实际执行（本地，非实机）

```powershell
PS> cd WindowXBedrock
PS> ruff check --select E9,F --target-version py39 --output-format concise .
All checks passed!

PS> python -c "import compileall; print('OK' if compileall.compile_dir('.', quiet=1, force=True) else 'FAIL')"
OK

PS> cd tools
PS> python run_tests.py
Ran 123 tests in 0.009s
OK
```

测试分布（123）：

| 文件 | 数量 |
|---|---|
| `test_camera_recovery.py` | 13 |
| `test_command_event.py` | 16 |
| `test_commands_schema.py` | 7 |
| `test_core_logic.py` | 19 |
| `test_hud_layer.py` | 20 |
| `test_permissions_dispatch.py` | 21 |
| `test_rev_registry.py` | 8 |
| `test_sdk_integration.py` | 19 |

> 这些数字来自 **Python 3.13 + 自建 Mock**；游戏内是 Python 2.7 运行时。
> 语法按 py2 兼容编写（无 f-string / 类型注解），但**未在 py2 解释器下执行**。

---

## 3. 剩余风险

| 级别 | 风险 | 说明 | 处理 |
|---|---|---|---|
| 高 | 事件字段/权限 API 与实机不一致 | 已按官方文档实现，Mock 只验证契约 | V1/V3 实测；失败则改 `command_event` / `permissions_service` |
| 高 | `AddTouchEventParams()` 空参是否被接受 | 已做 `TypeError` 回退 | V7 实测 |
| 中 | 触摸回调字段名（`TouchPos`/`ButtonState`） | 做了多键兜底 | V7 实测 |
| 中 | UI 槽位探测依赖 `/winN` 命名 | 生成器与运行时一致 | V7（删一个槽位）验证 |
| 中 | 相机 API 可用性/键名 | 失败可观测，不会伪装成功 | V8–V10 |
| 中 | Python 2.7 运行时差异 | 未在 py2 下跑 | 首次进图看日志是否有语法/导入错误 |
| 低 | 拖拽不同步服务端 | 明确取舍（无可信身份） | P1 再设计 |
| 低 | 逐窗口点击穿透未实现 | `SetIsSwallow` 界面级 | P1 |

---

## 4. MC Studio 导入方式

### 4.1 方式 A（推荐：在 Studio 生成的工程里覆盖）

1. `创作 → 新建 → 基岩版组件/地图`，类型选带 Python 脚本的模板；记下它生成的
   `behavior_packs/<BP>` 与 `resource_packs/<RP>` 目录名与 `manifest.json` 的 uuid。
2. 复制本工程到对应位置：
   - `WindowXBedrock/behavior_packs/windowxBehavior/netease_commands/` → `<BP>/netease_commands/`
   - `WindowXBedrock/behavior_packs/windowxBehavior/windowxScripts/` → `<BP>/windowxScripts/`
   - `WindowXBedrock/resource_packs/windowxResource/ui/` → `<RP>/ui/`
   - `WindowXBedrock/resource_packs/windowxResource/textures/ui/windowx/` → `<RP>/textures/ui/windowx/`
3. **保留 Studio 的 `manifest.json`**（uuid 用它的）；若 Studio 用 `pack_manifest.json`，以它为准。
4. 修改路径引用（如目录名不是 `windowxScripts`）：
   - `modConfig.SERVER_SYSTEM_CLS` / `CLIENT_SYSTEM_CLS`
   - 所有 `from windowxScripts...` 前缀
   - `modMain.py` 的 import

### 4.2 方式 B（直接放进地图）

1. 把两个 pack 复制到地图的 `behavior_packs/`、`resource_packs/`；
2. 在 `world_behavior_packs.json` / `world_resource_packs.json` 登记 `pack_id` 与 `version`；
3. 参考 `F:\Game\MCStudio\data\demo\CommandTemplate` 的结构。

### 4.3 进图自检（30 秒）

| 期望日志 | 含义 |
|---|---|
| `[WX] HUD backend bound: N/N slots, errors=0` | UI 绑定成功 |
| `[WX] HUD Create: slots=N touch_ready=N errors=0` | 槽位探测 + 触摸注册成功 |
| `/wx` 有 Tab 补全 | `netease_commands` 被识别 |
| `[WX-PERF] frames=...` | 逐帧采集在跑 |

若 `CreateUI failed`：检查 `HUD_UI_DEF='windowx_hud.main'` 与 `ui/_ui_defs.json` 登记。

---

## 5. V1–V10 操作清单（详细版见 `P0_RUNBOOK.md §11`）

| # | 一句话操作 | 关键日志 / 观察点 | 失败处理 |
|---|---|---|---|
| V1 | 开 `DEBUG_LOG_COMMAND_EVENT`，玩家/命令方块各跑一次 `wxcreate` | `[WX-DEV] ... has_entity=True/False`，id 打码、无坐标 | 字段不符 → 对照 `OFFICIAL_FACTS.md` |
| V2 | 普通玩家 `wxcreate` / `wxastop` | 后者 `cmd failed ...（wxa）` | 检查 `permission_level` |
| V3 | op 前后各跑 `wxalist all` | 结果相反 | 打印 `GetPlayerAbilities()` |
| V4 | 命令方块 `wxscreate s1` | owner=world，全员可见 | 查 `game_directors` |
| V5 | 临时调用 `debug_send_unauthorized_write()` | `拒绝客户端写请求 EV_CMD`；`/wxget` 值不变 | 状态变化 → 立即停测 |
| V6 | 退出重进 | 两次 `wx:full`，窗口复原 | 查 `AddServerPlayerEvent` 键名 |
| V7 | 删一个 `bar_drag` 后重进 | `hud api error ...`，其余正常 | 查 `_error` 是否被调用 |
| V8 | `set_camera(..., fov=5)` | 不崩，FOV≥30 | 查相机组件创建 |
| V9 | 退出/切维度/断线/卸载 | 无 `camera recovery incomplete` | 按 `failed` 列表定位 |
| V10 | 临时把 `SetFov` 改名 | `camera apply failed`，返回 False | 返回 True → 修 `_call` |

### 结果记录（实机填写；未跑请写 `NOT RUN`）

| # | 结果（PASS / FAIL / NOT RUN） | 现象/日志摘要 | 日期 | 设备/版本 |
|---|---|---|---|---|
| V1 | NOT RUN | | | |
| V2 | NOT RUN | | | |
| V3 | NOT RUN | | | |
| V4 | NOT RUN | | | |
| V5 | NOT RUN | | | |
| V6 | NOT RUN | | | |
| V7 | NOT RUN | | | |
| V8 | NOT RUN | | | |
| V9 | NOT RUN | | | |
| V10 | NOT RUN | | | |

---

## 6. 门禁

| 门禁 | 状态 | 依据 |
|---|---|---|
| 代码静态检查 | **PASS** | `ruff E9,F` 无问题；`compileall` OK |
| 本地回归 + Mock 集成 | **PASS（123 项）** | 见 §2 |
| 实机 V1–V10 | **NOT RUN** | 本文不含实机结论 |
| 来源与授权（G0） | **CONDITIONAL** | 类名包含 ≠ 字节码/官方来源；clean-room |
| Bridge（B0） | **FROZEN** | 无官方通道；剪贴板等绕过已否决 |

**进入 P1 的条件**：V1–V10 至少 V1–V6 通过（V7–V10 可带缺陷但需记录），且无高危安全项失败。
在此之前不启动 P1、不启动 Companion S2。

---

## 7. 明确不做

1. 未执行任何 MCStudio/真机测试；本文没有实机截图或日志。
2. 未实现 Bridge / Companion / 桌面捕获 / 音频。
3. 未做逐窗口点击穿透、拖拽服务端落库、机位方块与红石（P1）。
4. 未在 Python 2.7 解释器下运行测试（仅按 py2 语法编写）。
