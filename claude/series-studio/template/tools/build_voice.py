#!/usr/bin/env python3
"""通用配音合成（設定驅動）。在系列資料夾根目錄執行。

讀 ./series.yaml 的 voice 參數，把 episodes/epNN/script/epNN-script.md 的【旁白】
逐句用 MiniMax 克隆聲合成。冪等（內容雜湊命名，含詞庫 → 改發音會自動重合成）。

用法：
  python3 tools/build_voice.py --ep 3            # 合成第 3 集（缺的）
  python3 tools/build_voice.py --ep 3 --dry      # 只列句子驗斷句
  python3 tools/build_voice.py --ep 3 --limit 6  # 只合成前 6 句（試聽）
  python3 tools/build_voice.py --ep 3 --model speech-2.8-hd  # 一次性 A/B

輸出：remotion/public/audio/epNN/<hash>.mp3 + remotion/src/epNNData.ts(EP NN) + episodes/epNN/epNN.srt
金鑰 MINIMAX_API_KEY：找 ./.env，再找 ~/.claude/series-studio/.env。
"""
import argparse, json, re, sys, hashlib, subprocess, urllib.request
from pathlib import Path
import yaml

ap = argparse.ArgumentParser()
ap.add_argument("--ep", type=int, required=True)
ap.add_argument("--model", help="覆寫 series.yaml 或既有 manifest 的 MiniMax speech model")
ap.add_argument("--dry", action="store_true")
ap.add_argument("--limit", type=int)
args = ap.parse_args()
NN = f"{args.ep:02d}"

ROOT = Path.cwd()
CFG = yaml.safe_load((ROOT / "series.yaml").read_text(encoding="utf-8"))
V = CFG.get("voice", {})
CLONE = V["voice_id"]; SPEED = V.get("speed", 1.15); EMOTION = V.get("emotion", "happy")
VOL = V.get("vol", 1.0); PITCH = V.get("pitch", 0)
TTS_REPLACEMENTS = {str(k): str(v) for k, v in V.get("tts_replacements", {}).items() if str(k)}
FFPROBE = "/opt/homebrew/bin/ffprobe"
FPS = 30; GAP_S = 0.14; SCENE_GAP_S = 0.42

SCRIPT = ROOT / "episodes" / f"ep{NN}" / "script" / f"ep{NN}-script.md"
AUDIO_DIR = ROOT / "remotion" / "public" / "audio" / f"ep{NN}"
TS_OUT = ROOT / "remotion" / "src" / f"ep{NN}Data.ts"
SRT_OUT = ROOT / "episodes" / f"ep{NN}" / f"ep{NN}.srt"


def existing_manifest_model():
    """重抽舊集 cue 時沿用原 model；無 model 欄的 manifest 視為 legacy speech-02-hd。"""
    if not TS_OUT.exists():
        return None
    text = TS_OUT.read_text(encoding="utf-8")
    match = re.search(r'"model"\s*:\s*"([^"]+)"', text)
    return match.group(1) if match else "speech-02-hd"


MODEL = args.model or existing_manifest_model() or V.get("model", "speech-2.8-hd")


def read_key():
    for p in (ROOT / ".env", Path.home() / ".claude/series-studio/.env"):
        if p.exists():
            for l in p.read_text().splitlines():
                if l.strip().startswith("MINIMAX_API_KEY"):
                    return l.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("找不到 MINIMAX_API_KEY（放 ./.env 或 ~/.claude/series-studio/.env）")


KEY = None
LEX_PATH = ROOT / "voiceover" / "tw_lexicon.json"
LEX = {k: v for k, v in (json.loads(LEX_PATH.read_text(encoding="utf-8")) if LEX_PATH.exists() else {}).items() if not k.startswith("_")}


def lex_entries(t):
    return [f"{w}/{LEX[w]}" for w in sorted(LEX, key=len, reverse=True) if w in t]


