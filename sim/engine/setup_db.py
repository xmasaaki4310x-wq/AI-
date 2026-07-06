#!/usr/bin/env python3
"""初期セットアップ (一度だけ実行)。ユニバース定義と初回入金を登録する。

ユニバース選定基準 (2026-07-06 時点の調査):
- 月1万円の積立予算で現実に買える最小単位であること
  (日本株はSBI証券S株で1株から / 1655は10口≈9,000円弱 / BTCは0.001BTC)
- 財務健全で流動性の高い大型株を中心に、セクター分散
  (通信・金融・自動車・エレクトロニクス・商社・たばこ・リース・素材)
- インデックス(S&P500・TOPIX)と暗号資産も選択肢に入れ、
  Claudeが配分判断できる幅を持たせる
"""
from datetime import datetime, timezone

from db import connect

INSTRUMENTS = [
    # symbol, name_ja, kind, min_lot, lot_step, fee_note
    ("9432.T", "NTT",                "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("8306.T", "三菱UFJフィナンシャルG", "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("7203.T", "トヨタ自動車",         "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("6758.T", "ソニーグループ",       "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("6501.T", "日立製作所",           "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("8058.T", "三菱商事",             "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("2914.T", "日本たばこ産業(JT)",   "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("8591.T", "オリックス",           "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("4063.T", "信越化学工業",         "equity", 1, 1, "SBI証券S株: 売買手数料0円"),
    ("1655.T", "iシェアーズ S&P500 ETF", "etf",  10, 10, "SBI証券ゼロ革命: 売買手数料0円 (売買単位10口)"),
    ("1306.T", "NEXT FUNDS TOPIX ETF",  "etf",  10, 10, "SBI証券ゼロ革命: 売買手数料0円 (売買単位10口)"),
    ("BTC-JPY", "ビットコイン",        "crypto", 0.001, 0.001, "bitFlyer Lightning現物: 0.15%"),
]

CONFIG = {
    "start_date": "2026-07-06",
    "monthly_deposit_jpy": "10000",
    "base_currency": "JPY",
    "broker_model": "SBI証券(ゼロ革命+S株) / bitFlyer Lightning",
    "execution_model": "直近終値で約定(S株の寄付約定に相当)",
}


def main():
    con = connect()
    for row in INSTRUMENTS:
        con.execute(
            "INSERT OR IGNORE INTO instruments"
            "(symbol,name_ja,kind,min_lot,lot_step,fee_note) VALUES (?,?,?,?,?,?)", row)
    for k, v in CONFIG.items():
        con.execute("INSERT OR REPLACE INTO config(key,value) VALUES (?,?)", (k, v))

    # 初回入金 (2026-07分)
    if not con.execute("SELECT 1 FROM deposits").fetchone():
        con.execute("INSERT INTO deposits(date,amount,note) VALUES (?,?,?)",
                    ("2026-07-06", 10000, "2026-07 月次積立(初回)"))
    con.commit()
    print("セットアップ完了:",
          con.execute("SELECT COUNT(*) AS n FROM instruments").fetchone()["n"], "銘柄")


if __name__ == "__main__":
    main()
