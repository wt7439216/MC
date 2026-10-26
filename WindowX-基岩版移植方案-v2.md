# WindowX → 网易《我的世界》基岩版 移植方案 v2

> v1：以"游戏视口当桌面 + UI 伪窗口"为核心的单产品方案（`WindowX-基岩版移植方案.md`）
> v2：合并外部计划《架构与实施计划_20261026》的**双产品 + 安全门禁**思路，并用官方文档核实后的 API 事实修正双方方案
> 核查日期：2026-10-26 ｜ 本机：MCStudio `1.1.59.13193`

---

## 0. 对参考计划的评审结论

### 0.1 采纳（确实更优，已并入 v2）

| # | 参考计划的观点 | 为什么采纳 |
|---|---|---|
| 1 | **双产品：Bedrock Core + 独立 Windows Companion（不注入游戏）** | v1 把"真实窗口操作"直接判 0% 砍掉，但没有 sandbox 也能用**独立桌面程序**实现。这是"尽可能完整移植"最关键的补全：Companion 才是 WindowX 的原味（真窗口移动/缩放/震动/物理/多窗/通知/桌面捕获/WASAPI），Core 负责游戏内部分 |
| 2 | **Bridge 只做门禁验证，默认禁用** | v1 完全没考虑"游戏内指令驱动桌面程序"；参考计划给 B0（许可确认）/B1（最小端到端）两级门禁，且明确"不得以注入/改包/逆向私协议作为替代路径"，正确 |
| 3 | **默认拒绝的隐私模型**（手选窗口、每次采集显式同意、服务器永不触发采集、日志不含画面） | 源项目会把玩家真实桌面广播给同服玩家，v1 只写了一句提示，不够。参考计划把"手选窗口 + 显式授权 + 紧急停止 + 审计"体系化，直接采用 |
| 4 | **`netease_commands/*.json` + `CustomCommandTriggerServerEvent` + `permission_level`** | v1 把自定义指令列为"需 POC + 聊天解析兜底"；官方文档证实这是**标准能力**（含 5 档权限、Tab 补全、参数变体），指令层可直接按 A 级实现 |
| 5 | **不编造性能阈值 / 不做整体移植百分比承诺** | v1 给了 55fps/3ms 等硬指标，属于未经基线测量的臆测。v2 改为"先建基线，再定阈值"，并把百分比降级为**内部排期参考**，不作为对玩家的承诺 |
| 6 | **G0-G9 验收门禁 + "不满足时"分支** | 工程管理上比 v1 的里程碑更严谨，合并为 v2 的 Gate 表 |
| 7 | **版权/许可逐项核实、保留本地未加密源工程** | v1 只提"素材不能直接商用"。补充：`mods.toml` 声明 `license="MIT"`、作者 `XuTrain`；网易平台上传审核可能加密，云端副本不能当唯一源码 |
| 8 | **Companion 的窗口发现必须"用户手动选择句柄"** | 防止按标题误伤其他程序窗口，v1 缺失 |

### 0.2 不采纳 / 需要修正

| # | 参考计划的说法 | 核实结果 | v2 处理 |
|---|---|---|---|
| 1 | 摄像机 API 含 `BeginCameraMotion` / `EndCameraMotion` | **不存在**。实际是 `AddCameraTrackMotion / AddCameraAroundPointMotion / AddCameraAroundEntityMotion / AddCameraVelocityMotion` + `StartCameraMotion(id)` / `StopCameraMotion(id)` | 按真实 API 重写摄像机适配层与验收用例 |
| 2 | 可用 `SetCameraPos` 等实现自由机位（未提限制） | 存在，但有硬限制：`SetFov` 仅 **[30,110]**（越界钳制）；`SetCameraPos` 需先 `DepartCamera()` 且**不入存档**；`SetCameraOffset` 只对第三人称有效；`SetCameraRotation` 顺序是 **(Pitch, Yaw, Roll) 且与 F3 相反** | 修正"正交近似"方案，坐标系转换进单测 |
| 3 | 自定义指令"待验证是否支持" | 官方文档明确支持，但**参数变体最多 10 套**，且变体区分位不能同类型（否则解析歧义） | 指令拆成 6 个命令文件，用 `enum` 动作位区分 |
| 4 | Core 只做"镜头/方块/HUD 视觉替代" | 偏低。官方 UI 能力足以支撑**游戏内伪窗口系统**（位置/尺寸/贴图/层级/透明/触控拖拽/30fps Update），这是 v1 的核心贡献，v2 保留并给 API 级落地表 | Core 增加"窗口表现层"，与摄像机并列 |
| 5 | 整体不做百分比 | 内部排期需要量级感 | 保留内部估算，标注"仅内部排期，不作对外承诺" |
| 6 | Companion 可"可选桥接"进游戏 | 组件包本身**不能携带/自动运行 EXE**（平台分发无此能力，需平台书面确认） | 明确"两份产物、两条分发路径"，商店页只描述 Core |

