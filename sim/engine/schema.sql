-- Claude Code ペーパートレード・シミュレーター DBスキーマ (SQLite3)
-- 仮想マネーのみ。実際の売買は一切行わない。

CREATE TABLE IF NOT EXISTS config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- 取引対象ユニバース
CREATE TABLE IF NOT EXISTS instruments (
    symbol    TEXT PRIMARY KEY,   -- yfinance形式 (9432.T / 1655.T / BTC-JPY)
    name_ja   TEXT NOT NULL,
    kind      TEXT NOT NULL,      -- equity / etf / crypto
    min_lot   REAL NOT NULL,      -- 最小購入数量 (S株=1株, 1655=10口, BTC=0.001)
    lot_step  REAL NOT NULL,      -- 数量の刻み
    fee_note  TEXT NOT NULL       -- 適用する実在手数料の説明
);

-- 毎月の仮想入金 (積立)
CREATE TABLE IF NOT EXISTS deposits (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    date   TEXT NOT NULL,         -- YYYY-MM-DD
    amount REAL NOT NULL,         -- 円
    note   TEXT
);

-- 約定履歴 (Claudeの判断理由付き)
CREATE TABLE IF NOT EXISTS trades (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,     -- 記録時刻 (UTC ISO8601)
    date       TEXT NOT NULL,     -- 約定基準日 (使用した終値の日付)
    symbol     TEXT NOT NULL REFERENCES instruments(symbol),
    side       TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
    qty        REAL NOT NULL CHECK (qty > 0),
    price      REAL NOT NULL,     -- 約定価格 = 直近終値 (円)
    fee        REAL NOT NULL,     -- 手数料 (円)
    amount     REAL NOT NULL,     -- 受渡金額 (BUY: -(qty*price+fee) / SELL: qty*price-fee)
    cash_after REAL NOT NULL,     -- 約定後の現金残高
    reason     TEXT NOT NULL      -- Claudeの売買判断理由
);

-- 日次判断ログ (売買しなかった日も記録)
CREATE TABLE IF NOT EXISTS decisions (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    date    TEXT NOT NULL,
    ts      TEXT NOT NULL,
    summary TEXT NOT NULL,        -- 一行サマリ (例: "HOLD" / "BUY 9432×10")
    detail  TEXT NOT NULL         -- 判断の全文 (市況認識・根拠・リスク)
);

-- 日足価格 (GitHub Actionsがyfinanceで取得)
CREATE TABLE IF NOT EXISTS prices (
    date   TEXT NOT NULL,
    symbol TEXT NOT NULL,
    open   REAL, high REAL, low REAL, close REAL NOT NULL,
    volume REAL,
    PRIMARY KEY (date, symbol)
);

-- 日次時価評価
CREATE TABLE IF NOT EXISTS valuations (
    date            TEXT PRIMARY KEY,
    cash            REAL NOT NULL,
    positions_value REAL NOT NULL,
    equity          REAL NOT NULL,  -- cash + positions_value
    invested        REAL NOT NULL   -- 累計入金額 (元本)
);
