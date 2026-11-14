import unittest
from unittest.mock import patch
import psutil
from tools.restart_app import restart


class RestartTests(unittest.TestCase):
    def test_waits_for_exit_before_launch(self):
        events = []
        with patch('tools.restart_app.psutil.Process') as process, patch('tools.restart_app.subprocess.Popen') as launch:
            process.return_value.wait.side_effect = lambda **kw: events.append('exit')
            launch.side_effect = lambda *a, **kw: events.append('launch')
            self.assertEqual(restart(123, '.'), 0)
        self.assertEqual(events, ['exit', 'launch'])

    def test_timeout_never_launches_second_instance(self):
        with patch('tools.restart_app.psutil.Process') as process, patch('tools.restart_app.subprocess.Popen') as launch:
            process.return_value.wait.side_effect = psutil.TimeoutExpired(120)
            self.assertEqual(restart(123, '.'), 1)
            launch.assert_not_called()