### 0.3 一句话结论（v2）

> **Core（游戏内窗口演出，可独立上架）+ Companion（Windows 真实窗口增强，独立分发）+ Bridge（仅在官方许可且实测可用时开启）。**
> 先独立做成两个能各自跑的产品，再谈联动；任何一步不通过门禁就退回上一个可交付形态。

---

## 1. API 事实基线（本机 + 官方文档核对）

### 1.1 已在本机确认

| 项 | 结论 |
|---|---|
| MCStudio | `F:\Game\MCStudio\MCStudio.exe`，`1.1.59.13193`（我的世界开发者启动器） |
| 模板 | `data\demo\`（`CommandTemplate`、`PresetEmptyAddonTemplate` 等）、`data\pluginTemplate\neteaseTemplate`（网络服：`developer_mods` + `behavior_packs`，`mod.json` 支持 `game/lobby/master/service`） |
| 样例工程 | `data\apollo\awesomeOnlineGame\mods\`（AwesomeGameMod / LobbyMod / MasterMod / ServiceMod / TutorialGameMod） |
| 脚本形态 | `modMain.py` + `modClient/modServer/modCommon`；`RegisterSystem` / `GetEngineCompFactory` / `ListenForEvent` / `RegisterUI`+`CreateUI` |
| 语言 | **Python 2.7**（`print "..."`、`except Exception, e`、`iteritems()`、`xrange()`） |
| 源 Mod 元数据 | `modId=windowx`、`license=MIT`、`authors=XuTrain`、内部版本 `1.0.4`（与文件名 2.1.10-rc1 不一致） |
| 本地未提供 | 游戏运行时与 ModSDK 具体包（需 MCStudio 首次运行后下载），故 API 以官方文档为准 |

### 1.2 官方文档核实（社区镜像，2026-10-26）

**自定义指令**

- 位置：`<behavior_pack>/netease_commands/<团队>_<命名空间>_<指令名>.json`（一指令一文件）
- 字段：`format_version:"0.0.1"`、`name`、`description`、`permission_level`、`args`、`args1~args9`（**变体合计 ≤10 套**）
- `permission_level`：`game_directors`（默认）/`admin`/`host`/`owner`/`any`
- 参数类型：`float/int/bool/str/target/pos/entity/item/enum/enum_short`；带 `default` 的参数必须排在尾部
- 服务端事件：`CustomCommandTriggerServerEvent`（判 `variant` 区分变体）；`GlobalCommandServerEvent` 监听全部
- 支持聊天栏预览 + Tab 补全；代码内可用 `SetCommand` 触发
- **变体歧义规则**：两个变体在同一位置的参数类型不能相同，否则无法解析

**摄像机（`CreateCamera(levelId)` → `CameraComponentClient`）**

`SetCameraPos / SetCameraRotation(Pitch,Yaw,Roll) / SetCameraOffset(仅第三人称) / SetCameraAnchor / SetFov([30,110]) / SetCameraBindActorId / ResetCameraPos / ResetCameraBindActorId / DepartCamera / UnDepartCamera / LockCamera / UnLockCamera / LockModCameraPitch / LockModCameraYaw / SetCameraDistanceFixed / SetCameraPitchLimit / SetSpeedFovLock`
运动器：`AddCameraTrackMotion / AddCameraAroundPointMotion / AddCameraAroundEntityMotion / AddCameraVelocityMotion` → `StartCameraMotion(id) / StopCameraMotion(id) / RemoveCameraMotion(id)`
玩家视角（`CreatePlayerView(entityId)`）：`SetPerspective(0/1/2) / LockPerspective / GetPerspective / SetPlayerFovScale(0~100)`

**自定义 UI**

- 界面级：`SetIsHud`（HUD 模式）、`SetIsModal`、**`SetIsSwallow`（点击是否穿透到世界）**、`SetVisible`、`SetLayer`、`Update`（客户端每帧，约 30fps）、`SetAnimation/RemoveAnimation/PlayAnimation/SetAnimEndCallback`
- 控件级：`SetPosition/SetFullPosition`（比例+绝对）、`SetSize/SetFullSize/SetMinSize/SetMaxSize`、**`SetAlpha`（仅 image / label 生效）**、`SetSprite / SetSpriteColor / SetSpriteUV / SetSpriteClipRatio`、`SetText/SetTextColor/SetTextFontSize`、`SetLayer`
- 交互：按钮必须先 `AddTouchEventParams`，才有 `Down/Up/Cancel/Move/MoveIn/MoveOut/ScreenExit` 回调；`AddHoverEventParams` 才有悬浮；`SetTouchEnable` 控制可交互
- 世界锚定：索引中存在 `SetBindWorldPosition / SetBindPosition / ChangeBindOffset`（**子页未核，列为 POC**）
- 已知坑：`SetAlpha` 对 panel/button 无效（皮肤必须 image 化）；无 `GetAlpha`；`SetAnimation` 重复设置会失败

**摄像机/渲染的边界**

- 文档中**没有**渲染到纹理（RTT）、多视口、离屏渲染、把摄像机画面贴到方块/UI 的公开接口 → v1 的判断成立：实时多机位画面 **不可移植**（P3/科研）
- 文档中**没有**相机组件上的雾色/雾距接口（`SetFogColor` 不在该页）→ "天空/云/天气/雾开关"降级为"待证 + 不可用就砍"

---

## 2. 产品形态决策

| 方案 | 内容 | 能上架 | 真实窗口 | 工作量 | 建议 |
|---|---|---|---|---|---|
| **A. 仅 Core** | 游戏内伪窗口 + 摄像机 + 指令 + 记分板 | ✅ 最稳 | ❌ | 中 | **先做，作为保底可交付** |
| **B. Core + Companion（独立分发）** | + Windows 真窗口控制/多窗/通知/捕获/音频 | Core ✅；Companion 独立 | ✅ | 中高 | **主目标** |
| **C. B + Bridge** | 游戏内指令驱动 Companion | 取决于平台许可 | ✅ | +少量 | **仅门禁通过后作为实验特性** |

### 2.1 对外表述纪律

- 商店页/宣传只描述 **Core** 能力（游戏内窗口演出）；
- Companion 描述为"PC 可选增强（需另行下载）"，**不得**暗示组件包内含或会自动安装；
- 不对玩家承诺"多机位实时画面""把桌面投进游戏""操作用户的任意窗口"；
- 内部排期用 §3 的百分比，**不对外发布**。

---

## 3. 可移植性矩阵 v2（A/B/C/D + 优先级）

A=有明确公开 API；B=可改造模拟；C=依赖未证接口/额外许可；D=无法等价复刻。**Core 与 Companion 分列**，因为同一功能在两边可达性完全不同。

| 功能（源 WindowX） | Core | Companion | 结论 | 优先级 |
|---|---|---|---|---|
| `/windowx` 指令解析与权限 | **A**（netease_commands + 5 档权限） | A | Core 直接落地，语法保持 | P0 |
| 30+ 缓动 / 时长 / 队列 | **A**（纯数学） | A | 两端共享同一套曲线表 | P0 |
| 窗口移动/缩放/锚点 | **A-**（SetFullPosition/SetSize，30fps） | A（SetWindowPos/SetWindowPlacement） | Core 用 UI 面板；Companion 才是真窗口 | P0 |
| 抖动/绕圈/摇摆/呼吸 | **B**（UI 位移+缩放，30fps 采样） | A | Core 需降采样设计 | P0 |
| 重力/摩擦/弹性/拖拽 | **B**（2D 积分 + 触控拖拽） | A | 参数同名，逻辑可共享 | P1 |
| 窗口间碰撞推挤 | **B**（AABB 分离） | A | 仅 UI 层有"碰撞"语义 | P1 |
| 层级/置顶/点击穿透 | **B**（`SetLayer` + `SetIsSwallow`，注意后者是界面级） | A（SetWindowPos HWND_TOPMOST） | Core 需多界面分层模拟 | P1 |
| 最小化/最大化/全屏/无边框 | **B**（折叠/铺满/无边框皮肤） | A | 语义不同，需重定义 | P1 |
| 隐藏 HUD / 改标题 | **B**（隐藏自绘 UI；标题画在伪标题栏） | A | Core 无法隐藏原生 HUD | P2 |
| 系统光标接管 | **D** | A（需显式授权） | Core 只有 UI 虚拟光标 | P2 |
| 系统通知 | **C**（自绘游戏内通知） | A（Shell_NotifyIcon） | 两端各一套 | P2 |
| 记分板 / 变量互通 | **A-**（组件或 `/scoreboard`） | 无 | Core 数据出口 | P1 |
| 命令生成器 UI | **A**（自定义 UI） | A（WPF/WinUI 面板） | 两端独立实现 | P2 |
| 摄像机自由机位 / FOV / 绑定实体 | **A**（`CreateCamera` 全家桶，主视角） | 无 | Core 强项；**不是**多机位渲染 | P0 |
| 摄像机画面贴到窗口/方块 | **D**（无 RTT） | C | 永不承诺 | P3 |
| 真正的多视口/多画面 | **D** | C | 放弃 | — |
| 网页窗口（MCEF） | **D** | A（WebView2） | Companion 专属 | P2 |
| 贴图/序列帧窗口内容 | **A-**（`SetSprite` 逐帧切换，需性能验证） | A | Core 可做"视频感" | P1 |
| GUI/HUD 镜像到窗口 | **D**（无 RTT） | A | 只能复刻精简版 | P3 |
| 桌面捕获（WGC/GDI） | **D** | A（用户逐次授权） | Companion 专属 | P2 |
| 桌面 3D 投射 / 窗口碰撞体 | **C/D** | A（采集端） | 游戏内贴图仍缺 RTT | P3 |
| 跨玩家共享桌面画面 | **D**（不经游戏网络传视频） | B（自建通道，需授权） | 高风险，默认关闭 | P3 |
| 系统音频律动（WASAPI） | **D** | A | Companion 专属 | P2 |
| 药水效果驱动的窗口形变 | **B**（伪窗口形变 + FOV/视角变化） | A | Core 近似，参数沿用 | P1 |
| Iris / Sable 兼容 | **D** | 不适用 | 不移植 | — |
| 原生 DLL（windowx_wgc.dll） | **D** | 不复用（重写/新实现） | 授权另核 | — |

**内部排期参考（不对外）**：Core 侧"玩家可感知演出"约 75–85%，"机制等价"约 20%；加上 Companion 后整体体验覆盖可到 **85–90%**，但**永远缺**实时多机位画面。

---

## 4. 目标架构 v2

```
┌──────────────────────────── Minecraft 中国版基岩版 ────────────────────────────┐
│  Core（行为包 + 资源包）                                                        │
│   ServerSystem ─ CommandDispatcher(权限/配额) ─ WindowRegistry ─ SyncBroker     │
│        │                    └─ ScoreBridge / Persist(ExtraData)                 │
│   ClientSystem ─ WindowRuntime ─ Animator ─ Physics2D ─ Interp                  │
│        │            ├─ UiBackend（HUD 面板池：位置/尺寸/贴图/层级/触控）          │
│        │            ├─ WorldUiBackend（SetBindWorldPosition 世界锚定，POC）      │
│        │            └─ CameraAdapter（CreateCamera 全家桶 + 降级链）            │
│        └─ NoticeOverlay / GeneratorUI / DebugSuite                              │
└──────────────────────────────────────────────────────────────────────────────────┘
             ╎ 可选 Bridge（默认关闭；G-B0/B1 未通过则永不启用，禁止注入/改包）
