# WindowX 2.1.10-rc1（NeoForge 1.21.1）功能分析

> 分析对象：`c:/Users/90809/Desktop/MC/windowx-2.1.10-rc1-1.21.1-NeoForge`
> 该目录是**解包后的 Mod jar**，只包含 `.class` 与资源文件，没有 Java 源码。以下结论来自 `neoforge.mods.toml`、类结构、字段/方法签名、常量池字符串与 `mixins` 配置的静态分析。

---

## 一、项目性质

| 项 | 内容 |
|---|---|
| 类型 | Minecraft **客户端表现层** Mod（NeoForge 1.21.1） |
| Mod ID | `windowx`（`META-INF/neoforge.mods.toml` 内声明版本 `1.0.4`，与目录名 `2.1.10-rc1` 不一致） |
| 依赖 | NeoForge `21.1.234+`、Minecraft `1.21.1`；可选 `mcef`（网页）、`sable`（子世界物理） |
| 规模 | 328 个 class，约 11 个功能包；自带 native `windowx/native/windowx_wgc.dll`、内嵌 `sable-companion-1.6.0.jar` |
| 官方描述 | “Remote control your Minecraft client window via commands!”——通过指令远程操控客户端窗口 |

一句话概括：**把 Minecraft 的窗口（包括额外开出的窗口、摄像头画面、甚至真实桌面）当作物件，用服务端指令 + 数据包在客户端做实时动画、物理、多窗口与投屏。**

---

## 二、包结构总览

| 包 | 职责 |
|---|---|
| `command` | `/windowx`、`/windowxm` 两套指令树、窗口 ID 参数类型、相对坐标解析 |
| `network` | 60+ 种自定义 payload（S→C 控制、C→S 状态回传、摄像机同步） |
| `client` | 主窗口动画/物理、GLFW 操作、原生通知、音频律动、桌面捕获、UI 覆盖层 |
| `client.multiwindow` | 真实多开窗口（GLFW 子窗口、DWM/分层 alpha、HUD 镜像、环境覆盖层） |
| `client.generator` | 游戏内指令生成器 GUI（中英双语） |
| `camera` | 摄像机锚点方块/实体、离屏渲染到纹理、Iris 光影兼容 |
| `desktop` | 把“真实桌面”投射进世界的方块/实体/服务端会话 |
| `api` | 面向其他 Mod 的公开 API（窗口对象、控制器、事件、扩展点） |
| `compat` | Sable 子世界坐标与物理兼容 |
| `effect` | 两个 MobEffect：`windowed`、`rhythm` |
| `mixin` | 9 个注入点（窗口访问器、GUI 捕获、摄像机天空/云/雾、Iris 地平线等） |

---

## 三、核心功能模块

### 1. `/windowx`：主窗口远程控制

服务端指令，目标是玩家选择器（可控制**其他玩家**的客户端窗口）。

| 指令 | 功能 |
|---|---|
| `transmit` / `move` / `movex` / `movey` | 移动窗口；坐标支持绝对、`r` 相对、`p` 百分比；可配速度与缓动 |
| `size width\|height`、`zoom` | 改变尺寸 / 缩放；`zoom` 支持 8 种锚点（左上/右下/左/右/上/下…） |
| `shake`、`encircle`、`wobble`、`breath` | 抖动、绕圈、摇摆、呼吸式缩放四类效果动画 |
| `physics` | 重力、摩擦、弹性、起始位置、初速度、持续推力——窗口像刚体一样下落/弹跳 |
| `minimize` / `maximize` / `fullscreen` / `borderless` | 窗口状态控制 |
| `hidehud` | 隐藏 HUD（F1 效果） |
| `windowtitle set/reset` | 改窗口标题 |
| `button` | 启用/禁用标题栏按钮 |
| `mousemove` / `mousetransmit` | 移动/接管系统鼠标指针 |
| `notice` | 原生系统通知（Win 托盘气泡 / macOS 通知中心 / Linux libnotify）+ 游戏内 toast |
| `displayvalue`、`get`、`score` | 下发数值；读取窗口 X/Y/宽高、鼠标坐标、显示器尺寸、系统时间；写入记分板目标 |
| `test` | 创建一个独立的 `WindowX Preview` 测试窗口，用于预览动画 |
| `follow` | 窗口跟随实体/坐标/方向/距离，并可按距离缩放窗口 |
| `stop` | 停止所有动画 |

实现要点：`WindowAnimator` + `AnimationTask` 每帧推进，`EaseFunctions` 提供 30+ 缓动（含 `spring / wave / jump / glitch / stutter / packetloss / snap / step3/5/8` 等“整活”曲线）；位置/尺寸最终落到 `GLFWWindowHelper`（`glfwSetWindowPos/Size`、`glfwMaximizeWindow`、`glfwSetWindowAttrib`、`glfwSetCursorPos` 等）。

### 2. `/windowxm`：真实多窗口

