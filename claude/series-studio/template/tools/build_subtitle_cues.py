#!/usr/bin/env python3
"""
build_subtitle_cues.py — 字幕「自動校正斷句」（真實語音時間戳）

每集配音定稿後跑。用 whisper 把每段旁白 wav 轉成 srt（**真實時間軸＋依語音停頓
的自然斷句**），再轉成 Remotion 用的字幕 cues（時間＝真實語音，而非用字數比例
估算）。這就是修「聲音比字幕快／字幕飄」的標準做法——字幕時間必須來自這支工具，
不可再用字數比例分配。

用法：python3 tools/build_subtitle_cues.py --ep N [--model base|medium|large-v3]
輸出：
  episodes/epNN/voiceover/srt/<wav>.srt          （whisper 時間戳，逐段）
  episodes/epNN/voiceover/cues/epNN_cues.json    （每場景 cues：fromF/toF/text @30fps）

動畫師用法：字幕 cues 的 fromF/toF（影格）= 真實語音時間，直接拿去當字幕進出時間；
text 是 whisper 轉錄（base 會有同音/技術詞錯）——**技術詞、人名、專有名詞請對照
 episodes/epNN/script/epNN-script.md 的【旁白】校正後**再上字幕。

備註：若某段有剪輯版（如 epNN-scene00_short.wav），本工具會優先用 _short 版的 srt。
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

FPS = 30


def srt_time_to_sec(t):
    h, m, rest = t.split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(text):
    cues = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.strip().split("\n")
        if len(lines) >= 2:
            m = re.search(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', lines[1])
            if m:
                cues.append({
                    "from_s": srt_time_to_sec(m.group(1)),
                    "to_s": srt_time_to_sec(m.group(2)),
                    "text": " ".join(lines[2:]).strip(),
                })
    return cues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", type=int, required=True)
    ap.add_argument("--model", default="base", help="base 快堪用／medium·large-v3 較準較慢")
    ap.add_argument("--whisper", default="/opt/anaconda3/bin/whisper")
    args = ap.parse_args()
    epnn = f"{args.ep:02d}"
    vo = Path(f"episodes/ep{epnn}/voiceover")
    if not vo.exists():
        raise SystemExit(f"找不到 {vo}")
    srtdir = vo / "srt"
    cuedir = vo / "cues"
    srtdir.mkdir(exist_ok=True)
    cuedir.mkdir(exist_ok=True)

    # 每個場景選用的 wav：有 _short 剪輯版就優先用
    scene_wav = {}
    for w in sorted(vo.glob(f"ep{epnn}-scene*.wav")):
        m = re.search(r'scene(\d+)', w.name)
        if not m:
            continue
        scene = m.group(1)
        if "_short" in w.name:
            scene_wav[scene] = w            # _short 覆蓋主檔
        else:
            scene_wav.setdefault(scene, w)

    all_cues = {}
    for scene in sorted(scene_wav):
        wav = scene_wav[scene]
        srtf = srtdir / f"{wav.stem}.srt"
        if not srtf.exists():
            print(f"  whisper 轉錄 {wav.name} …")
            subprocess.run(
                [args.whisper, str(wav), "--language", "zh", "--model", args.model,
                 "--fp16", "False", "--output_format", "srt", "--output_dir", str(srtdir)],
                check=True, capture_output=True,
            )
        cues = parse_srt(srtf.read_text(encoding="utf-8"))
        all_cues[scene] = [
            {"fromF": round(c["from_s"] * FPS), "toF": round(c["to_s"] * FPS), "text": c["text"]}
            for c in cues
        ]

    out = cuedir / f"ep{epnn}_cues.json"
    out.write_text(json.dumps(all_cues, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(v) for v in all_cues.values())
    print(f"✓ {out}（{len(all_cues)} 場景、{total} 句，時間軸＝真實語音）")
    print("  ⚠️ cues 的 text 是 whisper 轉錄；技術詞/人名請對照 script.md【旁白】校正後再上字幕")


if __name__ == "__main__":
    main()
