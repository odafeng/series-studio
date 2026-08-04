#!/usr/bin/env python3
"""best-of-N 選 take：把 MiniMax 斷句的「盲抽一張」變成「抽 K 張、自動選最順」。

對指定 cue 合成 K 個新 take，用 forced-align 打「停頓嚴重度」分（詞內重罰、詞邊界
次罰、標點旁不計），**連同現有 take 一起比，挑分數最低那條**覆蓋回去。

⚠️ 現有 take 一定要參賽。CONVENTIONS.md 記著 EP02 的教訓：迴圈寫成「不夠好就丟掉」，
把 cue74 唯一 8.975s 的好 take、cue223 唯一乾淨的 take 全洗掉了，白跑十幾輪。
best-of-N 取樣一律先存最佳候選，最後再決定用不用。

用法（在系列根目錄，必須用 .venv-phrasing 跑，因為要 forced-align）：
  voiceover/.venv-phrasing/bin/python tools/pick_best_take.py --ep 3 --cues 13,132,134 --k 6
  加 --dry 只印現有 take 的分數，不合成、不覆蓋。

檔名 hash 不含取樣種子（含 model＋文字＋語音參數＋詞庫），所以覆蓋後 build_voice 仍認得同一個
檔案、不會重抽；跑完接 `build_voice.py --ep N` 重算時間軸，再跑 forced_align_phrasing 驗。

本系列的 build_voice.py 是腳本式（module-level argparse），import 前先擺好 sys.argv；
它有 `if __name__ == "__main__"` 保護，所以 import 不會觸發合成。
"""
import argparse, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--ep", type=int, required=True)
ap.add_argument("--cues", required=True, help="逗號分隔的 cue 索引（＝ epNNData 的 i）")
ap.add_argument("--k", type=int, default=6, help="每句合成幾個新 take（預設 6）")
ap.add_argument("--dry", action="store_true", help="只印現有 take 的分數")
a = ap.parse_args()

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "voiceover"))
sys.argv = ["build_voice.py", "--ep", str(a.ep)]   # 讓 build_voice 的 argparse 過關
import build_voice as bv                            # noqa: E402  金鑰/語音參數/詞庫/hash 全沿用
from phrasing_score import score_take               # noqa: E402


want = {int(x) for x in a.cues.split(",")}
parsed = bv.parse_script()
picked = []

for i, (sc, sent) in enumerate(parsed):
    if i not in want:
        continue
    at = bv.audio_text(sent)
    mp3 = bv.AUDIO_DIR / f"{bv.cue_hash(at)}.mp3"
    cur = score_take(mp3, at) if mp3.exists() else None
    cur_s = cur["score"] if cur else 999.0
    print(f"\ncue{i:>3} [{sc}] {sent[:34]}…")
    print(f"    現有 take: score={cur_s:.3f}（詞內 {cur['within'] if cur else '?'} / 邊界 {cur['boundary'] if cur else '?'}）")
    if a.dry:
        continue

    best_bytes, best_s, best_meta = None, cur_s, cur
    for k in range(a.k):
        audio = bv.minimax(at)
        tmp = mp3.with_suffix(f".cand{k}.mp3")
        tmp.write_bytes(audio)
        s = score_take(tmp, at)
        tmp.unlink()
        if s is None:
            print(f"    候選 {k+1}: align 失敗，跳過")
            continue
        mark = ""
        if s["score"] < best_s:
            best_bytes, best_s, best_meta = audio, s["score"], s
            mark = "  ← 目前最佳"
        print(f"    候選 {k+1}: score={s['score']:.3f}（詞內 {s['within']} / 邊界 {s['boundary']}）{mark}")

    if best_bytes is None:
        print(f"    ⇒ 保留現有 take（{a.k} 個候選都沒有更好的）")
    else:
        mp3.write_bytes(best_bytes)
        print(f"    ⇒ 換成新 take：{cur_s:.3f} → {best_s:.3f}（詞內 {best_meta['within']}）")
        picked.append((i, cur_s, best_s))

if not a.dry:
    print(f"\n{'='*56}")
    print(f"換掉 {len(picked)} / {len(want)} 句")
    for i, o, n in picked:
        print(f"  cue{i:>3}: {o:.3f} → {n:.3f}")
    print("接著跑：python3 tools/build_voice.py --ep %d（重算時間軸，不會重合成）" % a.ep)
