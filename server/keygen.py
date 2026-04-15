#!/usr/bin/env python3
"""
JARVIS License Admin CLI
========================
Использование:
    python keygen.py generate --type monthly --count 1
    python keygen.py generate --type monthly --count 5 --note "Telegram @username"
    python keygen.py list
    python keygen.py revoke JRVS-XXXX-XXXX-XXXX-XXXX
    python keygen.py reset  JRVS-XXXX-XXXX-XXXX-XXXX
    python keygen.py extend JRVS-XXXX-XXXX-XXXX-XXXX --days 30

Переменные окружения:
    JARVIS_SERVER   — URL сервера  (по умолчанию: http://localhost:8000)
    ADMIN_TOKEN     — Ваш секретный токен
"""

import argparse
import os
import sys
import requests

SERVER = os.environ.get("JARVIS_SERVER", "http://localhost:8000")
TOKEN  = os.environ.get("ADMIN_TOKEN",   "change-this-to-a-secure-random-token")
HEADERS = {"x-admin-token": TOKEN}


def ok(resp):
    """Вернуть JSON ответ или напечатать ошибку."""
    if resp.status_code == 200:
        return resp.json()
    print(f"❌ Ошибка {resp.status_code}: {resp.text}")
    sys.exit(1)


def cmd_generate(args):
    data = {"type": args.type, "count": args.count, "note": args.note}
    result = ok(requests.post(f"{SERVER}/admin/generate", json=data, headers=HEADERS))
    print(f"\n✅ Создано ключей ({args.type}): {result['count']}\n")
    for key in result["keys"]:
        print(f"  🔑  {key}")
    print()


def cmd_list(args):
    result = ok(requests.get(f"{SERVER}/admin/keys", headers=HEADERS))
    keys = result.get("keys", [])
    print(f"\n{'─'*80}")
    print(f"  {'Ключ':<28}  {'Тип':<10}  {'До':<12}  {'ПК':<10}  {'Статус'}")
    print(f"{'─'*80}")
    for k in keys:
        status = "✅ Активен" if k["is_active"] else "❌ Откл."
        hwid   = (k["hwid"] or "")[:8] + "..." if k["hwid"] else "не привязан"
        expires = (k["expires_at"] or "")[:10]
        print(f"  {k['key']:<28}  {k['type']:<10}  {expires:<12}  {hwid:<10}  {status}")
    print(f"{'─'*80}")
    print(f"  Всего: {len(keys)} ключей\n")


def cmd_revoke(args):
    result = ok(requests.delete(f"{SERVER}/admin/revoke/{args.key}", headers=HEADERS))
    print(f"✅ {result['message']}")


def cmd_reset(args):
    result = ok(requests.post(f"{SERVER}/admin/reset/{args.key}", headers=HEADERS))
    print(f"✅ {result['message']}")


def cmd_extend(args):
    result = ok(requests.post(
        f"{SERVER}/admin/extend/{args.key}",
        json={"days": args.days},
        headers=HEADERS
    ))
    print(f"✅ {result['message']}  Новая дата: {result['expires_at'][:10]}")


def main():
    parser = argparse.ArgumentParser(
        description="🔑 JARVIS License Admin Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="cmd", metavar="команда")

    # generate
    g = sub.add_parser("generate", help="Создать новые ключи")
    g.add_argument("--type",  choices=["monthly", "yearly", "lifetime"], default="monthly",
                   help="Тип подписки (default: monthly)")
    g.add_argument("--count", type=int, default=1, help="Количество ключей (default: 1)")
    g.add_argument("--note",  default="", help="Заметка (имя клиента)")

    # list
    sub.add_parser("list", help="Показать все ключи")

    # revoke
    r = sub.add_parser("revoke", help="Деактивировать ключ")
    r.add_argument("key", help="Ключ вида JRVS-XXXX-XXXX-XXXX-XXXX")

    # reset
    rs = sub.add_parser("reset", help="Сбросить привязку ключа к ПК")
    rs.add_argument("key")

    # extend
    ex = sub.add_parser("extend", help="Продлить подписку")
    ex.add_argument("key")
    ex.add_argument("--days", type=int, default=30)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        return

    dispatch = {
        "generate": cmd_generate,
        "list":     cmd_list,
        "revoke":   cmd_revoke,
        "reset":    cmd_reset,
        "extend":   cmd_extend,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