不是游戏内贴图，而是**用 GLFW 再创建真实的操作系统窗口**（共享或独立 OpenGL 上下文，`CustomWindow` 内维护 `handle / hwnd / parentContext / contextShared / monitor`）。

- **窗口内容分层**：`CAMERA`（摄像机画面）、`WEB`（MCEF 网页）、`TEXTURE`（贴图/序列帧）、`GUI`（主窗口 HUD 镜像），另有一层桌面覆盖层；顺序用 8 种符号组合配置（`CWTG`、`CGWT`、`TWC`…）。
- **窗口属性**：位置/尺寸/标题/颜色/无边框、层级（`normal / always_on_top / click_through / solid`）、点击是否抢焦点、显示模式（`fit / stretch / original / tile`）。
- **窗口即物体**：窗口之间会互相碰撞推挤（`checkCollisions`），可拖拽并带物理（重力/摩擦/弹性/拖动惯性）。
- **输入转发**：子窗口的鼠标移动/按下/滚轮、键盘按下/字符事件会映射回主窗口坐标或转发给网页，实现可交互的第二块屏幕。
- **环境覆盖层**：雨雪、南瓜头、望远镜、下界传送门、黑暗、着火——子窗口需要独立渲染这些全屏效果（`multiwindow/*OverlayManager`）。
- **平台特化**：Windows 用 DWM 扩展边框 + 颜色键透明，或 `UpdateLayeredWindow` 逐像素 alpha（`WindowsLayeredAlphaSurface`，配置项可关）；macOS 用 CoreGraphics + 自绘着色器子窗口。
- **指令**：`add / remove / modify / rename / content / web / size / zoom / move / follow / layer / contentlayer / button / gui / camera / score / get / stop …`

### 3. 摄像机系统（camera）

- `camera` 方块是**隐形锚点**（`RenderShape.INVISIBLE`），右键打开 `CameraScreen` 配置 `cameraId / offsetX / offsetY / fov / resolution`。
- `camera_entity`（实体相机）由物品生成，同样可配置；`CameraRegistry` 把 `cameraId` 映射到位置/朝向 locator。
- `CameraRenderManager` 在每帧把世界**离屏渲染**到 `CameraTexture`（双缓冲 + fence 同步），支持独立 FOV、分辨率、渲染距离、透视/正交投影，并可开关天空、云、天气、雾。
- **光影兼容**：`ShaderCompatibility` 反射接入 Iris，创建隔离 pipeline，避免摄像机渲染污染主画面；相关 mixin 处理正交投影下的天空/云/太阳月亮与雾。
- 画面用途：多窗口内容层、摄像机实体显示、桌面摄像机投影的渲染管线。

### 4. 桌面摄像机（desktop camera）

把玩家**真实电脑桌面**搬进 MC 世界：

- **捕获**：Windows Graphics Capture（自带 `windowx_wgc.dll`，JNA 调用）优先，回退 `PrintWindow`/GDI；macOS 走 CoreGraphics。可枚举窗口、扩展边框、过滤 DWM cloaked 窗口、读取 Wallpaper Engine 壁纸。
- **重建**：桌面被拆成「背景 + 每个窗口一张独立纹理 + 光标」；按 `orthoHeight / windowDepth / windowThickness / cursorScale / shareRadius / backgroundDistance` 在 3D 空间里立起来。
- **中继**：源客户端采集 → `DesktopCameraServer` 会话 → 广播给同服务器其他客户端（帧、单窗口图、光标、场景、几何更新）。
- **可交互**：为每个投影窗口生成碰撞体，玩家能踩、能抓取、能旋转（配合 Sable 子世界物理）；光标是独立实体（多种光标样式）。
- **传输优化**：`WindowFrameCodec` 用 JPEG + LZ4 压缩帧；`fps / resolutionHeight` 可调；两类快捷键（强制关闭、抓取/释放光标）。

### 5. 音频律动（Rhythm）

- `RhythmSoundMonitor` 抓取**系统输出音频**：Windows 用自带 WASAPI loopback（JNA COM 封装），其他平台回退 Java Sound loopback（Stereo Mix / BlackHole / Soundflower 等）。
- 计算 RMS/dB、平滑成包络与节拍，驱动 `RhythmEffectController` 让窗口随音乐缩放。
- 对应 MobEffect `rhythm`（等级越高幅度越大）。

### 6. Windowed 效果：窗口随玩家状态变形

`windowed` MobEffect 激活后，客户端窗口会按玩家状态实时改变尺寸/位置/抖动：蹲下压扁、趴下拉伸、冲刺放大、腾空拉长、落地回弹、鞘翅倾斜、受击按方向击退回弹、寒冷发抖、反胃扭曲、进出下界传送门形变、望远镜缩窗、低血量呼吸、节律缩放。

### 7. 系统通知

`NoticeOverlay`：Windows 托盘气泡（`Shell_NotifyIcon`）、macOS `NSUserNotification`、Linux `libnotify`，全部走 JNA 反射加载；失败自动降级为游戏内浮层提示（带淡入/停留/淡出动画）。

