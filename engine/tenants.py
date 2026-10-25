"""Tenant registry: which WhatsApp number belongs to which business, plus one-time join codes.

A tenant IS its folder: data/tenants/<tenant_id>/ (see docs/planning/multi-tenant-contract.md).
This SQLite file only maps phones to tenants, holds join codes, and remembers handled message ids.

Link a phone by hand:  python3 -m engine.tenants link 919999999999 mahesh-cnc
Check:                 python3 -m engine.tenants
"""
import os
import re
import secrets
import sqlite3
import sys
from pathlib import Path

DATA_ROOT = Path(os.environ.get("KABTAK_DATA", Path(__file__).resolve().parent.parent / "data"))
DEFAULT = "mahesh-cnc"   # the synthetic demo tenant; engine calls without a tenant use it


def tenant_dir(tid: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]{1,40}", tid or ""):
        raise ValueError(f"Bad tenant id {tid!r}")
    return DATA_ROOT / "tenants" / tid


def exists(tid: str) -> bool:
    return (tenant_dir(tid) / "profile.json").exists()


def new_id(name: str) -> str:
    """Slug of the business name plus a short random suffix, e.g. 'shree-textiles-k3f9'."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:30] or "biz"
    return f"{slug}-{secrets.token_hex(2)}"


def _db():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DATA_ROOT / "registry.sqlite")
    c.executescript("""
        CREATE TABLE IF NOT EXISTS phones (phone TEXT PRIMARY KEY, tenant_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS join_codes (code TEXT PRIMARY KEY, tenant_id TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS seen (msg_id TEXT PRIMARY KEY);""")
    return c


def _phone(p: str) -> str:
    return re.sub(r"\D", "", p)   # E.164 digits only, as the WhatsApp providers send them


def new_join_code(tid: str) -> str:
    """6-digit code the owner sends to the bot as 'JOIN 123456' to link their number."""
    with _db() as c:
        while True:
            code = f"{secrets.randbelow(10**6):06d}"
            if not c.execute("SELECT 1 FROM join_codes WHERE code=?", (code,)).fetchone():
                c.execute("INSERT INTO join_codes VALUES (?, ?)", (code, tid))
                return code


def claim(code: str, phone: str) -> str | None:
    """Link phone to the code's tenant and burn the code. Returns the tenant id, or None for a bad code."""
    with _db() as c:
        row = c.execute("SELECT tenant_id FROM join_codes WHERE code=?", (code.strip(),)).fetchone()
        if not row:
            return None
        c.execute("DELETE FROM join_codes WHERE code=?", (code.strip(),))
        c.execute("INSERT OR REPLACE INTO phones VALUES (?, ?)", (_phone(phone), row[0]))
        return row[0]


def link(phone: str, tid: str) -> None:
    with _db() as c:
        c.execute("INSERT OR REPLACE INTO phones VALUES (?, ?)", (_phone(phone), tid))


def tenant_for(phone: str) -> str | None:
    with _db() as c:
        row = c.execute("SELECT tenant_id FROM phones WHERE phone=?", (_phone(phone),)).fetchone()
    return row[0] if row else None


def first_time(msg_id: str) -> bool:
    """True the first time a provider message id is seen; False on a webhook retry (don't act twice)."""
    with _db() as c:
        return c.execute("INSERT OR IGNORE INTO seen VALUES (?)", (msg_id,)).rowcount == 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["link"]:
        link(sys.argv[2], sys.argv[3])
        print(f"linked {_phone(sys.argv[2])} -> {sys.argv[3]}")
        sys.exit()
    import tempfile
    DATA_ROOT = Path(tempfile.mkdtemp())
    code = new_join_code("shree-textiles-k3f9")
    assert len(code) == 6 and tenant_for("+91 99999 99999") is None
    assert claim("000000" if code != "000000" else "111111", "919999999999") is None
    assert claim(code, "+91 99999 99999") == "shree-textiles-k3f9"
    assert tenant_for("919999999999") == "shree-textiles-k3f9"
    assert claim(code, "918888888888") is None   # codes are single-use
    assert first_time("A1") and not first_time("A1")
    assert tenant_dir("mahesh-cnc").name == "mahesh-cnc" and new_id("Shree Textiles!").startswith("shree-textiles-")
    for bad in ("../x", "", "A"):
        try:
            tenant_dir(bad)
            raise AssertionError(bad)
        except ValueError:
            pass
    print("ok")
