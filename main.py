import sys
import os
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QImage, QPixmap

from core import JarvisCore

class SpeechRecognitionThread(QThread):
    log_user_signal = pyqtSignal(str)
    log_jarvis_signal = pyqtSignal(str)
    status_signal = pyqtSignal(bool)

    def __init__(self, core_instance):
        super().__init__()
        self.core = core_instance
        self.is_running = True

    def run(self):
        import speech_recognition as sr
        
        with sr.Microphone() as source:
            self.core.recognizer.adjust_for_ambient_noise(source, duration=1)
            
            while self.is_running:
                self.status_signal.emit(True) 
                try:
                    audio = self.core.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    command = self.core.recognizer.recognize_google(audio, language='ru-RU').lower()
                    print(f"РАСПОЗНАНО: {command}")
                    
                    if self.core.check_wake_word(command):
                        self.status_signal.emit(False)
                        self.log_user_signal.emit(command)
                        response = self.core.execute_command(command)
                        if response:
                            self.log_jarvis_signal.emit(response)
                    else:
                        print(f"Не реагирую, нет триггерного слова: {command}")

                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    print("Речь не распознана (UnknownValueError)")
                    continue
                except sr.RequestError as e:
                    print(f"Ошибка API: {e}")
                    self.log_jarvis_signal.emit(f"Ошибка API: {e}")
                except Exception as e:
                    print(f"Критическая ошибка в потоке распознавания: {e}")

    def stop(self):
        self.is_running = False

class HUDVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.last_user = "ОЖИДАНИЕ ГОЛОСОВОГО ВВОДА..."
        self.last_jarvis = "СИСТЕМА J.A.R.V.I.S: ГОТОВА К РАБОТЕ."
        self.is_listening = True
        
        video_path = os.path.join(os.path.dirname(__file__), "ironman hud.mp4")
        self.cap = cv2.VideoCapture(video_path)
        
        self.config = self.load_config()
        
        # 30 FPS video playback (~33ms)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(33)
        
    def load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if os.path.exists(config_path):
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"theme": "iron_man"}
        
    def update_animation(self):
        self.update()

    def set_listening(self, state):
        self.is_listening = state

    def set_user_text(self, text):
        self.last_user = text.upper()

    def set_jarvis_text(self, text):
        self.last_jarvis = text.upper()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # --- BACKGROUND VIDEO ---
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                # Loop video
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Scale image to window size keeping aspect ratio
                pixmap = QPixmap.fromImage(qimg).scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                
                # Center the video if aspect ratio differs
                x_offset = (self.width() - pixmap.width()) // 2
                y_offset = (self.height() - pixmap.height()) // 2
                painter.drawPixmap(x_offset, y_offset, pixmap)
        else:
            painter.fillRect(self.rect(), QColor(5, 5, 10, 240))
        
        # --- WATERMARK ---
        w = self.width()
        h = self.height()
        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QPen(QColor(255, 255, 255, 80)))
        painter.drawText(w - 220, h - 12, "J.A.R.V.I.S made by CrystaLL")


class JarvisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.core = JarvisCore()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('JARVIS HUD')
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.visualizer = HUDVisualizer()
        self.setCentralWidget(self.visualizer)
         
        self.thread = SpeechRecognitionThread(self.core)
        self.thread.log_user_signal.connect(self.visualizer.set_user_text)
        self.thread.log_jarvis_signal.connect(self.visualizer.set_jarvis_text)
        self.thread.status_signal.connect(self.visualizer.set_listening)
        self.thread.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        if hasattr(self, 'thread'):
            self.thread.stop()
            self.thread.wait()
        
        # Release video capture when closing
        if hasattr(self, 'visualizer') and self.visualizer.cap:
            self.visualizer.cap.release()
            
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # ============================================================
    #  ПРОВЕРКА ЛИЦЕНЗИИ
    # ============================================================
    from license import check_license_online
    from license_dialog import LicenseDialog

    status = check_license_online()

    if not status.get("valid"):
        reason = status.get("reason", "")
        # Показываем диалог активации
        dlg = LicenseDialog(status_message=reason)
        result = dlg.exec_()
        if result != LicenseDialog.Accepted:
            # Пользователь закрыл окно — выходим
            sys.exit(0)

    # Лицензия активна — запускаем HUD
    ex = JarvisApp()
    sys.exit(app.exec_())

