#!/usr/bin/env python3
"""把 generate_bgm.py 產的種子，做成可直接進組裝的 BGM 成品。

body ：挑一段最平穩的區間 → 頭尾 crossfade 做成「無縫 loop 單元」→ 接到指定秒數
       → 語音頻段微凹 EQ → 定量增益（不用 loudnorm 動態模式，避免 pumping）。
intro：從種子挑一個窗口 → 進場淡入、尾巴淡出乾淨收 → 同樣定量增益。

為什麼要無縫 loop：`-stream_loop` 直接接會在接縫留下一個聽得到的斷點。
本系列的 body 是 ambient pad，接縫比鼓點音樂更明顯（背景一旦「跳」一下，
觀眾的注意力就被拉走了，而這正是本系列最不想要的事）。
"""
import argparse, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "remotion" / "public" / "audio"

# 旁白 I=-21.6 LUFS（EP01 實測）。body 正規化到 -20 LUFS，組裝時再 ×0.15（-16.5 dB）
# ＋ sidechain ducking，旁白一開口 BGM 就掉到 -47 LUFS 附近＝聽得到空氣、聽不到音樂。
TARGET = {"body": -20.0, "intro": -18.0}
# 語音主要能量在 300Hz–3kHz。在 1.4kHz 挖一個 -3dB 的寬凹槽，
# 讓 BGM 不用再壓音量就能讓出旁白的位置。
# 40Hz 以下切掉：種子有 47% 能量在 200Hz 以下，最低那段手機喇叭放不出來，
# 只會吃掉 headroom、讓限幅器提早動作。
VOICE_DIP = "highpass=f=40,equalizer=f=1400:width_type=o:width=2.2:g=-3"


def run(args):
    subprocess.run(args, check=True, capture_output=True)


def dur(p):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)


def lufs(p):
    out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p),
                          "-af", "ebur128=peak=true", "-f", "null", "/dev/null"],
                         capture_output=True, text=True).stderr
    tail = out[out.rfind("Integrated loudness"):]
    return float(tail.split("I:")[1].split("LUFS")[0])


def gain_to(src, out, target, extra=""):
    """量測 → 算固定增益 → 套用（＋限幅到 -1.5 dBTP）。不用 loudnorm 動態模式。"""
    g = target - lufs(src)
    af = f"{extra},volume={g:.2f}dB,alimiter=limit=-1.5dB:level=disabled" if extra \
        else f"volume={g:.2f}dB,alimiter=limit=-1.5dB:level=disabled"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", af,
         "-ar", "48000", "-ac", "2", "-b:a", "256k", str(out)])
    return g


def build_body(seed, out, seconds, t0, length, xf):
    """[t0, t0+length] 這段做成無縫 loop 單元（長度 length-xf），再接到 seconds 秒。"""
    tmp = out.parent / ".bgm_unit.wav"
    t1 = t0 + length
    fc = (f"[0:a]atrim={t0}:{t1},asetpts=N/SR/TB,asplit=3[h][m][t];"
          f"[h]atrim=0:{xf},asetpts=N/SR/TB[head];"
          f"[m]atrim={xf}:{length - xf},asetpts=N/SR/TB[mid];"
          f"[t]atrim={length - xf}:{length},asetpts=N/SR/TB[tail];"
          f"[tail][head]acrossfade=d={xf}:c1=tri:c2=tri[xfade];"
          f"[xfade][mid]concat=n=2:v=0:a=1[u]")
    run(["ffmpeg", "-y", "-v", "error", "-i", str(seed), "-filter_complex", fc,
         "-map", "[u]", "-ar", "48000", "-ac", "2", str(tmp)])
    lvl = out.parent / ".bgm_unit_lvl.wav"
    g = gain_to(tmp, lvl, TARGET["body"], VOICE_DIP)
    # loop 到目標長度，最後才做進出場淡化（每個 loop 迭代內容完全一致）
    run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(lvl), "-t", f"{seconds}",
         "-af", f"afade=t=in:st=0:d=3,afade=t=out:st={seconds - 5:.2f}:d=5",
         "-ar", "48000", "-ac", "2", "-b:a", "256k", str(out)])
    tmp.unlink(); lvl.unlink()
    return dur(tmp := out), g


def build_intro(seed, out, t0, seconds, fin, fout):
    # 用 atrim 而非 -ss：mp3 的 -ss 會對到最近的 frame（±26ms），
    # 但這裡要把音樂的落點對準畫面的 0.87s，差 26ms 就看得出來不同步。
    tmp = out.parent / ".bgm_intro.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", str(seed), "-af",
         f"atrim=start={t0}:end={t0 + seconds},asetpts=N/SR/TB,"
         f"afade=t=in:st=0:d={fin},afade=t=out:st={seconds - fout:.3f}:d={fout}",
         "-ar", "48000", "-ac", "2", str(tmp)])
    g = gain_to(tmp, out, TARGET["intro"])
    tmp.unlink()
    return dur(out), g


ap = argparse.ArgumentParser()
ap.add_argument("--preset", choices=["body", "intro"], required=True)
ap.add_argument("--seed")
ap.add_argument("--out", required=True)
ap.add_argument("--seconds", type=float, required=True)
ap.add_argument("--start", type=float, default=0.0, help="種子裡的取用起點")
ap.add_argument("--length", type=float, default=120.0, help="body：取用區間長度")
ap.add_argument("--xfade", type=float, default=6.0, help="body：loop 接縫交叉淡化秒數")
ap.add_argument("--fade-in", type=float, default=0.05, help="intro：淡入")
ap.add_argument("--fade-out", type=float, default=1.2, help="intro：淡出")
a = ap.parse_args()

seed = Path(a.seed) if a.seed else AUDIO / f"bgm_{a.preset}_seed.mp3"
out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
if not seed.exists():
    sys.exit(f"找不到種子 {seed}（先跑 tools/generate_bgm.py --preset {a.preset}）")

if a.preset == "body":
    d, g = build_body(seed, out, a.seconds, a.start, a.length, a.xfade)
else:
    d, g = build_intro(seed, out, a.start, a.seconds, a.fade_in, a.fade_out)
print(f"✅ {out}  {d:.3f}s  gain {g:+.2f} dB  → {lufs(out):.1f} LUFS")