┌──────────────────────────────────────────────────────────────────────────────────┐
│  WindowX Companion（独立 EXE，用户自行启动）                                     │
│   PermissionManager · WindowDiscovery(手选句柄) · WindowController(Win32)        │
│   AnimationEngine · OverlayWindowManager · CaptureService(WGC) · Audio(WASAPI)  │
│   EmergencyStop · AuditLog                                                      │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Core 内部分层

| 层 | 模块 | 关键点 |
|---|---|---|
| 指令层 | `commandDispatcher.py` | 6 个 `netease_commands/*.json`；`CustomCommandTriggerServerEvent` 分发；`permission_level=admin`；自建"只能操作自己窗口"校验 |
| 状态层 | `windowRegistry.py` | 服务端权威；每玩家配额（建议 ≤8 窗口/人、≤20/场景）；`rev` 递增 |
| 同步层 | `syncBroker.py` | 增量 patch ≤20Hz + 动画参数一次性下发 + 全量纠偏；断线重连重建 |
| 表现层 | `windowRuntime.py` | 客户端镜像 + 插值（33ms 帧）；动画/物理在此推进 |
| 后端 | `uiBackend.py` / `worldUiBackend.py` | UI 面板池；世界锚定作为 POC 后端 |
| 摄像机 | `cameraAdapter.py` | 唯一 SDK 调用点；三级降级；坐标转换独立成 `cameraMath.py` 并单测 |
| 数据 | `scoreBridge.py` | 记分板/`SetCommand` 兜底；`displayvalue` 走服务端变量 |
| 工具 | `debugSuite.py` | 剧本化回归 + 帧耗时采样 |

