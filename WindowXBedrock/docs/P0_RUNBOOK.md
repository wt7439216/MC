# P0 / P0.5 运行手册（MCStudio 实机验证）

> 目标：用最少步骤跑出 v2.1 P0 的五项结论，并验证 P0.5 的修复。
> 前置：本地已通过 `python tools/run_tests.py`（112 项，含 SDK Mock）。
> **Mock 通过 ≠ 实机通过**：本手册的步骤才是实机门禁。

---

## 1. 工程结构

```
WindowXBedrock/
├─ behavior_packs/windowxBehavior/
│  ├─ manifest.json              # 若引擎只认 pack_manifest.json，复制改名
│  ├─ netease_commands/*.json    # 29 条，三权限族（生成物，勿手改）
│  └─ windowxScripts/            # modMain.py + modCommon/modServer/modClient
├─ resource_packs/windowxResource/
│  ├─ manifest.json
│  ├─ ui/windowx_hud.json        # 生成物（gen_ui.py）
│  ├─ ui/_ui_defs.json
│  └─ textures/ui/windowx/*.png  # 生成物（gen_textures.py）
└─ tools/                        # 生成器 + 单测（不进包）
```

重新生成：

```powershell
cd WindowXBedrock/tools
python gen_commands.py            # 29 个指令 JSON + command_index.py
python gen_textures.py            # 5 张占位贴图
python gen_ui.py                  # 默认 modConfig.HUD_SLOTS=24
python gen_ui.py --windows 20     # 分级测试用；运行时按实际控件探测槽位
python run_tests.py               # 112 项（纯逻辑 + SDK Mock）
```

## 2. 导入 MCStudio

**方式 A（推荐）**：`创作 → 新建基岩版组件/地图` → 让它生成 `behavior_packs/<xxx>` 与 `resource_packs/<xxx>` → 用本工程的
`netease_commands/`、`windowxScripts/`、`ui/`、`textures/ui/windowx/` 覆盖对应目录 → 合并 `manifest.json`（保留 Studio 生成的 uuid，改用它的）。

**方式 B**：直接把本工程的两个 pack 复制进地图的 `behavior_packs/`、`resource_packs/`，并在 `world_behavior_packs.json` / `world_resource_packs.json`
里登记 uuid（参考 `F:\Game\MCStudio\data\demo\CommandTemplate`）。

**必查 3 点**

1. `modMain.py` 必须位于 `<behavior_pack>/windowxScripts/` 下，且 `windowxScripts/__init__.py` 存在；
2. 若引擎不加载脚本，把目录改名为 `<pack名>Script`（样例用 `awesomeScripts`），同时把 `modConfig.SERVER_SYSTEM_CLS` / `CLIENT_SYSTEM_CLS`
   和所有 `from windowxScripts...` 的包名前缀同步替换；
3. `manifest.json` 与 `pack_manifest.json` 命名以当前 Studio 为准（两者内容一致，只是文件名差异）。

## 3. 启动自检（进图后 30 秒看日志）

| 期望日志 | 说明 |
|---|---|
| `[WX] HUD attached, slots=24` | UI 创建成功、后端绑定成功 |
| 无 `CreateUI failed` | 注册/路径正确 |
| 输入 `/wxcreate` 有 Tab 补全 | `netease_commands` 被识别 |
| `[WX-PERF] ...` 每 150 帧一行 | 逐帧采集在跑 |

## 4. S1：伪窗口验证（约 30 分钟）

```
/wxcreate w1 240 140 p50 p50 测试窗口
/wxmove   w1 p25 p40 2 quadout
/wxzoom   w1 400 240 1.5 backout center
/wxshake  w1 12 0.8
/wxencircle w1 80 40 1.5 360
/wxwobble w1 6 6 1 3
/wxbreath w1 0.08 0.5 3
/wxcontent w1 texture textures/ui/windowx/bg fit
/wxlayer  w1 top
/wxtitle  w1 set 你好
/wxphysics w1 1200 0.12 0.5 p30 p10
/wxget    w1 x
/wxscore  w1 wxobj
/wxstop   w1
/wxremove w1
```

**通过标准**

- 窗口出现、位置/尺寸与预期一致（`p50` = 屏幕中心）；
- 拖拽标题栏跟手，松开后位置保留；
- 6 类动效肉眼可辨、结束回到目标位（无残留偏移）；
- `wxlayer top` 后压住其他窗口；
- `wxremove` 后 UI 槽位释放（再创建不叠加）。

**若失败**：看 `backend.missing`（`hudBackend._call` 会记录缺失的方法名）→ 到日志里搜索缺了哪个 SDK 方法，按官方文档换名或降级。

## 5. L1–L4 性能（S1 的后半段）

1. `python gen_ui.py --windows N`（N=3/10/20/30），重启客户端；
2. 管理员身份先放宽配额：`/wxaquota <你的名字> 40`；
3. 依次创建 N 个窗口并让其中一半持续 `wxshake`；
4. 每档稳定 60 秒，抄 `[WX-PERF]` 日志到 `docs/UI_PERF_TEMPLATE.md`；
5. 删除到 10 个窗口，观察是否回落（降级可恢复）。

