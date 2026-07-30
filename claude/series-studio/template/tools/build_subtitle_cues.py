#!/usr/bin/env python3
"""
build_subtitle_cues.py — 字幕 cues（真實語音時間戳 + 字寬感知斷行）

每集配音定稿後跑。把 `ep{NN}Data.ts` 的每句 cue（＝一支 mp3）再切成「單行放得下
的短字幕段」，切點時間一律來自 faster-whisper 的 **word-level 真實語音時間 + 真實
停頓**，不做任何字數比例估算——那正是「聲音比字幕快／字幕飄」的成因。

用法（需要 faster-whisper，走 phrasing QC 的環境）：
    voiceover/.venv-phrasing/bin/python tools/build_subtitle_cues.py --ep N
    ... --out /tmp/probe.json      # 寫到別處，不覆蓋現有 cues（驗證用）

輸出 `voiceover/cues/ep{NN}_cues.json`：
    [{ "i":0, "scene":"00", "startF":.., "durF":.., "text":"..." }, ...]   30fps 絕對影格

動畫師用法：`startF`/`durF` 直接當字幕進出時間。`text` 取自 `ep{NN}Data.ts` 的腳本
原文（**不是** whisper 轉錄），所以技術詞與人名本來就是對的，不需要再校正。

沿革：舊版用 CLI whisper 產「逐段 srt」再轉 cues，只有段落級時間、且長句會折行。
本版改用 word-level 對齊 + 字寬斷行（EP01 實測 150 段，最寬 27.4 全形恆為單行）。
"""
import argparse
import json
import re
from pathlib import Path

# 只存在於 voiceover/.venv-phrasing，用系統 python 跑會 ImportError（見上方用法）
from faster_whisper import WhisperModel  # type: ignore[import-not-found]

FPS = 30
ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "remotion" / "public"
MAXW = 26.0  # 一段字幕的最大「全形寬度」（44px 下約 1200px，1560 上限內單行）

BREAK = "，、；：。！？"


def width(s: str) -> float:
    w = 0.0
    for ch in s:
        w += 0.55 if ord(ch) < 0x2E80 else 1.0
    return w


def split_atoms(text: str):
    """在標點後切原子（標點留在前一段）。"""
    out, cur = [], ""
    for ch in text:
        cur += ch
        if ch in BREAK:
            out.append(cur)
            cur = ""
    if cur.strip():
        out.append(cur)
    return out


def chunk(text: str):
    atoms = split_atoms(text)
    out, cur = [], ""
    for a in atoms:
        if cur and width(cur + a) > MAXW:
            out.append(cur)
            cur = a
        else:
            cur += a
    if cur:
        out.append(cur)
    return [c for c in out if c.strip()]


def norm_chars(s: str):
    """留下會發音的字元（去標點空白），回傳 list。"""
    return [c for c in s if not re.match(r"[\s，、；：。！？「」《》（）,.;:!?\"'()\[\]]", c)]