### 4.2 UI 伪窗口规范（v2 用真实 API 落地）

单个窗口的最小控件集（全部 image/label/button，因为 `SetAlpha` 只对 image/label 生效）：

```
WinRoot(panel)
├─ bg      (image, 九宫格)      ← SetAlpha / SetSprite / SetSize
├─ shadow  (image, 可选)
├─ titlebar(image) → title(label) + btn_min/btn_max/btn_close(button)
└─ content (image)             ← SetSprite 切换贴图/序列帧；或 label 显示文本
```

| WindowX 语义 | UI 落地 | 限制 |
|---|---|---|
| 位置/尺寸（绝对/`r`/`p`） | `SetFullPosition` / `SetFullSize`（支持比例+绝对） | 建议全用比例，天然适配分辨率 |
| 透明度 | `SetAlpha`（image/label） | panel/button 无效 → 皮肤必须 image 化；且无 Get，需自存状态 |
| 层级（置顶/普通） | `SetLayer` | 同一界面内排序 |
| 点击穿透 vs 拦截 | **界面级 `SetIsSwallow`** | 逐窗口穿透做不到 → 方案：按"是否可交互"分 2~3 个 HUD 界面，界面内用 `SetTouchEnable` |
| 拖拽 | `AddTouchEventParams` + `SetButtonTouchMoveCallback` | 需要窗口 root 可接收触摸（用透明 button 铺满） |
| 标题栏按钮 | button 回调 + `SetSprite` 换图标 | — |
| 内容贴图/序列帧 | `SetSprite` 逐帧（≤12fps） | 资源必须预打包；换图开销需实测 |
| 世界内屏幕 | `SetBindWorldPosition` + `ChangeBindOffset` | 索引级能力，POC 决定 |
| 窗口抖动 | `Update` 内改 `SetFullPosition` | 30fps 采样，观感需调参（可加运动模糊感） |

