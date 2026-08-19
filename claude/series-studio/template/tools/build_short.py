#!/usr/bin/env python3
"""系列廣告 Short 一站式產線（固化流程）。在系列資料夾根目錄執行：

    python3 tools/build_short.py            # 配音 → 渲染 → BGM 混音
    python3 tools/build_short.py --upload   # 上一步全做 + 上傳 unlisted

步驟：
  1. 配音合成  tools/build_short_intro_voice.py（MiniMax 克隆聲，NARRATION 在此檔改）
  2. BGM 生成  MiniMax music-2.6，upbeat（若 remotion/public/audio/shortIntro/bgm.mp3 不存在才生成）
  3. 渲染      Remotion ShortIntro（1080×1920，幀數讀 shortIntroData.ts 的 total）
  4. 混音      BGM 裁到成片長度 + 尾段淡出，volume 0.16 墊在旁白下 → brand/shortIntro_bgm.mp4
  5. 上傳      --upload 時用 brand/shortIntro-metadata.json 傳 unlisted

改動位置：
  - 文案/旁白：tools/build_short_intro_voice.py 的 NARRATION 與 SHORT_TTS
  - 畫面/動效：remotion/src/ShortIntro.tsx
  - 標題/描述/tags：brand/shortIntro-metadata.json
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path.cwd()
FF = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
REMOTION = ROOT / "remotion"
AUDIO_DIR = REMOTION / "public" / "audio" / "shortIntro"
BGM_RAW = AUDIO_DIR / "bgm.mp3"
VIDEO = ROOT / "brand" / "shortIntro.mp4"
FINAL = ROOT / "brand" / "shortIntro_bgm.mp4"
META = ROOT / "brand" / "shortIntro-metadata.json"
UPLOAD = Path.home() / ".claude" / "series-studio" / "youtube" / "upload.py"

BGM_VOL = 0.16
FADE_OUT = 3.5
SHORT_BGM_PROMPT = (
    "upbeat modern pop instrumental, bright acoustic guitar and piano, "
    "light driving drums, catchy energetic positive groove, "
    "for a lively YouTube Short ad, no vocals, 30 seconds"
)


def read_key():
    for p in (ROOT / ".env", Path.home() / ".claude" / "series-studio" / ".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip().startswith("MINIMAX_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("找不到 MINIMAX_API_KEY")


def gen_bgm():
    payload = {"model": "music-2.6", "prompt": SHORT_BGM_PROMPT, "is_instrumental": True,
               "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"}}
    req = urllib.request.Request(
        "https://api.minimax.io/v1/music_generation",
        data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": "Bearer " + read_key(), "Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
    if r.get("base_resp", {}).get("status_code") not in (0, None):
        sys.exit(f"MiniMax error: {r['base_resp']}")
    BGM_RAW.write_bytes(bytes.fromhex(r["data"]["audio"]))
    dur = r.get("extra_info", {}).get("music_duration", 0) / 1000
    print(f"✅ BGM 生成 {BGM_RAW} ({dur:.1f}s)")


def short_total_frames():
    ts = REMOTION / "src" / "shortIntroData.ts"
    m = re.search(r'"total"\s*:\s*(\d+)', ts.read_text(encoding="utf-8"))
    return int(m.group(1))


def dur(p):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", str(p)], capture_output=True, text=True)
    return float(r.stdout.strip())


def run(cmd, **kw):
    print("+", " ".join(str(c) for c in cmd[:6]), "…")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        sys.exit(f"✗ 命令失敗 exit={r.returncode}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upload", action="store_true")
    args = ap.parse_args()

    # 1. 配音
    run([sys.executable, "tools/build_short_intro_voice.py"])

    # 2. BGM（缺才生成；upbeat 只生成一次，不重複花錢）
    if not BGM_RAW.exists():
        gen_bgm()

    # 3. 渲染（幀數讀 manifest total）
    total = short_total_frames()
    run(["npx", "remotion", "render", "src/index.ts", "ShortIntro",
         str(VIDEO), f"--frames=0-{total - 1}"], cwd=REMOTION)

    # 4. 混音：BGM 裁到成片長度 + 尾段淡出 + 0.16 墊底
    vd = dur(VIDEO)
    trim = AUDIO_DIR / "bgm_trim.mp3"
    run([FF, "-y", "-v", "error", "-i", str(BGM_RAW), "-t", f"{vd:.2f}",
         "-af", f"afade=t=out:st={vd - FADE_OUT:.2f}:d={FADE_OUT}", "-ar", "48000", "-ac", "2", str(trim)])
    run([FF, "-y", "-v", "error", "-i", str(VIDEO), "-i", str(trim),
         "-filter_complex", f"[1:a]volume={BGM_VOL}[bg];[0:a][bg]amix=inputs=2:normalize=0:duration=first[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-ar", "48000", "-ac", "2", str(FINAL)])
    print(f"✅ 混音完成 {FINAL} ({dur(FINAL):.1f}s)")

    # 5. 上傳 unlisted
    if args.upload:
        run([sys.executable, str(UPLOAD), "--file", str(FINAL),
             "--metadata", str(META), "--privacy", "unlisted"])


if __name__ == "__main__":
    main()
