#!/usr/bin/env python3
"""
check_staleness.py — 組裝前的「產物比來源新」檢查

EP01 踩了三次同一個坑：mp4 看起來很新、幀數也對，但它比 `scenes01.tsx` 或比
其他場景舊——因為有人（或另一個 session）在你組裝之後又重渲了某幾支。這種錯
不會報錯，只會讓成片默默混著兩個版本。

用法：
    python3 tools/check_staleness.py --ep 1
    ... --assembled      # 連 body/final 一起查（組裝完成後驗收用）

exit 0 = 可以組裝；exit 1 = 有東西過期，訊息會指出是哪一支比什麼新。
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ["remotion/src/scenes01.tsx", "remotion/src/TerminalKit.tsx",
           "remotion/src/Episode01.tsx", "remotion/src/ep01Data.ts",
           "remotion/src/ep01Cues.ts"]


def mtime(p):
    return p.stat().st_mtime if p.exists() else None


def hhmmss(t):
    import datetime
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True)
    ap.add_argument("--assembled", action="store_true",
                    help="連 body_nobgm / ep01_final 一起查")
    args = ap.parse_args()
    nn = f"{args.ep:02d}"
    render = ROOT / "episodes" / f"ep{nn}" / "render"

    # 來源最後修改時間（集號帶入檔名）
    srcs = {}
    for s in SOURCES:
        p = ROOT / s.replace("01", nn) if "01" in s else ROOT / s
        if p.exists():
            srcs[p.name] = mtime(p)
    if not srcs:
        raise SystemExit("找不到任何動畫來源檔")
    newest_src_name = max(srcs, key=lambda k: srcs[k])
    newest_src = srcs[newest_src_name]

    scenes = sorted(render.glob("scenes/s*.mp4"))
    if not scenes:
        raise SystemExit(f"找不到場景 mp4：{render}/scenes/")

    problems = []
    print(f"來源最新：{newest_src_name} @ {hhmmss(newest_src)}\n")
    print(f"{'場景':<10}{'渲染於':>10}   狀態")
    for f in scenes:
        t = mtime(f)
        stale = t < newest_src
        print(f"  {f.name:<8}{hhmmss(t):>10}   {'✗ 比來源舊' if stale else '✓'}")
        if stale:
            problems.append(f"{f.name} 比 {newest_src_name} 舊，要重渲")

    if args.assembled:
        newest_scene = max(mtime(f) or 0 for f in scenes)
        print()
        for name in ("body_nobgm.mp4", "ep01_final.mp4".replace("01", nn)):
            p = render / name
            if not p.exists():
                continue
            t = mtime(p)
            stale = t < newest_scene
            print(f"  {name:<18}{hhmmss(t):>10}   {'✗ 比場景舊' if stale else '✓'}")
            if stale:
                problems.append(f"{name} 比最新的場景舊，要重組")

    print()
    if problems:
        for p in problems:
            print(f"🛑 {p}")
        return 1
    print("✓ 沒有過期產物，可以組裝")
    return 0


if __name__ == "__main__":
    sys.exit(main())
