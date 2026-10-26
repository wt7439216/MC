# G0：授权与来源核查报告

> 结论先行：**G0 = 有条件通过（个人/研究可用；公开上架前必须先澄清许可证，或按 clean-room 重写）**
> 核查日期：2026-10-26 ｜ 核查人：自动探测脚本 + 人工比对

---

## 1. 本地包基线

| 项 | 值 |
|---|---|
| 目录 | `windowx-2.1.10-rc1-1.21.1-NeoForge/`（解包后的 jar） |
| 文件数 | 349（不含本次分析文档） |
| 总字节 | 1,832,170 |
| class 数 | 328 |
| `META-INF/neoforge.mods.toml` | `modId=windowx`、`license=MIT`、`version=1.0.4`、`authors=XuTrain` |
| `neoforge.mods.toml` SHA-256 | 见 `docs/_hashes.txt` |
| `windowx.mixins.json` SHA-256 | 见 `docs/_hashes.txt` |
| `windowx/native/windowx_wgc.dll` SHA-256 | `cf8acb8b1f94f9c3fbc607552a0d35c798ed5cdb0457b37e1f0b816fc4f61ec0`（174,080 字节） |

## 2. 公开渠道基线（Modrinth API，2026-10-26）

| 项 | 值 |
|---|---|
| 项目 | `windowx`（project_id `zftGUYoz`）、作者 `XuTrain` |
| 平台标注许可证 | **Apache-2.0** |
| 公开版本 | `2.1.9-hotfix`(2026-10-03)、`2.1.2`、`2.1.0`、`1.0.0-lite` |
| 是否存在 `2.1.10-rc1` | **不存在**（公开 4 个版本全部为 release，无 rc/beta） |
| 下载校验 | 抓取 `2.1.9-hotfix` jar，SHA-1 = `4d7812d265c6a07af3aecd4bebc359d250dbd2bc`，与 Modrinth 一致 ✅ |

## 3. 本地包 vs 公开 2.1.9-hotfix

| 对比项 | 公开 2.1.9-hotfix | 本地 2.1.10-rc1 | 判断 |
|---|---|---|---|
| jar/目录体积 | 491,570 字节 | 1,832,170 字节（解包后，含 md 之外全部文件） | 本地更大 |
| zip 条目 / 文件数 | 269 | 349 | 本地更多 |
| 内部 `version` | `1.0.0` | `1.0.4` | 作者**从不按文件名改内部版本** |
| 内部 `license` | **MIT** | **MIT** | 两个 jar 一致 |
| 原生 DLL | 无 | `windowx_wgc.dll` | 后续版本新增 |
| class 交集 | 219 共有 | 109 仅本地有 | **0 个公开类缺失** |
| Jaccard | — | 0.6677 | 本地是公开版的**严格超集** |

**推论**

1. 本地包与公开 2.1.9 是同一代码谱系，且是更新的一次构建（公开版所有 class 都在，反向不成立）。
2. "目录名 2.1.10-rc1 / 内部 1.0.4"的版本错位**不是篡改**：公开 2.1.9 的内部版本同样是 `1.0.0`，说明作者习惯不改内部版本字段。
3. 许可证不一致**发生在上游**：两个 jar 都写 MIT，而 Modrinth 项目页写 Apache-2.0。属作者声明不一致，不是本地文件被改。
4. 但本地这个 `2.1.10-rc1` **确实不在公开版本列表**，来源（自建/草稿/私发）仍需作者确认。

## 4. 授权风险评估

| 用途 | 结论 | 依据 |
|---|---|---|
| 个人学习、本地原型、不公开分发 | **可用** | 不构成再发行 |
| 公开上架（组件/地图）但完全重写、不复制代码/美术 | **低风险** | 只参考行为与参数，属独立实现；建议保留来源说明 |
| 复用其 class/纹理/图标/原生 DLL | **必须书面许可** | MIT 与 Apache-2.0 均要求保留声明，但"哪个适用"未定；DLL 与第三方依赖不在声明覆盖内 |
| 商用 | **暂不可** | 许可证归属未澄清 |

## 5. 处置（已写入方案 v2.1 的 G0 阻塞项）

1. **默认 clean-room**：不复用任何 `.class`、`.png`、`windowx_wgc.dll`；本工程只使用"行为与参数语义"，皮肤与图标全部自绘（当前 `tools/gen_textures.py` 生成纯色占位）。
2. 对外材料标注："Inspired by WindowX by XuTrain"；不取名 `WindowX`（除非获授权）。
3. 上架前完成以下任一：
   - 取得作者书面确认（邮件/私信截图存档），或
   - 确认 Modrinth 页面许可证即为生效许可证，并在作品说明中按 Apache-2.0 保留声明。
4. 问询模板见 `docs/BRIDGE_B0_REPORT.md` 附录 B（同一条问询可一并确认授权与 Bridge 许可）。

## 6. 复现方式

```powershell
# 本地基线
python tools/gen_commands.py --check
Get-FileHash META-INF/neoforge.mods.toml -Algorithm SHA256   # 见 docs/_hashes.txt

# 公开版本比对（只读，临时文件放 %TEMP%，用完即删）
# 1) 下载 2.1.9-hotfix jar 并校验 SHA-1 == 4d7812d265c6a07af3aecd4bebc359d250dbd2bc
# 2) zipfile 读取 META-INF/neoforge.mods.toml 的 license/version
# 3) 枚举 jar 内 *.class 与本地 com/**.class 求交集（219 / 109 / 0）
```

> 本次比对使用的公开下载地址：
> `https://cdn.modrinth.com/data/zftGUYoz/versions/cvRF72Ih/windowx-2.1.9hotfix-full-1.21.1-NeoForge.jar`
> 比对完成后已删除本地临时 jar，未纳入工程。