**性能预算（先测后定）**：单场景 20 窗口 × 6 控件 = 120 控件；`Update` 内每帧只更新"脏窗口"；静止/远景窗口降频到 10Hz 或暂停；超过 25 个窗口自动切"低配模式"（无阴影/无序列帧）。

### 4.3 Companion 模块（Windows）

| 模块 | 职责 | 安全约束 |
|---|---|---|
| `WindowDiscovery` | 枚举顶层可见窗口，展示标题/进程/尺寸 | 仅展示，不自动选；用户点选后记录 HWND + 进程 ID |
| `WindowController` | 位置/尺寸/置顶/最小化/无边框 | 操作前快照原始 rect/style；句柄失效（进程退出）立即停手 |
| `AnimationEngine` | 与 Core 共用的缓动/物理曲线 | 固定步长；幅度上限可配 |
| `OverlayWindowManager` | 自建置顶窗显示图片/视频/WebView2 | 不声明"镜像游戏画面" |
| `CaptureService` | WGC 捕获指定窗口 | 默认关；每次显式同意；不自动上传 |
| `AudioMonitor` | WASAPI Loopback 幅度/频段 | 可关；启动时明示"将读取系统输出音频" |
| `EmergencyStop` | 托盘/热键一键停止 + 恢复原状 | 不依赖游戏是否运行 |
| `AuditLog` | 命令、错误码、耗时 | 不记录画面/账号/聊天 |

### 4.4 Bridge 协议（仅门禁通过后启用）

```json
{"schema":"windowx.bridge.v1","request_id":"d-0001","origin":"local_user",
 "target_hwnd":"user_selected","action":"shake",
 "args":{"amplitude_px":12,"duration_ms":800},"ttl_ms":1500}
```
强校验：来源必须是本机交互、目标必须是用户已选句柄、动作在白名单、TTL 过期即丢弃、幅度限幅、拒绝一切"启动捕获/上传/鼠标控制"类服务端请求。

---

## 5. 指令层落地设计

### 5.1 命令文件拆分（受"变体 ≤10 套"约束）

| 文件 | 覆盖 WindowX 子命令 | 变体数 |
|---|---|---|
| `wxTeam_wx_win.json` | `add / remove / move / movex / movey / size / zoom / layer / contentlayer / button / title / stop` | 10 |
| `wxTeam_wx_anim.json` | `shake / encircle / wobble / breath / physics / follow` | 6 |
| `wxTeam_wx_content.json` | `content texture / frames / text / web(占位) / gui(占位)` | 5 |
| `wxTeam_wx_camera.json` | `bind / config / feature / clear` | 4 |
| `wxTeam_wx_data.json` | `get / score / displayvalue / notice` | 4 |
| `wxTeam_wx_debug.json` | `test / suite / profile`（仅开发者权限） | 3 |

- 统一第一参数用 `enum`（动作名）避免歧义；`targets` 用 `target` 类型；坐标用 `str`（保留 `r`/`p` 语义）而不是 `pos`（`pos` 无法表达百分比）。
- `permission_level`：`admin`；服务端再加"目标必须是自己"的校验（源项目缺失，必须补）。
- 兜底：若某版本对 `enum` 支持不佳，退化为"每动作一个命令文件 + 聊天前缀解析"。

### 5.2 参数语义保持

`move` 的 `r`/`p`、`zoom` 的 8 种锚点、30+ 缓动名、`physics` 的 7 个参数名**全部沿用源项目**，让已有地图脚本可按机械替换迁移（`/windowx` → `/wxwin`）。

---

## 6. 摄像机子系统（按真实 API 重写）

### 6.1 能力与限制