def parse_script():
    scene = "S0"; mode = None; cues = []
    for raw in SCRIPT.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s.startswith("## "):
            m = re.match(r"##\s+(\S+)", s)
            if m:
                scene = m.group(1)
            mode = None; continue
        if s.startswith("**【旁白】"):
            mode = "narr"; continue
        if s.startswith("**【"):
            mode = None; continue
        if s == "---":
            mode = None; continue
        if mode != "narr" or not s:
            mode = mode if s else None
            continue
        body = s.replace("**", "").strip()
        for sent in re.split(r"(?<=[。！？])", body):
            sent = sent.strip()
            if sent:
                cues.append((scene, sent))
    return cues


def caption_text(s):
    for a, b in [(",", "，"), (":", "："), (";", "；"), ("?", "？"), ("!", "！")]:
        s = s.replace(a, b)
    return s.rstrip("。").strip()


def audio_text(sent):
    text = sent.replace("「", "").replace("」", "").replace("『", "").replace("』", "")
    for source in sorted(TTS_REPLACEMENTS, key=len, reverse=True):
        text = text.replace(source, TTS_REPLACEMENTS[source])
    return text


def cue_hash(text, model=None):
    selected_model = model or MODEL
    material = {
        "model": selected_model,
        "voice": CLONE,
        "speed": SPEED,
        "emotion": EMOTION,
        "vol": VOL,
        "pitch": PITCH,
        "audio": {"sample_rate": 44100, "format": "mp3"},
        "audio_text": text,
        "lex": lex_entries(text),
    }
    return hashlib.sha1(json.dumps(material, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def minimax(text):
    global KEY
    if KEY is None:
        KEY = read_key()
    payload = {"model": MODEL, "text": text, "stream": False,
               "voice_setting": {"voice_id": CLONE, "speed": SPEED, "vol": VOL, "pitch": PITCH, "emotion": EMOTION},
               "audio_setting": {"sample_rate": 44100, "format": "mp3"}}
    tones = lex_entries(text)
    if tones:
        payload["pronunciation_dict"] = {"tone": tones}
    req = urllib.request.Request("https://api.minimax.io/v1/t2a_v2", data=json.dumps(payload).encode(),
                                 method="POST", headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=120).read())
    if r.get("base_resp", {}).get("status_code") not in (0, None):
        sys.exit(f"MiniMax error: {r['base_resp']}")
    return bytes.fromhex(r["data"]["audio"])


def probe(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())


def srt_ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def main():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    parsed = parse_script()
    if args.limit:
        parsed = parsed[:args.limit]
    print(f"模型 {MODEL}｜解析到 {len(parsed)} 句")
    if args.dry:
        for sc, s in parsed:
            print(f"  [{sc}] {s}")
        return
    cues, t, prev, srt = [], 0.0, None, []
    for i, (sc, sent) in enumerate(parsed):
        at = audio_text(sent)
        h = cue_hash(at)
        mp3 = AUDIO_DIR / f"{h}.mp3"
        if not mp3.exists():
            mp3.write_bytes(minimax(at)); print(f"  ♪ {i:02d} [{sc}] {sent[:24]}…")
        dur = probe(mp3)
        if prev is not None and sc != prev:
            t += SCENE_GAP_S
        prev = sc
        cap = caption_text(sent)
        cues.append({"i": i, "scene": sc, "text": cap, "src": f"audio/ep{NN}/{h}.mp3", "startF": round(t * FPS), "durF": round(dur * FPS)})
        srt.append(f"{len(srt)+1}\n{srt_ts(t)} --> {srt_ts(t+dur)}\n{cap}\n")
        t += dur + GAP_S
    data = {"fps": FPS, "model": MODEL, "voice": CLONE, "total": round(t * FPS), "cues": cues}
    TS_OUT.write_text(f"// AUTO-GENERATED by tools/build_voice.py --ep {args.ep} --model {MODEL}\nexport const EP{NN} = " + json.dumps(data, ensure_ascii=False, indent=2) + " as const;\n")
    SRT_OUT.write_text("\n".join(srt))
    print(f"\n✅ {len(cues)} 句  {t:.1f}s  → {TS_OUT.relative_to(ROOT)} (EP{NN})")


if __name__ == "__main__":
    main()
