#!/usr/bin/env python3
"""パイプライン一括実行。

  python3 build.py          # data/raw が空ならシード生成、あれば既存rawで分析
  python3 build.py --live   # yfinanceで実データ取得(要インターネット)
  python3 build.py --seed   # 強制的にシード(デモ)データを再生成

実行順: (fetch|seed) -> analyze -> backtest -> meta.json
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR, RAW_DIR

HERE = Path(__file__).resolve().parent


def run(script: str, *args: str) -> None:
    r = subprocess.run([sys.executable, str(HERE / script), *args])
    if r.returncode != 0:
        print(f"警告: {script} が終了コード {r.returncode} で終了")


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    have_raw = RAW_DIR.exists() and any(RAW_DIR.glob("*.csv"))

    if mode == "--live":
        source = "live"
        run("fetch.py")
    elif mode == "--seed" or not have_raw:
        source = "seed-demo"
        run("seed.py")
    else:
        # 既存rawの由来は前回のmeta.jsonを引き継ぐ
        meta_path = DATA_DIR / "meta.json"
        source = "live"
        if meta_path.exists():
            source = json.loads(meta_path.read_text()).get("data_source", "live")

    run("analyze.py")
    run("backtest.py")

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_source": source,
    }
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    print(f"\nビルド完了 (data_source={source})")


if __name__ == "__main__":
    main()
