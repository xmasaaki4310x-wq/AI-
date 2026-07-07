#!/usr/bin/env python3
"""SQLite -> UI用JSONエクスポート。"""
import json
from datetime import datetime, timezone

from db import DATA_DIR, connect, cash_balance, invested_total, latest_close, positions

CANDLE_BARS = 260  # フォーカスチャートに出す日足の本数


def file_key(symbol: str) -> str:
    return symbol.replace(".", "_").replace("-", "_")


def dump(name: str, obj) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / name).write_text(
        json.dumps(obj, ensure_ascii=False, separators=(",", ":")))


def price_series(con, symbol: str, limit: int = 260):
    rows = con.execute(
        "SELECT date, close FROM prices WHERE symbol=? ORDER BY date DESC LIMIT ?",
        (symbol, limit)).fetchall()
    return [[r["date"], r["close"]] for r in reversed(rows)]


def realized_pnl(con) -> float:
    """確定損益: 売却ごとに (売却受取額 - 平均取得原価×数量) を積み上げる。"""
    lots: dict = {}
    total = 0.0
    for r in con.execute("SELECT symbol, side, qty, price, fee FROM trades ORDER BY id"):
        p = lots.setdefault(r["symbol"], {"qty": 0.0, "cost": 0.0})
        if r["side"] == "BUY":
            p["cost"] += r["qty"] * r["price"] + r["fee"]
            p["qty"] += r["qty"]
        else:
            if p["qty"] > 0:
                unit = p["cost"] / p["qty"]
                total += (r["qty"] * r["price"] - r["fee"]) - unit * r["qty"]
                p["cost"] -= unit * r["qty"]
            p["qty"] -= r["qty"]
    return round(total, 2)


def export_all(con=None) -> None:
    con = con or connect()

    instruments = [dict(r) for r in con.execute(
        "SELECT * FROM instruments ORDER BY kind, symbol")]

    pos_rows = []
    open_pnl = 0.0
    for sym, p in positions(con).items():
        date, close = latest_close(con, sym)
        inst = con.execute("SELECT name_ja, kind FROM instruments WHERE symbol=?",
                           (sym,)).fetchone()
        val = (close or 0) * p["qty"]
        if close:
            open_pnl += val - p["avg_cost"] * p["qty"]
        pos_rows.append({
            "symbol": sym,
            "name_ja": inst["name_ja"] if inst else sym,
            "kind": inst["kind"] if inst else "?",
            "qty": p["qty"],
            "avg_cost": p["avg_cost"],
            "close": close,
            "close_date": date,
            "value": round(val, 2),
            "pnl": round(val - p["avg_cost"] * p["qty"], 2) if close else None,
            "pnl_pct": round((close - p["avg_cost"]) / p["avg_cost"] * 100, 2)
                       if close else None,
            "spark": [x[1] for x in price_series(con, sym, 30)],
        })

    # 直近価格スナップショット + 銘柄別ローソク足
    market = []
    for inst in instruments:
        sym = inst["symbol"]
        date, close = latest_close(con, sym)
        series = price_series(con, sym, 60)
        prev = series[-2][1] if len(series) >= 2 else None
        market.append({
            "symbol": sym, "name_ja": inst["name_ja"],
            "kind": inst["kind"], "min_lot": inst["min_lot"],
            "key": file_key(sym),
            "close": close, "close_date": date,
            "chg1d": round((close / prev - 1) * 100, 2) if (close and prev) else None,
            "spark": [x[1] for x in series[-30:]],
        })
        bars = con.execute(
            "SELECT date, open, high, low, close, volume FROM prices "
            "WHERE symbol=? ORDER BY date DESC LIMIT ?", (sym, CANDLE_BARS)).fetchall()
        (DATA_DIR / "candles").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "candles" / f"{file_key(sym)}.json").write_text(json.dumps({
            "symbol": sym, "name_ja": inst["name_ja"],
            "bars": [[r["date"],
                      *(None if v is None else round(v, 4)
                        for v in (r["open"], r["high"], r["low"], r["close"])),
                      r["volume"]] for r in reversed(bars)],
        }, ensure_ascii=False, separators=(",", ":")))

    dump("portfolio.json", {
        "cash": cash_balance(con),
        "invested": invested_total(con),
        "open_pnl": round(open_pnl, 2),
        "realized_pnl": realized_pnl(con),
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
