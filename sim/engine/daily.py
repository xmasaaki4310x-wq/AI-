#!/usr/bin/env python3
"""日次バッチ (GitHub Actionsが毎営業日朝JSTに実行)。

1. yfinanceでユニバース全銘柄の日足を取得しDBへupsert
2. 月初の営業日なら仮想入金¥10,000を記録
3. 直近終値で時価評価 (valuations)
4. UI用JSONをエクスポート

ネットワークなし環境では --no-fetch で 2〜4 のみ実行できる。
"""
import sys
from datetime import datetime, timezone

from db import connect, cash_balance, invested_total, positions, latest_close
import export as export_mod

MONTHLY_DEPOSIT = 10_000  # 円/月


def fetch_prices(con) -> int:
    import time

    import pandas as pd
    import yfinance as yf

    def download(sym):
        # レート制限(YFRateLimitError)対策: 1回リトライ
        for attempt in (1, 2):
            try:
                df = yf.download(sym, period="500d", interval="1d",
                                 auto_adjust=True, progress=False)
            except Exception as e:
                print(f"  NG {sym} (試行{attempt}): {e}")
                df = None
            if df is not None and not df.empty:
                return df
            if attempt == 1:
                time.sleep(15)
        return None

    symbols = [r["symbol"] for r in con.execute("SELECT symbol FROM instruments")]
    n = 0
    for sym in symbols:
        df = download(sym)
        time.sleep(1.0)  # レート制限対策の取得間隔
        if df is None or df.empty:
            print(f"  NG {sym}: データなし")
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Close"])
        for idx, row in df.iterrows():
            con.execute(
                "INSERT OR REPLACE INTO prices(date,symbol,open,high,low,close,volume) "
                "VALUES (?,?,?,?,?,?,?)",
                (idx.strftime("%Y-%m-%d"), sym,
                 float(row["Open"]), float(row["High"]), float(row["Low"]),
                 float(row["Close"]), float(row.get("Volume") or 0)),
            )
        n += 1
        print(f"  OK {sym}: {len(df)}本 (最新 {df.index[-1].date()})")
    con.commit()
    return n


def monthly_deposit(con, today: str):
    month = today[:7]
    row = con.execute("SELECT 1 FROM deposits WHERE substr(date,1,7)=?", (month,)).fetchone()
    if row:
        return
    con.execute("INSERT INTO deposits(date,amount,note) VALUES (?,?,?)",
                (today, MONTHLY_DEPOSIT, f"{month} 月次積立"))
    con.commit()
    print(f"月次入金: ¥{MONTHLY_DEPOSIT:,} ({today})")


def mark_to_market(con, today: str):
    cash = cash_balance(con)
    pv = 0.0
    for sym, p in positions(con).items():
        _, close = latest_close(con, sym)
        if close:
            pv += close * p["qty"]
    con.execute(
        "INSERT OR REPLACE INTO valuations(date,cash,positions_value,equity,invested) "
        "VALUES (?,?,?,?,?)",
        (today, round(cash, 2), round(pv, 2), round(cash + pv, 2), invested_total(con)))
    con.commit()
    print(f"時価評価 {today}: 現金¥{cash:,.0f} + ポジション¥{pv:,.0f} = ¥{cash+pv:,.0f}")


def main():
    no_fetch = "--no-fetch" in sys.argv
    con = connect()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not no_fetch:
        ok = fetch_prices(con)
        if ok == 0:
            print("警告: 価格を1銘柄も取得できませんでした", file=sys.stderr)

    monthly_deposit(con, today)
    mark_to_market(con, today)
    export_mod.export_all(con)
    print("日次バッチ完了")


if __name__ == "__main__":
    main()
