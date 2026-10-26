# WindowX → 网易我的世界基岩版（中国版）移植可行性、架构与发布方案

- 源项目：`WindowX 2.1.10-rc1`（NeoForge 1.21.1 / Java 21，328 个 class，无源码）
- 目标平台：网易《我的世界》中国版基岩端（ModSDK / MCStudio）
- 本机环境：`F:\Game\MCStudio\MCStudio.exe`（我的世界开发者启动器 `1.1.59.13193`）
- 结论一句话：**"窗口演出"可移植约 75%～85%，"操作系统窗口能力"可移植约 0～15%；可行，但必须换一套宿主模型——把"游戏视口"当成桌面，把"窗口"做成游戏内对象。**

---

## 0. 先说结论

| 判断 | 内容 |
|---|---|
| **是否可行** | 可行，但不是"移植"，而是**以 WindowX 的指令语义与演出参数为规范的重写**（Java → Python 2.7，OS 窗口 → 游戏内伪窗口） |
| **能 1:1 复刻的** | 指令体系、30+ 缓动、动画时间轴、窗口移动/缩放/锚点、抖动/绕圈/摇摆/呼吸、2D 物理与窗口碰撞、层叠/置顶、follow 跟随、记分板联动、指令生成器 GUI、扩展 API |
| **必须换实现的** | 摄像机画面、窗口内容（贴图/序列帧可，实时画面不可）、窗口标题栏与按钮、隐藏 HUD、GUI 镜像、窗口内交互 |
| **必须放弃的** | 真实多开 OS 窗口、DWM/分层透明/无边框、系统鼠标接管、系统通知、桌面捕获（WGC/CoreGraphics）、系统音频节拍、Iris/Sable 兼容、原生 DLL |
| **推荐产品形态** | 先做**联机大厅玩法组件（地图 + Mod）**验证演出；再升级为**网络服组件**支持多人大厅与云端数据 |
| **工期估算** | POC 2 周 → MVP 约 10 周（2～3 人）→ 完整版约 5～6 个月（3～4 人，含美术），合计 ~150 人日 + 30% 缓冲 |
| **最大风险** | 相机组件能力边界、UI 每帧刷新性能（手机端）、审核对"窗口/外链/采集"类内容的敏感度 |

---

## 1. 为什么不是"直接移植"

### 1.1 WindowX 有两层，只有一层可移植

| 层 | 内容 | 可移植性 |
|---|---|---|
| **宿主层（Host）** | GLFW 窗口句柄、`glfwSetWindowPos/Size`、DWM 透明、`UpdateLayeredWindow`、系统光标、托盘通知、WGC 桌面捕获、WASAPI 环回、Iris 管线、Sable 子世界 | **0%**。基岩端是沙箱：无 Win32/JNA、无 DLL 加载、无进程外访问、无 RTT、无多视口 |
| **表现层（Show）** | 指令树、缓动曲线、动画任务、窗口布局/层级、物理参数、特效公式、跟随、记分板协议、演出节奏 | **75%～85%**。全是纯逻辑与数学，可逐行翻译 |

### 1.2 三条硬约束（决定架构）

1. **没有"窗口"，只有"画面"**
   基岩端不能创建/移动/缩放操作系统窗口，也没有"渲染到纹理（RTT）"和"多视口"。
   → 因此「窗口」只能是 **UI 面板**（2D，叠加在游戏画面上）或 **世界内屏幕实体/方块**（3D，可被相机拍到）。
2. **Python 2.7 + 组件化沙箱**
   本机模板与官方样例全部是 Python 2.7 语法（`print "..."`、`except Exception, e`、`iteritems()`、`xrange()`），运行在 `modMain.py + modClient/modServer/modCommon` 结构里，只有 30 tick/秒的脚本节奏。
   → 需要把 Java 的 OOP 结构压平成"系统 + 组件 + 数据表"，并严格控制每帧预算。
3. **服务端权威、客户端表现**
   指令与窗口状态在服务端（可跨玩家），画面与动画在客户端；网络只有自定义事件（`NotifyToServer / NotifyToClient / BroadcastToAllClient`）。

### 1.3 核心设计洞察：把「游戏视口」当成「桌面」

这是整个移植的地基：

```
真实 WindowX：           桌面 (OS)  ── 壁纸 + 多个窗口 + 光标
基岩版等价物：      游戏视口(全屏UI) ── 世界渲染 + 多个UI伪窗口 + UI光标
```