| 需求 | API | 限制/对策 |
|---|---|---|
| 自由机位 | `DepartCamera()` + `SetCameraPos` + `SetCameraRotation` | 不入存档；退出/切维度必须 `UnDepartCamera` + `ResetCameraPos` 复原 |
| 朝向 | `SetCameraRotation((pitch, yaw, roll))` | **顺序与 F3 相反** → `cameraMath.py` 做转换并单测 |
| 视场角 | `SetFov(30~110)` | 越界被钳制；不能做超广角/极窄角 |
| 近似正交 | `SetPlayerFovScale(0~100)`（渲染 FOV = 基准 × scale） | 影响玩家视角，需与相机共存测试；POC 决定是否保留 `ORTHOGRAPHIC` 模式 |
| 跟随实体 | `SetCameraBindActorId` | 需同维度且在加载范围；目标死亡/远离自动解绑 → 监听解绑并回退 |
| 第三人称偏移 | `SetCameraOffset` | **仅第三人称有效**；第一人称无效（源项目 `offsetRight/Up/Forward` 需按视角模式区分） |
| 锁定玩家操作 | `LockCamera / LockModCameraYaw / LockModCameraPitch / SetCameraPitchLimit` | 供"窗口盯着某处"的演出使用 |
| 平滑运动 | `AddCameraTrackMotion(...easeTime)` / `AroundPoint` / `AroundEntity` / `Velocity` + `StartCameraMotion` | 轨迹运动器**不可叠加**（只能一个）；与"每 tick 手推 SetCameraPos"二选一，需 POC 比较平滑度 |
| 视角模式 | `CreatePlayerView(id).SetPerspective(0/1/2)` | 形变类效果（windowed）会切视角，需保存并恢复 |
| 雾/天空/云/天气 | **无公开相机接口** | 不做承诺；如必须，评估其他组件或全局指令（P3） |

### 6.2 30fps 驱动策略

- 方案 A：每 tick `SetCameraPos`（30Hz）→ 简单、可控，观感略跳；
- 方案 B：用原生 `AddCameraTrackMotion` + `easeTime`（引擎插值，可能更顺）→ 只支持单段轨迹，复杂路径需拼接；
- **决策留到 POC**：先用 A 打通，再对比 B 的顺滑度与可控性。

### 6.3 状态安全

进入/退出、切维度、断线、组件卸载、异常：统一走 `CameraGuard.restore()`（`UnDepartCamera` + `ResetCameraPos` + `SetPerspective(原值)` + `SetFov(原值)`），并做"启动自检 + 定时心跳校验"，避免玩家卡在独立相机。

---

## 7. 同步与状态

| 方向 | 事件 | 频率 | 内容 |
|---|---|---|---|
| C→S | `wx:cmd` | 触发 | 拖拽结束、按钮、输入框提交 |
| S→C | `wx:patch` | ≤20Hz 合并 | 脏字段增量（`rev`） |
| S→C | `wx:anim` | 触发 | 动画参数（起止/时长/缓动/锚点） |
| S→C | `wx:full` | 登录/重连/校验失败 | 全量窗口表 |
| C→S | `wx:ack` | 触发 | `rev` 回执，用于纠偏 |

- 动画在客户端本地插值，不逐帧发包（否则 30tick 下网络必爆）。
- 服务端只存"意图状态"，不存中间帧。
- 配额与限流：单玩家 ≤ 8 窗口、单场景 ≤ 20 窗口、单指令 ≤ 20 条/秒（防刷）。

---

## 8. 安全与隐私（以参考计划的默认拒绝模型为基础）

1. Companion 首次启动只显示能力清单，**不自动寻找/捕获窗口**；必须用户点选目标窗口（记录 HWND + PID）。
2. 每次屏幕捕获由本机用户显式开启，界面常驻"正在采集"指示，随时可关；**服务器指令与房主永远不能触发采集/上传/鼠标控制**。
3. Companion 不做进程注入、不改网易文件、不读写游戏内存、不绕过反作弊；非管理员权限运行。
4. 日志只留命令、错误码、耗时；不留画面、剪贴板、聊天、账号。
5. `EmergencyStop` 独立于游戏存在（托盘 + 全局热键），一键停止动画、恢复窗口、关闭采集、销毁覆盖窗。
6. Core 的指令必须补权限（源项目无 `hasPermission`）：`permission_level=admin` + "只能操作自己的窗口" + 审计日志。
7. 素材与代码：`license=MIT` 允许再发行（保留版权声明与出处），但**原生 DLL、第三方库、美术资源需逐项核实**；建议重绘皮肤，不直接复用 PNG。

---

## 9. Gate 计划（合并 v1 里程碑 + 参考计划门禁）

