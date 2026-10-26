# WindowX → 网易我的世界基岩版（移植研究 + P0 工程）

本仓库包含两部分：

1. **原始 Mod 功能分析**：对 NeoForge 版 `WindowX 2.1.10-rc1`（328 个 class）的静态分析结论；
2. **移植方案与 P0 工程骨架**：面向网易《我的世界》中国版（ModSDK / MCStudio）的重写实现，采用 Core + Companion 双产品路线。

> 原始 Mod 的 `.class` / 资源 / DLL **不包含在本仓库**（见 `.gitignore` 与 `NOTICE.md`）。
> 本仓库代码为独立重写，仅在行为与参数层面参考原项目。

## 文档

| 文件 | 内容 |
|---|---|
| `WindowX-功能分析.md` | 原始 Mod 的包结构、指令树、渲染/捕获/音频等模块分析 |
| `WindowX-基岩版移植方案.md` | 初版方案（UI 伪窗口 + 视口即桌面） |
| `WindowX-基岩版移植方案-v2.md` | 双产品（Core + Companion）+ 门禁计划 |
| `WindowX-基岩版移植方案-v2.1.md` | 技术验证版：修正权限族、UI 性能分级、相机边界、Bridge 前置 |
| `WindowXBedrock/docs/` | G0 授权核查、B0 Bridge 核查、运行手册、性能记录模板 |

## 工程（`WindowXBedrock/`）

```
behavior_packs/windowxBehavior/
  netease_commands/           28 条自定义指令（wx* / wxs* / wxa* 三权限族，零参数变体）
  windowxScripts/
    modMain.py
    modCommon/                纯逻辑内核（无 SDK 依赖，可本地单测）
    modServer/                自定义指令事件适配、限流、增量下发
    modClient/                HUD 后端、动画/物理、相机适配与守卫、性能采集
resource_packs/windowxResource/
  ui/windowx_hud.json         可生成 N 个窗口槽位的 HUD
  textures/ui/windowx/*.png   生成的占位贴图
tools/                        指令/UI/贴图生成器 + 单测
```

### 快速开始

```powershell
cd WindowXBedrock/tools
python gen_commands.py          # 28 个 netease_commands
python gen_textures.py          # 占位 UI 贴图
python gen_ui.py --windows 24   # 生成 HUD（L1=3 / L2=10 / L3=20 / L4=30）
python run_tests.py             # 纯逻辑回归（47 项）
```

实机验证步骤见 `WindowXBedrock/docs/P0_RUNBOOK.md`。

### 设计约束（来自官方文档核实）

- 指令：`netease_commands/*.json`，`permission_level` 仅 `game_directors` 允许命令方块执行；
- UI：`SetAlpha` 仅对 image/label 生效；`SetIsSwallow`（点击穿透）为界面级；`Update` 约 30fps；
- 相机：`SetFov` 范围 [30,110]，`SetCameraRotation` 为 (Pitch,Yaw,Roll) 且与 F3 相反；无正交投影；
- 渲染：无 RTT / 多视口，实时多机位画面不可实现。

## 状态

| 项 | 状态 |
|---|---|
| G0 授权与来源核查 | 有条件通过（详见 docs） |
| 指令三族 + 权限矩阵 | 已完成（含单测） |
| 缓动 / 布局 / 物理 / 协议 | 已完成（47 项测试通过） |
| 摄像机坐标与复原守卫 | 代码完成，待实机校准 |
| UI L1–L4 性能 | 脚手架就绪，待 MCStudio 实机采集 |
| Bridge（游戏 ↔ 桌面程序） | 待平台书面确认；默认不立项 |

## 许可与来源

本仓库自有代码可自由参考。原项目 WindowX（作者 XuTrain）声明为 MIT（jar 内）/ Apache-2.0（Modrinth 页面），
本仓库不复制其任何代码与美术资源。详见 `NOTICE.md`。
