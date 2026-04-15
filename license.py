import uuid
import hashlib
import json
import os
import requests
import base64
from datetime import datetime

# ============================================================
#  НАСТРОЙТЕ ЭТО после деплоя сервера!
# ============================================================
SERVER_URL = "https://your-jarvis-server.com"   # <-- сюда URL вашего сервера
LICENSE_FILE = os.path.join(os.path.dirname(__file__), "license.dat")
REQUEST_TIMEOUT = 10  # секунд


def get_hwid() -> str:
    """Возвращает уникальный ID этого компьютера (по MAC-адресу)."""
    mac = uuid.getnode()
    raw = f"{mac}-JARVIS-HWID-SALT"
    return hashlib.sha256(raw.encode()).hexdigest()[:24].upper()


def save_license(data: dict):
    """Сохраняет данные лицензии в license.dat (base64-кодирование)."""
    encoded = base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode()
    with open(LICENSE_FILE, 'w') as f:
        f.write(encoded)


def load_license() -> dict | None:
    """Загружает данные лицензии. Возвращает None если файл не найден или повреждён."""
    if not os.path.exists(LICENSE_FILE):
        return None
    try:
        with open(LICENSE_FILE, 'r') as f:
            encoded = f.read().strip()
        decoded = base64.b64decode(encoded).decode()
        return json.loads(decoded)
    except Exception:
        return None


def check_license_online() -> dict:
    """
    Проверяет лицензию на сервере.
    Возвращает dict:
      {"valid": True,  "expires_at": "...", "days_left": N}   — если активна
      {"valid": False, "reason": "..."}                        — если нет
    """
    data = load_license()
    if not data or not data.get("key"):
        return {"valid": False, "reason": "Лицензия не найдена. Введите ключ."}

    hwid = get_hwid()
    try:
        resp = requests.post(
            f"{SERVER_URL}/check",
            json={"key": data["key"], "hwid": hwid},
            timeout=REQUEST_TIMEOUT
        )
        result = resp.json()
        if result.get("valid"):
            data.update(result)
            save_license(data)
        return result

    except requests.exceptions.ConnectionError:
        return {"valid": False, "reason": "Нет подключения к интернету."}
    except requests.exceptions.Timeout:
        return {"valid": False, "reason": "Сервер не отвечает. Попробуйте позже."}
    except Exception as e:
        return {"valid": False, "reason": f"Ошибка проверки: {e}"}


def activate_license(key: str) -> dict:
    """
    Активирует ключ на этом компьютере.
    Возвращает dict:
      {"success": True,  "expires_at": "...", "type": "monthly"} — успех
      {"success": False, "message": "..."}                        — ошибка
    """
    key = key.strip().upper()
    hwid = get_hwid()
    try:
        resp = requests.post(
            f"{SERVER_URL}/activate",
            json={"key": key, "hwid": hwid},
            timeout=REQUEST_TIMEOUT
        )
        result = resp.json()
        if result.get("success"):
            save_license({
                "key": key,
                "hwid": hwid,
                "expires_at": result.get("expires_at", ""),
                "type": result.get("type", "monthly")
            })
        return result

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Нет подключения к интернету."}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Сервер не отвечает. Попробуйте позже."}
    except Exception as e:
        return {"success": False, "message": f"Ошибка активации: {e}"}