| Gate | 内容 | 验收条件 | 不通过时 | 人日 |
|---|---|---|---|---|
| **G0** 权益与基线 | 源模块映射、命令清单、许可核实、SHA-256 记录 | `SOURCE_INVENTORY.md` + 许可结论 | 不复用争议资源，全部重写 | 3 |
| **G1** UI 后端可行性 | 全屏 HUD 透出世界、20 控件 30fps 移动、`SetSprite` 换图、触控拖拽、`SetIsSwallow` 分层 | 三项全过；记录 PC/安卓帧率与脚本耗时**基线** | 降级为"少窗口静态版"或用 `SetAnimation` 属性动画 | 8 |
| **G2** Core 骨架 | 工程创建、6 个指令文件、注册、协议、WindowDef、缓动库 | 单机 `/wxwin add/move/size/zoom/stop` 可用；非 OP 被拒 | 修 SDK 兼容/退聊天前缀 | 15 |
| **G3** 表现层 | 多窗口、层级、动画队列、四类特效、物理+碰撞、follow | 20 窗口同场景稳定；断线重连复原 | 降到 12 窗口 + 关闭阴影 | 28 |
| **G4** 摄像机 | `cameraAdapter` + 坐标转换 + 复原守卫 + 机位方块/实体 | 5 种运镜正确；任何退出路径都复原 | 只保留"绑定实体+FOV"最小集 | 18 |
| **G5** 联机与数据 | 双端同步、配额、记分板、持久化、生成器 UI | 2 客户端一致；越权被拒；无错发 | 仅单机发布 | 16 |
| **G6** Companion MVP | 手选窗口、Move/Resize/Shake/Breathe/Stop/Restore | 不启动游戏也能控制测试窗口；真实窗口正常权限可控；恢复成功 | 判为不兼容，仅交付 Core | 25 |
| **G7** Companion 高级 | 多辅助窗、WebView2、WGC、WASAPI、紧急停止/审计 | 显式授权可关；无默认上传；DPI/多屏不脱屏 | 砍到单辅助窗 | 25 |
| **G8** Bridge | B0 许可调研 + B1 端到端最小原型 | 有官方依据且稳定工作 | 双产品分离，禁用桥接 | 8 |
| **G9** 发布 | 性能达标、隐私合规、版权、审核、灰度 | 审核通过 + 灰度指标达标 | 不公开，仅内测 | 20 |

合计 ≈ **166 人日**（+30% 缓冲 ≈ 216）。3 人约 3.5～4 个月；2 人约 5～6 个月。

**MVP 定义（约 70 人日）**：G0–G2 + G4 最小集 + G6 MVP → "游戏内窗口演出 + 可独立运行的桌面增强"。

---

## 10. 测试矩阵

### 10.1 环境

1. MCStudio 当前开发包；中国版 **Windows PC 基岩版**（记录引擎/ModSDK 版本）；Android/iOS 只测 Core。
2. 单机开发测试 → 2 个 Mod PC 客户端局域网 → 平台允许时再测普通联机房间。
3. Companion：Win10/11 × 100%/125%/150% DPI × 单/双屏 × 窗口化/无边框 × 显示器热插拔。

### 10.2 用例（合并两版）

| ID | 测试 | 通过条件 |
|---|---|---|
| T01 | 空白 Core 启动 | 可进测试世界，日志无致命错误 |
| T02 | 指令正确性 | 合法参数执行；非法参数有可读报错 |
| T03 | 指令权限 | 普通玩家不能操作他人窗口；`permission_level` 生效 |
| T04 | 视角复原 | 退出/断线/切维度/崩溃重进后视角正常 |
| T05 | 方块/红石机位 | 放置/拆除/区块加载无残留、无泄漏 |
| T06 | 双客户端同步 | 各端收到正确目标效果，无错发 |
| T07 | 20 窗口压力 | 记录基线；无持续内存增长；帧率不低于基线设定阈值 |
| T08 | 相对/百分比坐标 | `r`/`p`/负值/越界（夹取不飞出） |
| T09 | 缓动一致性 | 30+ 曲线在两端采样点一致（与源实现比对表） |
| T10 | 断线重连 | 窗口 100% 复原（`rev` 校验） |
| T11 | UI 交互 | 拖拽/缩放/按钮/层级/点击穿透符合定义 |
| T12 | 摄像机极值 | FOV 30/110、绑定目标死亡、锁定视角、正交近似 |
| T13 | Companion 手选窗口 | 只能控制已选窗口；游戏关闭后不误操作新进程 |
| T14 | Companion 恢复 | 停止后窗口位置/尺寸/样式完全复原 |
| T15 | 紧急停止 | 动画停、采集关、覆盖窗销毁 |
| T16 | 采集授权 | 未同意绝不采集；撤销即停；默认不上传 |
| T17 | 恶意指令 | 未知动作/超幅/过期/伪造来源全部拒绝 |
| T18 | DPI/多屏 | 高 DPI 与跨屏移动后可恢复、不脱屏 |
| T19 | 发布候选 | 平台自测通过、合规材料齐备、限制说明清晰 |

### 10.3 性能纪律

- **G1 先建基线**（空白组件 + 原版客户端，PC 与中端安卓各一台），之后所有阈值=基线 ± 可接受偏差，不提前写死。
- 必测指标：`Update` 单帧耗时（P95）、脚本 tick 耗时、UI 控件数、实体数、内存 60 分钟增长、进图时间。
- 自动化边界：动画数学/坐标转换/协议编解码/权限判定做纯 Python 单测（py2 语法，py3 跑回归）；渲染与窗口集成靠手工/半自动剧本。

