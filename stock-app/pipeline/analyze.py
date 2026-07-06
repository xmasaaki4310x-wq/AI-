#!/usr/bin/env python3
"""テクニカル指標の計算とスクリーナー生成。

指標計算には stockstats(jealous/stockstats)を使用する。
data/raw/*.csv を読み、以下を出力する:
  - data/symbols/<KEY>.json : チャート用OHLCV+指標系列
  - data/screener.json      : 全銘柄スクリーナー(RSI・モメンタム・52週高安など)
"""
import json
import math

import numpy as np
import pandas as pd
from stockstats import StockDataFrame

from config import CHART_BARS, RAW_DIR, SYMBOLS_DIR, DATA_DIR, WATCHLIST, file_key


def round_price(x: float, ref: float) -> float:
    return round(x, 4 if ref < 10 else 2)


def series_out(s: pd.Series, ref: float, ndigits: int | None = None) -> list:
    out = []
    for v in s:
        if v is None or (isinstance(v, float) and math.isnan(v)):
            out.append(None)
        else:
            out.append(round(float(v), ndigits) if ndigits is not None
                       else round_price(float(v), ref))
    return out


def pct(a: float, b: float) -> float | None:
    if b == 0 or b is None or a is None or math.isnan(a) or math.isnan(b):
        return None
    return round((a / b - 1) * 100, 2)


def analyze_symbol(entry: dict) -> dict | None:
    key = file_key(entry["symbol"])
    path = RAW_DIR / f"{key}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    if len(df) < 60:
        return None

    # stockstats は ['rsi_14'] のようなキー参照で指標を遅延計算する
    sdf = StockDataFrame.retype(df.copy())
    ind = {
        "sma20": sdf["close_20_sma"],
        "sma50": sdf["close_50_sma"],
        "sma200": sdf["close_200_sma"],
        "bb_up": sdf["boll_ub"],
        "bb_mid": sdf["boll"],
        "bb_low": sdf["boll_lb"],
        "rsi14": sdf["rsi_14"],
        "macd": sdf["macd"],
        "macds": sdf["macds"],
        "macdh": sdf["macdh"],
        "atr14": sdf["atr_14"],
    }

    close = df["Close"]
    ref = float(close.iloc[-1])

    # ---- チャートJSON(直近 CHART_BARS 本) ----
    tail = df.tail(CHART_BARS)
    idx = tail.index
    bars = [
        [d.strftime("%Y-%m-%d"),
         round_price(o, ref), round_price(h, ref),
         round_price(l, ref), round_price(c, ref), int(v)]
        for d, o, h, l, c, v in zip(
            idx, tail["Open"], tail["High"], tail["Low"],
            tail["Close"], tail["Volume"].fillna(0))
    ]
    chart = {
        "symbol": entry["symbol"],
        "name_ja": entry["name_ja"],
        "market": entry["market"],
        "type": entry["type"],
        "currency": entry["currency"],
        "bars": bars,
        "ind": {
            "sma20": series_out(ind["sma20"].reindex(idx), ref),
            "sma50": series_out(ind["sma50"].reindex(idx), ref),
            "sma200": series_out(ind["sma200"].reindex(idx), ref),
            "bb_up": series_out(ind["bb_up"].reindex(idx), ref),
            "bb_mid": series_out(ind["bb_mid"].reindex(idx), ref),
            "bb_low": series_out(ind["bb_low"].reindex(idx), ref),
            "rsi14": series_out(ind["rsi14"].reindex(idx), ref, 1),
            "macd": series_out(ind["macd"].reindex(idx), ref, 4),
            "macds": series_out(ind["macds"].reindex(idx), ref, 4),
            "macdh": series_out(ind["macdh"].reindex(idx), ref, 4),
        },
    }
    SYMBOLS_DIR.mkdir(parents=True, exist_ok=True)
    (SYMBOLS_DIR / f"{key}.json").write_text(
        json.dumps(chart, ensure_ascii=False, separators=(",", ":")))

    # ---- スクリーナー行 ----
    year = close.tail(252)
    hi52, lo52 = float(year.max()), float(year.min())
    sma50 = ind["sma50"].iloc[-1]
    sma200 = ind["sma200"].iloc[-1]
    rsi = ind["rsi14"].iloc[-1]
    atr = ind["atr14"].iloc[-1]
    vol20 = df["Volume"].tail(20).mean()

    golden_recent = False
    s50, s200 = ind["sma50"].tail(21), ind["sma200"].tail(21)
    if not (s50.isna().any() or s200.isna().any()):
        above = (s50 > s200).to_numpy()
        golden_recent = bool((~above[:-1] & above[1:]).any())

    row = {
        "symbol": entry["symbol"],
        "key": key,
        "name_ja": entry["name_ja"],
        "market": entry["market"],
        "type": entry["type"],
        "currency": entry["currency"],
        "close": round_price(ref, ref),
        "chg1d": pct(ref, float(close.iloc[-2])) if len(close) >= 2 else None,
        "chg5d": pct(ref, float(close.iloc[-6])) if len(close) >= 6 else None,
        "chg20d": pct(ref, float(close.iloc[-21])) if len(close) >= 21 else None,
        "vs_hi52": pct(ref, hi52),
        "vs_lo52": pct(ref, lo52),
        "rsi14": None if math.isnan(rsi) else round(float(rsi), 1),
        "trend_up": None if (math.isnan(sma50) or math.isnan(sma200))
                    else bool(sma50 > sma200),
        "golden_cross_20d": golden_recent,
        "atr_pct": None if math.isnan(atr) else round(float(atr) / ref * 100, 2),
        "vol_ratio": None if (not vol20 or math.isnan(vol20) or vol20 == 0)
                     else round(float(df["Volume"].iloc[-1]) / float(vol20), 2),
        "spark": series_out(close.tail(30), ref),
    }
    return row


def main() -> None:
    rows = []
    for entry in WATCHLIST:
        row = analyze_symbol(entry)
        if row is None:
            print(f"  skip {entry['symbol']} (rawデータなし)")
            continue
        rows.append(row)
        print(f"  OK {entry['symbol']}: close={row['close']} rsi={row['rsi14']}")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "screener.json").write_text(
        json.dumps({"rows": rows}, ensure_ascii=False, separators=(",", ":")))
    print(f"\n分析完了: {len(rows)} 銘柄 -> screener.json / symbols/*.json")


if __name__ == "__main__":
    main()
