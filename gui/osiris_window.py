"""Optional OSIRIS map window. Construct and use only on the Qt GUI thread.

When PyQt6-WebEngine is unavailable, open the public/loopback map in the
system browser instead. No WebEngine import or window is created at startup.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget,
)

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None


def _allowed_url(address: str) -> bool:
    """Never let tool-provided arbitrary pages appear as trusted OSIRIS."""
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


class OsirisWindow(QMainWindow):
    """One re-usable top-level window, parented to the main JARVIS window."""

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("JARVIS — OSIRIS DÜNYA KOMUTA MERKEZİ")
        self.resize(1180, 760)
        self._url = "https://osirisai.live/"
        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(6, 6, 6, 6)

        header = QHBoxLayout()
        label = QLabel("🌍 OSIRIS — Dünya Komuta Merkezi")
        label.setStyleSheet("font-weight: bold; color: #70dae9;")
        header.addWidget(label)
        header.addStretch()

        browser_button = QPushButton("Tarayıcıda aç")
        browser_button.clicked.connect(self._open_external)
        header.addWidget(browser_button)

        close_button = QPushButton("Kapat")
        close_button.clicked.connect(self.hide)
        header.addWidget(close_button)
        layout.addLayout(header)

        self._status = QLabel("Harita hazırlanıyor…")
        self._status.setStyleSheet("color: #9ebbc5;")
        layout.addWidget(self._status)

        self._view = None
        if QWebEngineView is not None:
            try:
                self._view = QWebEngineView(root)
                self._view.loadFinished.connect(self._loaded)
                layout.addWidget(self._view, stretch=1)
            except Exception:
                # Keep JARVIS usable when QtWebEngine itself fails to start.
                self._view = None

        if self._view is None:
            note = QLabel(
                "Gömülü harita için isteğe bağlı PyQt6-WebEngine eksik. "
                "Harita sistem tarayıcısında açılacaktır."
            )
            note.setWordWrap(True)
            layout.addWidget(note, stretch=1)

        self.setCentralWidget(root)

    def navigate(self, address: str) -> bool:
        if not _allowed_url(address):
            self._status.setText("Güvenlik: izin verilmeyen OSIRIS adresi.")
            return False
        self._url = address
        if self._view is None:
            ok = QDesktopServices.openUrl(QUrl(address))
            self._status.setText(
                "Tarayıcı açma isteği gönderildi." if ok
                else "Sistem tarayıcısı açılamadı."
            )
            return bool(ok)
        self._status.setText("OSIRIS haritası yükleniyor…")
        self._view.load(QUrl(address))
        return True  # Queued, *not* proof the page loaded.

    def _loaded(self, success: bool) -> None:
        self._status.setText(
            "OSIRIS sayfası yüklendi." if success
            else "OSIRIS yüklenemedi. İnternet veya yerel sunucuyu kontrol edin."
        )

    def _open_external(self) -> None:
        QDesktopServices.openUrl(QUrl(self._url))
