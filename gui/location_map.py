"""Non-blocking city map. Location is approximate, derived from this device's IP."""
from __future__ import annotations

import json
import math
import time

from PyQt6.QtCore import QPointF, QRectF, QStandardPaths, Qt, QTimer, QUrl
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkDiskCache, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from gui.style import px_font
from gui.theme import C

USER_AGENT = b"JarvisMuratMap/1.0 (+https://github.com/fatmakahraman304-hash/Mark-LVII)"
TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
LOCATION_URL = "https://ipwho.is/"


def location_from_json(data: bytes) -> tuple[str, float, float]:
    value = json.loads(data)
    if not isinstance(value, dict) or value.get("success") is not True:
        raise ValueError("Location service unavailable")
    lat, lon = float(value["latitude"]), float(value["longitude"])
    if not math.isfinite(lat) or not math.isfinite(lon) or not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Invalid coordinates")
    city = str(value.get("city") or value.get("region") or "").strip()
    if not city:
        raise ValueError("City unavailable")
    return city, lat, lon


def tile_position(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    lat = max(-85.05112878, min(85.05112878, lat))
    n = 2 ** zoom
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


class CityMap(QWidget):
    """Only visible OSM tiles are requested; HTTP caching respects server headers."""

    def __init__(self, network, parent=None):
        super().__init__(parent)
        self.network = network
        self.center = None
        self.zoom = 11
        self.tiles = {}
        self.pending = set()
        self.failed = {}
        self.setMinimumHeight(40)
        self._reload = QTimer(self)
        self._reload.setSingleShot(True)
        self._reload.timeout.connect(self.load_tiles)

    def set_location(self, lat, lon):
        self.center = tile_position(lat, lon, self.zoom)
        self.load_tiles()
        self.update()

    def visible_tiles(self):
        if self.center is None:
            return []
        cx, cy = self.center
        left, top = cx * 256 - self.width() / 2, cy * 256 - self.height() / 2
        n = 2 ** self.zoom
        return [((self.zoom, x % n, y), x * 256 - left, y * 256 - top)
                for x in range(math.floor(left / 256), math.floor((left + self.width()) / 256) + 1)
                for y in range(max(0, math.floor(top / 256)), min(n - 1, math.floor((top + self.height()) / 256)) + 1)]

    def load_tiles(self):
        visible = self.visible_tiles()
        wanted = {key for key, _, _ in visible}
        self.tiles = {key: value for key, value in self.tiles.items() if key in wanted}
        for key, _, _ in visible:
            if key in self.tiles or key in self.pending or time.monotonic() - self.failed.get(key, -1000) < 60:
                continue
            z, x, y = key
            request = QNetworkRequest(QUrl(TILE_URL.format(z=z, x=x, y=y)))
            request.setRawHeader(b"User-Agent", USER_AGENT)
            request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, QNetworkRequest.CacheLoadControl.PreferCache)
            request.setTransferTimeout(12000)
            reply = self.network.get(request)
            self.pending.add(key)
            reply.finished.connect(lambda reply=reply, key=key: self._tile_ready(reply, key))

    def _tile_ready(self, reply, key):
        self.pending.discard(key)
        pix = QPixmap()
        if reply.error() == QNetworkReply.NetworkError.NoError and pix.loadFromData(bytes(reply.readAll())):
            if key in {item[0] for item in self.visible_tiles()}:
                self.tiles[key] = pix
            self.failed.pop(key, None)
        else:
            self.failed[key] = time.monotonic()
        reply.deleteLater()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reload.start(200)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(C.DARK))
        for key, x, y in self.visible_tiles():
            if key in self.tiles:
                p.drawPixmap(QPointF(x, y), self.tiles[key])
        if self.tiles:
            # Subtle tint keeps street labels readable in the dark HUD.
            p.fillRect(self.rect(), QColor(8, 14, 25, 28))
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(C.WHITE), 2))
            p.setBrush(QColor(C.PRI_DIM))
            p.drawEllipse(QPointF(self.width() / 2, self.height() / 2), 7, 7)
            p.setPen(QPen(QColor(C.PRI_DIM), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(self.width() / 2, self.height() / 2), 18, 18)
        else:
            p.setPen(QColor(C.TEXT_MED))
            p.setFont(px_font(11))
            message = "Konum bekleniyor" if self.center is None else "Harita yükleniyor…" if self.pending else "Harita yüklenemedi"
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, message)
        p.end()


class LocationPanel(QWidget):
    def __init__(self, parent=None, *, auto_start=True):
        super().__init__(parent)
        self.network = QNetworkAccessManager(self)
        cache = QNetworkDiskCache(self.network)
        cache.setCacheDirectory(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation) + "/jarvis-map")
        cache.setMaximumCacheSize(32 * 1024 * 1024)
        self.network.setCache(cache)
        self._busy = False
        self._has_location = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.city = QLabel("Şehrin bulunuyor…")
        self.city.setTextFormat(Qt.TextFormat.PlainText)
        self.city.setWordWrap(True)
        self.city.setFont(px_font(16))
        self.city.setStyleSheet(f"color: {C.WHITE}; background: transparent;")
        layout.addWidget(self.city)
        self.map = CityMap(self.network)
        layout.addWidget(self.map, 1)
        self.status = QLabel("IP üzerinden yaklaşık konum")
        self.status.setWordWrap(True)
        self.status.setFont(px_font(10))
        self.status.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        layout.addWidget(self.status)
        attribution = QLabel(f'<a style="color: {C.TEXT_MED};" href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a>')
        attribution.setOpenExternalLinks(True)
        attribution.setFont(px_font(9))
        attribution.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        layout.addWidget(attribution)
        self.setToolTip("Bu bilgisayarın internet bağlantısından yaklaşık şehir konumu. VPN veya operatör nedeniyle farklı görünebilir. Beş dakikada bir yenilenir.")
        self.timer = QTimer(self)
        self.timer.setInterval(300000)
        self.timer.timeout.connect(self.refresh)
        if auto_start:
            self.timer.start()
            QTimer.singleShot(0, self.refresh)

    def refresh(self):
        if self._busy:
            return
        self._busy = True
        request = QNetworkRequest(QUrl(LOCATION_URL))
        request.setRawHeader(b"User-Agent", USER_AGENT)
        request.setTransferTimeout(10000)
        request.setAttribute(QNetworkRequest.Attribute.CacheLoadControlAttribute, QNetworkRequest.CacheLoadControl.AlwaysNetwork)
        reply = self.network.get(request)
        reply.finished.connect(lambda: self._location_ready(reply))

    def _location_ready(self, reply):
        self._busy = False
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                raise ValueError("Network unavailable")
            city, lat, lon = location_from_json(bytes(reply.readAll()))
            self.city.setText(city)
            self.status.setText("Yaklaşık konum · " + time.strftime("%H:%M"))
            self._has_location = True
            self.map.set_location(lat, lon)
        except (ValueError, TypeError, KeyError, OverflowError):
            if not self._has_location:
                self.city.setText("Konum alınamadı")
            self.status.setText("Bağlantı yok · Son konum" if self._has_location else "İnternet bağlantısı bekleniyor")
        finally:
            reply.deleteLater()