- **壁纸** = 引擎渲染的 3D 世界（UI 层透明即可透出）
- **窗口** = 全屏 HUD 上的 UI 面板（背景九宫格 + 标题栏 + 内容槽 + 阴影/边框）
- **窗口内容** = 贴图 / 序列帧 / 文本 / 复刻的小型 UI（"实时另一个视角"做不到，见 §3）

按这个映射，WindowX 的绝大多数"演出效果"在玩家眼里几乎一致（因为它本来也是浮在桌面上的矩形），只是从"操作系统窗口"变成了"游戏内窗口"。

---

## 2. 本机环境核对（已确认）

| 项 | 结果 |
|---|---|
| MCStudio | `F:\Game\MCStudio\MCStudio.exe`，版本 `1.1.59.13193`（我的世界开发者启动器） |
| 地图/玩法模板 | `F:\Game\MCStudio\data\demo\`（`CommandTemplate`、`PresetEmptyAddonTemplate`、`AwesomeMod` 等 20+ 个） |
| 网络服插件模板 | `F:\Game\MCStudio\data\pluginTemplate\neteaseTemplate`（含 `behavior_packs / developer_mods / resource_packs / worlds`，`mod.json` 支持 `game/lobby/master/service`） |
| 官方网络服样例 | `F:\Game\MCStudio\data\apollo\awesomeOnlineGame\mods\`（AwesomeGameMod / LobbyMod / MasterMod / ServiceMod / TutorialGameMod / neteaseNpc） |
| 脚本语言 | **Python 2.7**（样例中 `print "..."`、`except Exception, e`、`iteritems`、`xrange`） |
| 脚本 SDK 位置 | 未随 MCStudio 附带（在游戏运行时内），需在 MCStudio 内首次"运行"后由启动器下载；API 细节以游戏内 `mod/` 包与官方文档为准 |
| 现有工程 | `F:\Game\MCStudio\data\demo\CommandTemplate`（含 `level.dat / world_behavior_packs.json`，适合直接做地图组件） |

> 结论：环境齐全，可以直接开工；但**相机/指令/记分板等具体方法名必须以本机下载后的 SDK 为准**，因此方案中所有不确定项都标了「需 POC」并给了回退方案（§5）。

---

## 3. 可移植性矩阵（逐模块）

评级：**A** 可 1:1 或近 1:1；**B** 需换实现但效果可近似；**C** 不可移植（给替代方案）。

### 3.1 指令与编排层

| WindowX 模块 | 基岩端实现 | 评级 |
|---|---|---|
| `/windowx <targets> move/movex/movey`（绝对/`r` 相对/`p` 百分比） | 服务端解析 + 客户端 UI 坐标换算，语法保持 | A |
| `size width/height`、`zoom`（8 锚点） | UI 面板尺寸与锚点插值（同公式） | A |
| 30+ 缓动（quad…spring/wave/jump/glitch/packetloss/step） | 纯数学，逐条翻译成 Python 表 | A |
| 动画任务 / 时长 / 速度 / 排队 | `WindowAnimator` 客户端系统，30tick 推进 | A |
| `physics`（重力/摩擦/弹性/初速度/推力/拖拽） | 2D 刚体积分器（UI 层），参数同名 | A |
| 窗口间碰撞推挤 | AABB 分离 + 推开，2D | A |
| `follow` 实体/坐标/方向/距离 | 客户端 tick 读实体位姿 → 驱动窗口位置 | A- |
| `stop` / `test` | 停止任务 / 调试窗口（UI 版） | A- |
| `get` / `score` / `displayvalue` | 窗口状态 → 记分板目标（或 ExtraData 变量） | A- |
| 指令生成器 GUI（中英双语） | 用网易 UI 做面板，逻辑同构（命令表/参数/复制到剪贴板） | A- |

### 3.2 窗口能力层

| WindowX 模块 | 基岩端实现 | 评级 |
|---|---|---|
| `minimize / maximize / fullscreen / borderless` | 折叠为标题条 / 铺满视口（"最大化"）/ 无边框皮肤 | B |
| `windowtitle set/reset` | 伪窗口标题栏文本 | B |
| `button`	启用/禁用标题栏按钮 | UI 按钮显隐与回调 | B |
| `hidehud` | 隐藏自定义 UI + 相机视角；**原生 HUD 无法完全隐藏** | B |
| 层级 `normal/always_on_top/click_through/solid` | UI 面板 z 序 + 是否拦截触摸/点击 | B |
| `mousemove / mousetransmit` | 只能操作**UI 虚拟光标**（界面打开时），不能动系统光标 | C |
| `notice`（系统通知） | 游戏内 Toast/公告/聊天气泡（自绘） | C |
| 窗口内键盘/鼠标转发 | UI 控件事件（按钮/滑动/长按） | B |
| 窗口透明/DWM/逐像素 alpha | 引擎不支持窗口级透明；只有 UI 层 alpha | C |
| 真实多开窗口 `/windowxm` | 同一屏幕上的多个伪窗口 + 世界内多个屏幕实体 | C |

### 3.3 画面与摄像机层

| WindowX 模块 | 基岩端实现 | 评级 |
|---|---|---|
| `camera` 方块/实体机位、`CameraRegistry` | 自定义方块/实体 + 机位注册表 + 相机组件（`CreateCamera`） | B（需 POC） |
| 摄像机参数：FOV / 偏移 / 渲染距离 | 相机组件 + `SetFov` 等 | B（需 POC） |
| 正交投影 `ORTHOGRAPHIC` | **引擎无正交相机** → 远距离 + 极小 FOV 视觉近似 | C→B |
| 天空/云/天气/雾 开关 | 雾可调；天空/云/天气不可单独关闭 | B |
| 摄像机画面贴到窗口/方块 | **无 RTT** → 只能「整屏视角」或「预烘焙序列帧」 | C |
| GUI/HUD 镜像到窗口 | 无 RTT → 只能复刻一套精简 HUD | C |
| Iris 光影兼容 / 隔离管线 | 不适用（基岩无此管线模型） | C |
| 桌面摄像机（WGC / GDI / CoreGraphics） | 沙箱无法访问操作系统；替代=预录序列帧或外部图片 | C |
| 桌面窗口 3D 投影 / 碰撞 / 抓取（Sable） | 不可；替代=静态"假桌面"布景（可碰撞方块/实体） | C |
| 环境覆盖层（雨雪/南瓜/望远镜/传送门/黑暗/火焰） | 主视角由引擎自带；子窗口无对应概念 | C |

### 3.4 感知与效果层

| WindowX 模块 | 基岩端实现 | 评级 |
|---|---|---|
| `rhythm` 系统音频节拍（WASAPI/Java Sound） | 无系统音频采集 → 服务端节拍时间轴 / 音符盒/唱片事件 / 玩家上传 BPM | C |
| `windowed` 药水效果（窗口随玩家状态形变） | 伪窗口尺寸/抖动 + 相机 FOV/视角形变 + 粒子，效果可近似 | B |
| 原生通知（Win/mac/Linux） | 游戏内通知 | C |
| Sable 子世界坐标/物理 | 不适用；如目标端有同类"载具/子世界"组件可做适配层 | C |

### 3.5 汇总

| 评级 | 数量（按 40 个功能点） | 占比 |
|---|---|---|
| A（近 1:1） | 10 | 25% |
| B（换实现可近似） | 14 | 35% |
| C（不可移植，需替代/砍掉） | 16 | 40% |

- **玩家可感知的演出效果**保留度：**约 80%**（窗口动、抖、绕、坠、撞、叠、跟随、标题、按钮都在）
- **底层机制**保留度：**约 15%**（真实窗口/桌面/音频全部换血）
- 因此产品定位应从"远程操控我的电脑窗口"改为 **"游戏内的窗口世界 / 屏幕演出系统"**，不要对玩家承诺"操作真实窗口"。

---

## 4. 目标架构

### 4.1 总体分层

```
┌──────────────────────────── 资源包 resource_pack ────────────────────────────┐
│ ui/  (窗口皮肤、九宫格、图标、字体)   textures/   models/   sounds/           │
└──────────────────────────────────────────────────────────────────────────────┘
┌──────────────────────────── 行为包 behavior_pack ────────────────────────────┐
│  modMain.py                                                                  │
│  windowxScripts/                                                             │
│   ├─ modCommon/  常量、缓动表、协议定义、窗口配置Schema、工具函数              │
│   ├─ modServer/  CommandSystem · WindowRegistry · SyncSystem · ScoreSystem    │
│   └─ modClient/  WindowSystem · Animator · Physics · UiBackend · ScreenBackend│
│                  CameraSystem · InputRouter · NoticeSystem · DebugSystem      │
└──────────────────────────────────────────────────────────────────────────────┘
                      ▲ 自定义事件（增量 patch / 指令 / 回执）
                      ▼
              [ 服务端权威状态 ]  ⇄  [ 客户端表现状态 + 插值 ]
