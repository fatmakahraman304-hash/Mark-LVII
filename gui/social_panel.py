"""On-demand views of the official websites, inside the central HUD."""

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from core.social_sites import SITES
from gui.style import btn_css

try:
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PyQt6.QtWebEngineWidgets import QWebEngineView
except ImportError:
    QWebEngineView = None


def permitted_url(url, site):
    return (
        url.scheme() == "https"
        and url.host().lower() in SITES[site][2]
        and url.port(443) == 443
        and not url.userInfo()
    )


if QWebEngineView is not None:
    class SocialPage(QWebEnginePage):
        blocked = pyqtSignal()

        def __init__(self, profile, view, site):
            super().__init__(profile, view)
            self.site = site
            self.newWindowRequested.connect(self._open_here)

        def acceptNavigationRequest(self, url, navigation_type, is_main_frame):
            if not is_main_frame:
                return True
            if permitted_url(url, self.site):
                return True
            self.blocked.emit()
            return False

        def _open_here(self, request):
            url = request.requestedUrl()
            if request.isUserInitiated() and permitted_url(url, self.site):
                self.setUrl(url)


class SocialPanel(QWidget):
    back_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._views = {}
        self._buttons = {}
        self._site = ""
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        for key, (label, _, _) in SITES.items():
            button = self._button(label, lambda checked=False, site=key: self.open_site(site))
            self._buttons[key] = button
            row.addWidget(button)
        row.addStretch()
        self._retry = self._button("Yenile", self._reload)
        row.addWidget(self._retry)
        row.addWidget(self._button("CORE’a dön", self.back_requested.emit))
        layout.addLayout(row)
        self._status = QLabel()
        self._status.setWordWrap(True)
        self._status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self._status)
        self._browser = self._button("Tarayıcıda aç", self._open_external)
        self._browser.hide()
        layout.addWidget(self._browser, alignment=Qt.AlignmentFlag.AlignLeft)
        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack, 1)

    @staticmethod
    def _button(text, action):
        button = QPushButton(text)
        button.setMinimumHeight(32)
        button.setStyleSheet(btn_css("dim", align="center"))
        button.clicked.connect(action)
        return button

    def open_site(self, site):
        label, address, _ = SITES[site]
        self._site = site
        for key, button in self._buttons.items():
            button.setStyleSheet(btn_css("primary" if key == site else "dim", align="center"))
        self._retry.setEnabled(QWebEngineView is not None)
        if QWebEngineView is None:
            self._status.setText("Gömülü web görünümü eksik. JARVIS kurulumunu yeniden çalıştır.")
            self._browser.show()
            return
        if site not in self._views:
            view = QWebEngineView(self._stack)
            # Separate site storage, alive until the application closes.
            profile = QWebEngineProfile("jarvis-social-" + site, QApplication.instance())
            page = SocialPage(profile, view, site)
            view.setPage(page)
            self._stack.addWidget(view)
            self._views[site] = [view, "Yükleniyor…", False]
            view.loadStarted.connect(lambda: self._set_status(site, "Yükleniyor…"))
            view.loadFinished.connect(lambda ok: self._loaded(site, ok))
            page.blocked.connect(lambda: self._set_status(site, "Bağlantı bu hizmetin dışına çıkıyor.", True))
            view.setUrl(QUrl(address))
        self._stack.setCurrentWidget(self._views[site][0])
        self._refresh_status()

    def _set_status(self, site, message, external=False):
        self._views[site][1:] = [message, external]
        if site == self._site:
            self._refresh_status()

    def _refresh_status(self):
        _, message, external = self._views[self._site]
        self._status.setText(message)
        self._status.setVisible(bool(message))
        self._browser.setVisible(external)

    def _loaded(self, site, ok):
        message = "" if ok else "Site yüklenemedi. Yenile veya tarayıcıda aç."
        self._set_status(site, message, not ok)

    def _reload(self):
        entry = self._views.get(self._site)
        if entry:
            view = entry[0]
            if permitted_url(view.url(), self._site):
                view.reload()
            else:
                view.setUrl(QUrl(SITES[self._site][1]))

    def _open_external(self):
        if self._site:
            QDesktopServices.openUrl(QUrl(SITES[self._site][1]))
