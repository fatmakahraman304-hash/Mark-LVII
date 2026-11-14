"""Categorised settings with accessible, draggable switches."""
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (QAbstractButton, QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QWidget, QStackedWidget, QFrame)
from gui.theme import C
from gui.style import px_font


class Toggle(QAbstractButton):
    def __init__(self, title):
        super().__init__()
        self.setCheckable(True)
        self.setFixedSize(54, 30)
        self.setAccessibleName(title)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(C.PRI if self.isChecked() else C.BORDER))
        p.drawRoundedRect(QRectF(1, 2, 52, 26), 13, 13)
        p.setBrush(QColor(C.BG if self.isChecked() else C.WHITE))
        p.drawEllipse(QRectF(29 if self.isChecked() else 5, 6, 18, 18))
        if self.hasFocus():
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QColor(C.WHITE))
            p.drawRoundedRect(QRectF(0.5, .5, 53, 29), 14, 14)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().x()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._start is not None and abs(event.position().x() - self._start) > 5:
            self.setDown(False)
            self.setChecked(event.position().x() > self._start)
            self.clicked.emit(self.isChecked())
        else:
            super().mouseReleaseEvent(event)
        self._start = None


class SettingsPage(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        from memory import config_manager as cfg
        self.setWindowTitle('J.A.R.V.I.S — Ayarlar')
        available = self.screen().availableGeometry()
        self.resize(min(980, available.width()-80), min(650, available.height()-100))
        self.setFont(px_font(13))
        self.setStyleSheet(f'''
            QDialog {{ background: {C.BG}; }}
            QLabel {{ color: {C.TEXT}; background: transparent; }}
            QWidget#page, QWidget#body {{ background: {C.BG}; }}
            QFrame#card {{ background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 12px; }}
            QFrame#nav {{ background: {C.PANEL}; border-radius: 14px; }}
            QPushButton {{ color: {C.TEXT}; background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 8px; padding: 9px 14px; }}
            QPushButton:hover {{ border-color: {C.PRI}; color: {C.WHITE}; }}
            QPushButton#category {{ text-align: left; border: none; background: transparent; padding: 13px; }}
            QPushButton#category:checked {{ background: {C.PRI_GHO}; color: {C.PRI}; }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{ background: transparent; width: 6px; margin: 2px; }}
            QScrollBar::handle:vertical {{ background: {C.BORDER_B}; border-radius: 3px; min-height: 25px; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        ''')
        root = QVBoxLayout(self)
        root.setContentsMargins(26, 22, 26, 20)
        root.setSpacing(22)
        top = QHBoxLayout()
        heading = QVBoxLayout()
        brand = QLabel('J.A.R.V.I.S  /  KONTROL MERKEZİ')
        brand.setFont(px_font(10, spacing=2))
        brand.setStyleSheet(f'color: {C.PRI};')
        heading.addWidget(brand)
        title = QLabel('Ayarlar')
        title.setFont(px_font(30))
        heading.addWidget(title)
        top.addLayout(heading)
        top.addStretch()
        close = QPushButton('Kapat  ×')
        close.clicked.connect(self.close)
        top.addWidget(close, alignment=Qt.AlignmentFlag.AlignTop)
        root.addLayout(top)
        content = QHBoxLayout()
        content.setSpacing(24)
        nav = QFrame()
        nav.setObjectName('nav')
        nav.setFixedWidth(190)
        navigation = QVBoxLayout(nav)
        navigation.setContentsMargins(10, 16, 10, 16)
        navigation.setSpacing(6)
        content.addWidget(nav)
        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)
        root.addLayout(content, 1)
        note = QLabel('Değişiklikler anında uygulanır.  •  Sürgü sağda: açık, solda: kapalı')
        note.setFont(px_font(11))
        note.setStyleSheet(f'color: {C.TEXT_DIM};')
        root.addWidget(note)
        self.syncs, self.categories = [], []
        def page(name, subtitle):
            index = self.stack.count()
            button = QPushButton(name)
            button.setObjectName('category')
            button.setCheckable(True)
            self.categories.append(button)
            navigation.addWidget(button)
            def select():
                self.stack.setCurrentIndex(index)
                for b in self.categories:
                    b.setChecked(b is button)
            button.clicked.connect(select)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            body = QWidget()
            body.setObjectName('body')
            rows = QVBoxLayout(body)
            rows.setContentsMargins(0, 0, 8, 0)
            rows.setSpacing(12)
            label = QLabel(name)
            label.setFont(px_font(22))
            rows.addWidget(label)
            sub = QLabel(subtitle)
            sub.setWordWrap(True)
            sub.setStyleSheet(f'color: {C.TEXT_DIM}; margin-bottom: 8px;')
            rows.addWidget(sub)
            rows.addStretch()
            scroll.setWidget(body)
            self.stack.addWidget(scroll)
            return rows
        def card(rows, title, detail):
            frame = QFrame()
            frame.setObjectName('card')
            row = QHBoxLayout(frame)
            row.setContentsMargins(18, 17, 18, 17)
            row.setSpacing(18)
            text = QVBoxLayout()
            text.setSpacing(6)
            title_lbl = QLabel(title)
            title_lbl.setFont(px_font(14))
            text.addWidget(title_lbl)
            description = QLabel(detail)
            description.setWordWrap(True)
            description.setFont(px_font(11))
            description.setStyleSheet(f'color: {C.TEXT_DIM};')
            text.addWidget(description)
            row.addLayout(text, 1)
            rows.insertWidget(rows.count()-1, frame)
            return row
        def switch(rows, title, detail, getter, action):
            row = card(rows, title, detail)
            control = Toggle(title)
            state = QLabel()
            state.setFont(px_font(10))
            state.setMinimumWidth(38)
            row.addWidget(state)
            row.addWidget(control)
            def sync():
                if control.isDown():
                    return
                value = bool(getter())
                control.setChecked(value)
                state.setText('Açık' if value else 'Kapalı')
                state.setStyleSheet(f'color: {C.PRI if value else C.TEXT_DIM};')
            def change(value):
                if bool(value) != bool(getter()):
                    action()
                sync()
            control.clicked.connect(change)
            self.syncs.append(sync)
            sync()
        def action(rows, title, detail, callback):
            row = card(rows, title, detail)
            button = QPushButton('Aç  →')
            button.setAccessibleName(title)
            def open_panel():
                self.hide()
                callback()
            button.clicked.connect(open_panel)
            row.addWidget(button)
        general = page('Genel', 'Başlangıç ve günlük kullanım tercihlerin.')
        switch(general, 'Windows ile başlat', 'Bilgisayar açıldığında JARVIS hazır olsun.', owner._check_autostart, owner._toggle_autostart)
        switch(general, 'Günlük özet', 'Günlük bilgilendirme rutinini etkinleştir.', cfg.get_brief_enabled, owner._toggle_brief)
        action(general, 'Masaüstü kısayolu', 'JARVIS’e masaüstünden hızlı eriş.', owner._create_desktop_shortcut)
        voice = page('Ses ve mikrofon', 'Dinleme şeklini ve ses cihazlarını yönet.')
        switch(voice, 'Uyandırma kelimesi', 'Seslenerek uyandır. Gerekirse model kurulumu açılır.', lambda: owner._wake_state().get('enabled', False), owner._toggle_wake_word)
        switch(voice, 'Basılı tutarak konuş', 'Yalnızca konuşma tuşunu basılı tutarken dinle.', cfg.get_push_to_talk_enabled, owner._toggle_ptt)
        action(voice, 'Ses cihazları', 'Mikrofon ve hoparlör seçimini değiştir.', owner._open_audio_devices)
        action(voice, 'Uyut / uyandır', 'Geçerli dinleme durumunu değiştir.', owner._tap_wake_manual)
        look = page('Görünüm', 'JARVIS’in görünümünü kendine göre düzenle.')
        switch(look, 'Tam ekran', 'Arayüzü ekranın tamamında göster.', owner.isFullScreen, owner._toggle_fullscreen)
        action(look, 'Kişiselleştirme', 'Renkleri ve asistan kimliğini düzenle.', owner._open_customize)
        action(look, 'Merkez görünümü', 'CORE ile animasyonlu yüz arasında geçiş yap.', owner._toggle_hud_style)
        brain = page('Zekâ ve hafıza', 'Modellerini ve asistanın hatırladıklarını yönet.')
        action(brain, 'Motor ve sağlayıcılar', 'Yapay zekâ modelleri ve bağlantı ayarları.', owner._open_providers)
        action(brain, 'Hafıza', 'Kaydedilmiş bilgileri görüntüle ve düzenle.', owner._open_memory_panel)
        extras = page('Bağlantılar', 'Ek yetenekler ve uzaktan erişim.')
        action(extras, 'Eklentiler', 'Kullanılabilir yetenekleri yönet.', owner._open_plugin_manager)
        action(extras, 'Eklenti ayarları', 'Eklentilere özel seçenekleri düzenle.', owner._open_plugin_settings)
        action(extras, 'Uzaktan kontrol', 'Uzaktan erişim seçeneklerini aç.', owner._open_remote)
        navigation.addStretch()
        self.categories[0].setChecked(True)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(700)

    def refresh(self):
        if self.isVisible():
            for sync in self.syncs:
                sync()
