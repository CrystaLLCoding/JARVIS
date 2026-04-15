"""
J.A.R.V.I.S — Admin Telegram Bot
===================================
Только ВЫ можете использовать этот бот (защита по ADMIN_CHAT_ID).

Настройка:
    1. Создайте бота через @BotFather → получите BOT_TOKEN
    2. Узнайте свой chat_id через @userinfobot → ADMIN_CHAT_ID
    3. Установите переменные и запустите:

    BOT_TOKEN=123456:ABC...
    ADMIN_CHAT_ID=987654321
    SERVER_URL=https://your-server.com
    ADMIN_TOKEN=your-secret-token

    python bot.py

Команды бота:
    /gen           — создать 1 ключ на месяц
    /list          — список всех ключей
    /revoke <ключ> — деактивировать ключ
    /reset <ключ>  — сбросить привязку к ПК (если сменил ПК)
    /extend <ключ> — продлить на 30 дней
    /stats         — краткая статистика
"""

import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)

# ============================================================
#  КОНФИГУРАЦИЯ — заполните через переменные окружения
# ============================================================
BOT_TOKEN      = os.environ.get("BOT_TOKEN",      "")
ADMIN_CHAT_ID  = int(os.environ.get("ADMIN_CHAT_ID", "0"))
SERVER_URL     = os.environ.get("SERVER_URL",     "http://localhost:8000")
ADMIN_TOKEN    = os.environ.get("ADMIN_TOKEN",    "change-this-to-a-secure-token")

HEADERS = {"x-admin-token": ADMIN_TOKEN}
TIMEOUT = 10


