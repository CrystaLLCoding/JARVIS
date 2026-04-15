import sys
import webbrowser
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

import license as lic


# ============================================================
#  Ссылка на страницу оплаты (Payme / Click / ваш лендинг)
# ============================================================
PAYMENT_URL = "https://your-payment-page.com"   # <-- замените на реальную ссылку


class ActivateWorker(QThread):
    """Выполняет активацию в фоне чтобы не зависал UI."""
    finished = pyqtSignal(dict)

    def __init__(self, key):
        super().__init__()
        self.key = key

    def run(self):
        result = lic.activate_license(self.key)
        self.finished.emit(result)


class LicenseDialog(QDialog):
    def __init__(self, parent=None, status_message: str = ""):
        super().__init__(parent)
        self.setWindowTitle("J.A.R.V.I.S — Активация лицензии")
        self.setFixedSize(520, 400)
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self._apply_style()
        self._build_ui(status_message)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1117;
                color: white;
            }
            QLabel {
                color: #c9d1d9;
            }
            QLineEdit {
                background-color: #161b22;
                border: 2px solid #30363d;
                border-radius: 8px;
                padding: 12px 16px;
                color: #e6edf3;
                font-size: 17px;
                font-family: "Consolas", monospace;
                letter-spacing: 3px;
            }
            QLineEdit:focus {
                border-color: #388bfd;
            }
            QPushButton#activate_btn {
                background-color: #238636;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#activate_btn:hover { background-color: #2ea043; }
            QPushButton#activate_btn:disabled { background-color: #3d4450; color: #8b949e; }
            QPushButton#buy_btn {
                background-color: #1f6feb;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton#buy_btn:hover { background-color: #388bfd; }
            QFrame#separator { color: #30363d; }
        """)

    def _build_ui(self, status_message: str):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(36, 30, 36, 30)

        # --- Заголовок ---
        title = QLabel("🤖  J.A.R.V.I.S — Активация")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        title.setStyleSheet("color: #58a6ff; margin-bottom: 4px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        sub = QLabel("Для доступа к ассистенту введите лицензионный ключ.")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(sub)

        # --- Разделитель ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #30363d;")
        layout.addWidget(line)

        # --- Если есть сообщение об ошибке (просроченный ключ и т.д.) ---
        if status_message:
            err_label = QLabel(f"⚠️  {status_message}")
            err_label.setAlignment(Qt.AlignCenter)
            err_label.setWordWrap(True)
            err_label.setStyleSheet("color: #f0883e; font-size: 12px; font-weight: bold;")
            layout.addWidget(err_label)

        # --- Поле ввода ключа ---
        key_hint = QLabel("Лицензионный ключ:")
        key_hint.setStyleSheet("font-size: 12px; color: #8b949e;")
        layout.addWidget(key_hint)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("JRVS-XXXX-XXXX-XXXX-XXXX")
        self.key_input.setAlignment(Qt.AlignCenter)
        self.key_input.returnPressed.connect(self._on_activate)
        layout.addWidget(self.key_input)

        # --- Кнопки ---
        self.activate_btn = QPushButton("✅  Активировать")
        self.activate_btn.setObjectName("activate_btn")
        self.activate_btn.clicked.connect(self._on_activate)
        layout.addWidget(self.activate_btn)

        buy_btn = QPushButton("💳  Купить подписку — 99 000 сум / мес")
        buy_btn.setObjectName("buy_btn")
        buy_btn.clicked.connect(lambda: webbrowser.open(PAYMENT_URL))
        layout.addWidget(buy_btn)

        # --- Статус ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(32)
        layout.addWidget(self.status_label)

        # --- ID компьютера (для поддержки) ---
        hwid = lic.get_hwid()
        hwid_label = QLabel(f"ID вашего ПК: {hwid}")
        hwid_label.setAlignment(Qt.AlignCenter)
        hwid_label.setStyleSheet("color: #484f58; font-size: 10px; font-family: Consolas;")
        layout.addWidget(hwid_label)

    def _on_activate(self):
        key = self.key_input.text().strip()
        if not key:
            self._set_status("❌  Введите ключ!", error=True)
            return

        # Форматируем ввод автоматически (убираем лишние символы)
        clean = key.replace(" ", "").replace("-", "")
        if len(clean) == 16:
            key = f"JRVS-{clean[0:4]}-{clean[4:8]}-{clean[8:12]}-{clean[12:16]}"
            self.key_input.setText(key)

        self.activate_btn.setText("⏳  Проверяю...")
        self.activate_btn.setEnabled(False)
        self._set_status("Подключаюсь к серверу...", error=False)

        self.worker = ActivateWorker(key)
        self.worker.finished.connect(self._on_activate_result)
        self.worker.start()

    def _on_activate_result(self, result: dict):
        self.activate_btn.setText("✅  Активировать")
        self.activate_btn.setEnabled(True)

        if result.get("success"):
            expires = result.get("expires_at", "")[:10]
            self._set_status(f"✅  Активировано! Подписка действует до: {expires}", error=False)
            # Небольшая задержка и закрываем диалог
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(1500, self.accept)
        else:
            msg = result.get("message", "Неизвестная ошибка.")
            self._set_status(f"❌  {msg}", error=True)

    def _set_status(self, text: str, error: bool):
        color = "#f85149" if error else "#3fb950"
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