## 6. 相机 POC（S3，约 40 分钟）

目的：验证"坐标转换 + 复原守卫"，不是验证正交。

```
1) 找一处平地，记录 F3 的 yaw/pitch；
2) 用调试入口（当前 P0 未开放指令，可在 clientSystem 里临时调用）
   self.set_camera((x, y+2, z), pitch=0, yaw=0, fov=70)
3) 对照：游戏里看到的方向是否与预期一致（若左右/上下相反，说明符号需翻）；
4) 依次改 fov = 30 / 110 / 5（越界）观察钳制；
5) 退出世界、切换维度、断线重连，各测一次视角是否复原。
```

**通过标准**

- 8 个方向（N/S/E/W + 4 斜角）朝向正确；
- `SetFov(5)` 不崩溃（被钳到 30）；
- 任一退出路径后，视角/FOV/视角模式全部复原。

**若朝向相反**：只改 `camera_math.to_native_rotation` 的符号，不改调用点；改完跑 `test_core_logic.py`。

## 7. 指令三族权限（约 20 分钟）

| 场景 | 操作 | 期望 |
|---|---|---|
| 普通玩家 | `/wxcreate a 100 60` | 成功，且只影响自己 |
| 普通玩家 | 尝试 `/wxastop` | 无补全/被拒 |
| 管理员 | `/wxalist all` | 列出各玩家窗口 |
| 命令方块 | `/wxscreate scene1 200 120` + 红石触发 | 成功，窗口 owner=world |
| 命令方块 | `/wxmove scene1 ...`（错用玩家族） | 失败（owner 不匹配） |
| 玩家 | `/wxs…` | 无权限 |

## 8. S2：Companion 最小验证（独立进行）

1. `dotnet new wpf` → 手选窗口（EnumWindows + 排除自身）→ 记录 rect/style 快照；
2. `Move / Resize / Shake / Stop / Restore`；
3. 关闭游戏后点"恢复"，确认不误操作新进程；
4. 记录：目标窗口 rect 前后是否完全一致（可用 `GetWindowRect` 打印比对）。

通过标准：rect/style 100% 复原；句柄失效时不报错、不误伤。

## 9. 结果回填

| 产出 | 文件 |
|---|---|
| UI 性能 | `docs/UI_PERF_TEMPLATE.md` |
| 相机 | 在本文 §6 下补一段"实测结论 + 符号修正" |
| 指令权限 | 在本文 §7 表格补"实测"列 |
| 授权 | `docs/LICENSE_SOURCE_REPORT.md`（已出结论，待作者确认） |
| Bridge | `docs/BRIDGE_B0_REPORT.md`（已出证据，待平台答复） |

## 10. 常见问题

| 现象 | 排查 |
|---|---|
| UI 完全不显示 | `CreateUI` 参数顺序 `(mod, uiName, pyClsPath, screenDef)`；`screenDef` 必须是 `windowx_hud.main` |
| 窗口是黑块 | 贴图路径 `textures/ui/windowx/xxx` 是否打进资源包；`_ui_defs.json` 是否登记 |
| 窗口位置偏 | 检查 `layout.to_ui_offset` 的百分比换算与 `anchor_from/to=center` 是否一致 |
| 调 `SetAlpha` 无效 | 只对 image/label 生效；panel/button 不行（皮肤必须 image 化） |
| 点击穿透整屏失效 | `SetIsSwallow` 是**界面级**，需分两个 HUD 界面（P1 处理） |
| 指令没反应 | 看 `CustomCommandTriggerServerEvent` 的 `args` 键名，用日志打印一次真实结构再对齐 |
| 相机复原不了 | 检查是否监听了 `DimensionChangeFinishClientEvent` 与退出事件；`CameraGuard.exit()` 是否被调用 |

---

## 11. V1–V10 实机验证（细化版，替代旧表）

> 全部默认玩家名为 `Tester`、窗口 id 为 `w1`；命令方块位于 `(10, 64, 10)`。
> 每项结束记录到 `docs/P0_5_REAL_DEVICE_READY.md` §5 的结果表。
> **未执行的项一律记 `NOT RUN`，不得写"通过"。**

### V1 事件结构（可开关、脱敏）

- 操作：把 `modConfig.DEBUG_LOG_COMMAND_EVENT` 改为 `True`，分别用**玩家**与**命令方块**各触发一次 `wxcreate`；随后改回 `False`。
- 日志关键词：`[WX-DEV] command=wxcreate variant=0 args=[id:str,...] origin=*** dim=0 has_entity=True`
- 预期：字段名/类型正确；`origin` 打码（`前3位+***` 或 `<none>`）；**不出现完整 entityId、不出现坐标**。
- 失败处理：字段缺失 → 对照 `docs/OFFICIAL_FACTS.md` §1；若出现身份/坐标 → 立即关开关并修 `describe_event`。
- 注意：命令方块那次应为 `has_entity=False`、`origin=<none>`。

