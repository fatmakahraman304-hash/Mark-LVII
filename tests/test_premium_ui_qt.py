"""Offscreen smoke tests for painted Qt premium HUD widgets.

No microphone, network, paid model or full application window is started.
"""
from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QApplication

from gui.settings_page import Toggle
from gui.theme import C
from gui.widgets import HeaderBar, HoloPanel


class PremiumQtRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def render_widget(self, widget, width, height):
        widget.resize(width, height)
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(QColor(C.BG))
        widget.render(image)
        self.assertFalse(image.isNull())
        widget.close()
        widget.deleteLater()
        return image

    def test_panel_with_tag_renders_on_offscreen_surface(self):
        image = self.render_widget(HoloPanel("SYSTEMS", "LIVE"), 285, 240)
        self.assertNotEqual(image.pixelColor(20, 20), QColor(C.BG))

    def test_header_renders_on_offscreen_surface(self):
        image = self.render_widget(HeaderBar(), 820, 84)
        self.assertNotEqual(image.pixelColor(410, 10), QColor(C.BG))

    def test_switch_renders_in_both_states(self):
        off = Toggle("Durum")
        off.setChecked(False)
        image_off = self.render_widget(off, 54, 30)
        on = Toggle("Durum")
        on.setChecked(True)
        image_on = self.render_widget(on, 54, 30)
        self.assertNotEqual(image_off.pixelColor(9, 14),
                            image_on.pixelColor(9, 14))


if __name__ == "__main__":
    unittest.main()
