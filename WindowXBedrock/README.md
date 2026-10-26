# WindowX Bedrock（P0 骨架）

把 NeoForge 版 WindowX 的**表现与指令语义**移植到网易《我的世界》基岩版中国版。
方案见上级目录 `WindowX-基岩版移植方案-v2.1.md`。

> 当前阶段：**P0 风险验证**。纯逻辑已可在本地回归；SDK 相关部分需在 MCStudio 实机跑（见 `docs/P0_RUNBOOK.md`）。

## 快速开始

```powershell
cd tools
python gen_commands.py          # 生成 28 个 netease_commands（三权限族，零变体）
python gen_textures.py          # 生成 5 张占位 UI 贴图
python gen_ui.py --windows 24   # 生成 HUD（L1=3 / L2=10 / L3=20 / L4=30）
python run_tests.py             # 47 项纯逻辑回归
```

## 目录

```
behavior_packs/windowxBehavior/
  manifest.json
  netease_commands/            28 条自定义指令（wx* / wxs* / wxa*）
  windowxScripts/
    modMain.py
    modCommon/                 纯逻辑（无 SDK 依赖，可单测）
      modConfig.py  easing.py  layout.py  window_def.py
      permissions.py  registry_core.py  dispatch_core.py
      animator_core.py  physics2d.py  camera_math.py  protocol.py
    modServer/serverSystem.py  事件适配：CustomCommandTriggerServerEvent / 聊天兜底 / 限流 / 下发
    modClient/
      clientSystem.py          补丁应用 + 插值 + 物理 + 相机守卫
      hudScreen.py  hudBackend.py  HUD 控件池与每帧同步
      cameraAdapter.py  cameraGuard.py  debugSuite.py
resource_packs/windowxResource/
  manifest.json  ui/windowx_hud.json  ui/_ui_defs.json
  textures/ui/windowx/*.png
tools/                         生成器 + 单测（不进包）
docs/                          G0 报告 / B0 报告 / 运行手册 / 性能模板
```

## 设计要点（与方案 v2.1 对齐）

- **一动作一命令**：28 个 JSON 只用 `args`，不启用 `args1..args9`，零解析歧义。
- **三权限族**：`wx*`=`any`（仅本人窗口）、`wxs*`=`game_directors`（命令方块/红石，操作 world 窗口）、`wxa*`=`admin`（跨玩家）；服务端 `permissions.py` 二次校验。
- **服务端权威 + 客户端插值**：服务端只存意图，客户端按动画任务本地插值（30fps），增量包 ≤20Hz。
- **UI 后端**：每窗口 6 控件（bg/shadow/content/title/bar_drag/…），`SetAlpha` 仅对 image/label，皮肤全 image 化；点击穿透按界面分层（P1）。
- **相机**：`cameraMath` 显式处理"与 F3 相反 + (Pitch,Yaw,Roll)"；`CameraGuard` 保证任何退出路径复原；正交/RTT 明确不做。

## P0 状态

| 项 | 状态 | 证据 / 阻塞 |
|---|---|---|
| G0 授权与来源 | ✅ 有条件通过 | `docs/LICENSE_SOURCE_REPORT.md`（本地是公开 2.1.9 的严格超集；许可证上游不一致；默认 clean-room） |
| 指令三族 | ✅ 代码+单测完成 | 28 文件生成、权限矩阵 12 组合单测通过 |
| 缓动/布局/物理/协议 | ✅ 代码+单测完成 | 47 项 `unittest` 全绿 |
| 摄像机 | 🟡 代码+数学单测完成 | 需实机校准符号（`docs/P0_RUNBOOK.md` §6） |
| UI 分级性能 | 🟡 脚手架就绪 | 需 MCStudio 跑 L1–L4，回填 `docs/UI_PERF_TEMPLATE.md` |
| B0 Bridge | 🟡 证据已收集 | `docs/BRIDGE_B0_REPORT.md`：本机直连无 API；仅"云中继/剪贴板"两条路，待平台书面确认 |

## 已知限制

1. **不能**操作真实窗口、无多视口/RTT → 这些归 Companion 或不做。
2. `SetFov` 只有 30–110，正交投影不可实现（仅"远机位+窄视场"技巧）。
3. `SetBindWorldPosition` 是**界面级**：一个界面只能锚一个世界坐标。
4. Python 2.7 语法：本工程 `modCommon` 已按 py2 兼容写法（无 f-string/类型注解/`yield from`）。

## 下一步（P1）

- 多窗口层级 + 双 HUD 界面（点击穿透）；
- follow/物理与拖拽的服务端回写；
- 机位方块/实体 + 红石触发；
- 多人同步配额与审计；
- Companion MVP（手选窗口 → 移动/震动 → 一键恢复）。
