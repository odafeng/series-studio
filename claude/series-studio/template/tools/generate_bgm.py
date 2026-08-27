#!/usr/bin/env python3
"""生成純樂器 BGM 種子 → remotion/public/audio/bgm_{preset}_seed.mp3。

後端是**本機的 MiniMax Music 3 開源權重**（`tools/music3.py`），不是 MiniMax 雲端 API。
`POST /v1/music_generation` 在 2026-08 對新用戶關閉（HTTP 410 / 2153），
官方在錯誤訊息裡指向開源權重，所以改走那條。安裝步驟見 music3.py 的 docstring。

CLI 與舊版相容（`--preset` / `--out` 照舊），另外多了：
    --seed      同一個 seed ＋ 同一段 caption ＝ 同一段音樂。**BGM 從此可重生。**
    --duration  秒數（預設 body 130、intro 30）
    --steps     flow-matching 步數，上限 30

之後仍然用 `tools/build_bgm.py` 做無縫 loop / 接長 / EQ / 定量增益，
留用前仍然要過 `tools/bgm_qc.py`（含 `--vocal`）——換了後端不代表換掉 QC，
Music 3 一樣可能自己加鼓、自己開始哼。
"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from music3 import generate, structured_caption  # noqa: E402


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
DEFAULT_DUR = {"body": 130, "intro": 30}
DEFAULT_BPM = {"body": 76, "intro": 120}

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", choices=list(PRESETS), default="body")
    ap.add_argument("--out")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--duration", type=int)
    ap.add_argument("--steps", type=int, default=30)
    args = ap.parse_args(argv)

    prompt = series_prompt(args.preset) or PRESETS[args.preset]
    out_path = (Path(args.out) if args.out else
                ROOT / "remotion" / "public" / "audio" / f"bgm_{args.preset}_seed.mp3")
    dur = args.duration or DEFAULT_DUR[args.preset]

    caption = structured_caption(prompt, bpm=DEFAULT_BPM[args.preset], instrumental=True)
    out, meta = generate(caption, out_path, duration=dur, steps=args.steps, seed=args.seed)
    print(f"✅ {out}  (seed={meta['seed']}, steps={meta['steps']}, ~{dur}s)")
    print(f"   重生參數已寫入 {out.name}.json")
    print(f"   留用前先跑：python3 tools/bgm_qc.py --vocal {out}")
    return out


# ⚠️ 沒有這道 guard 的話，任何 `import generate_bgm` 都會直接跑一次生成
#    （吃 15 分鐘 GPU、覆蓋既有素材，還會把呼叫端的 sys.argv 當成自己的參數解析）。
#    2026-08-27 實際踩到：只想測 series_prompt() 能不能讀到 series.yaml，
#    結果 import 就生出一支 43 秒的 bgm_body_seed.mp3。
if __name__ == "__main__":
    main()
