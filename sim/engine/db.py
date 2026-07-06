"""SQLite接続とポジション計算の共通処理。"""
import sqlite3
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent.parent
DB_PATH = SIM_DIR / "db" / "paper.db"
DATA_DIR = SIM_DIR / "data"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((Path(__file__).parent / "schema.sql").read_text())
    return con


def get_config(con, key: str, default=None):
    row = con.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def cash_balance(con) -> float:
    dep = con.execute("SELECT COALESCE(SUM(amount),0) AS s FROM deposits").fetchone()["s"]
    trd = con.execute("SELECT COALESCE(SUM(amount),0) AS s FROM trades").fetchone()["s"]
    return round(dep + trd, 4)


def invested_total(con) -> float:
    return con.execute("SELECT COALESCE(SUM(amount),0) AS s FROM deposits").fetchone()["s"]


def positions(con) -> dict:
    """symbol -> {qty, avg_cost}(加重平均取得単価、手数料込み)"""
    pos = {}
    rows = con.execute("SELECT symbol, side, qty, price, fee FROM trades ORDER BY id")
    for r in rows:
        p = pos.setdefault(r["symbol"], {"qty": 0.0, "cost": 0.0})
        if r["side"] == "BUY":
            p["cost"] += r["qty"] * r["price"] + r["fee"]
            p["qty"] += r["qty"]
        else:
            if p["qty"] > 0:
                unit_cost = p["cost"] / p["qty"]
                p["cost"] -= unit_cost * r["qty"]
            p["qty"] -= r["qty"]
    out = {}
    for sym, p in pos.items():
        if p["qty"] > 1e-12:
            out[sym] = {"qty": round(p["qty"], 8),
                        "avg_cost": round(p["cost"] / p["qty"], 4)}
    return out


def latest_close(con, symbol: str):
    row = con.execute(
        "SELECT date, close FROM prices WHERE symbol=? ORDER BY date DESC LIMIT 1",
        (symbol,)).fetchone()
    return (row["date"], row["close"]) if row else (None, None)
