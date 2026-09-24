# WatersSaveEink

> 给老旧安卓墨水屏设备用的横屏桌面：常显日历、时间、提醒、新闻、天气，播放大量电台与本地音乐。

- **仓库**：<https://github.com/icewatershuang/WatersSaveEink>
- **当前版本**：`V3.3_760`（横屏版）
- **中文别名**：水哥拯救墨水屏（横屏版）
- **包名**：`com.kindledash.landscape`

---

## ⚠️ 重要：安装后必须授予足够权限

这是本项目**最容易被忽略、也最容易导致功能异常**的一步。程序需要访问本地媒体文件与网络音频流，如果权限不足，**音乐播放（Music）等功能会直接无法正常使用**，而且通常不会给出明显报错。

请在安装完成后按下列步骤逐项授权。

### Android 6.0 及以上（运行时授权）

| 权限 | 用途 | 不授权的后果 |
| --- | --- | --- |
| **存储 / 文件与媒体**<br>`READ_EXTERNAL_STORAGE` / `READ_MEDIA_AUDIO` | 读取设备上的本地音乐文件 | **本地音乐列表为空，无法播放** |
| **音频录制 / 麦克风**<br>`RECORD_AUDIO` | 部分电台与语音相关功能所需的音频通道 | 相关音频功能异常 |
| **网络访问**<br>`INTERNET` | 在线电台、新闻、天气数据 | 电台无法加载、天气与新闻空白 |
| **通知**<br>`POST_NOTIFICATIONS`（Android 13+） | 常显提醒与通知栏信息 | 提醒不弹出 |
| **修改音频设置**<br>`MODIFY_AUDIO_SETTINGS` | 音量与音频输出控制 | 音量调节失效 |
| **唤醒锁定 / 前台服务**<br>`WAKE_LOCK` / `FOREGROUND_SERVICE` | 常显时保持运行、息屏后继续播放 | 息屏后程序被杀、音乐中断 |

**授权路径**：`设置 → 应用 → WatersSaveEink → 权限`，把「存储 / 文件与媒体」「麦克风 / 音频」两项手动打开。

### Android 4.x ~ 5.x（安装时授权）

安装向导会一次性列出全部权限，**必须全部勾选同意**。安装完成后系统不再提供补授入口，存储权限若当时未勾选，音乐功能将永久不可用。

### 授权后仍无法播放音乐的排查顺序

1. 确认「存储 / 文件与媒体」权限已开启 → 打开程序 → 进入音乐页，看列表是否出现本地文件；
2. 若列表为空，把音乐文件放到设备**根目录 `Music/`** 或程序提示的扫描目录下，重启程序重新扫描；
3. 确认网络权限已开启 → 在线电台才能正常加载；
4. 老设备（Android 4.0.x）若出现「应用未安装 / 解析包时出现问题」，请改装 **`dist/KDashBoardL_V3.3_760.apk`**（v1 签名版），该版本针对老系统签名链做了兼容。

---

## 版本与签名

| 文件 | 签名方案 | 适用设备 | 建议 |
| --- | --- | --- | --- |
| `dist/KDashBoardL_V3.3_760.apk` | v1 (JAR) | Android 4.0+ 老设备 | **优先安装**，兼容性最好 |
| `dist/KDashBoardL_V3.3_760_v123.apk` | v1 + v2 + v3 | Android 7.0+ 较新设备 | 新版系统安装失败时改用 |

两个包功能完全一致，仅签名方案不同。

---

## V3.3_760 本次修复

相对 `V3.2_759` 解决的两个问题：

### 1. 主页左右各留 12px 白边

**根因**：`#topWrap` 是全屏横向容器的唯一子元素，内部 `.layout` 的左右 12px 被算进了总宽度，因此左右各多出 12px 空白。

**修复**：给 `#topWrap` 加 `box-sizing: border-box; padding: 0 12px`，让 padding 消化在容器内部。

### 2. 设置页与次级清单可被上下拉动

**根因**：老旧 WebKit（Android 4.0.4 / WebKit 534.x）下 `scrollTop` 写入无效、`position: fixed` 容器不生成原生滚动条，原生滚动完全不可依赖。

**修复**：改用「裁剪盒 + `translateY` 夹层」方案 —— 外层 `overflow:hidden` 定高裁剪盒，内层 `.kdl-shift` 由 JS 直接写 `transform: translateY(-N)`；内层滚到头继续拖拽时，手势接力给外层。

---

## 目录结构

```
WatersSaveEink/
├── README.md      # 本文件
├── dist/          # 成品 APK（两个签名变体）
├── src/           # WebApp 源码
│   ├── assets/    #   dashboard.html / radio_presets.js / hls.min.js
│   ├── res/       #   资源 XML（图标、网络安全配置、设备管理）
│   └── AndroidManifest.xml
├── tools/         # 构建与打包脚本（AXML 改写、重签名、资源映射）
├── tests/         # 回归验证与截图工装（含老 WebKit 模拟器）
└── docs/          # 修复前后对照图
```

---

## 技术要点

| 项 | 说明 |
| --- | --- |
| 目标环境 | Android 4.0.4（API 14）老 WebKit 内核，`minSdkVersion=14` |
| 包名 | `com.kindledash.landscape` |
| 签名链 | `keytool`（PKCS12 / SHA1withRSA）→ `zipalign -p 4` → `apksigner sign` |
| 滚动方案 | 裁剪盒固定高度 + 内层 `transform: translateY(-N)`；夹层被渲染器冲掉后自动重新包裹 |
| 类名匹配 | 白名单 + `cn.split(/\s+/)` 整词匹配，避免 `.radio-my-row` 被子串误命中 |
| AXML 改动 | 原地等长改写，避免破坏资源表偏移 |

---

## 许可

个人自用项目，欢迎参考实现思路。
