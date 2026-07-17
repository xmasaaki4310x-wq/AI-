#!/usr/bin/env python3
"""日次売買判断セッション用のテクニカル指標スナップショット。

sim/AGENT.md の「市況分析」で使う。SMAだけでなくRSI・MACD・出来高比・
52週レンジまで一括で計算し表示する(stockstatsを使用、stock-appと同じ手法)。

使い方:
    python3 indicators.py            # ユニバース全銘柄
    python3 indicators.py 9432.T 8306.T   # 指定銘柄のみ
"""
import sys

import pandas as pd
from stockstats import StockDataFrame

from db import connect


def snapshot(con, symbol: str) -> dict | None:
    df = pd.read_sql(
        "SELECT date, open, high, low, close, volume FROM prices "
        "WHERE symbol=? ORDER BY date", con, params=(symbol,))
    if len(df) < 60:
        return None
    df = df.set_index(pd.to_datetime(df["date"])).drop(columns=["date"])
    df = df.rename(columns=str.title)
    sdf = StockDataFrame.retype(df.copy())

    close = df["Close"]
    ref = float(close.iloc[-1])
    rsi = sdf["rsi_14"].iloc[-1]
    macd, macds, macdh = sdf["macd"].iloc[-1], sdf["macds"].iloc[-1], sdf["macdh"].iloc[-1]
    sma20, sma50 = sdf["close_20_sma"].iloc[-1], sdf["close_50_sma"].iloc[-1]
    vol20 = df["Volume"].tail(20).mean()
    vol_ratio = df["Volume"].iloc[-1] / vol20 if vol20 else None
    yr = close.tail(252)

    def pct(a, b):
        return round((a / b - 1) * 100, 2) if b else None

    return {
        "symbol": symbol,
        "close": ref,
        "date": df.index[-1].strftime("%Y-%m-%d"),
        "chg1d": pct(ref, close.iloc[-2]) if len(close) >= 2 else None,
        "chg5d": pct(ref, close.iloc[-6]) if len(close) >= 6 else None,
        "chg20d": pct(ref, close.iloc[-21]) if len(close) >= 21 else None,
        "sma20": round(float(sma20), 2), "sma50": round(float(sma50), 2),
        "trend": "上昇" if sma20 > sma50 else "下降",
        "rsi14": round(float(rsi), 1) if rsi == rsi else None,
        "macd_hist": round(float(macdh), 4) if macdh == macdh else None,
        "macd_cross": "GC" if (macd == macd and macd > macds) else "DC",
        "vol_ratio": round(float(vol_ratio), 2) if vol_ratio else None,
        "vs_52w_high": pct(ref, yr.max()),
        "vs_52w_low": pct(ref, yr.min()),
    }


def main() -> None:
    con = connect()
    symbols = sys.argv[1:] or [
        r["symbol"] for r in con.execute("SELECT symbol FROM instruments")]
    for sym in symbols:
        s = snapshot(con, sym)
        if s is None:
            print(f"{sym:9} データ不足")
            continue
        overheat = ""
        if s["rsi14"] is not None:
            if s["rsi14"] >= 70:
                overheat = " [買われすぎ]"
            elif s["rsi14"] <= 30:
                overheat = " [売られすぎ]"
        print(
            f"{sym:9} 終値{s['close']:>10.1f} ({s['date']}) "
            f"1d{s['chg1d']:+6.2f}% 5d{s['chg5d']:+6.2f}% 20d{s['chg20d']:+6.2f}% "
            f"| トレンド{s['trend']}({s['macd_cross']}) RSI{s['rsi14']}{overheat} "
            f"出来高比{s['vol_ratio']}x "
            f"| vs52hi{s['vs_52w_high']:+6.2f}% vs52lo{s['vs_52w_low']:+6.2f}%"
        )


if __name__ == "__main__":
    main()
