#!/usr/bin/env python3
"""レジストリ候補のGitHubリポジトリ実在検証ツール。

registry_candidates.json の各候補について raw.githubusercontent.com 上の
README 系ファイルの存在を確認し、検証済みリポジトリだけを
stock-app/data/repos.json に書き出す。

使い方:
    python3 verify_registry.py
"""
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATES = HERE / "registry_candidates.json"
OUT = HERE.parent / "data" / "repos.json"

README_NAMES = [
    "README.md", "README.rst", "README.markdown", "readme.md",
    "README.txt", "Readme.md", "README",
]


def head_status(url: str) -> int:
    try:
        r = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "20", url],
            capture_output=True, text=True, timeout=30,
        )
        return int(r.stdout.strip() or 0)
    except Exception:
        return 0


def verify(entry: dict) -> tuple[dict, bool]:
    owner, repo = entry["owner"], entry["repo"]
    for name in README_NAMES:
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{name}"
        if head_status(url) == 200:
            return entry, True
    return entry, False


def main() -> None:
    doc = json.loads(CANDIDATES.read_text())
    candidates = [c for c in doc["candidates"] if c.get("desc_ja")]
    print(f"候補 {len(candidates)} 件を検証中...")

    verified, failed = [], []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for entry, ok in ex.map(verify, candidates):
            (verified if ok else failed).append(entry)
            mark = "OK " if ok else "NG "
            print(f"  {mark} {entry['owner']}/{entry['repo']}", flush=True)

    for e in verified:
        e["url"] = f"https://github.com/{e['owner']}/{e['repo']}"

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "categories": doc["categories"],
        "count": len(verified),
        "repos": sorted(verified, key=lambda e: (e["category"], e["owner"].lower())),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))

    print(f"\n検証OK: {len(verified)} 件 / NG: {len(failed)} 件 -> {OUT}")
    if failed:
        print("NG一覧:", ", ".join(f"{e['owner']}/{e['repo']}" for e in failed))
    if len(verified) < 100:
        print(f"警告: 100件未満です(あと {100 - len(verified)} 件必要)", file=sys.stderr)


if __name__ == "__main__":
    main()
