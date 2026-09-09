# Sublime Markdown Preview (stmpp)

面向 Sublime Text 4 的轻量级 Markdown 实时分栏预览插件。

内部 Package ID: `SublimeMarkdownPreview`

---

## 核心特性

- **纯原生内嵌**：基于 Sublime Text 4 原生 `sublime.HtmlSheet` (`minihtml`)，无需开启外部浏览器。
- **极低资源开销**：无 Electron、无 Node.js、无常驻独立后台服务，空闲内存占用小于 20MB。
- **50/50 左右分栏**：一键开启侧边预览，关闭预览时自动恢复原有单栏/多栏布局。
- **GFM 完整支持**：
  - 语法着色代码块（Python、JS/TS、Go、Rust、C/C++、Bash、SQL、JSON 等）
  - 表格（支持左、中、右列对齐）
  - 任务列表（Task List `[x]` / `[ ]`）
  - 引用块、删除线、行内代码
- **本地图片与路径解析**：兼容 Windows 反斜杠、盘符及相对路径（`./img.png`、`../assets/`）。
- **防抖实时刷新**：输入默认 200ms 防抖，100KB 文件渲染速度在 50~80ms，杜绝卡顿。
- **主题智能自适应**：自动跟随 Sublime Text 主题明暗模式，亦可手动指定 Light / Dark。
- **目录导航与 HTML 导出**：自动生成 Table of Contents 锚点导航，支持一键将 Markdown 导出为独立 HTML 文件。

---

## 快捷键

| 操作 | Windows / Linux | macOS |
| :--- | :--- | :--- |

| **开关预览 (Toggle Preview)** | `Ctrl + Shift + M` | `Super + Shift + M` |
| **强制刷新 (Refresh Preview)** | `Ctrl + Shift + Alt + M` | `Super + Shift + Alt + M` |

---

## 命令面板 (Command Palette)

按 `Ctrl+Shift+P` (或 macOS `Cmd+Shift+P`) 输入：

- `Markdown Preview: Toggle Preview`
- `Markdown Preview: Open Preview to Side`
- `Markdown Preview: Open Preview`
- `Markdown Preview: Refresh`
- `Markdown Preview: Close Preview`
- `Markdown Preview: Export HTML`

---

## 配置说明

通过 `Preferences -> Package Settings -> Sublime Markdown Preview -> Settings` 打开配置：

```json
{
    "preview_mode": "side",
    "split_ratio": 0.5,

    "auto_refresh": true,
    "refresh_delay": 200,

    "sync_scroll": true,
    "theme": "auto",

    "allow_html": true,
    "allow_remote_resources": false,

    "code_line_numbers": false,
    "toc": true,

    "custom_css": "",
    "custom_css_file": ""
}
```

---

## 目录架构

```text
stmpp/
├── plugin.py                     # 插件主入口与 EventListener
├── commands/                     # 命令集实现 (Open, Close, Refresh, Toggle, Export)
├── renderer/                     # 纯 Python GFM 解析、代码高亮、路径解析与安全过滤
├── preview/                      # HtmlSheet 视图管理、双栏布局与滚动锚点同步
├── assets/                       # 基础与主题样式表 (preview.css, theme_light.css, theme_dark.css)
├── settings/                     # 默认配置定义
├── tests/                        # 单元测试与基准性能套件
├── Default.sublime-commands      # 命令面板映射
├── Default (Windows).sublime-keymap # 快捷键映射
├── Default (OSX).sublime-keymap     # macOS 快捷键映射
└── Main.sublime-menu             # 菜单栏注册项
```