# ============================================================
#  ЗАЩИТА — только администратор
# ============================================================
def admin_only(func):
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != ADMIN_CHAT_ID:
            await update.message.reply_text("⛔ Доступ запрещён.")
            return
        await func(update, ctx)
    return wrapper


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================
def api_post(path: str, data: dict = None) -> dict | None:
    try:
        resp = requests.post(f"{SERVER_URL}{path}", json=data or {}, headers=HEADERS, timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def api_get(path: str) -> dict | None:
    try:
        resp = requests.get(f"{SERVER_URL}{path}", headers=HEADERS, timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def api_delete(path: str) -> dict | None:
    try:
        resp = requests.delete(f"{SERVER_URL}{path}", headers=HEADERS, timeout=TIMEOUT)
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


# ============================================================
#  КОМАНДЫ БОТА
# ============================================================

@admin_only
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 *J.A.R.V.I.S — Панель администратора*\n\n"
        "Доступные команды:\n\n"
        "🔑 /gen — создать ключ на 1 месяц\n"
        "📋 /list — список всех ключей\n"
        "❌ /revoke `JRVS-XXXX-XXXX-XXXX-XXXX` — деактивировать\n"
        "🔄 /reset `JRVS-XXXX-XXXX-XXXX-XXXX` — сбросить ПК\n"
        "⏳ /extend `JRVS-XXXX-XXXX-XXXX-XXXX` — продлить на 30 дней\n"
        "📊 /stats — статистика\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@admin_only
async def cmd_gen(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Генерирует 1 ключ на месяц."""
    # Имя клиента как заметка (опционально: /gen Имя Клиента)
    note = " ".join(ctx.args) if ctx.args else ""

    await update.message.reply_text("⏳ Генерирую ключ...")

    result = api_post("/admin/generate", {"type": "monthly", "count": 1, "note": note})

    if "error" in result:
        await update.message.reply_text(f"❌ Ошибка сервера: {result['error']}")
        return

    key = result["keys"][0]
    note_str = f"\n📝 Заметка: `{note}`" if note else ""

    text = (
        f"✅ *Ключ создан!*\n\n"
        f"🔑 `{key}`\n"
        f"📅 Тип: Ежемесячный (30 дней)\n"
        f"{note_str}\n\n"
        f"Отправьте этот ключ покупателю.\n"
        f"Он вводит его при первом запуске Джарвиса."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@admin_only
async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Показывает список всех ключей."""
    await update.message.reply_text("⏳ Загружаю список...")

    result = api_get("/admin/keys")
    if "error" in result:
        await update.message.reply_text(f"❌ Ошибка: {result['error']}")
        return

    keys = result.get("keys", [])
    if not keys:
        await update.message.reply_text("📭 Ключей ещё нет.")
        return

    # Группируем: активные и неактивные
    active = [k for k in keys if k["is_active"]]
    inactive = [k for k in keys if not k["is_active"]]

    lines = [f"📋 *Всего ключей: {len(keys)}*  (✅ {len(active)}  ❌ {len(inactive)})\n"]

    for k in keys[:20]:   # Показываем максимум 20 чтобы не спамить
        icon = "✅" if k["is_active"] else "❌"
        expires = (k.get("expires_at") or "")[:10]
        bound = "привязан" if k.get("hwid") else "не активирован"
        note = f"  _{k['note']}_" if k.get("note") else ""
        lines.append(f"{icon} `{k['key']}`\n   до {expires} | {bound}{note}")

    if len(keys) > 20:
        lines.append(f"\n_...и ещё {len(keys)-20} ключей_")

    await update.message.reply_text("\n\n".join(lines), parse_mode="Markdown")


@admin_only
async def cmd_revoke(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Деактивирует ключ. /revoke JRVS-XXXX-XXXX-XXXX-XXXX"""
    if not ctx.args:
        await update.message.reply_text("❌ Укажите ключ: `/revoke JRVS-XXXX-XXXX-XXXX-XXXX`", parse_mode="Markdown")
        return

    key = ctx.args[0].upper()
    result = api_delete(f"/admin/revoke/{key}")
    if "error" in result:
        await update.message.reply_text(f"❌ Ошибка: {result['error']}")
    else:
        await update.message.reply_text(f"✅ {result.get('message', 'Деактивирован.')}")


@admin_only
async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Сбрасывает привязку к ПК. /reset JRVS-XXXX-XXXX-XXXX-XXXX"""
    if not ctx.args:
        await update.message.reply_text("❌ Укажите ключ: `/reset JRVS-XXXX-XXXX-XXXX-XXXX`", parse_mode="Markdown")
        return

    key = ctx.args[0].upper()
    result = api_post(f"/admin/reset/{key}")
    if "error" in result:
        await update.message.reply_text(f"❌ Ошибка: {result['error']}")
    else:
        msg = result.get("message", "Привязка сброшена.")
        await update.message.reply_text(f"🔄 {msg}\n\nПользователь может активировать ключ заново на новом ПК.")


@admin_only
async def cmd_extend(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Продлевает подписку на 30 дней. /extend JRVS-XXXX-XXXX-XXXX-XXXX"""
    if not ctx.args:
        await update.message.reply_text("❌ Укажите ключ: `/extend JRVS-XXXX-XXXX-XXXX-XXXX`", parse_mode="Markdown")
        return

    key = ctx.args[0].upper()
    result = api_post(f"/admin/extend/{key}", {"days": 30})
    if "error" in result:
        await update.message.reply_text(f"❌ Ошибка: {result['error']}")
    else:
        new_date = result.get("expires_at", "")[:10]
        await update.message.reply_text(
            f"⏳ Подписка продлена на 30 дней.\n🗓 Новая дата окончания: `{new_date}`",
            parse_mode="Markdown"
        )


@admin_only
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Краткая статистика по ключам."""
    result = api_get("/admin/keys")
    if "error" in result:
        await update.message.reply_text(f"❌ Ошибка: {result['error']}")
        return

    keys = result.get("keys", [])
    total    = len(keys)
    active   = sum(1 for k in keys if k["is_active"])
    bound    = sum(1 for k in keys if k.get("hwid"))
    inactive = total - active

    text = (
        f"📊 *Статистика лицензий*\n\n"
        f"🔑 Всего ключей:         `{total}`\n"
        f"✅ Активных:             `{active}`\n"
        f"🖥️ Активированных (ПК): `{bound}`\n"
        f"❌ Деактивированных:     `{inactive}`\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ============================================================
#  ЗАПУСК БОТА
# ============================================================
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("❌ Укажите BOT_TOKEN в переменных окружения!")
        exit(1)
    if not ADMIN_CHAT_ID:
        print("❌ Укажите ADMIN_CHAT_ID в переменных окружения!")
        exit(1)

    print(f"🤖 Бот запущен. Admin ID: {ADMIN_CHAT_ID}")
    print(f"🌐 Сервер: {SERVER_URL}")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("gen",    cmd_gen))
    app.add_handler(CommandHandler("list",   cmd_list))
    app.add_handler(CommandHandler("revoke", cmd_revoke))
    app.add_handler(CommandHandler("reset",  cmd_reset))
    app.add_handler(CommandHandler("extend", cmd_extend))
    app.add_handler(CommandHandler("stats",  cmd_stats))

    app.run_polling(drop_pending_updates=True)
