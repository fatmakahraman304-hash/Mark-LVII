"""Service lifecycle checks; no network, node or external processes required."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import start_with_osiris as service


class ServiceTests(unittest.TestCase):
    def test_stopped_process_is_not_reported_ready(self):
        process = Mock()
        process.poll.return_value = 1
        with self.assertRaisesRegex(RuntimeError, "stopped"):
            service.wait_ready(process, "http://127.0.0.1:3010/", timeout=.1)

    def test_exact_health_payload_required(self):
        process = Mock()
        process.poll.return_value = None
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"jarvis_bridge":1}'
        opener = Mock()
        opener.open.return_value = response
        with patch.object(service, "build_opener", return_value=opener):
            service.wait_ready(process, "http://127.0.0.1:3010/", timeout=.1)
        response.read.assert_called_once_with(1024)

    def test_foreign_health_payload_times_out(self):
        process = Mock()
        process.poll.return_value = None
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"other_service":true}'
        opener = Mock()
        opener.open.return_value = response
        with patch.object(service, "build_opener", return_value=opener), patch.object(service.time,"sleep"):
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                service.wait_ready(process,"http://127.0.0.1:3010/",timeout=.01)

    def test_completed_process_is_not_terminated(self):
        process=Mock()
        process.poll.return_value=0
        service.stop_owned(process)
        process.terminate.assert_not_called()

    def test_owned_stuck_process_is_killed_after_timeout(self):
        process=Mock()
        process.poll.return_value=None
        process.wait.side_effect=[subprocess.TimeoutExpired("node",8),0]
        service.stop_owned(process)
        process.terminate.assert_called_once()
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
