#!/usr/bin/env python3
"""yfinance(ranaroussi/yfinance)で実データを取得し data/raw/*.csv に保存する。

インターネットに出られる環境(ローカルPC・GitHub Actions)で実行する。
成功したシンボルごとに Date,Open,High,Low,Close,Volume のCSVを書き出す。

使い方:
    python3 fetch.py            # 全銘柄
    python3 fetch.py AAPL 7203.T  # 指定銘柄のみ
"""
import sys
import time

import pandas as pd
import yfinance as yf

from config import HISTORY_YEARS, RAW_DIR, WATCHLIST, file_key


def fetch_one(symbol: str) -> pd.DataFrame | None:
    df = yf.download(
        symbol,
        period=f"{HISTORY_YEARS}y",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if df is None or df.empty:
        return None
    # yfinance>=1.x は単一銘柄でも列がMultiIndexになる
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna(subset=["Close"])
    df.index.name = "Date"
    return df


def main() -> None:
    targets = sys.argv[1:] or [w["symbol"] for w in WATCHLIST]
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    ok, ng = [], []
    for sym in targets:
        try:
            df = fetch_one(sym)
        except Exception as e:
            print(f"  NG {sym}: {e}")
            ng.append(sym)
            continue
        if df is None or len(df) < 60:
            print(f"  NG {sym}: データ不足")
            ng.append(sym)
            continue
        df.to_csv(RAW_DIR / f"{file_key(sym)}.csv")
        print(f"  OK {sym}: {len(df)}本 ({df.index[0].date()}〜{df.index[-1].date()})")
        ok.append(sym)
        time.sleep(0.5)  # レート制限対策
    print(f"\n取得OK {len(ok)} / NG {len(ng)}")
    if ng:
        print("NG:", ", ".join(ng))
        sys.exit(1 if not ok else 0)


if __name__ == "__main__":
    main()
