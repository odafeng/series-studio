#!/usr/bin/env python3
"""單一 take 的斷句「停頓嚴重度」打分（給 best-of-N 選 take 用；也給 gate 出軟報告）。

沿用 forced_align_phrasing.py 的原理：ctc-forced-aligner 拿每個字精準起訖時間、
silencedetect 抓真實停頓、jieba(繁轉簡) 判兩字是否同詞。差別是這裡**不只判詞內**：

  停頓中點落在 字[i]～字[i+1] 的間隙、且兩字都非標點 ⇒ 是一個「跑文中的停頓」。
  - 兩字同詞（jieba）        ⇒ 詞內斷句（最嚴重）weight=1.0
  - 兩字不同詞              ⇒ 詞邊界停頓（次嚴重）weight=0.6
  （本系列旁白語速快、自然停頓都落在 、，—：？。等標點上；標點旁的停頓一律不算，
    所以「跑文中、非標點」的停頓＝不自然換氣，正是使用者耳朵會抓的那種。）

score = Σ weight×gap（越低越好）；另回傳 max_sev（最糟單一停頓）給排序次鍵。
用法（CLI 測試/比較多個 take）：
  voiceover/.venv-phrasing/bin/python voiceover/phrasing_score.py --text "整句文字" a.mp3 b.mp3 …
可 import：from phrasing_score import score_take
"""
import re, subprocess
from pathlib import Path

FFMPEG = "/opt/homebrew/bin/ffmpeg"
PUNCT = "，。、；：？！…—,.!?：「」『』（）《》〈〉 "

import jieba
import ctc_forced_aligner as cfa
from opencc import OpenCC

_cc = OpenCC("t2s")
_al = cfa.AlignmentSingleton()
_model, _tok = _al.alignment_model, _al.alignment_tokenizer


def _to_simp(text):
    s = _cc.convert(text)
    return s if len(s) == len(text) else "".join(_cc.convert(ch) for ch in text)


def _char_times(mp3, text):
    audio = cfa.load_audio(str(mp3))
    emissions, stride = cfa.generate_emissions(_model, audio, batch_size=4)
    ts, txs = cfa.preprocess_text(text, romanize=True, language="zho", split_size="char")
    seg, sc, blank = cfa.get_alignments(emissions, ts, _tok)
    spans = cfa.get_spans(ts, seg, blank)
    return cfa.postprocess_results(txs, spans, stride, sc)


def _silences(mp3, noise, d):
    p = subprocess.run([FFMPEG, "-i", str(mp3), "-af", f"silencedetect=noise={noise}:d={d}", "-f", "null", "-"],
                       capture_output=True, text=True)
    ss = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", p.stderr)]
    se = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", p.stderr)]
    return [(ss[i], se[i] if i < len(se) else ss[i] + 0.3) for i in range(len(ss))]


def _token_id_map(text):
    simp = _to_simp(text)
    ids, tid, i = {}, 0, 0
    for w in jieba.cut(simp, HMM=True):
        for _ in w:
            ids[i] = (tid, w)
            i += 1
        tid += 1
    return ids


def score_take(mp3, text, noise="-32dB", d=0.14, min_gap=0.18):
    """回傳 {score, max_sev, within, boundary, hits, ok}。align 失敗回 None。"""
    try:
        ct = _char_times(mp3, text)
    except Exception:
        return None
    if len(ct) != len(text):
        return None
    ids = _token_id_map(text)
    hits, within, boundary, total, mx = [], 0, 0, 0.0, 0.0
    for ps, pe in _silences(mp3, noise, d):
        gap = pe - ps
        if gap < min_gap:
            continue
        pm = (ps + pe) / 2
        for i in range(len(text) - 1):
            if ct[i]["end"] - 0.12 <= pm <= ct[i + 1]["start"] + 0.12:
                l, r = text[i], text[i + 1]
                if l in PUNCT or r in PUNCT:
                    break  # 停頓落在標點旁 ⇒ 自然，不計
                ti, wl = ids.get(i, (None, ""))
                tj, _ = ids.get(i + 1, (None, ""))
                is_within = (ti is not None and ti == tj and len(wl) >= 2
                             and not re.search(r"[A-Za-z0-9]", wl))
                w = 1.0 if is_within else 0.6
                sev = w * gap
                total += sev
                mx = max(mx, sev)
                if is_within:
                    within += 1
                else:
                    boundary += 1
                hits.append({"at": round(ps, 2), "gap": round(gap, 2),
                             "kind": "within" if is_within else "boundary",
                             "word": wl if is_within else f"{l}｜{r}",
                             "split": f"{text[max(0,i-3):i+1]}｜{text[i+1:i+4]}"})
                break
    return {"score": round(total, 3), "max_sev": round(mx, 3),
            "within": within, "boundary": boundary, "hits": hits}


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--noise", default="-32dB")
    ap.add_argument("--d", type=float, default=0.14)
    ap.add_argument("--min-gap", type=float, default=0.18)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    rows = []
    for f in a.files:
        s = score_take(Path(f), a.text, a.noise, a.d, a.min_gap)
        rows.append((f, s))
    rows.sort(key=lambda r: (r[1]["score"], r[1]["max_sev"]) if r[1] else (9e9, 9e9))
    print(f'{"file":<40} {"score":>6} {"max":>5}  within/boundary  hits')
    for f, s in rows:
        if s is None:
            print(f"{Path(f).name:<40} ALIGN-FAIL")
            continue
        hh = "; ".join(f'{h["kind"][:1]}:{h["word"]}({h["gap"]})' for h in s["hits"]) or "-"
        print(f'{Path(f).name:<40} {s["score"]:>6} {s["max_sev"]:>5}  {s["within"]}/{s["boundary"]}  {hh}')
    print(f"\n★ 建議選：{Path(rows[0][0]).name}（score 最低）")
