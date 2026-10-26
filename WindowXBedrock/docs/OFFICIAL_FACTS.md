# 官方事实清单（P0.5 依据）

> 核对日期：2026-10-26。来源：网易开发者官网 / 我的世界中国版 Wiki（社区镜像）。
> 用途：所有"我们按官方实现"的说法必须能指到本文件的某一条；未能核实的写"未证实"。

## 1. 自定义指令事件 `CustomCommandTriggerServerEvent`

| 字段 | 类型 | 说明 |
|---|---|---|
| `command` | str | 自定义命令名（对应 json `name`） |
| `args` | **list(dict)** | 每项含 `name` / `type` / `value`；`value` 已转 Python 类型（`pos` → tuple、`target` → tuple…） |
| `variant` | int | 变体号 [0,9]，未配置为 0 |
| `origin` | **dict** | `entityId`（**命令方块触发时无此字段**）/ `dimension` / `blockPos` |
| `return_failed` | bool | 可写；True 时以红色提示失败 |
| `return_msg_key` | str | 可写；回显信息，支持 lang 键 |

来源：`https://mcwiki.easecation.net/mcdocs/1-ModAPI/事件/世界.html`（CustomCommandTriggerServerEvent 一节）。

**派生结论**

- `args` 是列表，**不能** `args.get(...)`；必须归一化为 `{name: value}`（`modCommon/command_event.py`）。
- `origin` 不含玩家名、不含权限等级；管理员必须另查。
- 命令方块与玩家的区分依据：`origin` 是否含 `entityId`。

## 2. 自定义指令 JSON

- 位置：`<behavior_pack>/netease_commands/<团队>_<命名空间>_<指令名>.json`
- `format_version` 固定 `"0.0.1"`；`permission_level` 可选 `game_directors / admin / host / owner / any`
- **`game_directors` 包含命令方块；`admin` 不允许命令方块执行**
- 变体 `args1..args9` 与 `args` 合计最多 10 套，且"区分位参数类型不能相同"

来源：`https://mc.163.com/dev/mcmanual/mc-dev/mcguide/20-玩法开发/15-自定义游戏内容/9-自定义指令.html`

**派生结论**：本项目采用**一动作一命令、零变体**，并在生成器里用 `name -> (family, action)` 索引精确分发，避免 `wxscore/wxshake/wxsize/wxstop` 被前缀误判为 `wxs*`。

## 3. 引擎 tick 事件名

- 客户端：**`OnScriptTickClient`**（约 30 次/秒）
- 服务端：`OnScriptTickServer`

来源：MCStudio 自带样例 `data/demo/AwesomeMod/awesomeBehaviorPack/awesomeScripts/modCommon/modConfig.py`

## 4. UI（自定义界面）

| 接口 | 层级 | 说明 |
|---|---|---|
| `ScreenNode.GetBaseUIControl(path)` | 界面 | 取控件基对象 |
| `BaseUIControl.asImage()/asLabel()/asButton()/asPanel()` | 控件 | 类型不符返回 None |
| `SetFullPosition/SetFullSize/SetAlpha/SetSprite/SetText/SetLayer/SetVisible` | 控件 | **SetAlpha 仅 image/label** |
| `AddTouchEventParams()` + `SetButtonTouchDown/Move/Up/CancelCallback` | 按钮 | 先开参数，再绑回调 |
| `SetIsSwallow` | **界面级** | 点击是否穿透到世界（不能逐控件设置） |
| `SetBindWorldPosition(dimension, position)` | **界面级** | 一个界面只能绑一个世界坐标 |
| `Update()` | 界面 | 每帧回调（约 30fps） |

来源：`1-ModAPI/接口/自定义UI/索引.html`、`.../UI界面.html`

## 5. 摄像机

`CreateCamera(levelId)` → `CameraComponentClient`：

- `SetCameraPos` / `SetCameraRotation(Pitch, Yaw, Roll)`（**与 F3 相反**）/ `SetCameraOffset`（仅第三人称）
- `SetFov(fov)`，范围 **[30, 110]**，越界钳制
- `SetCameraBindActorId` / `ResetCameraBindActorId` / `DepartCamera` / `UnDepartCamera` / `ResetCameraPos`
- `LockCamera` / `UnLockCamera` / `SetCameraPitchLimit`
- 运动器：`AddCameraTrackMotion` / `AddCameraAroundPointMotion` / `StartCameraMotion` / `StopCameraMotion`

`CreatePlayerView(entityId)` → `SetPerspective(0/1/2)` / `SetPlayerFovScale(0~100)`（变焦，**不是正交**）。

来源：`1-ModAPI/接口/玩家/摄像机.html`

**未证实**：相机组件上的雾/天空开关；正交投影；RTT；多视口。

## 6. 权限

- `CreatePlayer(entityId).GetPlayerAbilities()` → `dict`，含 `op: bool`
- `CreateCommand(levelId).GetCommandPermissionLevel()` 是服务器 op 等级，不是玩家身份

来源：`1-ModAPI/接口/玩家/权限.html`、`.../世界/指令.html`

**派生结论**：管理员判定用 `GetPlayerAbilities().op`，失败则 fail-closed（不回退为"放行"）。

## 7. 外部通信（B0）

- 客户端：**无** HTTP/WebSocket/Socket、无通用文件 IO、无启动进程/打开网址
- 客户端有 `GetClipboardContent` / `SetClipboardContent`
- Apollo 网络服：有服务器通信（master/service）与外部 HTTP 回调章节

来源：`1-ModAPI/接口/Api索引表.html`、`2-Apollo/4-SDK/8-服务器通信.html`

**派生结论**：本机直连不可行；剪贴板属未授权绕过手段，**不采用**；B0 维持冻结。
