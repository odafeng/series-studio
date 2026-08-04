#!/usr/bin/env python3
"""針對 forced_align_phrasing 抓到的缺陷 cue 重抽，抽到「詞內停頓 = 0」為止。

跟 pick_best_take.py 的差別：那支選「總分最低」，可能留下一個仍有詞內停頓的 take
（詞內 weight 1.0 × 小 gap 有機會低於 詞邊界 0.6 × 大 gap）。gate 只看詞內，
所以這支的排序鍵是 (within, score)——先保證 gate 過得了，再談順不順。

現有 take 一律參賽（CONVENTIONS：best-of-N 不可以把唯一的好 take 洗掉）。
抽到 within==0 就提早收工，省 API 費用。

用法（系列根目錄，必須用 .venv-phrasing）：
  voiceover/.venv-phrasing/bin/python tools/retake_until_clean.py --ep 4 --cues 52,57 --k 6
"""
import argparse, json, re, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--ep", type=int, required=True)
ap.add_argument("--cues", required=True)
ap.add_argument("--k", type=int, default=6, help="每句最多抽幾個新 take")
ap.add_argument("--gate-text", action="store_true",
                help="用 epNNData.ts 的 text 評分（＝gate 實際用的字串，含「」、無句尾句號）。"
                     "預設用送 MiniMax 的字串；兩者對含「」的句子會給出不同對齊結果。")
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "voiceover"))
sys.argv = ["build_voice.py", "--ep", str(a.ep)]
import build_voice as bv                     # noqa: E402
from phrasing_score import score_take        # noqa: E402


def key(s):
    return (s["within"], s["score"], s["max_sev"])


GATE_TEXT = {}
if a.gate_text:
    m = re.search(r"=\s*(\{.*\})\s*as const", bv.TS_OUT.read_text(encoding="utf-8"), re.S)
    GATE_TEXT = {c["i"]: c["text"] for c in json.loads(m.group(1))["cues"]}

want = [int(x) for x in a.cues.split(",")]
still_dirty, fixed, takes_used = [], [], {}

for i, (sc, sent) in enumerate(bv.parse_script()):
    if i not in want:
        continue
    at = bv.audio_text(sent)
    scoring_text = GATE_TEXT.get(i, at)
    mp3 = bv.AUDIO_DIR / f"{bv.cue_hash(at)}.mp3"
    cur = score_take(mp3, scoring_text) if mp3.exists() else None
    print(f"\ncue{i:>3} [{sc}] {sent[:34]}…")
    print(f"    現有: within={cur['within'] if cur else '?'} score={cur['score'] if cur else '?'}")
    if a.dry:
        continue
    if cur and cur["within"] == 0:
        print("    已乾淨，不動")
        continue

    best_bytes, best = None, cur
    n = 0
    for k in range(a.k):
        n += 1
        audio = bv.minimax(at)
        tmp = mp3.with_suffix(f".cand{k}.mp3")
        tmp.write_bytes(audio)
        s = score_take(tmp, scoring_text)
        tmp.unlink()
        if s is None:
            print(f"    候選 {k+1}: align 失敗")
            continue
        better = best is None or key(s) < key(best)
        if better:
            best_bytes, best = audio, s
        print(f"    候選 {k+1}: within={s['within']} score={s['score']}{'  ← 最佳' if better else ''}")
        if best and best["within"] == 0:
            break
    takes_used[i] = n
    if best_bytes is not None:
        mp3.write_bytes(best_bytes)
        print(f"    ⇒ 換 take：within={best['within']} score={best['score']}（抽了 {n} 次）")
        fixed.append(i)
    else:
        print(f"    ⇒ 保留原 take（{n} 個候選都沒更好）")
    if best is None or best["within"] > 0:
        still_dirty.append(i)

if not a.dry:
    print(f"\n{'='*56}")
    print(f"換掉 {len(fixed)} 句：{fixed}")
    print(f"仍有詞內停頓：{still_dirty}")
    print(f"抽樣次數：{takes_used}")
    print(f"接著跑：python3 tools/build_voice.py --ep {a.ep}（重算時間軸）")
