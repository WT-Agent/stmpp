# Sublime Markdown Preview (stmpp) 架构设计文档

## 1. 架构目标与设计原则

- **极致原生**：全面利用 Sublime Text 4 (Build 4050+) 官方引入的 `window.new_html_sheet()` (`sublime.HtmlSheet`)，杜绝子进程弹窗或 Win32 宿主 hook。
- **内存防膨胀**：内存占用 < 20MB，不启动外部 Node.js 服务，纯 Python 运行时环境。
- **无感刷新**：输入监听异步分发（`on_modified_async`）结合线程级防抖（Debounce 200ms），大文件解析与高亮限制在 100ms 以内。

---

## 2. 模块分层与依赖流

```text
[ Markdown View in Editor ] 
          │
          │ (on_modified_async / on_post_save_async)
          ▼
   [ SmpEventListener ] (plugin.py)
          │
          ▼
   [ PreviewManager ] (preview/manager.py)
    ├── 1. 获取/创建 HtmlSheet (在 Group 1 分栏)
    ├── 2. 防抖调度器 (Debounce 200ms)
    ├── 3. 布局协同 [ LayoutManager ] (preview/layout.py)
    └── 4. 驱动渲染管线
          │
          ▼
   [ MarkdownEngine ] (renderer/engine.py)
    ├── [ HtmlSanitizer ]    -> 剥离脚本与危险属性
    ├── [ PathResolver ]     -> 规范化 Windows 相对/绝对路径为 file:///
    ├── [ SyntaxHighlighter] -> 生成 minihtml 友好型代码语法着色
    └── 组装 TOC、CSS (preview.css + theme)
          │
          ▼
  [ sheet.set_contents(html) ]
```

---

## 3. 核心机制详解

### 3.1 视图与 Sheet 生命周期管理
- 通过 `view.id()` 建立 `PreviewSession` 映射表，多标签 Markdown 切换时在 `on_activated_async` 自动将对应的 Sheet 置顶，杜绝视图串台。
- 当视图关闭时，自动释放关联的 `HtmlSheet`。若分栏 Group 1 为空，自动恢复用户原有编辑器单栏布局。

### 3.2 渲染管线与 minihtml 约束
- `minihtml` 不执行任何客户端 JavaScript。
- 语法高亮在 Python 端静态完成：优先加载环境中的 `Pygments`；当缺少外部依赖时，平滑降级至内置的高速正则 Lexer (`MiniHtmlFormatter`)，保证零依赖运行。
- 本地图片路径统一转换为 `file:///` 格式，自动兼容 Windows 盘符（如 `C:/`）与反斜杠。
