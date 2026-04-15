"""
J.A.R.V.I.S License Server
===========================
Запуск:
    uvicorn main:app --host 0.0.0.0 --port 8000

Переменные окружения:
    ADMIN_TOKEN  — секретный токен для admin-эндпоинтов (обязательно смените!)
"""

import os
from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel
from datetime import datetime

from database import Database

app = FastAPI(
    title="JARVIS License Server",
    description="Сервер проверки лицензий для J.A.R.V.I.S",
    version="1.0.0"
)

db = Database()
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "change-this-to-a-secure-random-token")


# ==============================================================
#  МОДЕЛИ ЗАПРОСОВ
# ==============================================================

class ActivateRequest(BaseModel):
    key: str
    hwid: str

class CheckRequest(BaseModel):
    key: str
    hwid: str

class GenerateRequest(BaseModel):
    type: str = "monthly"    # monthly | yearly | lifetime
    count: int = 1
    note: str = ""           # заметка (например имя покупателя)

class ExtendRequest(BaseModel):
    days: int = 30


# ==============================================================
#  ВСПОМОГАТЕЛЬНОЕ
# ==============================================================

def verify_admin(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Недостаточно прав.")
    return True


# ==============================================================
#  ПУБЛИЧНЫЕ ЭНДПОИНТЫ (клиент)
# ==============================================================

@app.post("/activate", summary="Активировать ключ")
def activate(req: ActivateRequest):
    """Привязывает ключ к компьютеру (HWID). Вызывается при первой активации."""
    key = req.key.strip().upper()
    lic = db.get_license(key)

    if not lic:
        return {"success": False, "message": "Ключ не найден."}

    if not lic["is_active"]:
        return {"success": False, "message": "Ключ деактивирован администратором."}

    # Уже привязан к другому ПК?
    if lic["hwid"] and lic["hwid"] != req.hwid:
        return {"success": False, "message": "Ключ уже привязан к другому компьютеру. Обратитесь в поддержку."}

    # Истёк срок?
    expires_at = datetime.fromisoformat(lic["expires_at"])
    if datetime.now() > expires_at:
        return {"success": False, "message": f"Срок действия ключа истёк ({lic['expires_at'][:10]})."}

    # Первая активация — привязываем HWID
    if not lic["hwid"]:
        db.bind_hwid(key, req.hwid)

    return {
        "success": True,
        "type": lic["type"],
        "expires_at": lic["expires_at"],
        "message": "Активировано успешно. Добро пожаловать!"
    }


@app.post("/check", summary="Проверить лицензию")
def check(req: CheckRequest):
    """Проверяет действительность лицензии. Вызывается каждый запуск."""
    key = req.key.strip().upper()
    lic = db.get_license(key)

    if not lic:
        return {"valid": False, "reason": "Ключ не найден."}

    if not lic["is_active"]:
        return {"valid": False, "reason": "Ключ деактивирован."}

    if lic["hwid"] != req.hwid:
        return {"valid": False, "reason": "Ключ привязан к другому компьютеру."}

    expires_at = datetime.fromisoformat(lic["expires_at"])
    now = datetime.now()

    if now > expires_at:
        days_ago = (now - expires_at).days
        return {
            "valid": False,
            "reason": f"Подписка истекла {days_ago} дн. назад. Продлите подписку.",
            "expired": True,
            "expires_at": lic["expires_at"]
        }

    days_left = (expires_at - now).days
    return {
        "valid": True,
        "type": lic["type"],
        "expires_at": lic["expires_at"],
        "days_left": days_left
    }


# ==============================================================
#  ADMIN ЭНДПОИНТЫ (только для вас)
# ==============================================================

@app.post("/admin/generate", summary="[ADMIN] Создать ключи")
def admin_generate(req: GenerateRequest, _: bool = Depends(verify_admin)):
    """Генерирует N новых ключей указанного типа."""
    if req.count < 1 or req.count > 100:
        raise HTTPException(status_code=400, detail="count должен быть от 1 до 100")
    if req.type not in ("monthly", "yearly", "lifetime"):
        raise HTTPException(status_code=400, detail="Неверный тип. Используйте: monthly, yearly, lifetime")

    keys = [db.create_license(req.type, req.note) for _ in range(req.count)]
    return {"keys": keys, "type": req.type, "count": len(keys)}


@app.get("/admin/keys", summary="[ADMIN] Список всех ключей")
def admin_keys(_: bool = Depends(verify_admin)):
    return {"keys": db.get_all_licenses()}


@app.delete("/admin/revoke/{key}", summary="[ADMIN] Деактивировать ключ")
def admin_revoke(key: str, _: bool = Depends(verify_admin)):
    key = key.upper()
    if not db.get_license(key):
        raise HTTPException(status_code=404, detail="Ключ не найден.")
    db.revoke_license(key)
    return {"message": f"Ключ {key} деактивирован."}


@app.post("/admin/reset/{key}", summary="[ADMIN] Сбросить привязку к ПК")
def admin_reset(key: str, _: bool = Depends(verify_admin)):
    """Используется когда пользователь сменил компьютер."""
    key = key.upper()
    if not db.get_license(key):
        raise HTTPException(status_code=404, detail="Ключ не найден.")
    db.reset_hwid(key)
    return {"message": f"Привязка ПК для ключа {key} сброшена."}


@app.post("/admin/extend/{key}", summary="[ADMIN] Продлить подписку")
def admin_extend(key: str, req: ExtendRequest, _: bool = Depends(verify_admin)):
    key = key.upper()
    if not db.extend_license(key, req.days):
        raise HTTPException(status_code=404, detail="Ключ не найден.")
    updated = db.get_license(key)
    return {"message": f"Продлено на {req.days} дней.", "expires_at": updated["expires_at"]}


@app.get("/health")
def health():
    return {"status": "ok", "server": "JARVIS License Server v1.0"}