---

## 11. 发布与合规

| 形态 | 适用 | 备注 |
|---|---|---|
| **联机大厅地图组件（首发）** | 演出/整活/小游戏 | Core 完整能力；开箱即玩 |
| **玩法组件 Addon** | 通用地图复用 | 部分能力受宿主地图限制 |
| **网络服组件**（`developer_mods` + `mod.json`，`support_server_type: game/lobby`） | 多人大厅、活动、云端存档 | 需运维与更严审核 |
| Companion | **独立分发**（官网/仓库/网盘） | 组件包内不带 EXE；商店页只写"可选 PC 增强" |

流程：`开发 → 自测 → 导出组件包 → 开发者平台上传 → 填图标/描述/兼容版本/版权 → 自测与审核 → 灰度 → 全量`。

注意：
- 上传审核的作品可能被**加密**，云端下载副本不能当源码备份 → **保留本地未加密工程 + 版本 tag**。
- 商店页不得出现外链导流、站外支付、个人信息收集；Companion 相关表述需法务/平台确认后再写。
- 灰度观测：崩溃率、进图成功率、平均帧率、指令调用 Top10、差评关键词。
- 回滚：保留上一稳定包；服务端加总开关（禁用表现层但保留指令解析）。

---

## 12. 风险登记表

| # | 风险 | 影响 | 概率 | 应对 |
|---|---|---|---|---|
| R1 | UI 30fps 更新在手机端掉帧 | 核心体验 | 中高 | G1 先测；脏窗口增量更新 + 分级降频 + 低配模式 |
| R2 | `SetIsSwallow` 是界面级，逐窗口点击穿透做不到 | 交互语义缩水 | 高 | 按可交互性分 2~3 个 HUD 界面；文档明确限制 |
| R3 | 无 RTT，"窗口内实时画面"落空 | 与源项目落差 | 高 | 产品定位为"窗口演出"；序列帧/世界锚定 UI 近似 |
| R4 | 相机 FOV 仅 30–110，正交模式受限 | 摄像机模式缩水 | 中 | 用 `SetPlayerFovScale` 近似，POC 决定是否保留 |
| R5 | 平台不允许组件联动外部程序 | Bridge 失效 | 高 | 双产品独立可交付；Bridge 永不作为卖点 |
| R6 | 审核对"外部 EXE/采集"敏感 | 无法上架 | 中 | Core 与 Companion 完全解耦；商店页不提采集 |
| R7 | Python 2.7 可维护性 | 迭代慢 | 中 | 纯逻辑与 SDK 隔离；单测；`adapters/` 收口 |
| R8 | 多人同步带宽/延迟 | 抖动错位 | 中 | 增量 patch + 本地插值 + rev 纠偏 + 限流 |
| R9 | 版权/素材 | 下架 | 中 | MIT 保留声明；DLL/第三方/美术逐项核；重绘皮肤 |

---

## 13. 明确不做（避免无效投入）

1. Core 里操作真实窗口、多开 OS 窗口、DWM 透明/无边框。
2. 任何形式的 RTT、多视口、把摄像机画面贴到窗口/方块。
3. 游戏内指令直接触发本机采集/上传/鼠标控制。
4. 注入/改包/逆向私有协议换来的"联动"。
5. 系统音频在 Core 内采集（改预置节拍时间轴）。
6. Iris/Sable 兼容、原生 DLL 复用。

---

## 14. 下一步（72 小时）

1. **G0**：把 328 个 class 的功能清单与 6 个新命令文件一一对齐，产出 `SOURCE_INVENTORY.md`；确认 MIT 再发行条款与美术授权。
2. **G1**：在 `CommandTemplate` 上做三件事——全屏 HUD 透出世界、20 控件 30fps 移动、`SetSprite` 换图 + 按钮拖拽；记录 PC/安卓帧率与 `Update` 耗时基线。
3. **相机 POC**：`DepartCamera + SetCameraPos/Rotation + SetFov + SetPlayerFovScale` 跑通，验证坐标转换与复原守卫；对比"每 tick 手推"与"原生轨迹运动器"的顺滑度。
4. **指令 POC**：写 `wxTeam_wx_win.json`（10 变体 + enum 动作位），验证 Tab 补全、权限与被拒提示。
5. **Companion POC**：C#/.NET 8 + WPF（或 WinUI）做一个"手选窗口 → 抖动 → 一键恢复"的最小程序，验证快照/恢复/句柄失效处理。
6. 产出 `CAPABILITY_MATRIX.md`（把 §3 每行填成"实测通过/降级/否决"），据此冻结 v2.1 范围与排期。
