# 🌐 Global Stock Analyzer — 世界株式マーケット・ダッシュボード

世界中の株取引・分析が得意なオープンソースリポジトリを**132個**収集・分類・実在検証し、
その中の代表的なライブラリを実際に組み込んで作った株式分析Webアプリです。

- 公開URL: https://xmasaaki4310x-wq.github.io/AI-/stock-app/
- OSSレジストリ: https://xmasaaki4310x-wq.github.io/AI-/stock-app/repos.html

## 機能

| セクション | 内容 | 使用OSS |
|---|---|---|
| 世界市場の概況 | 主要13指数の終値・前日比・30日スパークライン | yfinance |
| チャート分析 | ローソク足+出来高、SMA20/50/200、ボリンジャーバンド、RSI、MACD(3ペイン同期) | stockstats + lightweight-charts |
| スクリーナー | 46銘柄(指数・米日欧亜株・FX・暗号資産・商品)のRSI・モメンタム・52週高安・GC検出、ソート可能 | stockstats |
| 戦略バックテスト | SMAクロス/RSI逆張り/ボリンジャーブレイクの3戦略×全銘柄、損益曲線とシャープレシオ等 | backtesting.py + quantstats |
| OSSレジストリ | 世界の株取引・分析系リポジトリ132個のカタログ(10カテゴリ、検索・絞り込み) | verify_registry.py(自作) |

## 実際に組み込んでいるOSS(5つ)

1. [ranaroussi/yfinance](https://github.com/ranaroussi/yfinance) — 市場データ取得
2. [jealous/stockstats](https://github.com/jealous/stockstats) — テクニカル指標計算
3. [kernc/backtesting.py](https://github.com/kernc/backtesting.py) — バックテストエンジン
4. [ranaroussi/quantstats](https://github.com/ranaroussi/quantstats) — リスク調整後指標(シャープ・ソルティノ・最大DD・CAGR)
5. [tradingview/lightweight-charts](https://github.com/tradingview/lightweight-charts) — チャート描画(Apache-2.0、`assets/` に同梱)

残り127個は [OSSレジストリ](repos.html) に日本語解説付きで収録しています。全リポジトリは
`pipeline/verify_registry.py` がGitHub上での実在を自動検証済みです。

## データについて(重要)

初回コミットに含まれるデータは**合成デモデータ**です(`data/meta.json` の
`data_source: "seed-demo"`)。UIにも警告バナーが表示されます。

実データへの切り替え方法(いずれか):

1. **GitHub Actions(推奨)**: `.github/workflows/update-stock-data.yml` が
   平日JST朝にyfinanceで実データを取得し、`stock-app/data/` を自動更新します。
   リポジトリの Actions タブからワークフローを有効化し、`workflow_dispatch` で
   手動実行も可能です。
2. **ローカル実行**:
   ```bash
   pip install -r pipeline/requirements.txt
   python3 pipeline/build.py --live
   ```

## ディレクトリ構成

```
stock-app/
├── index.html            # ダッシュボード
├── repos.html            # OSSレジストリ・カタログ
├── assets/
│   ├── app.js / registry.js / style.css
│   └── lightweight-charts.standalone.production.js  (同梱・Apache-2.0)
├── data/                 # パイプラインが生成するJSON(コミット対象)
│   ├── meta.json / screener.json / backtests.json / repos.json
│   └── symbols/*.json    # 銘柄別OHLCV+指標系列
└── pipeline/
    ├── config.py         # ウォッチリスト46銘柄の定義
    ├── fetch.py          # yfinanceで実データ取得
    ├── seed.py           # デモ用合成データ生成
    ├── analyze.py        # stockstatsで指標計算・スクリーナー生成
    ├── backtest.py       # backtesting.py+quantstatsで3戦略検証
    ├── build.py          # 一括実行(--live / --seed)
    ├── verify_registry.py       # レジストリ実在検証
    └── registry_candidates.json # レジストリ候補(日本語解説付き)
```

## ローカルでの表示確認

`fetch()` を使うため、HTTPサーバー経由で開いてください:

```bash
cd stock-app && python3 -m http.server 8000
# → http://localhost:8000/
```

## 免責事項

本アプリは教育・研究目的のデモであり、投資助言ではありません。
表示データ・バックテスト結果に基づく投資判断は自己責任で行ってください。