def split_one_cue(c, model):
    """把一句 cue 切成多段字幕；回傳 [{i,scene,startF,durF,text}, ...]。"""
    text = c["text"]
    parts = chunk(text)
    start_f, dur_f = c["startF"], c["durF"]
    if len(parts) == 1:
        return [{"i": c["i"], "scene": c["scene"], "startF": start_f,
                 "durF": dur_f, "text": parts[0]}]

    wav = AUDIO / c["src"]
    segs, _ = model.transcribe(str(wav), language="zh", word_timestamps=True,
                               vad_filter=False, beam_size=1)
    words = []
    for s in segs:
        for w in (s.words or []):
            words.append((w.word, float(w.start), float(w.end)))

    # 每個 word 的累積「可發音字元數」
    wchars = []
    acc = 0
    for w, ws, we in words:
        n = len(norm_chars(w))
        if n == 0:
            continue
        acc += n
        wchars.append((acc, ws, we))
    total_w = acc

    # 腳本文字的累積字元 → 邊界字元位置
    script_total = len(norm_chars(text))
    bounds = []
    run = 0
    for p in parts[:-1]:
        run += len(norm_chars(p))
        bounds.append(run)

    # word 之間的真實停頓（gap），供 snap 用
    gaps = []
    for k in range(1, len(wchars)):
        gaps.append((wchars[k][1] - wchars[k - 1][2], k))

    times = []
    ok = total_w > 0 and script_total > 0 and len(wchars) >= 2
    for b in bounds:
        if not ok:
            times.append(None)
            continue
        target = b / script_total * total_w
        # 找累積字元剛好越過 target 的 word index
        idx = 0
        for k, (a, ws, we) in enumerate(wchars):
            if a >= target:
                idx = k
                break
        else:
            idx = len(wchars) - 1
        # 在 ±2 個 word 的窗內 snap 到最大真實停頓
        best_k, best_gap = idx, -1.0
        for g, k in gaps:
            if abs(k - idx) <= 2 and g > best_gap:
                best_gap, best_k = g, k
        k = best_k if best_gap > 0.06 else idx
        k = max(1, min(k, len(wchars) - 1))
        # 切點取「前一個字結束」與「這個字開始」的中間
        t = (wchars[k - 1][2] + wchars[k][1]) / 2
        times.append(t)

    # 轉成影格、單調遞增、每段至少 12 幀
    marks = [0]
    prev = 0
    for j, t in enumerate(times):
        if t is None:
            f = round((j + 1) / len(parts) * dur_f)
        else:
            f = int(round(t * FPS))
        f = max(prev + 12, min(f, dur_f - 12 * (len(parts) - 1 - j)))
        marks.append(f)
        prev = f
    marks.append(dur_f)

    return [{"i": c["i"], "scene": c["scene"],
             "startF": start_f + marks[j],
             "durF": marks[j + 1] - marks[j],
             "text": p} for j, p in enumerate(parts)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True, help="集數 N")
    ap.add_argument("--model", default="small",
                    help="faster-whisper 模型（medium 在本機 CPU 會卡死，別用）")
    ap.add_argument("--out", help="輸出路徑；省略則寫 voiceover/cues/ep{NN}_cues.json")
    args = ap.parse_args()
    nn = f"{args.ep:02d}"

    ts_path = ROOT / "remotion" / "src" / f"ep{nn}Data.ts"
    if not ts_path.exists():
        raise SystemExit(f"找不到 manifest：{ts_path}（配音跑完才會有）")
    src = ts_path.read_text()
    cues = json.loads(src[src.index("{"): src.rindex("}") + 1])["cues"]

    model = WhisperModel(args.model, device="cpu", compute_type="int8")

    out = []
    for c in cues:
        segs = split_one_cue(c, model)
        out.extend(segs)
        print(f"[{c['i']:3d}] {len(segs)} seg  {' | '.join(s['text'] for s in segs)}",
              flush=True)

    dst = Path(args.out) if args.out else ROOT / "voiceover" / "cues" / f"ep{nn}_cues.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"wrote {dst} {len(out)} segments")

    # 同步產 Remotion 用的 ts。這一步以前是手工轉的，EP01 因此差點讓整集字幕
    # 跑在舊講稿的時間軸上（json 重產了、ts 沒跟上，而且沒有任何檢查會發現）。
    if not args.out:
        ts = ROOT / "remotion" / "src" / f"ep{nn}Cues.ts"
        rows = "\n".join(
            f'  {{ startF: {c["startF"]}, durF: {c["durF"]}, '
            f'text: {json.dumps(c["text"], ensure_ascii=False)} }},' for c in out)
        ts.write_text(
            f"// AUTO-GENERATED — 由 voiceover/cues/ep{nn}_cues.json 轉出"
            "（whisper word-level 真實語音時間戳）。\n"
            "// ⚠️ 字幕進出時間一律以此為準，嚴禁用字數比例估算。\n"
            "// 不要手改：重跑 tools/build_subtitle_cues.py --ep N 會一併更新這個檔。\n"
            f"export const EP{nn}_SUBCUES = [\n{rows}\n] as const;\n",
            encoding="utf-8")
        print(f"wrote {ts} {len(out)} segments")


if __name__ == "__main__":
    main()
