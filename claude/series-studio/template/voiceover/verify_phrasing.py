#!/usr/bin/env python3
"""
verify_phrasing.py — 配音斷句「自動偵測 + 自動修正」一支搞定

偵測（為什麼抓得到「第三｜種」）：
  1. ffmpeg silencedetect 找出音檔裡「真實的靜音停頓」——物理事實，不靠模型腦補。
  2. whisper 對齊每個字大概在第幾秒——只用來定位停頓落在哪兩個字之間。
  3. jieba ＋「序數+量詞」pattern 判斷那兩字該不該連；停頓落在「同一個詞內部」→ 斷錯。

修正（--fix）：
  詞被切開＝詞中間多了一段不該有的靜音。直接把那段純靜音剪短即可，
  接縫兩端是字的尾音與起音，剪完就是正常連續的詞。不重唸、不碰 MiniMax。
  輸出 *_fixed 檔，原檔完全不動。

  ⚠ 一定要用「純旁白音檔」，混 BGM 的成片會把停頓蓋掉，驗不出來。

裝一次： pip install faster-whisper jieba       （另需系統有 ffmpeg）
用法：
  python voiceover/verify_phrasing.py <純旁白音檔>                    # 只偵測
  python voiceover/verify_phrasing.py <純旁白音檔> --fix --srt x.srt  # 偵測+自動修正
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PUNCT = set("，。、！？；：「」『』（）()…—~,.!?;:\"' \n\t　")


def to_wav(src: Path) -> Path:
    if src.suffix.lower() == ".wav":
        return src
    out = Path(tempfile.mkdtemp()) / "a.wav"
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), "-ac", "1", "-ar", "16000", "-vn", str(out)],
        capture_output=True, check=True)
    return out


def transcribe(wav: Path):
    """whisper 對齊，回傳字級序列 [{char, start, end}]（時間僅供定位）。"""
    from faster_whisper import WhisperModel
    # 本機 CPU 跑 medium 會卡(同 phrasing_gate 教訓)；single-cue 對齊用 small 足夠且快很多。
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = model.transcribe(str(wav), language="zh",
                               word_timestamps=True, vad_filter=False)
    chars = []
    for s in segs:
        for w in (s.words or []):
            cs = [c for c in (w.word or "") if c not in PUNCT]
            if not cs:
                continue
            span = (w.end - w.start) / len(cs)
            for i, c in enumerate(cs):
                chars.append({"char": c,
                              "start": w.start + i * span,
                              "end": w.start + (i + 1) * span})
    return chars


def detect_silences(wav: Path, noise: str, d: float):
    """ffmpeg 偵測真實靜音段，回傳 [(start, end)]（秒）。"""
    r = subprocess.run(
        ["ffmpeg", "-i", str(wav), "-af",
         f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"],
        capture_output=True, text=True)
    ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return list(zip(ss, se))


def word_internal(text: str):
    """回傳 set，i 表示 text[i] 與 text[i+1] 之間不該有停頓。
    來源：(1) jieba 同一個詞內部（抓「關｜係」）；
          (2) 序數+量詞 pattern（jieba 常把量詞切開，補回「第三｜種」）。"""
    import jieba
    internal, pos = set(), 0
    for word in jieba.cut(text, HMM=True):
        for k in range(len(word) - 1):
            internal.add(pos + k)
        pos += len(word)
    for m in re.finditer(r"第[一二三四五六七八九十兩0-9]+[種個點步類層項者次回度]", text):
        for k in range(m.start(), m.end() - 1):
            internal.add(k)
    return internal


def analyze(chars, silences):
    text = "".join(c["char"] for c in chars)
    internal = word_internal(text)
    out = []
    for ss, se in silences:
        mid = (ss + se) / 2
        j = next((k for k in range(len(chars)) if chars[k]["start"] > mid), None)
        if not j:
            continue
        i = j - 1
        if mid < chars[i]["end"] - 0.02:
            continue
        if i in internal:
            out.append({
                "time": round(ss, 2),
                "gap": round(se - ss, 3),
                "split": f"{text[i]}｜{text[i+1]}",
                "ctx": f"…{text[max(0, i-5):i+1]}▌{text[i+1:i+6]}…",
            })
    return out, len(chars)


def shift_srt(src: Path, out: Path, dels):
    """剪掉某些音檔區間後，把字幕時間往前平移對齊，另存到 out。"""
    def t2s(t):
        h, m, r = t.split(":"); s, ms = r.split(",")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

    def s2t(x):
        ms = round(x * 1000); h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(ms):03d}"

    def adj(x):
        return x - sum(min(b, x) - a for a, b in dels if a < x)

    txt = src.read_text("utf-8")
    new = re.sub(r"\d{2}:\d{2}:\d{2},\d{3}",
                 lambda m: s2t(adj(t2s(m.group(0)))), txt)
    out.write_text(new, "utf-8")


def apply_fix(src: Path, bad, keep: float, srt):
    """把每段詞內靜音剪短到 keep 秒；輸出 *_fixed 檔，原檔不動。"""
    dels = [(b["time"] + keep, b["time"] + b["gap"]) for b in bad
            if b["gap"] - keep > 0.02]
    if not dels:
        print("（沒有足夠長的靜音可剪，未產生修正檔）")
        return
    expr = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in dels)
    out = src.with_name(f"{src.stem}_fixed{src.suffix}")
    subprocess.run(["ffmpeg", "-y", "-i", str(src), "-af",
                    f"aselect='not({expr})',asetpts=N/SR/TB", str(out)],
                   capture_output=True, check=True)
    cut = sum(b - a for a, b in dels)
    print(f"✓ 修正 {len(dels)} 處、剪掉 {cut:.2f}s → {out.name}（原檔未動）")
    if srt and srt.exists():
        sout = srt.with_name(f"{srt.stem}_fixed{srt.suffix}")
        shift_srt(srt, sout, dels)
        print(f"✓ 字幕已平移對齊 → {sout.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", type=Path, help="純旁白音檔（不要用混 BGM 的成片）")
    ap.add_argument("--noise", default="-32dB", help="靜音音量門檻，預設 -32dB")
    ap.add_argument("--min-sil", type=float, default=0.10,
                    help="最短算停頓的秒數，預設 0.10")
    ap.add_argument("--fix", action="store_true",
                    help="偵測完自動剪掉詞內靜音，輸出 *_fixed（原檔不動）")
    ap.add_argument("--srt", type=Path, help="搭配 --fix，同時輸出平移好的字幕")
    ap.add_argument("--keep", type=float, default=0.06,
                    help="詞內停頓修剪後保留秒數，預設 0.06")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    if not a.audio.exists():
        sys.exit(f"✗ 找不到 {a.audio}")

    wav = to_wav(a.audio)
    chars = transcribe(wav)
    if not chars:
        sys.exit("✗ whisper 沒抓到字，確認音檔有人聲")
    sil = detect_silences(wav, a.noise, a.min_sil)
    bad, total = analyze(chars, sil)

    print(f"\n斷句驗收 | {a.audio.name} | 字數 {total} | "
          f"靜音 {len(sil)} 段 | 斷錯 {len(bad)} 處")
    for b in bad:
        m, s = divmod(b["time"], 60)
        print(f"  [{int(m):02d}:{s:05.2f}] 停{b['gap']}s 切開「{b['split']}」 {b['ctx']}")
    if not bad:
        print("  ✓ 沒有把詞切開的停頓")
    if a.json:
        a.json.write_text(json.dumps(bad, ensure_ascii=False, indent=2), "utf-8")

    if a.fix and bad:
        apply_fix(a.audio, bad, a.keep, a.srt)

    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