### 8. 指令生成器 GUI

`CommandGeneratorScreen`：游戏内界面（默认键位打开），左侧选命令、右侧填参数，支持 `/windowx` 与 `/windowxm` 两套、缓动/布尔/枚举下拉、一键复制指令到剪贴板；界面标签为中文（含“主窗口 / 多窗口”“复制指令”等）。

### 9. 二次开发 API

- `WindowXApi`：`registerExtension` + `WindowXExtension#onApiAvailable(Context)`，带 API 版本号。
- `WindowXClientApi`：`create / getWindow(s) / snapshots / isAvailable`，返回 `ClientWindow`。
- `WindowXServerApi`：`controller(player[, selector]) / create(...)`，返回 `ServerWindowController`。
- `WindowController` 统一了窗口操作：标题、位置、动画移动、缩放、颜色、无边框、最小/最大化、层级、内容层顺序、贴图、网页、GUI 镜像、绑定摄像机、摄像机参数/特性、抖动/绕圈/摇摆/呼吸、物理、停止、关闭。
- 事件：`WindowCreatedEvent / WindowChangedEvent / WindowRemovedEvent / WindowXCommandRegistrationEvent`。

### 10. 兼容与底层

- **Sable**：`SableCompatibility` / `SablePhysicsCompatibility` 把方块/实体/桌面窗口的坐标与碰撞投影到子世界（可移动结构）坐标系，支持抓取子世界并旋转。
- **MCEF**：子窗口内嵌浏览器（可选依赖，反射调用）。
- **9 个 Mixin**：窗口/摄像机/GameRenderer 访问器、GUI/HUD 捕获、雾、摄像机天空与云、正交地平线、桌面摄像机遮挡。
- 其他：LZ4 压缩、JNA 平台调用、GLFW 直接操作。

---

## 四、运行时数据流

```
[服务端] /windowx、/windowxm 指令
      │  解析目标玩家 / 坐标（绝对、r 相对、p 百分比）/ 缓动 / 时长
      ▼
[自定义 Payload]  ──►  [客户端] 应用到 GLFW 窗口 / 创建子窗口 / 触发动画
      ▲                        │
      │                        ├─ 多窗口：本地离屏渲染（摄像机 / 网页 / 贴图 / HUD 镜像）
      │                        └─ 桌面摄像机：采集本机桌面 → 编码 → 上传
      │
      └── C→S 回传：窗口位置/尺寸/鼠标坐标、摄像机配置、桌面帧与会话
                                   │
                                   ▼
                          [服务端中继 / 记分板写值]
```

- 动画与物理在**客户端**逐帧计算，服务端只下发参数。
- 摄像机与多窗口画面在**客户端本地**渲染；桌面画面需经过服务端中继给其他玩家。

---

## 五、值得注意的点

1. **没有权限校验**：两套指令的常量池中都找不到 `hasPermission` / `requires` 之类的判断，意味着默认任何玩家都能执行，并且能通过选择器操作**其他玩家**的窗口（多人服务器上是明显风险，建议配合权限插件/命令白名单）。
2. **两端都需要安装**：指令与中继在服务端，实际效果在客户端；缺客户端 Mod 时指令无可见效果。
3. **强平台差异**：透明窗口、通知、桌面捕获在 Windows / macOS / Linux 各写一套，Windows 支持最完整（含原生 DLL）。
4. **隐私敏感**：桌面摄像机会把源玩家的真实屏幕内容（窗口画面、壁纸、光标位置）广播给同服玩家，只应在可信环境使用。
5. **打包细节**：`mods.toml` 版本为 `1.0.4` 与目录名 `2.1.10-rc1` 不一致；`assets/examplemod/lang/en_us.json` 是模板残留；`data/windowx` 只有方块掉落表，没有配方（相机方块/物品只能通过创造模式 OP 物品栏获得）。
6. **无可读源码**：如需审计或二次开发，需先用 Vineflower/CFR 反编译这 328 个 class。

---

## 六、总结

WindowX 表面是“用指令抖动/移动 MC 窗口”的娱乐 Mod，实际实现了一套相当完整的**窗口合成与远程编排框架**：

- 指令层：两套 Brigadier 命令树 + 游戏内生成器；
- 表现层：30+ 缓动动画、物理、四类特效、窗口状态控制；
- 窗口层：真实多开窗口、内容分层、透明/层级/交互、HUD 镜像与环境覆盖；
- 画面层：离屏摄像机渲染 + Iris 兼容 + 真实桌面捕获投屏 + 服务端中继；
- 感知层：系统音频节拍、玩家状态驱动的窗口形变、原生系统通知；
- 扩展层：公开 API、事件、扩展注册、Sable 子世界兼容。

整体是一个高度客户端化、平台特化明显的“Minecraft 窗口外挂式演出工具”，适合做地图演出、直播效果、整活视频与服务端活动。
