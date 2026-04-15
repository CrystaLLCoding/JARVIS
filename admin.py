import sys
import json
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTabWidget, QListWidget, QFormLayout, QLineEdit, QComboBox, 
                             QPushButton, QMessageBox, QLabel, QGroupBox)
from PyQt5.QtCore import Qt

CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config.json')
VOICE_PACK_DIR = os.path.join(os.path.dirname(__file__), 'voice_pack')

class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J.A.R.V.I.S - Панель Администратора")
        self.resize(900, 550)
        self.config = self.load_config()
        self.available_sounds = self.get_available_sounds()
        self.initUI()
        self.load_commands_list()

    def get_available_sounds(self):
        sounds = [""]
        if os.path.exists(VOICE_PACK_DIR):
            for file in os.listdir(VOICE_PACK_DIR):
                if file.endswith(('.wav', '.mp3')):
                    sounds.append(file)
        return sorted(sounds)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"theme": "iron_man", "commands": []}

    def save_config(self):
        self.save_current_command_edits()
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Успех", "Настройки сохранены! Главный HUD J.A.R.V.I.S обновится автоматически через пару секунд.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки:\n{e}")

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # === Вкладка 1: Команды ===
        cmd_tab = QWidget()
        cmd_layout = QHBoxLayout(cmd_tab)

        # Левая панель: список команд
        left_panel = QVBoxLayout()
        self.cmd_list = QListWidget()
        self.cmd_list.itemClicked.connect(self.on_command_select)
        left_panel.addWidget(QLabel("Все доступные команды:"))
        left_panel.addWidget(self.cmd_list)
        
        btn_add = QPushButton("➕ Добавить новую")
        btn_add.clicked.connect(self.add_command)
        btn_del = QPushButton("❌ Удалить выбранную")
        btn_del.clicked.connect(self.delete_command)
        left_panel.addWidget(btn_add)
        left_panel.addWidget(btn_del)
        cmd_layout.addLayout(left_panel, 1)

        # Правая панель: форма редактирования
        right_group = QGroupBox("Редактирование выбранной команды")
        right_panel = QFormLayout(right_group)
        
        self.edit_id = QLineEdit()
        self.edit_id.setToolTip("Уникальное имя команды английскими буквами (например: open_game)")
        
        self.edit_type = QComboBox()
        self.edit_type.addItems(["cmd", "url", "tts_only", "built_in"])
        self.edit_type.setToolTip("cmd - запустить приложение\nurl - открыть ссылку\ntts_only - просто сказать текст\nbuilt_in - встроенная системная функция")
        
        self.edit_phrases = QLineEdit()
        self.edit_phrases.setToolTip("Слова, на которые отреагирует Джарвис. Разделяйте запятыми!")
        
        self.edit_value = QLineEdit()
        self.edit_value.setToolTip("Что именно открывать? Пример: start chrome, или ссылка https://youtube.com. Для built_in укажите имя функции.")
        
        self.edit_sound = QComboBox()
        self.edit_sound.addItems(self.available_sounds)
        self.edit_sound.setToolTip("Выберите звук из папки voice_pack, который Джарвис проиграет.")
        
        self.edit_reply = QLineEdit()
        self.edit_reply.setToolTip("Текст, который появится на экране и будет сказан Джарвисом.")

        right_panel.addRow("Имя (ID) команды:", self.edit_id)
        right_panel.addRow("Тип действия:", self.edit_type)
        right_panel.addRow("Фразы триггеры (через запятую):", self.edit_phrases)
        right_panel.addRow("Значение (Путь / Ссылка):", self.edit_value)
        right_panel.addRow("Звуковой файл (voice_pack/):", self.edit_sound)
        right_panel.addRow("Текст ответа на экране:", self.edit_reply)

        self.btn_apply = QPushButton("Применить изменения в список (Не забыть нажать сохранить в конце!)")
        self.btn_apply.clicked.connect(self.apply_edits_to_list)
        right_panel.addRow("", self.btn_apply)

        cmd_layout.addWidget(right_group, 2)
        self.tabs.addTab(cmd_tab, "Команды")

        # === Вкладка 2: Интерфейс ===
        ui_tab = QWidget()
        ui_layout = QFormLayout(ui_tab)

        self.ui_theme = QComboBox()
        self.ui_theme.addItems(["iron_man", "dark_neon"])
        current_theme = self.config.get("theme", "iron_man")
        if current_theme in ["iron_man", "dark_neon"]:
            self.ui_theme.setCurrentText(current_theme)

        ui_layout.addRow("Цветовая тема HUD (Голограммы):", self.ui_theme)
        
        help_text = QLabel("Iron Man - Красный и Золотой.\nDark Neon - Фиолетовый и Кибер-Синий.")
        help_text.setStyleSheet("color: gray;")
        ui_layout.addRow("", help_text)

        # --- Разделитель ---
        sep = QLabel("─" * 60)
        sep.setStyleSheet("color: #555; margin-top: 10px;")
        ui_layout.addRow("", sep)

        # --- Быстрая смена ссылки на музыку ---
        music_label = QLabel("🎵 Ссылка на музыку (команда 'включи музыку'):")
        music_label.setStyleSheet("font-weight: bold; color: #61afef; margin-top: 6px;")
        ui_layout.addRow("", music_label)

        self.music_url_edit = QLineEdit()
        self.music_url_edit.setPlaceholderText("например: https://music.yandex.uz")
        self.music_url_edit.setToolTip("Это значение — ссылка, которую Джарвис откроет по команде 'включи музыку'.")
        # Заполняем текущим значением из config
        current_music_url = self._get_music_url()
        self.music_url_edit.setText(current_music_url)
        ui_layout.addRow("URL сервиса музыки:", self.music_url_edit)

        music_hint = QLabel("Примеры: music.yandex.uz  |  music.yandex.ru  |  music.youtube.com  |  open.spotify.com")
        music_hint.setStyleSheet("color: gray; font-size: 11px;")
        ui_layout.addRow("", music_hint)

        # --- Разделитель ---
        sep2 = QLabel("─" * 60)
        sep2.setStyleSheet("color: #555; margin-top: 10px;")
        ui_layout.addRow("", sep2)

        # --- Выбор браузера ---
        browser_label = QLabel("🌐 Постоянный браузер для открытия ссылок:")
        browser_label.setStyleSheet("font-weight: bold; color: #61afef; margin-top: 6px;")
        ui_layout.addRow("", browser_label)

        self.browser_combo = QComboBox()
        self.browser_combo.addItems([
            "default (системный по умолчанию)",
            "chrome",
            "firefox",
            "edge",
            "opera",
            "yandex"
        ])
        self.browser_combo.setToolTip("Джарвис будет открывать все ссылки и поиск в этом браузере.")
        current_browser = self.config.get("browser", "default")
        # Находим подходящий пункт в списке
        for i in range(self.browser_combo.count()):
            if self.browser_combo.itemText(i).startswith(current_browser):
                self.browser_combo.setCurrentIndex(i)
                break
        ui_layout.addRow("Браузер:", self.browser_combo)

        browser_hint = QLabel("Чтобы Yandex Browser работал, он должен быть добавлен в PATH (обычно уже есть).")
        browser_hint.setStyleSheet("color: gray; font-size: 11px;")
        ui_layout.addRow("", browser_hint)

        self.tabs.addTab(ui_tab, "Интерфейс (HUD)")

        # Нижняя кнопка сохранения всего
        save_btn = QPushButton("💾 СОХРАНИТЬ ВСЕ НАСТРОЙКИ ДЛЯ J.A.R.V.I.S")
        save_btn.setStyleSheet("background-color: #2E7D32; color: white; font-size: 14px; font-weight: bold; padding: 12px; border-radius: 5px;")
        save_btn.clicked.connect(self.save_config)
        main_layout.addWidget(save_btn)

        self.current_selected_index = -1

    def load_commands_list(self):
        self.cmd_list.clear()
        for cmd in self.config.get("commands", []):
            label = f"{cmd.get('id', 'Unknown')} [{cmd.get('type','')}]"
            self.cmd_list.addItem(label)

    def on_command_select(self, item):
        self.save_current_command_edits()
        
        row = self.cmd_list.row(item)
        self.current_selected_index = row
        cmd = self.config["commands"][row]
        
        self.edit_id.setText(cmd.get("id", ""))
        self.edit_type.setCurrentText(cmd.get("type", "tts_only"))
        
        phrases = cmd.get("phrases", [])
        self.edit_phrases.setText(", ".join(phrases))
        
        self.edit_value.setText(cmd.get("value", ""))
        
        sound_val = cmd.get("sound", "")
        if sound_val in self.available_sounds:
            self.edit_sound.setCurrentText(sound_val)
        else:
            self.edit_sound.setCurrentText("")
        
        self.edit_reply.setText(cmd.get("reply", ""))

    def _get_music_url(self):
        """Возвращает текущую ссылку из команды play_music."""
        for cmd in self.config.get("commands", []):
            if cmd.get("id") == "play_music":
                return cmd.get("value", "https://music.yandex.uz")
        return "https://music.yandex.uz"

    def _set_music_url(self, url):
        """Сохраняет ссылку в команду play_music."""
        url = url.strip()
        if not url:
            return
        if not url.startswith("http"):
            url = "https://" + url
        for cmd in self.config.get("commands", []):
            if cmd.get("id") == "play_music":
                cmd["value"] = url
                return

    def save_current_command_edits(self):
        self.config["theme"] = self.ui_theme.currentText()
        # Сохраняем ссылку на музыку из поля быстрого доступа
        if hasattr(self, 'music_url_edit'):
            self._set_music_url(self.music_url_edit.text())
        # Сохраняем выбранный браузер
        if hasattr(self, 'browser_combo'):
            selected = self.browser_combo.currentText()
            # Очищаем от приписки в скобках
            browser_key = selected.split(" (")[0].strip()
            self.config["browser"] = browser_key
        
        if self.current_selected_index == -1 or self.current_selected_index >= len(self.config["commands"]):
            return
            
        cmd = self.config["commands"][self.current_selected_index]
        cmd["id"] = self.edit_id.text().strip()
        cmd["type"] = self.edit_type.currentText()
        
        phrases_str = self.edit_phrases.text()
        phrases = [p.strip().lower() for p in phrases_str.split(",") if p.strip()]
        cmd["phrases"] = phrases
        
        cmd["value"] = self.edit_value.text().strip()
        cmd["sound"] = self.edit_sound.currentText()
        cmd["reply"] = self.edit_reply.text().strip()
        
        label = f"{cmd['id']} [{cmd['type']}]"
        self.cmd_list.item(self.current_selected_index).setText(label)

    def apply_edits_to_list(self):
        self.save_current_command_edits()

    def add_command(self):
        new_cmd = {
            "id": "new_command",
             "type": "tts_only",
             "phrases": ["какая-то фраза"],
             "value": "",
             "sound": "",
             "reply": "Мой ответ"
        }
        self.config["commands"].append(new_cmd)
        self.load_commands_list()
        self.cmd_list.setCurrentRow(len(self.config["commands"]) - 1)
        self.on_command_select(self.cmd_list.currentItem())

    def delete_command(self):
        row = self.cmd_list.currentRow()
        if row != -1:
            reply = QMessageBox.question(self, 'Удаление', 'Вы уверены, что хотите удалить эту команду навсегда?',
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.config["commands"].pop(row)
                self.current_selected_index = -1
                self.load_commands_list()
                
                self.edit_id.setText("")
                self.edit_phrases.setText("")
                self.edit_value.setText("")
                self.edit_sound.setCurrentIndex(0)
                self.edit_reply.setText("")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    app.setStyle("Fusion")
    palette = app.palette()
    from PyQt5.QtGui import QColor
    palette.setColor(palette.Window, QColor(40, 44, 52))
    palette.setColor(palette.WindowText, Qt.white)
    palette.setColor(palette.Base, QColor(30, 34, 39))
    palette.setColor(palette.AlternateBase, QColor(40, 44, 52))
    palette.setColor(palette.ToolTipBase, Qt.white)
    palette.setColor(palette.ToolTipText, Qt.white)
    palette.setColor(palette.Text, Qt.white)
    palette.setColor(palette.Button, QColor(53, 59, 69))
    palette.setColor(palette.ButtonText, Qt.white)
    palette.setColor(palette.BrightText, Qt.red)
    palette.setColor(palette.Highlight, QColor(97, 175, 239))
    palette.setColor(palette.HighlightedText, Qt.black)
    app.setPalette(palette)
    
    admin = AdminPanel()
    admin.show()
    sys.exit(app.exec_())
