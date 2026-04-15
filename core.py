import pyttsx3
import speech_recognition as sr
import os
import subprocess
import webbrowser
import datetime
import asyncio
import edge_tts
import pygame
import tempfile
import json
import random

class JarvisCore:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.voice = 'ru-RU-DmitryNeural' 
        pygame.mixer.init()
        
        self.voice_pack_dir = os.path.join(os.path.dirname(__file__), 'voice_pack')
        if not os.path.exists(self.voice_pack_dir):
            os.makedirs(self.voice_pack_dir)
            
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"theme": "iron_man", "commands": []}

    def reload_config(self):
        self.config = self.load_config()

    async def _async_speak(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_path = temp_file.name
        temp_file.close()
        await communicate.save(temp_path)
        return temp_path

    def play_audio(self, filename, fallback_text):
        print(f"JARVIS: {fallback_text}")
        file_path = os.path.join(self.voice_pack_dir, filename)
        
        if os.path.exists(file_path):
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_file_path = loop.run_until_complete(self._async_speak(fallback_text))
            loop.close()
            
            pygame.mixer.music.load(audio_file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            try:
                os.remove(audio_file_path)
            except:
                pass
                
    def speak(self, text):
        self.play_audio("non_existent_file.mp3", text)

    def open_url(self, url):
        """Opens a URL in the browser specified in config. Falls back to system default."""
        browser = self.config.get("browser", "default")
        if browser == "chrome":
            os.system(f'start chrome "{url}"')
        elif browser == "firefox":
            os.system(f'start firefox "{url}"')
        elif browser == "edge":
            os.system(f'start msedge "{url}"')
        elif browser == "opera":
            os.system(f'start opera "{url}"')
        elif browser == "yandex":
            os.system(f'start browser "{url}"')
        else:
            webbrowser.open(url)

    def check_wake_word(self, command):
        wake_words = ["джарвис", "jarvis", "чарвис"]
        for word in wake_words:
            if word in command:
                return True
        return False

    def listen(self):
        with sr.Microphone() as source:
            print("Слушаю...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                command = self.recognizer.recognize_google(audio, language='ru-RU').lower()
                print(f"Вы сказали: {command}")
                return command
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                print("Не удалось распознать речь")
                return ""
            except sr.RequestError as e:
                print(f"Ошибка сервиса распознавания: {e}")
                return ""

    def execute_command(self, command):
        if not command:
            return ""

        if not self.check_wake_word(command):
            return ""

        command = command.replace("джарвис", "").replace("jarvis", "").replace("чарвис", "").strip()
        
        if not command:
            greetings = ["greeting1.wav", "greeting2.wav", "greeting3.wav", "greeting4.wav", "greeting5.wav"]
            resp = "Да, сэр?"
            self.play_audio(random.choice(greetings), resp)
            return resp

        # === 1. ГЛАВНЫЙ цикл парсинга config.json ===
        self.reload_config()
        
        for cmd_config in self.config.get("commands", []):
            if any(phrase in command for phrase in cmd_config.get("phrases", [])):
                sound = cmd_config.get("sound", "")
                reply = cmd_config.get("reply", "Выполняю.")
                cmd_type = cmd_config.get("type", "tts_only")
                value = cmd_config.get("value", "")
                
                # Встроенные команды со сложной логикой Питона
                if cmd_type == "built_in":
                    if value == "volume_up":
                        vol_sounds = [
                            "[Русский Диктор]«Гром......ста.».mp3",
                            "[Русский Диктор]«Гром......сэр.» (1).mp3",
                            "[Русский Диктор]«Гром......сэр.».mp3",
                            "[Русский Диктор]«Гром......чше.».mp3"
                        ]
                        sel_sound = random.choice(vol_sounds)
                        self.play_audio(sel_sound, reply)
                        import ctypes
                        VK_VOLUME_UP = 0xAF
                        for _ in range(10):
                            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                            ctypes.windll.user32.keybd_event(VK_VOLUME_UP, 0, 2, 0)
                        return "Громкость увеличена."
                        
                    elif value == "volume_down":
                        self.play_audio(sound, reply)
                        import ctypes
                        VK_VOLUME_DOWN = 0xAE
                        for _ in range(10): 
                            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 0, 0)
                            ctypes.windll.user32.keybd_event(VK_VOLUME_DOWN, 0, 2, 0)
                        return "Громкость уменьшена."
                        
                    elif value == "system_on":
                        self.play_audio(sound, reply)
                        return reply

                    elif value == "open_camera":
                        self.play_audio(sound, reply)
                        import threading
                        def record_camera():
                            try:
                                import cv2
                                import time
                            except ImportError:
                                print("ОШИБКА: Библиотека opencv-python не установлена!")
                                return
                            cap = cv2.VideoCapture(0)
                            if not cap.isOpened(): return
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            filename = f"record_{int(time.time())}.avi"
                            out = cv2.VideoWriter(filename, fourcc, 20.0, (640,  480))
                            while cap.isOpened():
                                ret, frame = cap.read()
                                if not ret: break
                                out.write(frame)
                                cv2.imshow("JARVIS Camera", frame)
                                if cv2.waitKey(1) & 0xFF == ord('q'): break
                            cap.release()
                            out.release()
                            cv2.destroyAllWindows()
                        threading.Thread(target=record_camera, daemon=True).start()
                        return "Камера открыта."

                    elif value == "tell_time":
                        now = datetime.datetime.now()
                        hour = now.hour
                        minute = now.minute
                        # Формируем правильный текст
                        hour_word = "час" if hour % 10 == 1 and hour % 100 != 11 else \
                                    "часа" if 2 <= hour % 10 <= 4 and not (12 <= hour % 100 <= 14) else "часов"
                        if minute == 0:
                            time_str = f"Сейчас ровно {hour} {hour_word}."
                        else:
                            min_word = "минута" if minute % 10 == 1 and minute % 100 != 11 else \
                                       "минуты" if 2 <= minute % 10 <= 4 and not (12 <= minute % 100 <= 14) else "минут"
                            time_str = f"Сейчас {hour} {hour_word} {minute} {min_word}."
                        # Сначала играем звук-заставку, потом произносим время через TTS
                        if sound and os.path.exists(os.path.join(self.voice_pack_dir, sound)):
                            pygame.mixer.music.load(os.path.join(self.voice_pack_dir, sound))
                            pygame.mixer.music.play()
                            while pygame.mixer.music.get_busy():
                                pygame.time.Clock().tick(10)
                            pygame.mixer.music.unload()
                        self.speak(time_str)
                        return time_str
                        
                    elif value == "shutdown":
                        import re
                        delay = 5
                        match = re.search(r'через\s+(\d+)\s+(минут[уаы]?|час[ова]?|секунд[уаы]?)', command)
                        if match:
                            num = int(match.group(1))
                            unit = match.group(2)
                            if 'час' in unit:
                                delay = num * 3600
                            elif 'минут' in unit:
                                delay = num * 60
                            elif 'секунд' in unit:
                                delay = num
                                
                        self.play_audio(sound, reply)
                        os.system(f"shutdown /s /t {delay}")
                        if delay > 5:
                            return f"Запланировано выключение через {delay} сек."
                        return "Комплекс выключается..."

                    elif value == "cancel_shutdown":
                        self.play_audio(sound, reply)
                        os.system("shutdown /a")
                        return "Отмена таймера выключения."

                    elif value == "reboot":
                        self.play_audio(sound, reply)
                        os.system("shutdown /r /t 5")
                        return "Перезагрузка через 5 секунд."

                    elif value == "check_network":
                        self.play_audio(sound, reply)
                        os.system("start cmd /k ping google.com")
                        return reply

                    elif value == "task_manager":
                        self.play_audio(sound, reply)
                        os.system("taskmgr")
                        return reply

                    elif value == "lock_screen":
                        self.play_audio(sound, reply)
                        import ctypes
                        ctypes.windll.user32.LockWorkStation()
                        return reply

                    elif value == "sleep":
                        self.play_audio(sound, reply)
                        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                        return reply

                    elif value == "screenshot":
                        render_sound = random.choice(["render1.wav", "render2.wav"])
                        self.play_audio(render_sound, reply)
                        os.system("snippingtool")
                        return reply

                    elif value == "save_screenshot":
                        try:
                            from PIL import ImageGrab
                            ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                            filename = os.path.join(os.path.dirname(__file__), f"screenshot_{ts}.png")
                            img = ImageGrab.grab()
                            img.save(filename)
                            self.play_audio(sound, f"Снимок сохранён: {filename}")
                            return f"Скриншот сохранён как {filename}"
                        except ImportError:
                            self.play_audio(sound, reply)
                            os.system("snippingtool")
                            return "Установите Pillow: pip install Pillow"

                    elif value == "restart_explorer":
                        self.play_audio(sound, reply)
                        os.system("taskkill /f /im explorer.exe")
                        import time
                        time.sleep(1)
                        os.system("start explorer.exe")
                        return reply

                    elif value == "show_desktop":
                        self.play_audio(sound, reply)
                        import ctypes
                        VK_LWIN = 0x5B
                        VK_D = 0x44
                        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 0, 0)
                        ctypes.windll.user32.keybd_event(VK_D, 0, 0, 0)
                        ctypes.windll.user32.keybd_event(VK_D, 0, 2, 0)
                        ctypes.windll.user32.keybd_event(VK_LWIN, 0, 2, 0)
                        return reply

                    elif value == "exit":
                        self.play_audio(sound, reply)
                        os._exit(0)

                # Стандартные команды (Открытие файлов / Сайтов / Обычный ответ)
                else:
                    self.play_audio(sound, reply)
                    if cmd_type == "cmd":
                        os.system(value)
                    elif cmd_type == "url":
                        self.open_url(value)
                    return reply

        # === 2. GOOGLE ПОИСК ПО УМОЛЧАНИЮ ===
        search_prefixes = ["найди", "поищи", "что такое", "кто такой", "кто такая", "кто такие", "что значит"]
        search_query = command
        for prefix in search_prefixes:
            if search_query.startswith(prefix):
                search_query = search_query[len(prefix):].strip()
                break
        
        if search_query:
            self.play_audio("[Русский Диктор]«Ищу ......сэр.».mp3", f"Ищу информацию по запросу: {search_query}")
            import urllib.parse
            safe_query = urllib.parse.quote(search_query)
            self.open_url(f"https://www.google.com/search?q={safe_query}")
            self.play_audio(random.choice(["done1.wav", "done2.wav"]), "Запрос выполнен.")
            return f"Поиск: {search_query}"
        else:
            fallback_msg = "Команда не распознана."
            self.play_audio("not_found.wav", fallback_msg)
            return fallback_msg
