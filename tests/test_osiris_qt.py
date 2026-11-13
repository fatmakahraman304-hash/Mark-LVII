"""Real Qt/WebEngine transport against an offline adapter fixture (not the OSIRIS globe)."""
import json
import os
from pathlib import Path
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt6.QtCore import QCoreApplication, Qt
QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from gui.osiris_window import OsirisWindow, QWebEngineView, _allowed_url

FIXTURE = b"""<!doctype html><html><body>OSIRIS adapter test fixture<script type="module">
import {installJarvisBridge} from '/bridge.mjs';
let layers={earthquakes:false,flights:true};
let view={lat:20,lng:0,zoom:2.5};
installJarvisBridge({
 layers:()=>layers,view:()=>view,
 setLayers:(on,off)=>setTimeout(()=>{on.forEach(k=>layers[k]=true);off.forEach(k=>layers[k]=false)},20),
 flyTo:(lat,lng,zoom)=>setTimeout(()=>view={lat,lng,zoom},20),
 geocode:async()=>({lat:35.12,lng:33.94})
});
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/?") or self.path == "/":
            content, mime = FIXTURE, "text/html"
        elif self.path == "/bridge.mjs":
            content = (Path(__file__).resolve().parents[1] / "integrations/osiris/jarvis-bridge.mjs").read_bytes()
            mime = "text/javascript"
        else:
            self.send_error(404); return
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
    def log_message(self, *args): pass


@unittest.skipIf(QWebEngineView is None, "PyQt6-WebEngine required")
class QtBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(["jarvis-osiris-test"])
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = "http://127.0.0.1:%d/" % cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def wait(self, condition, timeout=12):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertTrue(condition())

    def test_same_document_commands_and_results(self):
        win = OsirisWindow()
        self.addCleanup(win.close)
        results, loads = [], []
        win.result.connect(results.append)
        win._view.loadStarted.connect(lambda: loads.append(True))
        self.assertTrue(win.navigate(self.url + "?layers=none"))
        win.show()
        self.wait(lambda: win._loaded_ok)
        for command in ({"kind":"layers","layers":["earthquakes"]},
                        {"kind":"locate","place":"Gazimağusa"},
                        {"kind":"zoom","delta":1},
                        {"kind":"status"}):
            count=len(results)
            self.assertTrue(win.command(command))
            self.wait(lambda: len(results)>count)
            self.assertEqual(results[-1]["status"], "done", results[-1])
        count=len(results)
        win.navigate(self.url + "?layers=flights")
        self.wait(lambda: len(results)>count)
        self.assertEqual(results[-1]["state"]["layers"], ["flights"])
        self.assertEqual(len(loads), 1, "Commands must not reload the document")
        self.assertFalse(win.command({"kind":"layers","layers":["javascript:evil"]}))
        self.assertFalse(win.command({"kind":"zoom","delta":float("nan")}))
        self.assertFalse(win.navigate("https://untrusted.example/"))


class UrlTests(unittest.TestCase):
    def test_url_boundary(self):
        for url in ("file:///tmp/index.html", "https://osirisai.live.evil/", "http://192.168.1.1/",
                    "http://127.0.0.1:3000/evil", "http://user@127.0.0.1/"):
            self.assertFalse(_allowed_url(url),url)
        self.assertTrue(_allowed_url("http://127.0.0.1:3000/?layers=none"))


if __name__ == "__main__":
    unittest.main()
