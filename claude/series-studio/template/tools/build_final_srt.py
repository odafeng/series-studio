#!/usr/bin/env python3
"""
build_final_srt.py — 產「成片時間軸」的 YouTube 字幕軌

`voiceover/cues/ep{NN}_cues.json` 走的是**純旁白**的連續時間軸，但成片是三段式：

    前言（乾聲）→ 品牌片頭 → 本體

片頭夾在中間，所以本體所有 cue 都要往後推一個片頭的長度。直接拿 cues 的時間
上傳，整條字幕會早片頭那幾秒。前言（scene 00）在片頭之前，不能位移。

用法：
    python3 tools/build_final_srt.py --ep 1
    ... --intro-frames 0     # 這集不插片頭
    ... --dry-run            # 只印摘要不寫檔

輸出：`episodes/ep{NN}/render/ep{NN}.srt`

片頭長度預設**量測 series.yaml 的 intro 檔案的視訊幀數**，不看容器長度——
容器可能因為尾巴掛靜音音軌而比畫面長（EP01 是 4.544s vs 4.500s）。

cues 的 text 取自腳本原文而非 whisper 轉錄（見 build_subtitle_cues.py），
所以技術詞與人名本來就是對的，這裡不需要再校正。
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

FPS = 30
ROOT = Path(__file__).resolve().parent.parent
PRE_SCENE = "00"  # 片頭之前的場景（前言），不位移


def intro_frames_from_series():
    """量 series.yaml 指定的片頭影片有幾個視訊幀；沒設定或檔案不在就回 0。"""
    y = ROOT / "series.yaml"
    if not y.exists():
        return 0
    m = re.search(r'^\s*intro:\s*["\']?([^"\'\n#]*)', y.read_text(encoding="utf-8"), re.M)
    if not m or not m.group(1).strip():
        return 0
    p = ROOT / m.group(1).strip()
    if not p.exists():
        return 0
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-count_frames",
         "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(p)],
        capture_output=True, text=True)
    return int(r.stdout.strip().rstrip(",") or 0)


def ts(frame):
    ms = round(frame * 1000 / FPS)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True)
    ap.add_argument("--intro-frames", type=int,
                    help="片頭幀數；省略則量 series.yaml 的 intro 影片")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    nn = f"{args.ep:02d}"

    cues_path = ROOT / "voiceover" / "cues" / f"ep{nn}_cues.json"
    if not cues_path.exists():
        raise SystemExit(f"找不到 cues：{cues_path}（先跑 build_subtitle_cues.py）")
    cues = json.loads(cues_path.read_text(encoding="utf-8"))

    shift = args.intro_frames if args.intro_frames is not None else intro_frames_from_series()

    lines, n_shifted = [], 0
    for i, c in enumerate(cues, 1):
        off = 0 if c["scene"] == PRE_SCENE else shift
        if off:
            n_shifted += 1
        start, end = c["startF"] + off, c["startF"] + c["durF"] + off
        lines.append(f"{i}\n{ts(start)} --> {ts(end)}\n{c['text']}\n")

    total = max(c["startF"] + c["durF"] + (0 if c["scene"] == PRE_SCENE else shift)
                for c in cues)
    print(f"cue 段數 {len(cues)}｜片頭位移 {shift} 幀（{shift / FPS:.2f}s）"
          f"｜位移了 {n_shifted} 段、前言 {len(cues) - n_shifted} 段不動")
    print(f"字幕總長 {ts(total)}")

    if args.dry_run:
        print("(dry-run，未寫檔)")
        return 0

    out = ROOT / "episodes" / f"ep{nn}" / "render" / f"ep{nn}.srt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
