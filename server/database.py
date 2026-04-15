import sqlite3
import os
import random
import string
from datetime import datetime, timedelta


DB_PATH = os.path.join(os.path.dirname(__file__), "licenses.db")

# Типы подписок → количество дней
LICENSE_DURATIONS = {
    "monthly":  30,
    "yearly":   365,
    "lifetime": 36500,   # ~100 лет
}


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS licenses (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                key          TEXT    UNIQUE NOT NULL,
                hwid         TEXT,
                type         TEXT    NOT NULL DEFAULT 'monthly',
                activated_at DATETIME,
                expires_at   DATETIME NOT NULL,
                is_active    INTEGER  NOT NULL DEFAULT 1,
                note         TEXT,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    # ------------------------------------------------------------------
    #  ГЕНЕРАЦИЯ КЛЮЧА
    # ------------------------------------------------------------------
    def _make_key(self) -> str:
        chars = string.ascii_uppercase + string.digits
        parts = ["".join(random.choices(chars, k=4)) for _ in range(4)]
        return f"JRVS-{'-'.join(parts)}"

    def create_license(self, type_: str = "monthly", note: str = "") -> str:
        """Создаёт новый ключ и сохраняет в БД. Возвращает ключ."""
        key = self._make_key()
        # Гарантируем уникальность
        while self.get_license(key):
            key = self._make_key()

        days = LICENSE_DURATIONS.get(type_, 30)
        expires_at = (datetime.now() + timedelta(days=days)).isoformat()

        self.conn.execute(
            "INSERT INTO licenses (key, type, expires_at, note) VALUES (?, ?, ?, ?)",
            (key, type_, expires_at, note)
        )
        self.conn.commit()
        return key

    # ------------------------------------------------------------------
    #  ПОЛУЧЕНИЕ / ПОИСК
    # ------------------------------------------------------------------
    def get_license(self, key: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM licenses WHERE key = ?", (key,)
        ).fetchone()
        return dict(row) if row else None

    def get_all_licenses(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM licenses ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    #  ИЗМЕНЕНИЕ СТАТУСА
    # ------------------------------------------------------------------
    def bind_hwid(self, key: str, hwid: str):
        self.conn.execute(
            "UPDATE licenses SET hwid = ?, activated_at = ? WHERE key = ?",
            (hwid, datetime.now().isoformat(), key)
        )
        self.conn.commit()

    def revoke_license(self, key: str):
        self.conn.execute(
            "UPDATE licenses SET is_active = 0 WHERE key = ?", (key,)
        )
        self.conn.commit()

    def reset_hwid(self, key: str):
        """Сбросить привязку (если пользователь сменил ПК)."""
        self.conn.execute(
            "UPDATE licenses SET hwid = NULL, activated_at = NULL WHERE key = ?",
            (key,)
        )
        self.conn.commit()

    def extend_license(self, key: str, days: int):
        """Продлить подписку на N дней."""
        lic = self.get_license(key)
        if not lic:
            return False
        current = datetime.fromisoformat(lic["expires_at"])
        new_exp = (max(current, datetime.now()) + timedelta(days=days)).isoformat()
        self.conn.execute(
            "UPDATE licenses SET expires_at = ?, is_active = 1 WHERE key = ?",
            (new_exp, key)
        )
        self.conn.commit()
        return True
