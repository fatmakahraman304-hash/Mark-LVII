"""No-GUI restart scheduling tests. Never launch a real JARVIS process."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from core.restart_manager import schedule_restart


class RestartManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "JARVIS"
        self.root.mkdir()
        (self.root / "tools").mkdir()
        self.helper = self.root / "tools" / "restart_app.py"
        self.helper.write_text("# restart helper for test\n", encoding="utf-8")
        self.env = patch.dict(os.environ, {
            "LOCALAPPDATA": self.tmp.name,
            "JARVIS_MANAGED_RESTART": "0",
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_helper_is_scheduled_before_gui_closes(self):
        proc = MagicMock()
        proc.poll.return_value = None
        with patch("core.restart_manager.subprocess.Popen", return_value=proc) as launch:
            kind = schedule_restart(self.root, 1234, executable=sys.executable)
        self.assertEqual(kind, "helper")
        launch.assert_called_once()
        args, kwargs = launch.call_args
        self.assertEqual(args[0][0], sys.executable)
        self.assertTrue(Path(args[0][1]).samefile(self.helper))
        self.assertEqual(args[0][2], "1234")
        self.assertTrue(Path(args[0][3]).samefile(self.root))
        self.assertTrue(Path(kwargs["cwd"]).samefile(self.root))
        self.assertTrue((Path(self.tmp.name) / "Jarvis/logs/restart.log").is_file())

    def test_supervised_restart_does_not_launch_second_process(self):
        os.environ["JARVIS_MANAGED_RESTART"] = "1"
        self.helper.unlink()
        with patch("core.restart_manager.subprocess.Popen") as launch:
            self.assertEqual(schedule_restart(self.root, 1234), "managed")
            launch.assert_not_called()

    def test_missing_helper_prevents_unsafe_gui_shutdown(self):
        self.helper.unlink()
        with patch("core.restart_manager.subprocess.Popen") as launch:
            with self.assertRaises(FileNotFoundError):
                schedule_restart(self.root, 1234)
            launch.assert_not_called()

    def test_invalid_pid_rejected(self):
        with self.assertRaises(ValueError):
            schedule_restart(self.root, 0)

    def test_immediate_helper_failure_is_reported(self):
        proc = MagicMock()
        proc.poll.return_value = 1
        proc.returncode = 1
        with patch("core.restart_manager.subprocess.Popen", return_value=proc):
            with self.assertRaisesRegex(RuntimeError, "hemen sonlandı"):
                schedule_restart(self.root, 1234)


class LayoutContractTests(unittest.TestCase):
    """Source layout checks: these complement, not replace, a real Qt GUI test."""

    @classmethod
    def setUpClass(cls):
        cls.source = (
            Path(__file__).resolve().parents[1] / "gui/window.py"
        ).read_text(encoding="utf-8")

    def test_command_sidebar_is_left_of_hud_and_telemetry_right(self):
        text = self.source
        beginning = text.index("        body = QHBoxLayout()")
        end = text.index("        root.addLayout(body, stretch=1)", beginning)
        layout = text[beginning:end]
        self.assertLess(layout.index("body.addWidget(self._right_panel"),
                        layout.index("body.addWidget(self._center_split"))
        self.assertLess(layout.index("body.addWidget(self._center_split"),
                        layout.index("body.addWidget(self._left_panel"))

    def test_header_actions_are_left_and_duplicate_state_hidden(self):
        text = self.source
        beginning = text.index("    def _build_header(self)")
        end = text.index("    def _start_update(self)", beginning)
        header = text[beginning:end]
        for item in ("_drawer_btn", "_ctrl_btn", "_update_btn", "_fs_btn"):
            self.assertIn(f"left_lay.addWidget(self.{item})", header)
        self.assertNotIn("left_lay.addWidget(self._state_chip)", header)
        self.assertIn("lay.addLayout(clock_col)", header)

    def test_update_auto_schedules_restart(self):
        text = self.source
        beginning = text.index("    def _update_done(self, changed, message)")
        end = text.index("    def _tick_clock(self)", beginning)
        restarter = text[beginning:end]
        self.assertIn("QTimer.singleShot(1500, self._restart_after_update)", restarter)
        self.assertIn("schedule_restart(project, os.getpid()", restarter)
        self.assertIn("self._restart_requested = True", restarter)
        self.assertIn("QApplication.instance().quit()", restarter)


if __name__ == "__main__":
    unittest.main()
