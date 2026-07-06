# AI Daily Business Intelligence

AIビジネスニュースを毎日収集・整理して公開しているHTMLレポートサイトです。

- 公開URL: https://xmasaaki4310x-wq.github.io/AI-/
- `latest.html` が最新号、`index.html` がアーカイブ一覧です。
- 各号は `ai_daily_intel_<日付>_<時刻JST>.html` として保存されます。

## 更新の仕組み

レポートは `tools/gen_report.py` で生成します。ニュースの収集・和訳・スコア付けは
Claude Code のセッションが毎朝行い、スクリプト内の `ITEMS` と `JA_TITLES` を
更新してから実行します(手順はスクリプト冒頭のdocstringを参照)。
