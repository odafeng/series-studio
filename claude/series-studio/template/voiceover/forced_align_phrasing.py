#!/usr/bin/env python3
"""字級 forced-align 斷句偵測（ctc-forced-aligner + silencedetect + jieba）。根目錄執行。

比 phrasing_gate.py（whisper word_timestamps，±1~2 字飄移）與比例映射可靠：用 MMS CTC
forced-align 把「已知文字」對齊到音檔、拿**每個字的精準起訖時間**，再看 silencedetect 的
真實停頓落在「哪兩個字中間」，jieba 判這兩字是否同一個詞 ⇒ 詞內停頓＝真斷句缺陷。

判據（零模糊）：一個顯著靜音的中點落在 字[i] 結束 與 字[i+1] 開始 的間隙，且
  - 字[i]、字[i+1] 都不是標點，且
  - jieba 認為 i、i+1 在同一個（>=2 字、非英數）詞裡
⇒ 該詞被唸斷。終端標點前的收尾停頓、詞組邊界（不同詞之間）不算。

用法：
  voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py --ep 11
  voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py --ep 11 --cue-start 0 --cue-end 39
  --json episodes/ep11/_auto_logs/fa11.json 存報告。exit 2=對齊失敗、1=有缺陷、0=乾淨。
修法：刪缺陷 cue 的 mp3 → build_voice.py --ep N 重合成 → 重跑本工具確認。
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
target = ap.add_mutually_exclusive_group(required=True)
target.add_argument("--ep", type=int)
target.add_argument("--short")
ap.add_argument("--noise", default="-32dB")
ap.add_argument("--d", type=float, default=0.14)
ap.add_argument("--min-gap", type=float, default=0.18, help="只看靜音 >= 此秒數")
ap.add_argument("--boundary-gap", type=float, default=0.40,
                help="軟報告：跑文中(非標點)的詞邊界停頓 >= 此秒數也列出（不影響 exit code）。"
                     "EP14 校準：會｜像 0.36 可接受、0.43+ 礙耳，故預設 0.40")
ap.add_argument("--cue-start", type=int, default=0, help="只檢查此 cue 以後（含）")
ap.add_argument("--cue-end", type=int, help="只檢查此 cue 以前（含）")
ap.add_argument("--json", type=Path)
a = ap.parse_args()

if a.short and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", a.short):
    ap.error("--short 只能包含小寫英數字與連字號")
if a.cue_start < 0:
    ap.error("--cue-start 不能小於 0")
if a.cue_end is not None and a.cue_end < a.cue_start:
    ap.error("--cue-end 不能小於 --cue-start")

ROOT = Path.cwd()
FFMPEG = "/opt/homebrew/bin/ffmpeg"
PUBLIC = ROOT / "remotion" / "public"
if a.ep is not None:
    nn = f"{a.ep:02d}"
    DATA = ROOT / "remotion" / "src" / f"ep{nn}Data.ts"
    TARGET_LABEL = f"EP{nn}"
else:
    short_parts = re.split(r"[^a-zA-Z0-9]+", a.short)
    short_stem = "short" + "".join(part[:1].upper() + part[1:] for part in short_parts)
    DATA = ROOT / "remotion" / "src" / f"{short_stem}Data.ts"
    TARGET_LABEL = f"SHORT {a.short}"
PUNCT = "，。、；：？！…—,.!?：「」『』（）《》〈〉 "

sys.path.insert(0, str(ROOT / "voiceover"))
import jieba  # noqa: E402
import ctc_forced_aligner as cfa  # noqa: E402
from opencc import OpenCC  # noqa: E402

# jieba 預設是簡體字典；本系列文字是繁體，直接斷詞會切錯（強化→體強/化學習）。
# 先把文字繁→簡（字級 1:1）再斷詞，索引與原文對齊。
_cc = OpenCC("t2s")


def to_simp(text):
    s = _cc.convert(text)
    if len(s) == len(text):
        return s
    return "".join(_cc.convert(ch) for ch in text)  # 保 1:1 對齊

m = re.search(r"=\s*(\{.*\})\s*as const", DATA.read_text(encoding="utf-8"), re.S)
data = json.loads(m.group(1))

_al = cfa.AlignmentSingleton()
_model, _tok = _al.alignment_model, _al.alignment_tokenizer


def char_times(mp3, text):
    audio = cfa.load_audio(str(mp3))
    emissions, stride = cfa.generate_emissions(_model, audio, batch_size=4)
    ts, txs = cfa.preprocess_text(text, romanize=True, language="zho", split_size="char")
    seg, sc, blank = cfa.get_alignments(emissions, ts, _tok)
    spans = cfa.get_spans(ts, seg, blank)
    return cfa.postprocess_results(txs, spans, stride, sc)  # [{text,start,end}], 與 text 1:1


def silences(mp3):
    p = subprocess.run([FFMPEG, "-i", str(mp3), "-af", f"silencedetect=noise={a.noise}:d={a.d}", "-f", "null", "-"],
                       capture_output=True, text=True)
    ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    return [(ss[i], se[i] if i < len(se) else ss[i] + 0.3) for i in range(len(ss))]


def token_id_map(text):
    # 在「簡體」上斷詞（字典才對得上），索引沿用原文（t2s 字級 1:1）
    simp = to_simp(text)
    ids, tid, i = {}, 0, 0
    for w in jieba.cut(simp, HMM=True):
        for _ in w:
            ids[i] = (tid, w)
            i += 1
        tid += 1
    return ids


report = []
align_errors = []
soft_report = []  # 詞邊界跑文停頓（gate 不 fail，只提醒；EP14 起補上「會｜像」這種盲區）
for c in data["cues"]:
    if c["i"] < a.cue_start or (a.cue_end is not None and c["i"] > a.cue_end):
        continue
    text = c["text"]
    mp3 = PUBLIC / c["src"]
    if not mp3.exists():
        continue
    try:
        ct = char_times(mp3, text)
    except Exception as e:
        print(f"cue{c['i']} align 失敗: {e}", file=sys.stderr)
        align_errors.append({"cue": c["i"], "scene": c["scene"], "error": str(e), "text": text})
        continue
    if len(ct) != len(text):
        # 對齊字數與文字不符（罕見），跳過避免錯位
        align_errors.append({"cue": c["i"], "scene": c["scene"],
                             "error": f"對齊字數 {len(ct)} != 文字字數 {len(text)}", "text": text})
        continue
    ids = token_id_map(text)
    hits = []
    soft = []
    for ps, pe in silences(mp3):
        # TTS 正常會留約 0.2s 起音空白；它不是兩個字之間的停頓。
        if ps <= 0.01:
            continue
        if pe - ps < a.min_gap:
            continue
        pm = (ps + pe) / 2
        for i in range(len(text) - 1):
            if ct[i]["end"] - 0.12 <= pm <= ct[i + 1]["start"] + 0.12:
                l, r = text[i], text[i + 1]
                if l in PUNCT or r in PUNCT:
                    break
                ti, wl = ids.get(i, (None, ""))
                tj, _ = ids.get(i + 1, (None, ""))
                split = f"{text[max(0,i-3):i+1]}｜{text[i+1:i+4]}"
                if ti is not None and ti == tj and len(wl) >= 2 and not re.search(r"[A-Za-z0-9]", wl):
                    hits.append({"at": round(ps, 2), "gap": round(pe - ps, 2), "word": wl, "split": split})
                elif pe - ps >= a.boundary_gap:            # 跨詞、跑文中的顯著停頓＝可疑換氣（軟報告）
                    soft.append({"at": round(ps, 2), "gap": round(pe - ps, 2), "pair": f"{l}｜{r}", "split": split})
                break
    if hits:
        report.append({"cue": c["i"], "scene": c["scene"], "src": Path(c["src"]).name, "hits": hits, "text": text})
    if soft:
        soft_report.append({"cue": c["i"], "scene": c["scene"], "hits": soft, "text": text})

print(f"=== {TARGET_LABEL} forced-align 斷句偵測：{len(report)} 句有詞內停頓（真缺陷）===")
for r in report:
    print(f"\ncue{r['cue']:>3} [{r['scene']}] {r['text']}")
    for h in r["hits"]:
        print(f"    @{h['at']}s 停{h['gap']}s 斷在詞「{h['word']}」  …{h['split']}…")
if not report:
    print("（無詞內停頓；所有顯著停頓都落在詞組邊界或標點上）")

if align_errors:
    print(f"\n--- ✗ {len(align_errors)} 句對齊失敗（QC 不完整）---")
    for err in align_errors:
        print(f"    cue{err['cue']:>3} [{err['scene']}] {err['error']}  {err['text']}")

if soft_report:
    n = sum(len(r["hits"]) for r in soft_report)
    print(f"\n--- ⚠ 詞邊界停頓軟報告：{len(soft_report)} 句 / {n} 處（>= {a.boundary_gap}s，跑文中非標點；不 fail，請耳朵複核）---")
    for r in soft_report:
        pairs = "、".join(f'{h["pair"]}({h["gap"]})' for h in r["hits"])
        print(f"    cue{r['cue']:>3} [{r['scene']}] {pairs}  …{r['hits'][0]['split']}…")
    print("    （這類 gate 判「乾淨」但耳朵可能覺得換氣怪；要修用 pick_best_take 抽 best-of-N 選最低分）")

if a.json:
    a.json.parent.mkdir(parents=True, exist_ok=True)
    a.json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

sys.exit(2 if align_errors else (1 if report else 0))
