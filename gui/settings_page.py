"""Unified settings, using existing handlers and confirmed setting values."""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QScrollArea, QWidget
from gui.theme import C
from gui.style import px_font


class SettingsPage(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        from memory import config_manager as cfg
        self.setWindowTitle('J.A.R.V.I.S — Ayarlar')
        self.resize(690, 720)
        self.setStyleSheet(f'QDialog, QWidget {{ background: {C.BG}; color: {C.TEXT}; }} QPushButton {{ background: {C.PANEL2}; border: 1px solid {C.BORDER_B}; border-radius: 8px; padding: 10px; }}')
        self.setFont(px_font(13))
        layout = QVBoxLayout(self)
        heading = QLabel('AYARLAR')
        heading.setFont(px_font(24))
        layout.addWidget(heading)
        layout.addWidget(QLabel('Sola: kapalı  •  Sağa: açık'))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        rows = QVBoxLayout(body)
        self.syncs = []
        def switch(title, detail, getter, action):
            row = QHBoxLayout()
            texts = QVBoxLayout()
            texts.addWidget(QLabel(title))
            hint = QLabel(detail)
            hint.setWordWrap(True)
            hint.setStyleSheet(f'color: {C.TEXT_DIM};')
            texts.addWidget(hint)
            row.addLayout(texts, 1)
            state = QLabel()
            row.addWidget(state)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(0, 1)
            slider.setFixedSize(66, 32)
            slider.setAccessibleName(title)
            slider.setStyleSheet(f'QSlider::groove:horizontal {{ height: 24px; border-radius: 12px; background: {C.PANEL2}; }} QSlider::sub-page:horizontal {{ background: {C.PRI}; border-radius: 12px; }} QSlider::handle:horizontal {{ width: 24px; background: {C.WHITE}; border-radius: 12px; }}')
            def sync():
                if slider.isSliderDown():
                    return
                value = bool(getter())
                slider.blockSignals(True)
                slider.setValue(int(value))
                slider.blockSignals(False)
                state.setText('Açık' if value else 'Kapalı')
            def change(value):
                if bool(value) != bool(getter()):
                    action()
                sync()
            slider.valueChanged.connect(change)
            row.addWidget(slider)
            rows.addLayout(row)
            self.syncs.append(sync)
            sync()
        switch('Windows ile başlat', 'Bilgisayar açıldığında JARVIS başlasın.', owner._check_autostart, owner._toggle_autostart)
        switch('Günlük özet', 'Günlük bilgilendirme rutini.', cfg.get_brief_enabled, owner._toggle_brief)
        switch('Uyandırma kelimesi', 'Seslenerek uyandır. Gerekirse model kurulumu açılır.', lambda: owner._wake_state().get('enabled', False), owner._toggle_wake_word)
        switch('Basılı tutarak konuş', 'Mikrofon için konuşma tuşunu basılı tut.', cfg.get_push_to_talk_enabled, owner._toggle_ptt)
        switch('Tam ekran', 'Arayüz tüm ekranı kaplasın.', owner.isFullScreen, owner._toggle_fullscreen)
        def action(label, callback):
            button = QPushButton(label)
            def open_panel():
                self.hide()
                callback()
            button.clicked.connect(open_panel)
            rows.addWidget(button)
        for label, callback in [
            ('Görünüm ve kişiselleştirme', owner._open_customize),
            ('Ses ve mikrofon cihazları', owner._open_audio_devices),
            ('Yapay zekâ motoru ve sağlayıcılar', owner._open_providers),
            ('Hafıza', owner._open_memory_panel),
            ('Eklentiler', owner._open_plugin_manager),
            ('Eklenti ayarları', owner._open_plugin_settings),
            ('Uzaktan kontrol', owner._open_remote),
            ('Masaüstü kısayolu oluştur', owner._create_desktop_shortcut),
            ('CORE / animasyonlu yüz değiştir', owner._toggle_hud_style),
            ('Uyut / uyandır', owner._tap_wake_manual)]:
            action(label, callback)
        scroll.setWidget(body)
        layout.addWidget(scroll)
        close = QPushButton('Kapat')
        close.clicked.connect(self.close)
        layout.addWidget(close)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(700)

    def refresh(self):
        if self.isVisible():
            for sync in self.syncs:
                sync()
