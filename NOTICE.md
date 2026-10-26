# NOTICE / 来源与第三方说明

## 1. 参考项目

- 名称：**WindowX**
- 作者：**XuTrain**
- 平台：NeoForge 1.21.1
- 公开页面：<https://modrinth.com/mod/windowx>
- 许可证声明：jar 内 `META-INF/neoforge.mods.toml` 为 `license="MIT"`；Modrinth 项目页标注 **Apache-2.0**（两处不一致，属上游声明差异）。

## 2. 本仓库与原项目的关系

- 本仓库**不包含**原项目的 `.class`、贴图、模型、语言文件与原生 DLL；
- `WindowXBedrock/` 为面向网易中国版 ModSDK 的**独立重写**，仅在行为语义（指令名、参数含义、缓动与物理参数）上参考；
- UI 贴图由 `tools/gen_textures.py` 生成纯色占位图，未使用原作者美术资源。

## 3. 署名

若本项目后续公开发布，应在作品说明中注明：

> Inspired by WindowX by XuTrain (<https://modrinth.com/mod/windowx>).
> This project is an independent reimplementation for Minecraft Bedrock (NetEase China Edition) and contains no assets from the original mod.

## 4. 第三方依赖

- 本仓库 Python 代码仅使用标准库；
- 运行环境为网易《我的世界》中国版 ModSDK（Python 2.7 语法兼容）；
- 生成器与单测使用本机 Python 3（不影响游戏内运行）。

## 5. 合规提醒

- 网易平台的组件/地图作品需经审核；外部桌面程序（Companion）的分发方式需平台书面确认；
- 不在作品中收集玩家个人信息，不上传屏幕内容。
