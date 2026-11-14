"""Qt-only OSIRIS window with a bounded, local-origin map command bridge."""
from __future__ import annotations

import json
import secrets
import time
import uuid
from collections import deque
from urllib.parse import parse_qs, urlsplit

from PyQt6.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEnginePage
except ImportError:
    QWebEngineView = QWebEnginePage = None


def _allowed_url(address: str) -> bool:
    try:
        u = urlsplit(address)
        if u.username or u.password or u.fragment or u.path not in ("", "/"):
            return False
        if u.scheme == "https" and u.hostname == "osirisai.live":
            return u.port in (None, 443)
        if u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1", "::1"):
            return u.port is None or u.port > 0
    except ValueError:
        pass
    return False


def _origin(address: str) -> tuple:
    u = urlsplit(address)
    return u.scheme, u.hostname, u.port or (443 if u.scheme == "https" else 80)


def _local(address: str) -> bool:
    return _allowed_url(address) and urlsplit(address).scheme == "http"


if QWebEnginePage is not None:
    class MapPage(QWebEnginePage):
        """A redirect or clicked link cannot take the command bridge elsewhere."""
        def __init__(self, parent):
            super().__init__(parent)
            self.expected_origin = None

        def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
            if not is_main_frame:
                return True
            address = url.toString()
            return _allowed_url(address) and _origin(address) == self.expected_origin


