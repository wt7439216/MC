# G0：源项目功能清单（328 class → 四分类）

> 目的：把"移植范围"钉死成可验收的条目，而不是一句"覆盖率"。
> 分类：**交付**（有公开 API，实测通过即算）/ **降级**（近似实现，文档标注）/ **研究**（无接口，不排期）/ **不做**（明确放弃）。

## 1. 包级分布

| 包 | class 数 | 说明 |
|---|---|---|
| `client` | 78 | 主窗口动画/物理、GLFW、通知、音频、桌面捕获 |
| `network` | 68 | 60+ 自定义 payload + 双端 handler |
| `desktop` | 44 | 桌面摄像机（方块/实体/会话/几何/网络） |
| `camera` | 30 | 机位注册、离屏渲染、纹理同步、Iris 兼容 |
| `client/generator` | 25 | 指令生成器 GUI（含 20 个内部类） |
| `client/multiwindow` | 25 | 真实多开窗口、DWM/分层 alpha、HUD 镜像、覆盖层 |
| `api/window` | 20 | 对外窗口 API（Controller/Options/Snapshot…） |
| `mixin` | 9 | 窗口/相机/GUI/雾/天空注入 |
| `api/internal` | 7 | API 实现（ClientWindowImpl / ServerWindowControllerImpl…） |
| `api` | 5 | Api/Extension/Event 入口 |
| `compat` | 5 | Sable 子世界 |
| `api/event` | 4 | 4 个事件 |
| `command` | 4 | `/windowx` `/windowxm` |
| `effect` | 2 | `windowed` / `rhythm` 药水效果 |
| `(root)` | 2 | `WindowX` / `WindowXConfig` |
| **合计** | **328** | |

## 2. 功能 → 分类 → 落点

| 源功能（代表类） | 分类 | 目标实现 |
|---|---|---|
| `/windowx` `/windowxm` 指令树（`command/*`） | **交付** | `netease_commands/` 29 条（三权限族，零变体，含 `wxresync`） |
| 30+ 缓动（`client/EaseFunctions`） | **交付** | `modCommon/easing.py`（已实现 50 条，含端点保证） |
| 动画任务（`WindowAnimator`/`AnimationTask`） | **交付** | `modCommon/animator_core.py` + 客户端 tick |
| 2D 物理与碰撞（`ph*` 字段） | **交付** | `modCommon/physics2d.py`（重力/摩擦/弹性/拖拽甩出） |
| 窗口移动/缩放/锚点（`GLFWWindowHelper` 一半） | **交付** | `layout.py` + `hudBackend`（`SetFullPosition/SetFullSize`） |
| 抖动/绕圈/摇摆/呼吸 | **交付** | `animator_core` 的 fx 采样 |
| 层级/置顶/点击穿透 | **降级** | `SetLayer` + 界面级 `SetIsSwallow`（逐窗口穿透不可实现） |
| 最小化/最大化/无边框/标题 | **降级** | 折叠为标题条 / 铺满视口 / 自绘标题栏 |
| 隐藏 HUD | **降级** | 隐藏自绘 UI；原生 HUD 无法完全关闭 |
| 系统光标接管 | **不做**（Core） | UI 虚拟光标；Companion 才做真实光标 |
| 系统通知（`NoticeOverlay`） | **降级** | 游戏内 toast（自绘） |
| 记分板联动（`scoreCmd`） | **交付** | `dispatch_core._act_score` + `SetCommand` 写分 |
| 指令生成器（`generator/*`） | **降级** | P3 用自定义 UI 重做（当前 P0 不做） |
| 真实多开窗口（`multiwindow/*`） | **不做**（Core）/ **交付**（Companion） | Core 用同屏多伪窗口；Companion 用 Win32 真窗口 |
| 窗口内网页（`WindowWebContent`/MCEF） | **不做**（Core）/ **交付**（Companion） | Companion 用 WebView2 |
| HUD 镜像（`GuiHudMirrorManager`） | **不做** | 无 RTT，只能复刻精简 HUD |
| 环境覆盖层（雨雪/南瓜/望远镜/传送门/黑暗/火焰） | **不做** | 子窗口概念不存在 |
| 摄像机机位（`CameraBlock/Entity/Registry`） | **交付** | `cameraAdapter` + `commands`（P3 补方块/实体） |
| 摄像机运动（`CameraRenderManager` 一半） | **交付** | `CreateCamera` 全家桶 + `cameraMath` |
| 正交投影（`CameraProjection.ORTHOGRAPHIC`） | **研究** | 引擎无正交相机；仅"远机位+30°"技巧 |
| 多机位离屏渲染（`CameraTexture/RenderManager`） | **研究** | 无 RTT/多视口 |
| 摄像机画面贴窗口/方块 | **研究** | 同上 |
| Iris 光影兼容（`ShaderCompatibility`） | **不做** | 基岩无此管线模型 |
| 桌面摄像机（`desktop/*` 全部 44 类） | **不做**（Core）/ **研究**（Companion 采集端可做） | 游戏内无 RTT，投屏无意义 |
| 系统音频律动（`WindowsWasapiLoopback`/`RhythmSoundMonitor`） | **不做**（Core）/ **交付**（Companion） | Core 用预置节拍时间轴替代 |
| `windowed` 药水效果（窗口形变） | **降级** | 伪窗口尺寸/抖动 + FOV 变化 |
| `network/*` 60+ payload | **降级** | 收敛为 5 个事件（patch/full/ack/cmd/debug） |
| `api/*` 扩展接口 | **降级** | Python 版 `windowxApi`（P3） |
| `mixin/*` | **不做** | 基岩不可注入 |
| `compat/Sable*` | **不做** | 无对应生态 |
| `assets/data`（方块/物品/模型/掉落） | **重制** | 资源包自绘；不复用原作者 PNG |

## 3. 与 P0 的关系

P0 只要求"能证明风险"的最小集：

- ✅ 指令三族（29 条 JSON 已生成，权限/归属逻辑已单测）
- ✅ 缓动/动画/物理/布局/协议（纯逻辑已实现并 112 项测试通过，含 SDK Mock）
- ✅ 摄像机坐标与守卫（`cameraMath`/`CameraGuard` 已实现，待实机校准）
- ⏳ UI 后端与性能（代码就绪，等 MCStudio 实机跑 L1–L4）
- ✅ G0 授权与来源（见 `LICENSE_SOURCE_REPORT.md`）
- ⏳ B0（见 `BRIDGE_B0_REPORT.md`，已有官方能力证据，待平台问询）

P1 起才补：多窗口层级细节、跟随、生成器 UI、机位方块/红石、多人同步配额。
