#!/usr/bin/env python3
"""戦略バックテスト。

エンジンには backtesting.py(kernc/backtesting.py)、
評価指標の一部には quantstats(ranaroussi/quantstats)を使用する。

3つの古典戦略を全銘柄に適用し、data/backtests.json に
統計値と損益曲線(ダウンサンプル済み)を書き出す。
"""
import json
import math
import warnings

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

import quantstats.stats as qs_stats

from config import DATA_DIR, EQUITY_POINTS, RAW_DIR, WATCHLIST, file_key

warnings.filterwarnings("ignore")

CASH = 1_000_000
COMMISSION = 0.001  # 0.1%


def SMA(arr, n):
    return pd.Series(arr).rolling(n).mean()


def RSI(arr, n=14):
    s = pd.Series(arr)
    diff = s.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    down = (-diff.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / down
    return 100 - 100 / (1 + rs)


class SmaCross(Strategy):
    """ゴールデンクロス戦略: SMA20がSMA50を上抜けで買い、下抜けで手仕舞い。"""
    n1, n2 = 20, 50

    def init(self):
        self.sma1 = self.I(SMA, self.data.Close, self.n1)
        self.sma2 = self.I(SMA, self.data.Close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.position.close()
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.position.close()


class RsiMeanRevert(Strategy):
    """RSI逆張り戦略: RSI14が30未満で買い、70超えで手仕舞い。"""
    def init(self):
        self.rsi = self.I(RSI, self.data.Close, 14)

    def next(self):
        if not self.position and self.rsi[-1] < 30:
            self.buy()
        elif self.position and self.rsi[-1] > 70:
            self.position.close()


class BbandBreakout(Strategy):
    """ボリンジャーブレイクアウト戦略: +2σ上抜けで買い、中心線割れで手仕舞い。"""
    n = 20

    def init(self):
        close = pd.Series(self.data.Close)
        self.mid = self.I(lambda c: pd.Series(c).rolling(self.n).mean(), self.data.Close)
        self.upper = self.I(
            lambda c: pd.Series(c).rolling(self.n).mean()
            + 2 * pd.Series(c).rolling(self.n).std(), self.data.Close)

    def next(self):
        if not self.position and crossover(self.data.Close, self.upper):
            self.buy()
        elif self.position and crossover(self.mid, self.data.Close):
            self.position.close()


STRATEGIES = [
    ("sma_cross", "SMAクロス (20/50)", SmaCross),
    ("rsi_revert", "RSI逆張り (30/70)", RsiMeanRevert),
    ("bb_breakout", "ボリンジャー・ブレイクアウト", BbandBreakout),
]


def downsample(s: pd.Series, n: int) -> list:
    if len(s) <= n:
        idx = range(len(s))
    else:
        idx = np.linspace(0, len(s) - 1, n).astype(int)
    return [[s.index[i].strftime("%Y-%m-%d"), round(float(s.iloc[i]), 1)] for i in idx]


def clean(x) -> float | None:
    try:
        f = float(x)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 3)
    except (TypeError, ValueError):
        return None


def run_symbol(entry: dict) -> dict | None:
    key = file_key(entry["symbol"])
    path = RAW_DIR / f"{key}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
    if len(df) < 220:
        return None
    df = df[["Open", "High", "Low", "Close", "Volume"]].astype(float)

    results = []
    for sid, name_ja, cls in STRATEGIES:
        bt = Backtest(df, cls, cash=CASH, commission=COMMISSION,
                      exclusive_orders=True, finalize_trades=True)
        stats = bt.run()
        equity = stats["_equity_curve"]["Equity"]
        daily_ret = equity.pct_change().dropna()

        # quantstats によるリスク調整後指標
        sharpe = clean(qs_stats.sharpe(daily_ret)) if len(daily_ret) > 30 else None
        sortino = clean(qs_stats.sortino(daily_ret)) if len(daily_ret) > 30 else None
        max_dd = clean(qs_stats.max_drawdown(equity))
        cagr = clean(qs_stats.cagr(daily_ret)) if len(daily_ret) > 30 else None

        results.append({
            "id": sid,
            "name_ja": name_ja,
            "return_pct": clean(stats["Return [%]"]),
            "buy_hold_pct": clean(stats["Buy & Hold Return [%]"]),
            "sharpe": sharpe,
            "sortino": sortino,
            "max_dd_pct": None if max_dd is None else round(max_dd * 100, 2),
            "cagr_pct": None if cagr is None else round(cagr * 100, 2),
            "trades": int(stats["# Trades"]),
            "win_rate": clean(stats["Win Rate [%]"]),
            "equity": downsample(equity, EQUITY_POINTS),
        })
    return {
        "symbol": entry["symbol"],
        "key": key,
        "name_ja": entry["name_ja"],
        "strategies": results,
    }


def main() -> None:
    out = []
    for entry in WATCHLIST:
        try:
            r = run_symbol(entry)
        except Exception as e:
            print(f"  NG {entry['symbol']}: {type(e).__name__}: {e}")
            continue
        if r is None:
            print(f"  skip {entry['symbol']}")
            continue
        best = max(r["strategies"], key=lambda s: s["return_pct"] or -999)
        print(f"  OK {entry['symbol']}: best={best['id']} ({best['return_pct']}%)")
        out.append(r)
    (DATA_DIR / "backtests.json").write_text(
        json.dumps({"cash": CASH, "commission": COMMISSION, "results": out},
                   ensure_ascii=False, separators=(",", ":")))
    print(f"\nバックテスト完了: {len(out)} 銘柄 -> backtests.json")


if __name__ == "__main__":
    main()