class OsirisWindow(QMainWindow):
    result = pyqtSignal(object)
    back_requested = pyqtSignal()

    def __init__(self, parent=None, embedded=False):
        super().__init__(parent, Qt.WindowType.Widget if embedded else Qt.WindowType.Window)
        if embedded:
            self.setWindowFlags(Qt.WindowType.Widget)
        self._embedded = embedded
        self.setWindowTitle("JARVIS — OSIRIS DÜNYA KOMUTA MERKEZİ")
        self.resize(1180, 760)
        self._url = ""
        self._loaded_ok = False
        self._loading_now = False
        self._session = secrets.token_hex(32)
        self._bound = False
        self._queue = deque()
        self._active = None
        self._callback_pending = False
        self._deadline = 0.0
        self._epoch = 0
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(6, 6, 6, 6)
        header = QHBoxLayout()
        header.addWidget(QLabel("OSIRIS — Dünya Komuta Merkezi"))
        header.addStretch()
        actions = (("CORE’a dön", self.back_requested.emit),) if embedded else (("Tarayıcıda aç", self._open_external), ("Kapat", self.hide))
        for text, slot in actions:
            button = QPushButton(text)
            button.clicked.connect(slot)
            header.addWidget(button)
        layout.addLayout(header)
        self._status = QLabel("Harita hazırlanıyor…")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)
        self._view = None
        if QWebEngineView is not None:
            self._view = QWebEngineView(root)
            self._view.setPage(MapPage(self._view))
            self._view.loadStarted.connect(self._loading)
            self._view.loadFinished.connect(self._loaded)
            self._view.page().renderProcessTerminated.connect(self._renderer_failed)
            layout.addWidget(self._view, 1)
        else:
            note = QLabel("Gömülü harita için PyQt6-WebEngine gerekli. URL komutları tarayıcıda açılabilir; anlık kontrol kullanılamaz.")
            note.setWordWrap(True)
            layout.addWidget(note, 1)
        self.setCentralWidget(root)
        self._timer = QTimer(self)
        self._timer.setInterval(150)
        self._timer.timeout.connect(self._tick)

    def _emit_result(self, result):
        self.result.emit(result)
        labels = {"done": "Harita durumu doğrulandı.", "failed": "Harita komutu başarısız.",
                  "unverified": "Harita komutu doğrulanamadı."}
        self._status.setText(labels.get(result.get("status"), "Harita hazırlanıyor…") +
                             (" " + str(result["error"]) if result.get("error") else ""))

    def _fail_all(self, reason):
        commands = ([self._active] if self._active else []) + list(self._queue)
        self._active = None
        self._queue.clear()
        for command in commands:
            self._emit_result({"id": command["id"], "status": "failed", "error": reason})
        self._timer.stop()

    def _loading(self):
        self._loading_now = True
        self._epoch += 1
        self._session = secrets.token_hex(32)
        self._bound = False
        self._loaded_ok = False
        self._callback_pending = False
        if self._active:
            self._fail_all("Sayfa komut sırasında yeniden yüklendi.")
        self._deadline = time.monotonic() + 30

    def _loaded(self, success):
        self._loading_now = False
        self._loaded_ok = success
        self._status.setText("OSIRIS sayfası yüklendi." if success else "OSIRIS yüklenemedi.")
        if not success:
            self._fail_all("Sayfa yüklenemedi.")
        elif self._queue:
            self._timer.start()

    def _renderer_failed(self, *args):
        self._loaded_ok = False
        self._bound = False
        self._epoch += 1
        self._callback_pending = False
        self._fail_all("Harita görüntüleyicisi kapandı; haritayı yeniden açın.")

    def navigate(self, address: str) -> bool:
        if not _allowed_url(address):
            self._status.setText("İzin verilmeyen OSIRIS adresi.")
            return False
        if self._view is None:
            self._url = address
            if self._embedded:
                self._status.setText("Harita için PyQt6-WebEngine kurulmalı. JARVIS kurulumunu yeniden çalıştırın.")
                return True
            accepted = QDesktopServices.openUrl(QUrl(address))
            self._status.setText("Tarayıcı açma isteği gönderildi." if accepted else "Tarayıcı açılamadı.")
            return bool(accepted)
        same_local = bool(self._url and _local(address) and _origin(address) == _origin(self._url))
        layers = parse_qs(urlsplit(address).query).get("layers")
        if same_local and (self._loaded_ok or self._loading_now) and layers:
            return self.command({"kind": "layers", "layers": [] if layers[0] == "none" else layers[0].split(",")})
        self._epoch += 1
        self._callback_pending = False
        self._fail_all("Yeni harita adresine geçildi.")
        self._loading_now = True
        self._url = address
        self._view.page().expected_origin = _origin(address)
        self._view.load(QUrl(address))
        return True

    def command(self, payload: dict) -> bool:
        if self._view is None or not _local(self._url):
            self._emit_result({"status": "failed", "error": "Anlık kontrol, köprü kurulmuş yerel OSIRIS gerektirir."})
            return False
        if not isinstance(payload, dict) or len(self._queue) >= 16:
            self._emit_result({"status": "failed", "error": "Harita komut kuyruğu dolu veya komut geçersiz."})
            return False
        # Copy only a bounded schema; never run tool-provided JavaScript.
        kind = payload.get("kind")
        command = {"id": uuid.uuid4().hex, "kind": kind}
        if kind == "layers":
            from plugins.osiris_world import ALLOWED_LAYERS
            layers = payload.get("layers")
            if not isinstance(layers, list) or len(layers) > 64 or any(not isinstance(x, str) or x not in ALLOWED_LAYERS for x in layers):
                return False
            command["layers"] = layers
        elif kind == "locate":
            place = payload.get("place")
            if not isinstance(place, str) or not 1 <= len(place.strip()) <= 120:
                return False
            command["place"] = place.strip()
        elif kind == "zoom":
            delta = payload.get("delta")
            if type(delta) not in (int, float) or not -3 <= delta <= 3:
                return False
            command["delta"] = delta
        elif kind != "status":
            return False
        self._queue.append(command)
        if not self._active:
            self._deadline = time.monotonic() + 20
        self._timer.start()
        return True

    def _js(self, expression, callback):
        epoch = self._epoch
        self._callback_pending = True
        def finished(raw):
            if epoch != self._epoch:
                return
            self._callback_pending = False
            try:
                result = json.loads(raw) if isinstance(raw, str) else None
            except (TypeError, ValueError):
                result = None
            callback(result)
        script = "JSON.stringify((() => { try { return " + expression + "; } catch (_) { return null; } })())"
        self._view.page().runJavaScript(script, finished)

    def _tick(self):
        if not self._queue and not self._active:
            self._timer.stop()
            return
        if time.monotonic() > self._deadline:
            self._epoch += 1
            self._callback_pending = False
            # Cancel delayed adapter work before it can mutate the map later.
            self._session = secrets.token_hex(32)
            self._bound = False
            token = json.dumps(self._session)
            self._view.page().runJavaScript("window.__jarvisOsiris?.bind(" + token + ")")
            self._fail_all("Yerel köprü hazır değil veya komut zaman aşımına uğradı.")
            return
        if self._callback_pending or not self._loaded_ok:
            return
        current = self._view.url().toString()
        if not _local(current) or _origin(current) != _origin(self._url):
            self._fail_all("Harita origin doğrulaması başarısız.")
            return
        token = json.dumps(self._session)
        if not self._bound:
            self._js("window.__jarvisOsiris?.version === 1 && window.__jarvisOsiris.bind(" + token + ")",
                     lambda ready: setattr(self, "_bound", ready is True))
        elif self._active is None:
            self._active = self._queue.popleft()
            self._deadline = time.monotonic() + 16
            self._js("window.__jarvisOsiris.dispatch(" + token + "," + json.dumps(self._active) + ")", self._received)
        else:
            self._js("window.__jarvisOsiris.read(" + token + "," + json.dumps(self._active["id"]) + ")", self._received)

    def _received(self, result):
        if not isinstance(result, dict) or not self._active:
            return
        if result.get("status") in ("done", "failed", "unverified"):
            if result.get("id") not in (None, self._active["id"]):
                return
            self._emit_result(result)
            self._active = None
            self._deadline = time.monotonic() + 20

    def _open_external(self):
        if self._url:
            QDesktopServices.openUrl(QUrl(self._url))
