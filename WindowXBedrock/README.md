# WindowX Bedrock（P0.5）

把 NeoForge 版 WindowX 的**表现与指令语义**移植到网易《我的世界》基岩版中国版。
方案见上级目录 `WindowX-基岩版移植方案-v2.1.md`。

> 当前阶段：**P0.5 修复完成 + 实机测试准备就绪**（事件解析、HUD 对象层级、安全边界、
> rev 重同步、相机恢复、生命周期顺序、`wxresync` 身份校验）。
> 纯逻辑 + SDK Mock 集成测试共 **123 项通过**；**尚未做 MCStudio 实机验证**。
> 上机步骤见 `docs/P0_5_REAL_DEVICE_READY.md`。

## 快速开始

```powershell
cd tools
python gen_commands.py          # 29 条指令 JSON + command_index.py（唯一数据源）
python gen_textures.py          # 占位 UI 贴图
python gen_ui.py                # 默认 HUD_SLOTS=24；可 --windows N 做分级测试
python run_tests.py             # 123 项（纯逻辑 + SDK Mock）
ruff check --select E9,F --target-version py39 .
```

## 目录

```
behavior_packs/windowxBehavior/
  manifest.json
  netease_commands/            29 条自定义指令（wx* / wxs* / wxa*）
  windowxScripts/
    modMain.py
    modCommon/
      modConfig.py  command_index.py(生成)  command_event.py
      easing.py  layout.py  window_def.py  permissions.py
      registry_core.py  rev_store.py  dispatch_core.py
      animator_core.py  physics2d.py  camera_math.py  protocol.py
    modServer/
      serverSystem.py          事件解析 / 可信 origin / 补丁路由 / 拒绝客户端写
      permissions_service.py   GetPlayerAbilities().op（fail-closed）
    modClient/
      clientSystem.py          tick=OnScriptTickClient、复合键、rev 缺口标记
      hudScreen.py             GetBaseUIControl + AddTouchEventParams/SetButtonTouch*
      hudBackend.py            控件对象层级；关键错误不静默
      cameraAdapter.py         失败账本；restore 返回真实结果
      cameraGuard.py           异常路径也尝试恢复，失败不伪装成功
      debugSuite.py
resource_packs/windowxResource/
  ui/windowx_hud.json  ui/_ui_defs.json  textures/ui/windowx/*.png
tools/                         生成器 + 单测 + SDK Mock
docs/                          OFFICIAL_FACTS / G0 / B0 / P0_RUNBOOK / P0_5_REVIEW …
```

## 关键设计（都已落到代码）

- **指令**：29 条、零变体；`command_index.py` 用显式 `name -> (family, action)` 分发，
  避免 `wxscore/wxshake/wxsize/wxstop` 被前缀误判成 `wxs*`。
- **事件**：按官方 `args: list(dict)` + `origin: dict` 解析；命令方块 = origin 无 `entityId`；
  失败写 `return_failed=True`。
- **权限**：`wx*`=any（仅本人）、`wxs*`=game_directors（命令方块，操作 world 窗口）、`wxa*`=admin；
  服务端二次校验；管理员判定 `GetPlayerAbilities().op`，查不到即拒绝。
- **安全**：客户端 `EV_CMD` 不可信 → **一律拒绝写状态**；`EV_ACK` 忽略；
  重同步只走引擎可信入口（玩家加入 / `wxresync`）。
- **UI**：控件对象层级；`SetAlpha` 仅 image/label；点击穿透为界面级（P1 处理）；
  槽位按 UI 实际控件探测，不再固定 24。
- **相机**：`SetFov` 30–110；无正交/RTT；失败记入账本并返回 False。

## P0.5 状态

| 项 | 状态 |
|---|---|
| G0 授权与来源 | 有条件通过（类名包含 ≠ 字节码/来源已证明；保持 clean-room） |
| B0 Bridge | **冻结**（本机无通信 API；剪贴板等绕过手段已否决） |
| 指令事件解析 | 已修（list(dict)/origin），含回归测试 |
| HUD 对象层级 + 触摸 | 已修，含 Mock 集成测试 |
| tick 事件名 | 已修 `OnScriptTickClient` |
| 客户端写权限 | 已禁用（含跨 owner 伪造防护） |
| rev / FULL 重同步 | 已修（按 owner，显式缺口 + `wxresync`） |
| 相机恢复 | 已修（异常路径 + 失败注入测试） |
| MCStudio 实机 | **未做**（步骤见 `docs/P0_RUNBOOK.md`） |

详见 `docs/P0_5_REVIEW.md`。
