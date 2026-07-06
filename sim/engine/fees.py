"""実在の手数料モデル (2026年7月調査)。

- 国内株式・国内ETF: 0円
  SBI証券「ゼロ革命」(2023年9月末〜) により、インターネットコース+
  取引報告書等の全面電子交付を条件に、現物・信用・S株(単元未満株)の
  売買手数料が無料。単元未満株の売買が完全無料なのは主要ネット証券では
  SBI証券のみ。
  出典: https://www.sbisec.co.jp/visitor/zero-revolution
        https://faq.sbisec.co.jp/answer/64f176ea8e582c2aa5655c2a/

- 暗号資産(BTC現物): 約定金額の0.15%
  bitFlyer Lightning(取引所)の直近30日取引量 50BTC未満の
  ティア手数料。販売所(スプレッド約5%)ではなく取引所を想定。
  出典: https://bitflyer.com/ja-jp/s/commission

注: S株の約定は1日数回の寄付タイミングのため、本シミュレーターの
「直近終値で約定」モデルは現実のS株取引の粒度とほぼ一致する。
"""

CRYPTO_FEE_RATE = 0.0015  # bitFlyer Lightning 現物 (<50BTC/30日)


def trade_fee(kind: str, qty: float, price: float) -> float:
    """約定手数料(円)を返す。"""
    if kind in ("equity", "etf"):
        return 0.0  # SBI証券ゼロ革命 (電子交付条件を満たす前提)
    if kind == "crypto":
        return round(qty * price * CRYPTO_FEE_RATE, 4)
    raise ValueError(f"未知の商品種別: {kind}")
