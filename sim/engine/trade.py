#!/usr/bin/env python3
"""売買・判断記録CLI (Claude Codeの日次セッションが使用する)。

使い方:
    python3 trade.py status
    python3 trade.py buy  9432.T 10 --reason "配当利回り3.7%で..."
    python3 trade.py sell 1655.T 10 --reason "利益確定..."
    python3 trade.py decision --summary "HOLD" --detail "本日は..."

約定価格は常にDB内の直近終値を使う(価格の手入力は不可 = 改ざん防止)。
数量は instruments の min_lot / lot_step を満たす必要がある。
"""
import argparse
import sys
from datetime import datetime, timezone

from db import connect, cash_balance, latest_close, positions
from fees import trade_fee


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def die(msg: str):
    print(f"エラー: {msg}", file=sys.stderr)
    sys.exit(1)


def check_lot(inst, qty: float):
    if qty < inst["min_lot"] - 1e-12:
        die(f"{inst['symbol']} の最小数量は {inst['min_lot']} です")
    steps = (qty - inst["min_lot"]) / inst["lot_step"]
    if abs(steps - round(steps)) > 1e-6:
        die(f"{inst['symbol']} の数量刻みは {inst['lot_step']} です")


def cmd_trade(args, side: str):
    con = connect()
    inst = con.execute("SELECT * FROM instruments WHERE symbol=?", (args.symbol,)).fetchone()
    if not inst:
        die(f"ユニバース外の銘柄です: {args.symbol}")
    qty = float(args.qty)
    check_lot(inst, qty)

    date, price = latest_close(con, args.symbol)
    if price is None:
        die(f"{args.symbol} の価格データがありません (Actionsの価格取得を待ってください)")

    fee = trade_fee(inst["kind"], qty, price)
    if side == "BUY":
        need = qty * price + fee
        cash = cash_balance(con)
        if need > cash + 1e-9:
            die(f"現金不足: 必要 ¥{need:,.0f} / 残高 ¥{cash:,.0f}")
        amount = -need
    else:
        held = positions(con).get(args.symbol, {"qty": 0})["qty"]
        if qty > held + 1e-9:
            die(f"保有数量不足: 保有 {held} / 売却指定 {qty}")
        amount = qty * price - fee

    cash_after = round(cash_balance(con) + amount, 4)
    con.execute(
        "INSERT INTO trades(ts,date,symbol,side,qty,price,fee,amount,cash_after,reason) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (now_iso(), date, args.symbol, side, qty, price, fee, round(amount, 4),
         cash_after, args.reason),
    )
    con.commit()
    print(f"{side} {args.symbol} {qty} @ ¥{price:,.2f} (基準日 {date}, 手数料 ¥{fee:,.2f}) "
          f"-> 現金残高 ¥{cash_after:,.0f}")


def cmd_decision(args):
    con = connect()
    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    con.execute("INSERT INTO decisions(date,ts,summary,detail) VALUES (?,?,?,?)",
                (date, now_iso(), args.summary, args.detail))
    con.commit()
    print(f"判断を記録: [{date}] {args.summary}")


def cmd_status(_args):
    con = connect()
    cash = cash_balance(con)
    pos = positions(con)
    print(f"現金: ¥{cash:,.0f}")
    total = cash
    for sym, p in sorted(pos.items()):
        date, close = latest_close(con, sym)
        val = (close or 0) * p["qty"]
        total += val
        pnl = (close - p["avg_cost"]) / p["avg_cost"] * 100 if close else 0
        print(f"  {sym}: {p['qty']}株/口 取得単価¥{p['avg_cost']:,.2f} "
              f"時価¥{val:,.0f} ({pnl:+.2f}%) [終値{date}]")
    print(f"資産総額: ¥{total:,.0f}")
    n = con.execute("SELECT COUNT(*) AS n FROM prices").fetchone()["n"]
    d = con.execute("SELECT MAX(date) AS d FROM prices").fetchone()["d"]
    print(f"価格データ: {n}行 (最新 {d})")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    for side in ("buy", "sell"):
        sp = sub.add_parser(side)
        sp.add_argument("symbol")
        sp.add_argument("qty", type=float)
        sp.add_argument("--reason", required=True, help="売買判断の理由(必須)")

    dp = sub.add_parser("decision")
    dp.add_argument("--summary", required=True)
    dp.add_argument("--detail", required=True)
    dp.add_argument("--date")

    sub.add_parser("status")

    args = p.parse_args()
    if args.cmd == "buy":
        cmd_trade(args, "BUY")
    elif args.cmd == "sell":
        cmd_trade(args, "SELL")
    elif args.cmd == "decision":
        cmd_decision(args)
    else:
        cmd_status(args)


if __name__ == "__main__":
    main()
