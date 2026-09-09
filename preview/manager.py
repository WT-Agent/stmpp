"""Preview session manager and lifecycle coordination."""

import os
import threading
import sublime
from typing import Dict, Optional, Any
from ..renderer.engine import MarkdownEngine
from .layout import LayoutManager


class PreviewSession:
    """Represents an active preview session for a Sublime Text window."""

    def __init__(self, window_id, sheet, original_layout=None):
        self.window_id = window_id
        self.sheet = sheet
        self.original_layout = original_layout
        self.active_view_id = None
        self.last_content = ""
        self.render_generation = 0


class PreviewManager:
    """Coordinates Markdown preview sessions, themes, and debounce rendering."""

    _instance = None
    _window_sessions = {}
    _lock = threading.Lock()
    _css_cache = {}

    @classmethod
    def get_instance(cls) -> "PreviewManager":
        if cls._instance is None:
            cls._instance = PreviewManager()
        return cls._instance

    def is_markdown_view(self, view: sublime.View) -> bool:
        if not view or not view.is_valid():
            return False
        syntax = view.settings().get("syntax", "").lower()
        if "markdown" in syntax or "mdown" in syntax:
            return True
        fname = view.file_name()
        if fname:
            ext = os.path.splitext(fname)[1].lower()
            return ext in (".md", ".markdown", ".mdown", ".mkdn", ".mkd")
        return False

    def get_session(self, window_id: int) -> Optional[PreviewSession]:
        session = self._window_sessions.get(window_id)
        if session and session.sheet:
            window = sublime.active_window()
            if window and hasattr(window, "sheets"):
                try:
                    open_ids = [s.id() for s in window.sheets()]
                    if session.sheet.id() not in open_ids:
                        self._window_sessions.pop(window_id, None)
                        return None
                except Exception:
                    pass
        return session

    def has_session(self, view_id: int) -> bool:
        window = sublime.active_window()
        if not window:
            return False
        return self.get_session(window.id()) is not None

    def open_preview(self, view: sublime.View, mode: str = "side"):
        if not self.is_markdown_view(view):
            sublime.status_message("Current file is not a Markdown document")
            return

        window = view.window()
        if not window:
            return

        window_id = window.id()
        session = self.get_session(window_id)

        # If already open, simply refresh current view without opening a new tab
        if session:
            self.render_view(view, force=True)
            return

        settings = self._load_settings()
        split_ratio = float(settings.get("split_ratio", 0.5))

        original_layout = None
        target_group = window.active_group()

        if mode == "side":
            original_layout = LayoutManager.split_to_side(window, split_ratio)
            target_group = 1 if window.num_groups() > 1 else target_group

        title = "Markdown Preview"
        initial_html = '<body id="sublime-markdown-preview"><p>Rendering preview...</p></body>'

        try:
            sheet = window.new_html_sheet(title, initial_html, group=target_group)
        except TypeError:
            sheet = window.new_html_sheet(title, initial_html)
            if target_group > 0:
                window.set_sheet_index(sheet, target_group, 0)

        session = PreviewSession(window_id, sheet, original_layout)
        with self._lock:
            self._window_sessions[window_id] = session

        # Return focus to editor view
        self._is_switching = True
        try:
            window.focus_view(view)
        except Exception:
            pass
        finally:
            sublime.set_timeout(lambda: setattr(self, "_is_switching", False), 80)

        # Initial render
        self.render_view(view, force=True)

    def close_preview(self, view: sublime.View = None):
        window = (view.window() if view else None) or sublime.active_window()
        if not window:
            return

        window_id = window.id()
        session = self._window_sessions.pop(window_id, None)
        if not session:
            return

        try:
            session.sheet.close()
        except Exception:
            pass

        LayoutManager.restore_layout(window, session.original_layout)

    def toggle_preview(self, view: sublime.View):
        if not view or not view.is_valid():
            return
        window = view.window() or sublime.active_window()
        if not window:
            return

        session = self.get_session(window.id())
        if session:
            self.close_preview(view)
        else:
            self.open_preview(view, mode="side")

    def schedule_render(self, view: sublime.View):
        if not view or not view.is_valid():
            return

        window = view.window()
        if not window:
            return

        session = self.get_session(window.id())
        if not session:
            return

        settings = self._load_settings()
        if not settings.get("auto_refresh", True):
            return

        delay_ms = max(50, int(settings.get("refresh_delay", 200)))

        session.render_generation += 1
        current_gen = session.render_generation

        sublime.set_timeout(lambda: self._on_debounce_fire(view, current_gen), delay_ms)

    def _on_debounce_fire(self, view: sublime.View, gen: int):
        if not view or not view.is_valid():
            return

        window = view.window()
        if not window:
            return

        session = self.get_session(window.id())
        if not session or session.render_generation != gen:
            return

        self.render_view(view)

    def render_view(self, view: sublime.View, force: bool = False):
        if not view or not view.is_valid():
            return

        window = view.window()
        if not window:
            return

        session = self.get_session(window.id())
        if not session:
            return

        content = view.substr(sublime.Region(0, view.size()))
        if not force and session.active_view_id == view.id() and content == session.last_content:
            return

        session.active_view_id = view.id()
        session.last_content = content
        settings = self._load_settings()

        file_name = view.file_name()
        base_dir = os.path.dirname(file_name) if file_name else ""

        # Prepare CSS
        css = self._prepare_css(view, settings)

        # Render Markdown
        engine = MarkdownEngine(options=settings, base_dir=base_dir)
        html_out = engine.render(content, custom_css=css)

        # Update sheet content on main thread
        try:
            session.sheet.set_contents(html_out)
        except Exception as e:
            import traceback
            err_msg = f"[SublimeMarkdownPreview] Render error: {e}\n{traceback.format_exc()}"
            print(err_msg)
            sublime.status_message(f"Markdown Preview Render Error: {e}")

    def on_view_activated(self, view: sublime.View):
        if not view or not view.is_valid():
            return

        if getattr(self, "_is_switching", False):
            return

        if not self.is_markdown_view(view):
            return

        window = view.window() or sublime.active_window()
        if not window:
            return

        session = self.get_session(window.id())
        if not session:
            return

        # Preview panel is active in this window! Follow editor file switch and force update
        self.render_view(view, force=True)

    def on_view_closed(self, view: sublime.View):
        # We only close preview layout if all views in window are closed
        pass

    def _load_settings(self) -> Dict[str, Any]:
        defaults = {
            "preview_mode": "side",
            "split_ratio": 0.5,
            "auto_refresh": True,
            "refresh_delay": 200,
            "sync_scroll": True,
            "theme": "auto",
            "allow_html": True,
            "allow_remote_resources": False,
            "code_line_numbers": False,
            "copy_button": True,
            "toc": True,
            "toc_position": "right",
            "table_mode": "auto",
            "custom_css": "",
            "custom_css_file": "",
        }
        try:
            s = sublime.load_settings("SublimeMarkdownPreview.sublime-settings")
            if s:
                for k in defaults:
                    val = s.get(k)
                    if val is not None:
                        defaults[k] = val
        except Exception:
            pass
        return defaults

    def _prepare_css(self, view: sublime.View, settings: Dict[str, Any]) -> str:
        css_parts = []

        # 1. Base CSS
        base_css = self._load_asset_text("preview.css")
        if base_css:
            css_parts.append(base_css)

        # 2. Theme CSS
        theme_setting = settings.get("theme", "auto")
        is_dark = False

        if theme_setting == "auto":
            color_scheme = view.settings().get("color_scheme", "").lower()
            if any(k in color_scheme for k in ("dark", "mariana", "monokai", "black", "twilight", "slate")):
                is_dark = True
        elif theme_setting == "dark":
            is_dark = True

        theme_file = "theme_dark.css" if is_dark else "theme_light.css"
        theme_css = self._load_asset_text(theme_file)
        if theme_css:
            css_parts.append(theme_css)

        # 3. User Custom CSS
        custom_css = settings.get("custom_css", "")
        if custom_css:
            css_parts.append(custom_css)

        custom_css_file = settings.get("custom_css_file", "")
        if custom_css_file and os.path.isfile(custom_css_file):
            try:
                with open(custom_css_file, "r", encoding="utf-8") as f:
                    css_parts.append(f.read())
            except Exception:
                pass

        return "\n".join(css_parts)

    def _load_asset_text(self, filename: str) -> str:
        if filename in self._css_cache:
            return self._css_cache[filename]

        text = ""
        pkg_resource = f"Packages/SublimeMarkdownPreview/assets/{filename}"
        try:
            text = sublime.load_resource(pkg_resource)
        except Exception:
            current_dir = os.path.dirname(os.path.dirname(__file__))
            local_path = os.path.join(current_dir, "assets", filename)
            if os.path.isfile(local_path):
                try:
                    with open(local_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    pass

        if text:
            self._css_cache[filename] = text
        return text
