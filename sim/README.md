# 🤖 Claude Code 投資シミュレーター(ペーパートレード)

Claude Code が**仮想資金・毎月1万円積立**で毎営業日売買判断を行い、
その成果を測定する実験です。リアルマネーは一切使いません。

- UI: https://xmasaaki4310x-wq.github.io/AI-/sim/
- 売買履歴・判断理由は **SQLite3** (`db/paper.db`) に記録され、UIからダウンロードも可能

## 仕組み

```
毎営業日 JST 07:45  GitHub Actions (sim-daily.yml)
   └─ yfinanceで12銘柄の実終値を取得 → SQLiteへ保存
      月初なら¥10,000入金 → 時価評価 → UI用JSONエクスポート → コミット

毎営業日 JST 09:00  定時トリガー (Claude Code Routine, 自己バインド方式)
   └─ セッションが再開し、AGENT.md の手順で
      市況分析(indicators.py) → 損益ラダーに基づく判断 → trade.pyで執行
      → 判断理由をDBに記録 → コミット
```

判断ルールは投資歴70年の個人投資家・藤本茂氏の相場観を参考にした
含み損益ベースの段階的ラダー(詳細は `AGENT.md` 参照)。

## ルール(実験条件)

| 項目 | 内容 |
|---|---|
| 資金 | 仮想。毎月最初の営業日に¥10,000自動入金 |
| 対象 | 日本株9(S株1株〜)+ ETF2(1655/1306、10口〜)+ BTC(0.001〜)の12銘柄 |
| 執行 | 直近終値で約定(S株の寄付約定に相当) |
| 手数料 | 国内株・ETF: 0円(SBI証券ゼロ革命+S株・電子交付条件) / BTC: 0.15%(bitFlyer Lightning現物) |
| 判断 | Claude Code自身。理由の記録は必須。エンジン改変は禁止 |

手数料の出典: [SBI証券 ゼロ革命](https://www.sbisec.co.jp/visitor/zero-revolution) /
[bitFlyer 手数料一覧](https://bitflyer.com/ja-jp/s/commission)(2026年7月調査)

## ディレクトリ

```
sim/
├── index.html / assets/     # UI (資産推移・保有・売買履歴・判断ログ)
├── AGENT.md                 # 日次判断セッションの運用手順書
├── db/paper.db              # SQLite3 データベース (真実の記録)
├── data/*.json              # UI用エクスポート
└── engine/
    ├── schema.sql / db.py   # スキーマ・共通処理
    ├── fees.py              # 実在手数料モデル
    ├── setup_db.py          # 初期化 (ユニバース12銘柄)
    ├── trade.py             # 売買CLI (検証付き: 現金・ロット・保有数量)
    ├── daily.py             # 日次バッチ (価格取得・入金・時価評価)
    ├── indicators.py        # テクニカル指標スナップショット (RSI/MACD/出来高比等)
    ├── export.py            # SQLite→JSON
    └── requirements.txt     # yfinance / pandas / stockstats
```

## 手動での操作

```bash
cd sim/engine
python3 trade.py status                          # 現状確認
python3 daily.py --no-fetch                      # 再評価+エクスポート(ネット不要)
python3 daily.py                                 # 価格取得込み(要インターネット)
python3 trade.py buy 9432.T 10 --reason "..."    # 売買(理由必須)
```

## 免責事項

教育・研究目的の実験です。投資助言ではありません。
