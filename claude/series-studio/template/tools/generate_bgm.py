#!/usr/bin/env python3
"""用 MiniMax music_generation 生成純樂器 BGM 種子 → remotion/public/audio/bgm_seed.mp3。
model `music-2.6` + is_instrumental:true（純樂器、無人聲，單次最長 ~3 分鐘）。
之後用 ffmpeg -stream_loop 接到 ≥ 影片長度，再做 ducking 混音。
"""
import argparse, json, re, sys, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
def read_key():
    for p in (ROOT / ".env", Path.home() / ".claude/series-studio/.env"):
        if p.exists():
            for l in p.read_text().splitlines():
                if l.strip().startswith("MINIMAX_API_KEY"):
                    return l.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("找不到 MINIMAX_API_KEY（放 ./.env 或 ~/.claude/series-studio/.env）")


KEY = read_key()

def series_prompt(preset):
    """series.yaml 的 `bgm.{preset}_prompt` 可覆寫下面的內建 preset。

    ⚠️ **片頭樂一定要逐系列自訂。** 模板的 intro prompt 若原封不動照用，
    各系列的片頭會撞聲——ai-shuoshuren 和 colon-and-code 就是這樣一路
    共用同一段 "epic cinematic logo sting..."，聽起來像同一個節目。
    寫在 series.yaml 而不是改這支程式，是為了讓「這系列的片頭長什麼樣」
    跟其他系列設定放在一起、一眼看得到，不用翻程式碼。
    """
    p = ROOT / "series.yaml"
    if p.exists():
        m = re.search(rf'^\s*{preset}_prompt:\s*["\'](.+?)["\']\s*$',
                      p.read_text(encoding="utf-8"), re.M)
        if m:
            return m.group(1)
    return None




# 通用 fallback；本系列的實際 prompt 寫在 series.yaml 的 bgm.intro_prompt / bgm.body_prompt。
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
    r = json.loads(urllib.request.urlopen(req, timeout=600).read())
except urllib.error.HTTPError as e:
    sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")
if r.get("base_resp", {}).get("status_code") not in (0, None):
    sys.exit(f"MiniMax error: {r['base_resp']}")
OUT.write_bytes(bytes.fromhex(r["data"]["audio"]))
dur = r.get("extra_info", {}).get("music_duration", 0) / 1000
print(f"✅ {OUT}  ({dur:.1f}s)")