### V2 玩家族权限

- 操作：普通玩家 `/wxcreate a 120 80`；再 `/wxastop all`。
- 日志关键词：成功时 `[WX]` 无 error；被拒时 `[WX] cmd failed: 当前身份无权使用该指令（wxa）`。
- 预期：前者创建成功且只影响自己；后者在 Tab 不出现或被拒（`return_failed` 红色提示）。
- 失败处理：玩家能执行 `wxa*` → 检查 `permission_level` 是否被误设 `any`，以及 `permissions.can_run`。

### V3 管理员真实权限

- 操作：给 `Tester` op 后 `/wxalist all`；再取消 op 重复一次。
- 日志关键词：op 时无 `cmd failed`；取消后出现 `[WX] cmd failed: 当前身份无权使用该指令（wxa）`。
- 预期：两次结果相反，说明 `GetPlayerAbilities().op` 生效。
- 失败处理：op 仍被拒 → 打印一次 `GetPlayerAbilities()` 返回值核对键名；若该 API 不可用，记录并改用 `ADMIN_UIDS` 临时白名单（仅测试服）。

### V4 命令方块（演出族）

- 操作：命令方块执行 `wxscreate s1 240 140`；红石块触发一次。
- 日志关键词：无 `cmd failed`；客户端 `[WX] toast` 不发给实体（无 entityId）。
- 预期：窗口 owner=`world`，所有客户端都看到；玩家 `/wxs…` 仍被拒。
- 失败处理：失败先查 JSON `permission_level` 是否为 `game_directors`；再查命令名是否在 `command_index.py`。

### V5 未授权客户端写入（主动构造）

- 准备：先用 `/wxcreate w1 200 120`，再 `/wxget w1 x` 记录当前 X。
- 操作：在 `hudScreen.Create()` 末尾**临时**加一行（验证后删除）：
  ```python
  self.system.debug_send_unauthorized_write('<另一个玩家id或自己>', 'w1')
  ```
- 日志关键词：服务端出现 `拒绝客户端写请求 EV_CMD`（只打印一次）；客户端出现 `DEBUG EV_CMD sent, expect server reject`。
- 预期：服务端窗口状态**不变**（再 `/wxget w1 x` 与记录一致）；无新补丁下发。
- 失败处理：若 X 改变或出现补丁 → 安全边界失效，立即停止实机并回滚 `ALLOW_CLIENT_WRITES` 相关改动。

### V6 断线重连 / FULL

- 操作：创建 2 个窗口后退出世界并重进。
- 日志关键词：客户端 `[WX] HUD backend bound`；服务端发送两次 `wx:full`（`owner=Tester` 与 `owner=world`）。
- 预期：窗口按 rev 复原；无需手动 `/wxresync`。
- 失败处理：未收到 → 检查 `AddServerPlayerEvent` 的 id 键名（`id/playerId/entityId` 三种已兼容）；仍失败可手动 `/wxresync` 兜底并记录。

### V7 HUD 关键错误不静默

- 操作：把 `resource_packs/.../ui/windowx_hud.json` 中 `win2/bar_drag` 删掉，重进。
- 日志关键词：`[WX] hud api error /win2/bar_drag ...`、`[WX] HUD Create: slots=24 touch_ready=23 errors=N`。
- 预期：其余窗口正常；该槽位不可拖；不崩溃。
- 失败处理：无任何错误日志 → `hudScreen._error` 未生效（检查是否走了兼容分支）。

### V8 FOV 钳制

- 操作：`self.set_camera((x,y,z), 0, 0, fov=5)`。
- 日志关键词：无 error。
- 预期：不崩溃；实际 FOV ≥ 30（可用 F3/调试读出）。
- 失败处理：崩溃 → 相机组件调用方式有误；FOV 仍为 5 → 钳制未生效。

### V9 相机复原（多路径）

- 操作：依次测试：退出世界、切换维度、断线重连、`shutdown()`（卸载组件）。
- 日志关键词：**不应**出现 `[WX] camera recovery incomplete` / `camera restore incomplete`。
- 预期：视角、FOV、第一/第三人称、锁定状态全部恢复。
- 失败处理：出现 incomplete → 按 `failed` 列表定位缺失方法；若 `snapshot` 失败，说明 `GetFov` 等不可用。

### V10 失败不得伪装成功

- 操作：把 `cameraAdapter.set_fov` 内的 `'SetFov'` 临时改成 `'SetFovX'`。
- 日志关键词：`[WX] camera api SetFovX failed: method missing`、`[WX] camera apply failed`。
- 预期：`set_camera` 返回 `False`；guard 退出；不留下"已应用"的假象。
- 失败处理：返回 True → 失败被吞，必须修 `_call`。
- 收尾：改回 `'SetFov'` 并重跑 `run_tests.py`。
