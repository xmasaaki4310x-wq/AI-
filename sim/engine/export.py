#!/usr/bin/env python3
"""SQLite -> UI用JSONエクスポート。"""
import json
from datetime import datetime, timezone

from db import DATA_DIR, connect, cash_balance, invested_total, latest_close, positions


def dump(name: str, obj) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / name).write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def price_series(con, symbol: str, limit: int = 260):
    rows = con.execute(
        "SELECT date, close FROM prices WHERE symbol=? ORDER BY date DESC LIMIT ?",
        (symbol, limit)).fetchall()
    return [[r["date"], r["close"]] for r in reversed(rows)]


def export_all(con=None) -> None:
    con = con or connect()

    instruments = [dict(r) for r in con.execute(
        "SELECT * FROM instruments ORDER BY kind, symbol")]

    pos_rows = []
    for sym, p in positions(con).items():
        date, close = latest_close(con, sym)
        inst = con.execute("SELECT name_ja, kind FROM instruments WHERE symbol=?",
                           (sym,)).fetchone()
        val = (close or 0) * p["qty"]
        pos_rows.append({
            "symbol": sym,
            "name_ja": inst["name_ja"] if inst else sym,
            "kind": inst["kind"] if inst else "?",
            "qty": p["qty"],
            "avg_cost": p["avg_cost"],
            "close": close,
            "close_date": date,
            "value": round(val, 2),
            "pnl_pct": round((close - p["avg_cost"]) / p["avg_cost"] * 100, 2)
                       if close else None,
        })

    # 直近価格スナップショット(全ユニバース、判断とUIの参考用)
    market = []
    for inst in instruments:
        date, close = latest_close(con, inst["symbol"])
        series = price_series(con, inst["symbol"], 60)
        prev = series[-2][1] if len(series) >= 2 else None
        market.append({
            "symbol": inst["symbol"], "name_ja": inst["name_ja"],
            "kind": inst["kind"], "min_lot": inst["min_lot"],
            "close": close, "close_date": date,
            "chg1d": round((close / prev - 1) * 100, 2) if (close and prev) else None,
            "spark": [x[1] for x in series[-30:]],
        })

    dump("portfolio.json", {
        "cash": cash_balance(con),
        "invested": invested_total(con),
        "positions": pos_rows,
        "history": [dict(r) for r in con.execute(
            "SELECT * FROM valuations ORDER BY date")],
        "deposits": [dict(r) for r in con.execute(
            "SELECT date, amount, note FROM deposits ORDER BY date")],
    })
    dump("trades.json", {"trades": [dict(r) for r in con.execute(
        "SELECT * FROM trades ORDER BY id DESC")]})
    dump("decisions.json", {"decisions": [dict(r) for r in con.execute(
        "SELECT * FROM decisions ORDER BY id DESC LIMIT 120")]})
    dump("market.json", {"instruments": market})
    dump("meta.json", {
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "latest_price_date": con.execute(
            "SELECT MAX(date) AS d FROM prices").fetchone()["d"],
    })
    print(f"エクスポート完了 -> {DATA_DIR}")


if __name__ == "__main__":
    export_all()
