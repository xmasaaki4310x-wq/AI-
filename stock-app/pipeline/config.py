"""ウォッチリストとパイプライン共通設定。

symbol は Yahoo Finance 形式(yfinance でそのまま取得可能)。
file_key はデータファイル名に使う安全な識別子。
seed_price / seed_vol は初回シードデータ生成用の目安値(実データ取得後は未使用)。
"""
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
SYMBOLS_DIR = DATA_DIR / "symbols"

HISTORY_YEARS = 2      # 取得・収録する日足の年数
CHART_BARS = 500       # チャートJSONに含める最大本数
EQUITY_POINTS = 150    # バックテスト損益曲線のダウンサンプル点数


def file_key(symbol: str) -> str:
    """Yahoo形式のシンボルをファイル名向けに変換する。"""
    return (symbol.replace("^", "IDX_").replace("=X", "_FX")
                  .replace("=F", "_FUT").replace(".", "_").replace("-", "_"))


# type: index / equity / fx / crypto / commodity
WATCHLIST = [
    # --- 世界の主要株価指数 ---
    {"symbol": "^GSPC",     "name_ja": "S&P 500",            "market": "米国",   "type": "index",  "currency": "USD", "seed_price": 6900,   "seed_vol": 0.13},
    {"symbol": "^IXIC",     "name_ja": "NASDAQ総合",          "market": "米国",   "type": "index",  "currency": "USD", "seed_price": 23000,  "seed_vol": 0.17},
    {"symbol": "^DJI",      "name_ja": "NYダウ",              "market": "米国",   "type": "index",  "currency": "USD", "seed_price": 47500,  "seed_vol": 0.12},
    {"symbol": "^N225",     "name_ja": "日経平均株価",         "market": "日本",   "type": "index",  "currency": "JPY", "seed_price": 51000,  "seed_vol": 0.16},
    {"symbol": "^GDAXI",    "name_ja": "ドイツDAX",           "market": "欧州",   "type": "index",  "currency": "EUR", "seed_price": 24000,  "seed_vol": 0.14},
    {"symbol": "^FTSE",     "name_ja": "英FTSE 100",          "market": "欧州",   "type": "index",  "currency": "GBP", "seed_price": 9700,   "seed_vol": 0.11},
    {"symbol": "^FCHI",     "name_ja": "仏CAC 40",            "market": "欧州",   "type": "index",  "currency": "EUR", "seed_price": 8100,   "seed_vol": 0.13},
    {"symbol": "^STOXX50E", "name_ja": "ユーロ・ストックス50", "market": "欧州",   "type": "index",  "currency": "EUR", "seed_price": 5600,   "seed_vol": 0.13},
    {"symbol": "^HSI",      "name_ja": "香港ハンセン",         "market": "アジア", "type": "index",  "currency": "HKD", "seed_price": 25500,  "seed_vol": 0.20},
    {"symbol": "000001.SS", "name_ja": "上海総合指数",         "market": "アジア", "type": "index",  "currency": "CNY", "seed_price": 4000,   "seed_vol": 0.15},
    {"symbol": "^KS11",     "name_ja": "韓国KOSPI",           "market": "アジア", "type": "index",  "currency": "KRW", "seed_price": 4300,   "seed_vol": 0.16},
    {"symbol": "^AXJO",     "name_ja": "豪ASX 200",           "market": "アジア", "type": "index",  "currency": "AUD", "seed_price": 8700,   "seed_vol": 0.11},
    {"symbol": "^BSESN",    "name_ja": "印SENSEX",            "market": "アジア", "type": "index",  "currency": "INR", "seed_price": 85000,  "seed_vol": 0.13},
    # --- 米国株 ---
    {"symbol": "AAPL",  "name_ja": "アップル",             "market": "米国", "type": "equity", "currency": "USD", "seed_price": 270, "seed_vol": 0.25},
    {"symbol": "MSFT",  "name_ja": "マイクロソフト",        "market": "米国", "type": "equity", "currency": "USD", "seed_price": 480, "seed_vol": 0.24},
    {"symbol": "NVDA",  "name_ja": "エヌビディア",          "market": "米国", "type": "equity", "currency": "USD", "seed_price": 190, "seed_vol": 0.42},
    {"symbol": "GOOGL", "name_ja": "アルファベット",        "market": "米国", "type": "equity", "currency": "USD", "seed_price": 320, "seed_vol": 0.28},
    {"symbol": "AMZN",  "name_ja": "アマゾン",             "market": "米国", "type": "equity", "currency": "USD", "seed_price": 230, "seed_vol": 0.30},
    {"symbol": "META",  "name_ja": "メタ・プラットフォームズ", "market": "米国", "type": "equity", "currency": "USD", "seed_price": 650, "seed_vol": 0.33},
    {"symbol": "TSLA",  "name_ja": "テスラ",               "market": "米国", "type": "equity", "currency": "USD", "seed_price": 420, "seed_vol": 0.55},
    {"symbol": "BRK-B", "name_ja": "バークシャー・ハサウェイ", "market": "米国", "type": "equity", "currency": "USD", "seed_price": 500, "seed_vol": 0.16},
    {"symbol": "JPM",   "name_ja": "JPモルガン・チェース",   "market": "米国", "type": "equity", "currency": "USD", "seed_price": 300, "seed_vol": 0.22},
    {"symbol": "V",     "name_ja": "ビザ",                 "market": "米国", "type": "equity", "currency": "USD", "seed_price": 340, "seed_vol": 0.20},
    {"symbol": "UNH",   "name_ja": "ユナイテッドヘルス",     "market": "米国", "type": "equity", "currency": "USD", "seed_price": 330, "seed_vol": 0.28},
    {"symbol": "XOM",   "name_ja": "エクソンモービル",      "market": "米国", "type": "equity", "currency": "USD", "seed_price": 115, "seed_vol": 0.24},
    # --- 日本株 ---
    {"symbol": "7203.T", "name_ja": "トヨタ自動車",           "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 3100,  "seed_vol": 0.24},
    {"symbol": "6758.T", "name_ja": "ソニーグループ",         "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 4300,  "seed_vol": 0.26},
    {"symbol": "9984.T", "name_ja": "ソフトバンクグループ",    "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 21000, "seed_vol": 0.40},
    {"symbol": "8306.T", "name_ja": "三菱UFJフィナンシャルG",  "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 2300,  "seed_vol": 0.25},
    {"symbol": "6861.T", "name_ja": "キーエンス",             "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 62000, "seed_vol": 0.26},
    {"symbol": "9983.T", "name_ja": "ファーストリテイリング",  "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 54000, "seed_vol": 0.28},
    {"symbol": "4063.T", "name_ja": "信越化学工業",           "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 4800,  "seed_vol": 0.26},
    {"symbol": "6501.T", "name_ja": "日立製作所",             "market": "日本", "type": "equity", "currency": "JPY", "seed_price": 4600,  "seed_vol": 0.30},
    # --- 欧州・アジア株 ---
    {"symbol": "ASML",      "name_ja": "ASML(蘭・ADR)",       "market": "欧州",   "type": "equity", "currency": "USD", "seed_price": 1050,  "seed_vol": 0.32},
    {"symbol": "SAP",       "name_ja": "SAP(独・ADR)",        "market": "欧州",   "type": "equity", "currency": "USD", "seed_price": 250,   "seed_vol": 0.24},
    {"symbol": "MC.PA",     "name_ja": "LVMH(仏)",           "market": "欧州",   "type": "equity", "currency": "EUR", "seed_price": 620,   "seed_vol": 0.26},
    {"symbol": "TSM",       "name_ja": "TSMC(台・ADR)",       "market": "アジア", "type": "equity", "currency": "USD", "seed_price": 220,   "seed_vol": 0.32},
    {"symbol": "BABA",      "name_ja": "アリババ(中・ADR)",    "market": "アジア", "type": "equity", "currency": "USD", "seed_price": 130,   "seed_vol": 0.38},
    {"symbol": "005930.KS", "name_ja": "サムスン電子(韓)",     "market": "アジア", "type": "equity", "currency": "KRW", "seed_price": 90000, "seed_vol": 0.28},
    {"symbol": "0700.HK",   "name_ja": "テンセント(中・香港)", "market": "アジア", "type": "equity", "currency": "HKD", "seed_price": 640,   "seed_vol": 0.30},
    # --- 為替 ---
    {"symbol": "USDJPY=X", "name_ja": "米ドル/円",   "market": "FX", "type": "fx", "currency": "JPY", "seed_price": 155,  "seed_vol": 0.09},
    {"symbol": "EURUSD=X", "name_ja": "ユーロ/米ドル", "market": "FX", "type": "fx", "currency": "USD", "seed_price": 1.16, "seed_vol": 0.07},
    # --- 暗号資産 ---
    {"symbol": "BTC-USD", "name_ja": "ビットコイン",  "market": "暗号資産", "type": "crypto", "currency": "USD", "seed_price": 95000, "seed_vol": 0.50},
    {"symbol": "ETH-USD", "name_ja": "イーサリアム",  "market": "暗号資産", "type": "crypto", "currency": "USD", "seed_price": 3300,  "seed_vol": 0.60},
    # --- 商品先物 ---
    {"symbol": "GC=F", "name_ja": "金先物",     "market": "商品", "type": "commodity", "currency": "USD", "seed_price": 4200, "seed_vol": 0.15},
    {"symbol": "CL=F", "name_ja": "WTI原油先物", "market": "商品", "type": "commodity", "currency": "USD", "seed_price": 62,   "seed_vol": 0.32},
]
