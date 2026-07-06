#!/usr/bin/env python3
"""初回デモ用のシードデータ生成。

実データ取得(fetch.py)がまだ実行できない環境向けに、幾何ブラウン運動で
「それらしい」日足OHLCVを合成して data/raw/*.csv に書き出す。
config.py の seed_price / seed_vol で銘柄ごとの水準・変動率を調整している。

これは合成データであり実際の市場価格ではない。build.py はシードで
生成した場合 meta.json に data_source="seed-demo" を記録し、
アプリのUIは「デモデータ」バナーを表示する。
"""
import hashlib

import numpy as np
import pandas as pd

from config import HISTORY_YEARS, RAW_DIR, WATCHLIST, file_key

TRADING_DAYS = 252


def gen_symbol(entry: dict) -> pd.DataFrame:
    sym = entry["symbol"]
    rng = np.random.default_rng(int(hashlib.sha256(sym.encode()).hexdigest()[:8], 16))
    n = HISTORY_YEARS * TRADING_DAYS
    dt = 1.0 / TRADING_DAYS
    vol = entry["seed_vol"]
    drift = rng.uniform(0.02, 0.12)  # 年率ドリフト

    # レジーム(強気/弱気/レンジ)を数ヶ月単位で切り替えて単調な系列を避ける
    regime_len = rng.integers(40, 90)
    regimes = np.repeat(rng.choice([1.6, 1.0, -1.2], size=n // regime_len + 1,
                                   p=[0.4, 0.35, 0.25]), regime_len)[:n]
    shocks = rng.standard_normal(n)
    log_ret = (drift * regimes - 0.5 * vol**2) * dt + vol * np.sqrt(dt) * shocks

    # 終値が seed_price 付近で「今」終わるように逆算
    end_price = entry["seed_price"] * rng.uniform(0.97, 1.03)
    close = np.exp(np.concatenate([[0.0], np.cumsum(log_ret)]))[1:]
    close = close / close[-1] * end_price

    day_range = np.abs(rng.standard_normal(n)) * vol * np.sqrt(dt) * close
    open_ = np.empty(n)
    open_[0] = close[0]
    open_[1:] = close[:-1] * (1 + rng.standard_normal(n - 1) * vol * np.sqrt(dt) * 0.3)
    high = np.maximum(open_, close) + day_range * 0.6
    low = np.minimum(open_, close) - day_range * 0.6

    base_volume = 10 ** rng.uniform(5.5, 7.5)
    volume = (base_volume * np.exp(rng.standard_normal(n) * 0.5)).astype(np.int64)
    if entry["type"] in ("fx",):
        volume[:] = 0  # 為替は出来高なし

    if entry["type"] == "crypto":
        dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n, freq="D")
    else:
        dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)

    decimals = 4 if entry["seed_price"] < 10 else 2
    df = pd.DataFrame({
        "Open": np.round(open_, decimals),
        "High": np.round(high, decimals),
        "Low": np.round(low, decimals),
        "Close": np.round(close, decimals),
        "Volume": volume,
    }, index=dates)
    df.index.name = "Date"
    return df


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for entry in WATCHLIST:
        df = gen_symbol(entry)
        df.to_csv(RAW_DIR / f"{file_key(entry['symbol'])}.csv")
        print(f"  seed {entry['symbol']}: {len(df)}本 (終値 {df['Close'].iloc[-1]})")
    print(f"\nシード生成完了: {len(WATCHLIST)} 銘柄 -> {RAW_DIR}")


if __name__ == "__main__":
    main()
