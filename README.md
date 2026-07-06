# AI Daily Business Intelligence

AIビジネスニュースを毎日収集・整理して公開しているHTMLレポートサイトです。

- 公開URL: https://xmasaaki4310x-wq.github.io/AI-/
- `latest.html` が最新号、`index.html` がアーカイブ一覧です。
- 各号は `ai_daily_intel_<日付>_<時刻JST>.html` として保存されます。

## 更新の仕組み

レポートは `tools/gen_report.py` で生成します。ニュースの収集・和訳・スコア付けは
Claude Code のセッションが毎朝行い、スクリプト内の `ITEMS` と `JA_TITLES` を
更新してから実行します(手順はスクリプト冒頭のdocstringを参照)。

## サブエージェントの見える化

`.claude/settings.json` のフック設定により、Claude Code がサブエージェントを
起動するたびに `.claude/subagent-activity.jsonl` へ記録が残ります
(起動・終了イベントと、サブエージェントに渡した指示文の先頭500文字)。

- セッション中に「サブエージェントのログを見せて」と頼むと内容を確認できます。
- ログはコミット対象外です(`.gitignore` 済み)。
