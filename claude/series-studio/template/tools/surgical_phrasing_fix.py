#!/usr/bin/env python3
"""外科手術修詞內停頓：剪掉詞中間那段靜音，只留 60ms 自然銜接。

什麼時候用（CONVENTIONS.md 定案）：**重抽 >= 10 次仍不乾淨** ⇒ 那是系統性斷裂，
MiniMax 在該處固定換氣，再抽只是燒 API 費用。EP02 的「視野」抽 27 次只有 1 次乾淨，
最後就是靠這招修掉的（剪 1.579–1.921s，腳本不動、時間軸不動）。

順序一律是：① 重抽 fresh take ② pick_best_take 抽 K 張選最順 ③ 都不行才動刀。

⚠️ 剪完長度會變短。若該集**動畫已經寫好**（scenesNN.tsx 的 at={} 是寫死常數），
必須用 --pad 把長度補回原本的精確秒數，否則後面所有動畫會相對旁白飄掉。
動畫還沒開始的話不用補，讓 build_voice 重算時間軸即可（比較乾淨）。

用法（系列根目錄，用 .venv-phrasing 跑，因為要 forced-align 定位）：
  voiceover/.venv-phrasing/bin/python tools/surgical_phrasing_fix.py --ep 3 --cues 146,149
  --pad      剪完補靜音回原長度（動畫已定稿時必加）
  --dry      只印會剪哪一段，不動檔案
"""
import argparse, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--ep", type=int, required=True)
ap.add_argument("--cues", required=True)
ap.add_argument("--keep", type=float, default=0.06, help="詞中間保留多少秒銜接（預設 0.06）")
ap.add_argument("--pad", action="store_true", help="剪完 apad 補回原長度（動畫已定稿時用）")
ap.add_argument("--dry", action="store_true")
a = ap.parse_args()

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "voiceover"))
sys.argv = ["build_voice.py", "--ep", str(a.ep)]
import build_voice as bv                      # noqa: E402
from phrasing_score import score_take         # noqa: E402

FFMPEG = "/opt/homebrew/bin/ffmpeg"


want = {int(x) for x in a.cues.split(",")}
for i, (sc, sent) in enumerate(bv.parse_script()):
    if i not in want:
        continue
    at_text = bv.audio_text(sent)
    scoring_text = bv.caption_text(sent)
    mp3 = bv.AUDIO_DIR / f"{bv.cue_hash(at_text)}.mp3"
    s = score_take(mp3, scoring_text)
    print(f"\ncue{i:>3} [{sc}] {sent[:34]}…")
    if not s:
        print("    align 失敗，跳過"); continue
    within = [h for h in s["hits"] if h["kind"] == "within"]
    if not within:
        print(f"    沒有詞內停頓（score={s['score']:.3f}），不用動刀"); continue

    dur0 = bv.probe(mp3)
    # 由後往前剪，前面的時間戳才不會被位移
    segs = []
    for h in sorted(within, key=lambda x: -x["at"]):
        cut_a = h["at"] + a.keep / 2
        cut_b = h["at"] + h["gap"] - a.keep / 2
        if cut_b <= cut_a:
            print(f"    停頓 {h['gap']}s 比保留量還短，跳過"); continue
        segs.append((cut_a, cut_b, h))
        print(f"    剪「{h['word']}」中間 {cut_a:.3f}–{cut_b:.3f}s（{h['gap']}s → {a.keep}s）")

    if a.dry or not segs:
        continue

    src = mp3
    for n, (ca, cb, _) in enumerate(segs):
        out = mp3.with_suffix(f".cut{n}.mp3")
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(src), "-filter_complex",
                        f"[0]atrim=0:{ca},asetpts=N/SR/TB[x];[0]atrim={cb},asetpts=N/SR/TB[y];"
                        f"[x][y]concat=n=2:v=0:a=1[o]", "-map", "[o]",
                        "-c:a", "libmp3lame", "-q:a", "2", str(out)], check=True)
        if src != mp3:
            src.unlink()
        src = out

    if a.pad:
        padded = mp3.with_suffix(".padded.mp3")
        subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(src), "-af",
                        f"apad=whole_dur={dur0}", "-c:a", "libmp3lame", "-q:a", "2", str(padded)],
                       check=True)
        src.unlink(); src = padded

    src.replace(mp3)
    s2 = score_take(mp3, scoring_text)
    print(f"    ⇒ {dur0:.3f}s → {bv.probe(mp3):.3f}s｜score {s['score']:.3f} → "
          f"{s2['score']:.3f}（詞內 {s2['within']}）" if s2 else "    ⇒ 剪完但重新評分失敗")

if not a.dry:
    print(f"\n接著跑：python3 tools/build_voice.py --ep {a.ep}，再跑 forced_align_phrasing 驗收")
