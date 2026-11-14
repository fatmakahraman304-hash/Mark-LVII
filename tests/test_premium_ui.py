"""Static visual regression contracts for the Qt premium HUD.

These checks intentionally do not import PyQt or launch the user's desktop.
They catch accidental loss of key bindings, visual surfaces and UI behaviours.
"""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def contrast_ratio(a: str, b: str) -> float:
    def luminance(h):
        rgb = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        v = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
             for c in rgb]
        return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]
    x, y = sorted((luminance(a), luminance(b)), reverse=True)
    return (x + .05) / (y + .05)


class PremiumHudTests(unittest.TestCase):
    def test_all_changed_python_modules_parse(self):
        for path in ("gui/theme.py", "gui/style.py", "gui/widgets.py",
                     "gui/window.py", "gui/settings_page.py"):
            with self.subTest(file=path):
                ast.parse(source(path), filename=path)

    def test_default_palette_is_readable(self):
        text = source("gui/theme.py")
        values = dict(re.findall(r'^\s+([A-Z_]+)\s+=\s+"(#[0-9a-fA-F]{6})"',
                                 text, flags=re.MULTILINE))
        for front, back in (("WHITE", "PANEL"), ("TEXT", "BG"),
                            ("TEXT_MED", "PANEL2")):
            self.assertGreaterEqual(
                contrast_ratio(values[front], values[back]), 4.5,
                f"{front} on {back} lacks normal-text contrast")

    def test_glass_panels_and_accessible_controls(self):
        widgets = source("gui/widgets.py")
        settings = source("gui/settings_page.py")
        self.assertIn("class HoloPanel(QWidget)", widgets)
        self.assertIn("p.setClipPath(clip)", widgets)
        self.assertIn("p.drawRoundedRect(bounds, 14, 14)", widgets)
        self.assertIn("class Toggle(QAbstractButton)", settings)
        self.assertIn("self.setAccessibleName(title)", settings)
        self.assertIn("self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)", settings)
        self.assertIn("self.setChecked(event.position().x() > self._start)", settings)
        self.assertIn("QPushButton#category:checked", settings)

    def test_controls_and_original_column_layout_remain(self):
        window = source("gui/window.py")
        self.assertIn("brand_stack = QVBoxLayout()", window)
        self.assertIn("body.addWidget(self._left_panel, stretch=0)", window)
        self.assertIn("body.addWidget(self._center_split, stretch=5)", window)
        self.assertIn("body.addWidget(self._right_panel, stretch=0)", window)
        for connection in (
            "self._drawer_btn.clicked.connect(self._open_settings_page)",
            "customize.clicked.connect(self._open_customize)",
            "self._update_btn.clicked.connect(self._start_update)",
            "self._fs_btn.clicked.connect(self._toggle_fullscreen)",
        ):
            self.assertIn(connection, window)
        self.assertNotIn("left_lay.addWidget(self._state_chip)", window)


if __name__ == "__main__":
    unittest.main()