```

### 4.2 工程目录（可直接照建）

```
WindowXBedrock/
├─ behavior_packs/windowxBehavior/
│  ├─ pack_manifest.json                # uuid/version/min_engine_version
│  ├─ windowxScripts/
│  │  ├─ modMain.py
│  │  ├─ modCommon/
│  │  │  ├─ modConfig.py                # 命名空间/系统名/事件名/默认参数
│  │  │  ├─ easing.py                   # 30+ 缓动（数学直译）
│  │  │  ├─ protocol.py                 # 事件名 & 数据包 schema/版本
│  │  │  ├─ windowDef.py                # WindowDef / WindowState / 序列化
│  │  │  ├─ layout.py                   # 坐标系、锚点、百分比/相对换算
│  │  │  └─ util.py                     # 时间、插值、AABB、限幅
│  │  ├─ modServer/
│  │  │  ├─ commandSystem.py            # 自定义指令注册 + 兼容语法
│  │  │  ├─ windowRegistry.py           # 每玩家窗口表 + 校验 + 配额
│  │  │  ├─ syncSystem.py               # 增量下发 / 频率控制 / 回执
│  │  │  └─ scoreSystem.py              # 记分板读写 & displayvalue
│  │  └─ modClient/
│  │     ├─ windowSystem.py             # 客户端窗口运行时（唯一真源在服务端，本地镜像）
│  │     ├─ animator.py                 # AnimationTask / Zoom / Move
│  │     ├─ physics2d.py                # 重力/摩擦/弹性/碰撞推挤/拖拽
│  │     ├─ uiBackend.py                # 伪窗口渲染后端（UI 节点池）
│  │     ├─ screenBackend.py            # 世界内屏幕后端（实体/方块 + 贴图切换）
│  │     ├─ cameraSystem.py             # 机位注册 & 相机参数应用
│  │     ├─ inputRouter.py              # 虚拟光标/拖拽/缩放/层级交互
│  │     ├─ noticeSystem.py             # 游戏内通知
│  │     └─ debugSystem.py              # 回归剧本 & 性能采样
│  ├─ entities/  items/  windowx_blocks/  # 机位方块、屏幕实体、相机物品
│  └─ netease_*_json/                     # 网易扩展定义（方块/物品/实体）
├─ resource_packs/windowxResource/
│  ├─ ui/  windowx_hud.json  windowx_generator.json  _ui_defs.json
│  ├─ textures/ui/windowx/*.png
│  ├─ textures/flipbook/                  # 序列帧图集（视频替代）
│  └─ texts/zh_CN.lang  en_US.lang
├─ worlds/windowx_demo/                   # 演示地图（联机大厅组件用）
└─ tools/                                 # 外部工具：图集打包、参数导出、单测
```

### 4.3 核心数据结构

```python
# modCommon/windowDef.py （Python 2.7 风格）
WindowDef = {
    "id": "mywin",            # 唯一 ID（服务端分配，支持 auto 编号）
    "owner": "playerUid",
    "backend": "ui",          # ui | screen  （双后端）
    "frame":   {"x": 0.5, "y": 0.5, "w": 300, "h": 200, "unit": "px", "anchor": "center"},
    "chrome":  {"title": "Window", "borderless": False, "buttons": {"min": True, "max": True, "close": True},
                "color": "black", "layer": "normal", "interactive": True, "contentLayerOrder": ["camera","web","texture","gui"]},
    "content": {"texture": None, "frames": None, "fps": 12, "mode": "fit",
                "screen": {"pos": [10, 64, 10], "facing": "north", "size": [4, 3]}},
    "anim":    [],            # 动画任务队列（move/zoom/shake/...）
    "physics": None,          # 重力/摩擦/弹性/速度
    "meta":    {"rev": 12, "dirty": ["frame"]},
}
```

- **状态唯一真源在服务端**；客户端保存镜像 + 插值，避免"各端不同步"。
- `rev` 递增 + `dirty` 字段做**增量补丁**（只发变化的字段，单包 < 200B）。

### 4.4 双渲染后端

| 后端 | 适用 | 优点 | 代价 |
|---|---|---|---|
| **UI 后端**（全屏 HUD + 面板池） | 90% 演出、指令生成器、通知、桌面式布局 | 轻量、可交互、跨端一致、支持任意动画 | UI 节点数有上限；无法被世界遮挡/被相机拍到 |
| **世界后端**（屏幕实体/方块 + 贴图/序列帧） | 世界里的公告屏、投影布、影院、多视角布景 | 有 3D 存在感、可被相机拍到、可碰撞 | 更新频率低、贴图需预打包、数量严格受限 |

- 统一抽象 `ScreenBackend` 接口：`create / destroy / setFrame / setContent / setVisible / setLayer`，由 `WindowDef.backend` 选择。
- 允许同一逻辑窗口"降级"：手机端或节点超预算时自动从 UI 后端降级为静态贴图。

### 4.5 指令层（保持 WindowX 语法）

- 优先：ModSDK 自定义指令注册（**需 POC**）。
- 回退：监听 `ServerChatEvent`，以 `/windowx` `$wx` 前缀解析（必定可用）。
- 语法兼容层（建议 v1 子集）：
  ```
  /windowx <targets> add <id> [w h] [x y]
  /windowx <targets> move <id> <x> <y> [speed] [ease]
  /windowx <targets> size <id> <w|h> <value> [speed] [ease]
  /windowx <targets> shake <id> <intensity> [dur]
  /windowx <targets> encircle <id> <rx> <ry> [speed] [ease] [deg] [dur]
  /windowx <targets> wobble <id> <ix> <iy> <speed> [cycles]
  /windowx <targets> breath <id> <intensity> <speed> [cycles]
  /windowx <targets> physics <id> <gravity> <friction> <elasticity> ...
  /windowx <targets> follow <id> <entity> [distance] [scale]
  /windowx <targets> content <id> texture|frames|text <path> [mode]
  /windowx <targets> title <id> set|reset [text]
  /windowx <targets> layer <id> normal|top|clickthrough|solid
  /windowx <targets> camera <id> bind|config|clear ...
  /windowx <targets> get <id> <prop> / score <id> <objective>
  /windowx <targets> stop <id>|all
  ```
- `move` 的 `r`/`p` 语义、锚点、缓动枚举**完全沿用**，让旧地图脚本迁移成本最低。
- 权限：**必须加**（源项目缺失）：`op` / 地图权限 / 白名单，默认只允许操作自己的窗口。

### 4.6 同步协议

| 方向 | 事件 | 频率 | 内容 |
|---|---|---|---|
| C→S | `wx:cmd` | 事件触发 | 玩家 UI 操作（拖拽结束、按钮、输入） |
| S→C | `wx:patch` | ≤ 20 Hz，合并脏字段 | 窗口增量补丁（rev 递增） |
| S→C | `wx:anim` | 事件触发 | 动画任务（起点/终点/时长/缓动/锚点） |
| S→C | `wx:full` | 登录/重连/校验失败 | 全量窗口表 |
| C→S | `wx:ack` | 事件触发 | rev 回执（用于纠偏） |

- 客户端只在 `rev` 落后时请求全量；断线重连自动重建。
- 动画在客户端本地插值（不逐帧发包），这是能在 30tick 下保持顺滑的关键。

### 4.7 摄像机子系统

- `CameraRegistry`（客户端）：`cameraId → {pos, rot, fov, offset, renderDistance}`，机位来自自定义方块/实体。
- 应用层：封装 `CameraAdapter`，唯一调用 SDK 相机组件的地方，方法缺失时降级：
  1. 完整相机（位置/朝向/FOV/雾）→ 2. 仅 `SetPlayerFov` + 视角锁定 → 3. 第三人称固定机位。
- **正交投影**用"极小 FOV + 远机位"近似；必须 POC 确认 `SetFov` 下限。
- `windowed` 效果：相机 FOV 随玩家状态微变 + UI 面板形变 + 屏幕轻微位移（伪镜头抖动）。

### 4.8 数据互通

- 记分板：优先 SDK 记分板组件；回退 `/scoreboard` 指令（`RunCommand`）。
- 持久化：世界 `ExtraData`（窗口布局）+ 玩家 `ExtraData`（个人偏好）；网络服用云端存储。
- `displayvalue`：改为服务端变量 + 下发，供 UI 文本/进度条使用。

### 4.9 扩展 API（对齐 WindowX 的 api 包）

```python
import windowx.api as wxapi
wxapi.register_extension("mymod", MyExtension())   # on_api_available(ctx)
win = wxapi.get_window(player_id, "mywin")
win.set_title("Hi").move_to(100, 200, dur=0.5, ease="quadout")
win.bind_camera("cam01", mode="fit")
```
- 内部用事件总线（`wxapi.on("window_created"/"changed"/"removed")`）实现，等价于源项目 4 个事件。

### 4.10 资源与美术

- 窗口皮肤：3 套风格（黑玻璃/白瓷/像素），九宫格切片，适配 720p～4K 与 UI 缩放。
- 字体：中文用引擎字体，避免外挂字体包（审核风险）。
- 序列帧：用于"视频替代"，建议 480×270 / 12fps / ≤ 6 秒循环，图集控制在 8MB 内。

---

## 5. 关键技术验证（POC）—— 先做这 10 项再写业务代码

| # | 验证点 | 方法 | 通过标准 | 失败回退 |
|---|---|---|---|---|
| P1 | 全屏 HUD 透出世界 | `CreateUI(isHud=1)` + 透明背景 | 面板后方能看到 3D 世界 | 退化为半透明底 + 边框强调 |
| P2 | UI 每帧改位置/尺寸 | 20 个面板 30tick 移动 | PC ≥ 55fps、手机 ≥ 30fps，脚本 < 3ms/tick | 降到 15Hz 逻辑帧 + 缓动插值 |
| P3 | UI 动态换图 | `SetSprite` 或控件显隐切图 | 切图无闪烁、内存稳定 | 预生成 N 套控件显隐 |
| P4 | 相机组件 | `CreateCamera`：位置/朝向/FOV | 可自由机位、FOV 10～110 | 仅 FOV + 固定第三人称 |
| P5 | 相机与 UI 共存 | 相机移动时 UI 稳定 | UI 不随相机抖动/位移 | UI 改世界坐标锚定 |
| P6 | 世界内屏幕 | 实体/方块 + 运行时换贴图 或 flipbook | 12fps 序列帧不卡顿 | 降为 4fps 或静态图 |
| P7 | 自定义指令 | 注册 + Tab 补全 + 权限 | 非 OP 被拒绝 | 聊天前缀解析 |
| P8 | 记分板读写 | 组件或 `/scoreboard` | 读写延迟 < 1 tick | ExtraData 变量 |
| P9 | 手机端触摸拖拽 | UI 手势事件 | 拖动跟手、无丢帧 | 改为"点击选中 + 按钮微调" |
| P10 | 双端联机同步 | 2 客户端 + 主机 | 补丁 < 200ms，无漂移 | 降低频率 + 全量纠偏 |

> P1～P3 决定 UI 后端是否成立，P4～P5 决定"摄像机"功能是否保留，P7 决定指令是否兼容。**这 6 项不通过，方案要降级为"纯 UI 演出组件"。**

---

## 6. 里程碑与工作量

| 阶段 | 内容 | 交付物 | 人日 |
|---|---|---|---|
| **M0** 可行性 | P1～P10 POC，产出《能力判定表》 | 可运行 demo 地图（1 个抖动窗口 + 1 个机位 + 1 条指令） | 12 |
| **M1** 骨架 | 工程结构、modMain、注册、协议、WindowDef、缓动库、UI 后端单窗口 | `add/move/size/zoom/stop` 可用 | 20 |
| **M2** 核心表现 | 多窗口、层级、动画任务队列、四类特效、2D 物理 + 碰撞、follow、拖拽交互 | 20 个窗口同屏稳定 | 35 |
| **M3** 屏幕与摄像机 | screenBackend、序列帧、机位方块/实体、相机适配层、windowed 效果 | 世界里能看到"屏幕" | 30 |
| **M4** 数据与扩展 | `get/score/displayvalue`、持久化、扩展 API、事件总线、指令生成器 UI | 第三方可接入 | 25 |
| **M5** 打磨发布 | 性能优化、手机适配、回归剧本、审核物料、灰度 | 上架版本 | 25 |
| 美术 | 窗口皮肤 3 套、图标、序列帧、UI 动效 | 资源包 | 15 |
| **合计** | | | **162 人日**（+30% 缓冲 ≈ 210） |

- 1 人：约 9～10 个月（不推荐）
- 2 人（程序 + 美术）：约 5 个月
- 3 人（服务端/客户端/美术）：约 3.5～4 个月

---

## 7. 测试方案

### 7.1 分层测试

| 层 | 做法 | 工具 |
|---|---|---|
| 纯逻辑（缓动/布局/物理/协议编解码） | 抽成**不依赖 SDK 的纯 Python 模块**，py2/py3 双跑单测 | pytest + tox（本机 Python 3 跑回归，py2 跑兼容） |
| 系统集成 | MCStudio 单机"运行"，逐条指令验证 | MCStudio + 日志断点 |
| 联机 | MCStudio 联机测试（2～4 客户端）、开发者平台测试服 | 网易开发者工具 |
| 演出回归 | 内置 `windowx.debug.play <scene>` 剧本：固定种子跑 10 个场景，截图/日志断言 | 自建 DebugSystem |
| 性能 | 采样 tick 耗时、UI 节点数、实体数、内存、帧率（PC/中端手机/低端手机） | 内置 Profiler + 网易性能面板 |
| 兼容 | 分辨率（720p/1080p/2K/4K）、UI 缩放 50%～150%、Android/iOS/PC、不同 SDK 小版本 | 真机矩阵 |

### 7.2 用例矩阵（示例）

1. 单窗口：`add → move → size → zoom → stop` 顺序与并发。
2. 20 窗口：同时抖动 + 绕圈，检查帧率与层级。
3. 物理：重力下落 → 底部停靠 → 拖拽甩出 → 碰撞推挤。
4. 相对坐标：`r100`、`p50`、负值、越界（应夹取而非飞出）。
5. 断线重连：窗口状态是否复原（rev 校验）。
6. 多人：A 控制 B 的窗口（权限拒绝）、B 自己操作（允许）。
7. 摄像机：绑定机位、切窗、FOV 10/110 极值。
8. 序列帧：12fps 循环 10 分钟，内存不增长。
9. 降级：手机端 30 窗口自动降级，视觉可接受。
10. 异常：非法 ID、未注册机位、超配额、畸形包（不得崩溃）。

### 7.3 质量门槛（发布前必须满足）

- 崩溃率 < 0.1%；进入地图 60 秒内无脚本报错。
- 中端手机（骁龙 7 系）：20 窗口场景 ≥ 30fps；PC ≥ 60fps。
- 客户端脚本单帧 ≤ 3ms（P95），单帧网络包 ≤ 2KB。
- 断线重连后窗口 100% 复原；连续运行 60 分钟内存增长 < 10%。
- 所有指令有权限校验与错误提示，不出现静默失败。

---

## 8. 发布方案

### 8.1 三种形态

| 形态 | 适用 | 优点 | 限制 | 建议 |
|---|---|---|---|---|
| **联机大厅玩法组件（地图 + Mod）** | 演出/整活/小游戏 | 客户端能力全、开箱即玩、审核快 | 依赖地图、无跨局数据 | **首发形态** |
| **玩法组件（Addon）** | 服务器/存档通用 | 可被任意地图引用 | 纯客户端表现有限制 | 第二阶段 |
| **网络服组件**（`developer_mods` + `mod.json`，`support_server_type: game/lobby`） | 多人大厅、云端存档、活动 | 可做服务端权威 + 数据持久化 | 需运维、审核更严 | 第三阶段 |

### 8.2 发布流程

```
开发(M0~M5) → 内部自测(测试清单+回归剧本) → 提审(组件/地图)
   → 审核反馈修正 → 小范围灰度(白名单/测试服, 1~2 周)
   → 数据观测(帧率/崩溃/留存/差评关键词) → 全量发布 → 版本迭代
```

- **审核合规要点**：不得含外链与站外引流；不得收集个人信息；素材需自有版权（**WindowX 的图标/贴图不可直接商用，需重绘并取得授权**）；不得含"修改客户端/注入/加速"等表述；未成年人保护与内容分级。
- **命名与法务**：建议另起中文名（如《窗口世界》《WindowX·方块版》需授权），指令前缀保留 `windowx` 需原作者许可；算法与参数可参考，代码必须重写（源项目无源码，本就只能重写）。
- **热更与回滚**：脚本与资源走组件版本更新（无需玩家更新客户端）；保留上一稳定包，异常时下架回滚；服务端加开关 `windowx.enable=false` 一键停用表现层。
- **监控埋点**：启动成功率、场景加载耗时、平均帧率、指令调用量 Top10、异常堆栈上报（网易日志/自建 HTTP 上报）。

### 8.3 上线节奏

| 版本 | 内容 | 周期 |
|---|---|---|
| v0.1 内测 | 单/多窗口 + 动画 + 指令 | M1～M2 后 |
| v0.5 灰度 | 加物理、摄像机、屏幕后端 | M3 后 |
| v1.0 上架 | 加生成器 UI、扩展 API、性能达标 | M5 后 |
| v1.x | 节拍时间轴、更多皮肤、地图模板 | 持续 |

---

## 9. 风险登记表

| # | 风险 | 影响 | 概率 | 应对 |
|---|---|---|---|---|
| R1 | 相机组件能力不足（无法自由机位/正交） | 摄像机模块缩水 | 中 | M0 先验；降级为 FOV+固定机位；文案不承诺"自由摄像机" |
| R2 | UI 每帧刷新在手机端掉帧 | 核心体验受损 | 中高 | 逻辑 15Hz + 插值；节点池复用；超限自动降级；提供"低配模式" |
| R3 | 无 RTT 导致"窗口里看另一个画面"落空 | 与源项目预期落差 | 高 | 产品定位改为"窗口演出"；用序列帧/多客户端联机做近似 |
| R4 | Python 2.7 可维护性差 | 迭代变慢 | 中 | 纯逻辑与 SDK 隔离、单测覆盖、代码规范、适配层收口 |
| R5 | SDK 小版本 API 漂移 | 线上故障 | 中 | 所有 SDK 调用集中到 `adapters/`，启动自检 + 特性开关 |
| R6 | 审核（外链/隐私/素材） | 无法上架 | 中 | 不上传/不采集；素材重绘；提前预审咨询 |
| R7 | 多人同步带宽/延迟 | 抖动、错位 | 中 | 增量补丁 + 客户端插值 + 20Hz 上限 + rev 纠偏 |
| R8 | 玩家预期错位（以为能操纵真窗口） | 差评 | 中 | 商店页明确"游戏内窗口演出"；教程引导 |

---

## 10. 明确放弃清单（不做，避免无效投入）

1. 真实操作系统窗口的移动/缩放/置顶/透明/无边框。
2. 多开真实窗口（`/windowxm` 的 OS 语义）。
3. 桌面捕获与投屏（WGC/GDI/CoreGraphics）、桌面窗口 3D 投影与抓取。
4. 系统级通知、系统鼠标接管。
5. 系统音频采集与节拍检测（改为预置时间轴）。
6. Iris 光影管线隔离、Sable 子世界物理。
7. 实时画面 RTT（摄像机画面贴到窗口/方块）。
8. 原生 DLL / 平台特化代码。

---

## 11. 下一步 72 小时行动清单

1. **在 MCStudio 新建工程**：用 `data\demo\CommandTemplate` 复制一份，改名 `WindowXBedrock`，改 `pack_manifest.json` 的 uuid/version。
2. **跑通 P1/P2/P3**：做一个全屏 HUD + 3 个可移动面板 + 一个按钮，脚本 30tick 改变位置，记录帧率与 tick 耗时（PC + 一台安卓真机）。
3. **跑通 P4/P6**：用 `CreateCamera` 做固定机位；用自定义实体 + `SetTexture` 做 4fps 序列帧屏幕。
4. **跑通 P7**：注册一条 `windowx` 指令（失败则用聊天前缀），验证权限与 Tab 补全。
5. **产出《能力判定表 v1》**：把 §5 的 10 项填成 通过/降级/否决，据此把 §3 矩阵里所有 B 项重新定级，冻结 v1 范围。
6. **决策会**：按判定表决定 v1 是否保留摄像机与屏幕后端，然后进入 M1。

---

## 12. 附：源项目 → 目标模块映射速查

| 源类（WindowX） | 目标模块 |
|---|---|
| `command/WindowXCommand`、`WindowXMCommand` | `modServer/commandSystem.py` |
| `client/WindowAnimator`、`AnimationTask`、`EaseFunctions` | `modClient/animator.py` + `modCommon/easing.py` |
| `client/GLFWWindowHelper` | `modClient/uiBackend.py`（UI 面板） / `screenBackend.py`（3D） |
| `client/multiwindow/CustomWindow`、`MultiWindowManager` | `modClient/windowSystem.py` + `uiBackend.py` |
| `client/multiwindow/GuiHudMirrorManager` | 放弃（改为 HUD 复刻控件） |
| `client/NoticeOverlay` | `modClient/noticeSystem.py` |
| `client/WindowedEffectController`、`RhythmEffectController` | `modClient/effects/`（状态驱动 + 时间轴） |
| `camera/CameraRegistry`、`CameraRenderManager` | `modClient/cameraSystem.py` + `CameraAdapter` |
| `desktop/DesktopCameraServer`、`client/DesktopCameraCapture` | 放弃（保留"假桌面布景"美术方案） |
| `network/*Payload`（60+） | `modCommon/protocol.py`（收敛为 5 个事件） |
| `api/WindowXApi`、`WindowController` | `windowxScripts/windowxApi/`（对外 SDK） |
| `mixin/*` | 无对应（引擎行为不可注入） |
