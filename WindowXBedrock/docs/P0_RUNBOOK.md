# P0 运行手册（MCStudio 实机验证）

> 目标：用最少步骤跑出 v2.1 P0 的五项结论。
> 前置：本地已通过 `python tools/run_tests.py`（47 项）。

---

## 1. 工程结构

```
WindowXBedrock/
├─ behavior_packs/windowxBehavior/
│  ├─ manifest.json              # 若引擎只认 pack_manifest.json，复制改名
│  ├─ netease_commands/*.json    # 28 条，三权限族（生成物，勿手改）
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
python gen_commands.py            # 28 个指令 JSON
python gen_textures.py            # 5 张占位贴图
python gen_ui.py --windows 24     # UI 槽位（L1=3 / L2=10 / L3=20 / L4=30）
python run_tests.py               # 47 项回归
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
