"""Unit tests for scroll synchronization and viewport calculations."""

import unittest
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
pkg_dir = os.path.dirname(current_dir)
# Mock sublime module for offline testing environment
import types
if "sublime" not in sys.modules:
    sublime_mock = types.ModuleType("sublime")
    class Vector:
        def __init__(self, x, y):
            self.x = x
            self.y = y
        def __getitem__(self, idx):
            return [self.x, self.y][idx]
    sublime_mock.Vector = Vector
    sublime_mock.View = object
    sublime_mock.active_window = lambda: None
import importlib.util
sync_path = os.path.join(pkg_dir, "preview", "sync.py")
spec = importlib.util.spec_from_file_location("stmpp_sync", sync_path)
sync_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_mod)
ScrollSynchronizer = sync_mod.ScrollSynchronizer


class MockRegion:
    def __init__(self, begin_pt):
        self._begin = begin_pt

    def begin(self):
        return self._begin


class MockView:
    def __init__(self, vp_pos=(0.0, 200.0), layout_ext=(800.0, 1000.0), vp_ext=(800.0, 200.0), row=10):
        self._vp_pos = vp_pos
        self._layout_ext = layout_ext
        self._vp_ext = vp_ext
        self._row = row

    def viewport_position(self):
        return self._vp_pos

    def layout_extent(self):
        return self._layout_ext

    def viewport_extent(self):
        return self._vp_ext

    def visible_region(self):
        return MockRegion(0)

    def rowcol(self, pt):
        return (self._row, 0)


class MockHtmlSheet:
    def __init__(self, layout_ext=(600.0, 2000.0), vp_ext=(600.0, 400.0)):
        self._layout_ext = layout_ext
        self._vp_ext = vp_ext
        self.last_viewport_pos = None
        self.last_animate = None

    def layout_extent(self):
        return self._layout_ext

    def viewport_extent(self):
        return self._vp_ext

    def set_viewport_position(self, pos, animate=False):
        self.last_viewport_pos = pos
        self.last_animate = animate


class TestScrollSynchronizer(unittest.TestCase):
    def test_get_current_line(self):
        view = MockView(row=15)
        line = ScrollSynchronizer.get_current_line(view)
        self.assertEqual(line, 16)

    def test_find_nearest_heading_anchor(self):
        lines = [
            "# Project Overview",
            "This is intro.",
            "## Architecture Design",
            "Details here.",
            "### Database Schema",
            "More details.",
            "Regular text paragraph."
        ]
        # At line 7 (index 6, Regular text), nearest heading is ### Database Schema
        anchor = ScrollSynchronizer.find_nearest_heading_anchor(lines, 7)
        self.assertEqual(anchor, "database-schema")

        # At line 2 (index 1), nearest is # Project Overview
        anchor = ScrollSynchronizer.find_nearest_heading_anchor(lines, 2)
        self.assertEqual(anchor, "project-overview")

        # Before any heading
        anchor = ScrollSynchronizer.find_nearest_heading_anchor(["text before heading", "# First"], 1)
        self.assertIsNone(anchor)

    def test_calculate_scroll_ratio(self):
        # view_h=1000, vp_h=200, max_scroll = 800. view_y = 200 -> ratio = 200 / 800 = 0.25
        view = MockView(vp_pos=(0.0, 200.0), layout_ext=(800.0, 1000.0), vp_ext=(800.0, 200.0))
        ratio = ScrollSynchronizer.calculate_scroll_ratio(view)
        self.assertAlmostEqual(ratio, 0.25, places=3)

        # At top
        view_top = MockView(vp_pos=(0.0, 0.0), layout_ext=(800.0, 1000.0), vp_ext=(800.0, 200.0))
        self.assertAlmostEqual(ScrollSynchronizer.calculate_scroll_ratio(view_top), 0.0)

        # At bottom: view_y = 800 -> ratio = 1.0
        view_bottom = MockView(vp_pos=(0.0, 800.0), layout_ext=(800.0, 1000.0), vp_ext=(800.0, 200.0))
        self.assertAlmostEqual(ScrollSynchronizer.calculate_scroll_ratio(view_bottom), 1.0)

    def test_calculate_target_sheet_y(self):
        # sheet_h = 2000, vp_h = 400 -> max_sheet_scroll = 1600. ratio = 0.25 -> target_y = 400
        sheet = MockHtmlSheet(layout_ext=(600.0, 2000.0), vp_ext=(600.0, 400.0))
        target_y = ScrollSynchronizer.calculate_target_sheet_y(sheet, 0.25)
        self.assertAlmostEqual(target_y, 400.0, places=2)

    def test_sync_editor_to_preview(self):
        view = MockView(vp_pos=(0.0, 400.0), layout_ext=(800.0, 1000.0), vp_ext=(800.0, 200.0))  # ratio = 0.5
        sheet = MockHtmlSheet(layout_ext=(600.0, 2000.0), vp_ext=(600.0, 400.0))  # max = 1600

        ScrollSynchronizer.sync_editor_to_preview(view, sheet, animate=False)
        self.assertIsNotNone(sheet.last_viewport_pos)
        self.assertFalse(sheet.last_animate)
        # 0.5 * 1600 = 800
        pos_y = sheet.last_viewport_pos[1] if isinstance(sheet.last_viewport_pos, (tuple, list)) else sheet.last_viewport_pos.y
        self.assertAlmostEqual(pos_y, 800.0, places=2)


if __name__ == "__main__":
    unittest.main()
