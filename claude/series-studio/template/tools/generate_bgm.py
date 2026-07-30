#!/usr/bin/env python3
"""用 MiniMax music_generation 生成純樂器 BGM 種子 → remotion/public/audio/bgm_seed.mp3。
model `music-2.6` + is_instrumental:true（純樂器、無人聲，單次最長 ~3 分鐘）。
之後用 ffmpeg -stream_loop 接到 ≥ 影片長度，再做 ducking 混音。
"""
import argparse, json, re, sys, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
KEY = next(l.split("=", 1)[1].strip().strip('"').strip("'")
           for l in (ROOT / ".env").read_text().splitlines()
           if l.strip().startswith("MINIMAX_API_KEY"))

PRESETS = {
    "body": ("warm uplifting modern tech lofi, soft synth pads and mellow electric piano, "
             "gentle subtle beat, clean minimal hopeful and unobtrusive, "
             "background music for an AI and coding explainer video"),
    "intro": ("epic cinematic logo sting, powerful uplifting orchestral synth hybrid, "
              "rising swell with big impact hit and shimmer, modern tech brand intro, "
              "confident and grand, short and energetic"),
}
ap = argparse.ArgumentParser()
ap.add_argument("--preset", choices=list(PRESETS), default="body")
ap.add_argument("--out")
args = ap.parse_args()
PROMPT = series_prompt(args.preset) or PRESETS[args.preset]
OUT = Path(args.out) if args.out else ROOT / "remotion" / "public" / "audio" / f"bgm_{args.preset}_seed.mp3"

payload = {
    "model": "music-2.6",
    "prompt": PROMPT,
    "is_instrumental": True,
    "audio_setting": {"sample_rate": 44100, "bitrate": 256000, "format": "mp3"},
}
req = urllib.request.Request("https://api.minimax.io/v1/music_generation",
                             data=json.dumps(payload).encode(), method="POST",
                             headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=180).read())
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")
if r.get("base_resp", {}).get("status_code") not in (0, None):
    sys.exit(f"MiniMax error: {r['base_resp']}")
OUT.write_bytes(bytes.fromhex(r["data"]["audio"]))
dur = r.get("extra_info", {}).get("music_duration", 0) / 1000
print(f"✅ {OUT}  ({dur:.1f}s)")
