#!/usr/bin/env python3
"""BGM 量測：素材鼓點／密度／長度／人聲關卡 ＋ 成品循環可偵測度 ＋ 接縫評分。

`music-2.6` 有超過一半的機率無視 prompt 裡的 `no drums no percussion`
（EP02 實測 7 支退 4 支）。沒有自動 QC 的話，鼓點會直接混進成片，
而且沒有任何人會發現——所以每支新素材都要先過這裡再留用。

CLI：
    python3 tools/bgm_qc.py episodes/ep03/render/seed_*.mp3          # 基本關卡
    python3 tools/bgm_qc.py --vocal episodes/ep08/render/seed_*.mp3  # 加跑 whisper 人聲關卡
    python3 tools/bgm_qc.py --loop episodes/ep03/render/bgm_body.mp3 # 循環可偵測度

三個指標的校準值（都用本檔量的，可並排比較）：
  鼓點 drum_r：乾淨床樂 0.26–0.47（EP02 出貨的三支種子）；
               合成打點對照 0.82–0.91（100/128 BPM）。→ 判退線 0.60
  床樂密度   ：乾淨床樂 2–15%（13 支真素材實測）。→ 判退線 22%
  循環 r     ：交錯拼接 0.08（EP03 本體，lag≥60 s）、0.14（EP02 本體）；
               單一樂段 stream_loop 0.99 且有五階諧波階梯。→ 目標 <0.25
  長度       ：< 78 s 直接退（見 MIN_DUR）。

⚠️ EP05 修掉了兩個「gate 會說謊」的缺陷，改動請先讀 bed_density() 與 MIN_DUR 的註解：
  ① 舊版 bed_density 拿檔案自己的中位數當參考點，靜音過半時中位數塌進靜音地板、
     讀數變 0.0%——**素材越爛分數越漂亮**，最該退的反而滿分通過。
  ② 舊版完全不檢查長度，15.85 s 的素材兩關 PASS 且 exit 0，但拼接工具根本切不動。
"""
import argparse
import re
import subprocess
import sys
import numpy as np


# ── 解碼與基本量測 ────────────────────────────────────────────────
def decode(path, sr=22050, ch=1):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le",
         "-ar", str(sr), "-ac", str(ch), "-"],
        capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    return a if ch == 1 else a.reshape(-1, 2)


def duration(path):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout)


def lufs(path):
    """(integrated LUFS, true peak dBTP)"""
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
         "-af", "ebur128=peak=true", "-f", "null", "/dev/null"],
        capture_output=True, text=True).stderr
    tail = err[err.rfind("Integrated loudness"):]
    return (float(tail.split("I:")[1].split("LUFS")[0]),
            float(tail[tail.rfind("Peak:"):].split("Peak:")[1].split("dBFS")[0]))


# ── 關卡④：可辨識人聲 ────────────────────────────────────────────
def filter_confident_vocal_segments(segments, max_no_speech=0.65, min_logprob=-1.0):
    """留下可辨識語音；也抓 no_speech 偏高、但內容長且轉錄信心高的歌聲。"""
    out = []
    for segment in segments:
        text = segment.text.strip()
        units = re.findall(r"[A-Za-z']+|[\u3400-\u9fff]", text)
        strict_speech = segment.no_speech_prob < max_no_speech and segment.avg_logprob > min_logprob
        sung_phrase = (
            len(units) >= 4
            and segment.no_speech_prob < 0.90
            and segment.avg_logprob > -0.70
        )
        if text and (strict_speech or sung_phrase):
            out.append({
                "start": float(segment.start),
                "end": float(segment.end),
                "text": text,
                "no_speech_prob": float(segment.no_speech_prob),
                "avg_logprob": float(segment.avg_logprob),
            })
    return out


def detect_vocals(path, model):
    """用已載入的 faster-whisper model 掃描人聲，避免每個檔案重載模型。"""
    segments, _ = model.transcribe(str(path), vad_filter=False, beam_size=5)
    return filter_confident_vocal_segments(segments)


def _stft_mag(x, n_fft, hop, block=4096):
    """分塊算，避免 35 分鐘的檔一次配置數百 MB。"""
    win = np.hanning(n_fft).astype(np.float32)
    n = 1 + (len(x) - n_fft) // hop
    out = np.empty((n, n_fft // 2 + 1), dtype=np.float32)
    base = np.arange(n_fft)
    for s in range(0, n, block):
        e = min(n, s + block)
        idx = base[None, :] + hop * np.arange(s, e)[:, None]
        out[s:e] = np.abs(np.fft.rfft(x[idx] * win, axis=1)).astype(np.float32)
    return out


# ── 關卡①：鼓點 ──────────────────────────────────────────────────
def onset_env(path, sr=22050, n_fft=1024, hop=256, fmin=2000.0, detrend=0.4):
    """高頻帶（>2 kHz）起音包絡：spectral flux → 減 0.4 s 移動平均 → 半波整流。

    減移動平均這步不能省：不減的話 pad 的緩慢起伏會讓自相關整段偏高，
    量到的是「音樂在呼吸」而不是「有沒有鼓」（乾淨的 seed_b 會從 0.264 虛報成 0.395）。
    """
    x = decode(path, sr, 1)
    mag = _stft_mag(x, n_fft, hop)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    flux = np.maximum(0.0, np.diff(mag[:, freqs > fmin], axis=0)).sum(axis=1)
    w = max(3, int(detrend * sr / hop) | 1)
    local = np.convolve(np.pad(flux, w // 2, mode="edge"),
                        np.ones(w) / w, mode="valid")[:len(flux)]
    return np.maximum(0.0, flux - local), sr / hop


def drum_r(path, lag_lo=0.30, lag_hi=1.0, **kw):
    """起音包絡的週期性自相關，取 0.30–1.0 s（60–200 BPM）的最大值。回傳 (r, bpm)。

    lag 窗開到 1.5 s 會讓 pad 的緩慢起伏冒充節拍，是用合成參考校準出來的。

    ⚠️ **判退線 0.60 對應的「打點多大聲」與合成配方綁定，換配方就要重新校準，
    不同報告的校準表不可以並排比較。** 同樣叫「k ＝ 打點峰值 ÷ 床樂 RMS」：
      EP04（8 ms 白噪，無尾巴）      k=1.0→0.452  1.25→0.566  1.5→0.645  ⇒ 0.60 線在 k≈1.3
      EP05（8 ms 白噪 + 60 ms 衰減尾）k=1.0→0.561  1.25→0.665  1.5→0.732  ⇒ 0.60 線在 k≈1.09
    差 0.1 不是素材變乾淨或這關變嚴格，只是尾巴長度不同。要宣稱「這關抓得到多小的鼓」，
    一律**重跑自己的階梯**再講，不要引用別集的數字。

    共通結論（兩次校準都成立）：k≈0.5 以下抓不到（埋在床樂 RMS 底下），
    但那個強度在 body_volume 0.15 ＋ ducking 之後也聽不見，可以接受——
    **但不能宣稱「這關能抓到所有鼓」。**
    """
    env, fps = onset_env(path, **kw)
    if env.std() < 1e-12:
        return 0.0, 0.0
    f = (env - env.mean()) / env.std()
    n = 1 << (2 * len(f) - 1).bit_length()
    ac = np.fft.irfft(np.abs(np.fft.rfft(f, n)) ** 2)[:len(f)]
    ac /= ac[0]
    lo, hi = int(lag_lo * fps), int(lag_hi * fps)
    k = lo + int(np.argmax(ac[lo:hi]))
    return float(ac[k]), float(60.0 * fps / k)


# ── 關卡②：床樂密度 ──────────────────────────────────────────────
def _frame_db(path, sr=22050, frame=0.050, hop=0.025):
    x = decode(path, sr, 1)
    nf, nh = int(frame * sr), int(hop * sr)
    n = 1 + (len(x) - nf) // nh
    idx = np.arange(nf)[None, :] + nh * np.arange(n)[:, None]
    return 20 * np.log10(np.sqrt((x[idx].astype(np.float64) ** 2).mean(axis=1) + 1e-20))


def bed_density(path, drop_db=20.0, ref_pct=95, **kw):
    """短時 RMS 低於「音樂在響」基準 20 dB 的時間占比。基準＝該檔 95 百分位幀電平。

    >22% 代表它給的是「靜音中的零星音符」而不是床樂。

    ⚠️ **參考點必須是絕對的（95 百分位），不能用中位數——這是 EP05 修掉的真缺陷。**
    舊版寫 `db < median(db) - 10`，拿檔案自己的中位數當參考點。一旦靜音占超過一半，
    中位數本身就掉到靜音地板上（實測 duty 0.40 的中位數 = -200 dB），
    「低於中位數 10 dB」就抓不到任何東西，讀數變 0.0%：

        duty（有聲比例）  1.00   0.90   0.70   0.60   0.50   0.40   0.30
        舊版（中位數）    6.0%  14.7%  32.3%  41.2%  48.4%   0.0%   0.0%  ← 非單調
        本版（95 百分位） 9.1%  17.5%  34.2%  43.3%  52.2%  61.1%  70.4%  ← 全程單調

    **素材越爛分數越漂亮、而且失效方向是「放行」**——一支「95% 是靜音、偶爾一顆音」
    的素材在舊版會拿到 0.0%，比乾淨床樂的 6.0% 還好看，然後順利進池。

    ⚠️ 判退線 22% 是**配這個量法重新校準**的，不是沿用舊版的 20%（尺換了刻度就要跟著換）。
    校準依據（13 支真素材 ＋ 合成對照，全部用本函式量）：
      必須 PASS 的真素材最高 ＝ seed_h 15.1%（其餘 11 支落在 2.4–10.1%）
      必須 REJECT 最低       ＝ seed_r 28.6%（合成 duty 對照 34–70%）
      → 取兩者中點 21.9 ⇒ **22%**，上下各留 ~6.8 個百分點餘裕。
    這條線在 13 支真素材上與舊版**判定完全一致**（改的只有盲區行為，不動既有結論）。
    """
    db = _frame_db(path, **kw)
    return float((db < np.percentile(db, ref_pct) - drop_db).mean())


def bed_density_median(path, **kw):
    """舊版讀數（自參考中位數）。只作為附加欄位並排顯示，**不參與 exit code**。

    留著是為了讓歷史報告的數字對得上，不是還在用它判定。
    """
    db = _frame_db(path, **kw)
    return float((db < np.median(db) - 10.0).mean())


# ── 頻帶特徵（循環與接縫都用它）────────────────────────────────────
def band_feature(path, **kw):
    return band_feature_arr(decode(path, kw.get("sr", 22050), 1), **kw)


def band_feature_arr(x, sr=22050, n_fft=4096, hop=2205, n_bands=24, sec=1.0):
    """每秒一幀、24 個對數頻帶（40 Hz–10 kHz）的 dB 特徵矩陣 (T, 24)。

    ⚠️ hop 必須整除 sr，否則「一幀＝一秒」只是近似。原本用 hop=1024 @22050，
    一幀其實是 1.0217 s，索引到第 2100 幀時已經偏 46 秒——接縫分析會抓到
    完全不同的位置（實測把片尾的淡出誤判成「最差接縫」，還差點就這樣出貨）。
    """
    assert sr % hop == 0, f"hop {hop} 沒整除 sr {sr}，幀不會對齊秒"
    mag = _stft_mag(x, n_fft, hop)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    edges = np.geomspace(40.0, 10000.0, n_bands + 1)
    cols = [mag[:, (freqs >= edges[i]) & (freqs < edges[i + 1])].mean(axis=1)
            for i in range(n_bands)]
    b = np.stack(cols, axis=1)
    per_sec = int(sec * sr // hop)
    t = (len(b) // per_sec) * per_sec
    return 20 * np.log10(b[:t].reshape(-1, per_sec, n_bands).mean(axis=1) + 1e-10)


# ── 循環可偵測度 ──────────────────────────────────────────────────
def loop_curve(feat):
    """r(L)：每秒特徵逐頻帶 z-score 後，不同 lag 的正規化互相關（頻帶平均）。"""
    z = (feat - feat.mean(axis=0)) / (feat.std(axis=0) + 1e-9)
    T = len(z)
    curve = np.zeros(T // 2 + 1)
    for L in range(1, T // 2 + 1):
        a, b = z[:T - L], z[L:]
        curve[L] = ((a * b).sum(axis=0) /
                    (np.sqrt((a * a).sum(axis=0) * (b * b).sum(axis=0)) + 1e-9)).mean()
    return curve


def loop_r(curve, floor=30):
    """max_{L≥floor} r(L)。回傳 (r, lag)。

    floor 的意義：floor 太低量到的是「環境音樂本來就自我相似」（EP03 在 lag 16 s
    有 0.29，但那是同一個片段內部的連續性，不是循環）；floor 拉到比最長片段還長
    才是真正的「同一段又回來了」。報告兩個都寫。
    """
    L = int(np.argmax(curve[floor:])) + floor
    return float(curve[L]), L


def harmonic_ladder(curve, L0, k_max=6):
    """諧波階梯：r(k·L0) 是否也是局部峰。stream_loop 會階階都強，交錯拼接不會。"""
    out = []
    for k in range(1, k_max + 1):
        L = L0 * k
        if L >= len(curve):
            break
        w = curve[max(0, L - 3):min(len(curve), L + 4)]
        out.append({"k": k, "lag": L, "r": float(curve[L]),
                    "peak": bool(curve[L] >= w.max() - 1e-9)})
    return out


# ── 接縫評分 ─────────────────────────────────────────────────────
def seam_scores(centers, feat, win=12, skip=3):
    """每個交叉淡接的『頻譜差 + 電平落差』（dB）。

    比較中心前後各 12 s（跳過中心 ±3 s 的混合區）：
    頻譜差＝扣掉整體電平後 24 個頻帶的平均 dB 差；電平落差＝兩邊平均電平差。
    排程搜尋（模擬特徵）與成品實測用同一支函式，選出來的才等於量出來的。
    """
    out = []
    for i, c in enumerate(centers):
        a = feat[int(c - skip - win):int(c - skip)].mean(axis=0)
        b = feat[int(c + skip):int(c + skip + win)].mean(axis=0)
        la, lb = a.mean(), b.mean()
        spec = float(np.abs((a - la) - (b - lb)).mean())
        lvl = float(abs(la - lb))
        out.append({"i": i, "t": float(c), "spec": spec, "lvl": lvl,
                    "score": spec + lvl})
    return out


DRUM_MAX, BED_MAX = 0.60, 0.22

# 長度關卡：從 build_bgm_montage.py 的排程器推導，不是拍腦袋的數字。
# 那支的 Source.cap = int(min(SEG_MAX, dur - 30))（"留 ≥30 s 的取用起點自由度"），
# 而 make_schedule 會跑 rng.integers(SEG_MIN, cap + 1) —— cap < SEG_MIN 時直接爆。
#   cap >= SEG_MIN(48)  ⇒ int(dur - 30) >= 48 ⇒ **dur >= 78.0**  ← 低於此完全排不進去
#   cap >= SEG_MAX(82)  ⇒ dur - 30 >= 82      ⇒ **dur >= 112.0** ← 低於此切不出最長片段
# ⚠️ 常見的誤推是 SEG_MAX + 2×GUARD = 84 s（只看 GUARD、漏掉 dur-30 那個 cap）。
# 那個數字是錯的：實際硬底線是 78 s，而「能用滿 48–82 s 全距」要到 112 s。
MIN_DUR = 78.0        # 低於此 → REJECT（排程器根本用不了）
FULL_SEG_DUR = 112.0  # 低於此 → 可用但受限，只警告不退
                      # （EP02–04 的 seed_b 90 s 就卡在這區間：cap 只有 60 s、
                      #   起點區間 28 s，EP04 因此逼出兩對近乎重複的取用）


def gate(path, vocals=None):
    dur = duration(path)
    r, bpm = drum_r(path)
    d = bed_density(path)
    return {"dur": dur, "lufs": lufs(path)[0], "drum_r": r, "bpm": bpm,
            "bed_low": d, "bed_low_median": bed_density_median(path),
            "short": dur < FULL_SEG_DUR,
            "vocals": [] if vocals is None else vocals,
            "pass": r < DRUM_MAX and d <= BED_MAX and dur >= MIN_DUR and not vocals}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--loop", action="store_true", help="加量循環可偵測度（成品用）")
    ap.add_argument("--vocal", action="store_true", help="用 faster-whisper 加跑可辨識人聲關卡")
    ap.add_argument("--vocal-model", default="small", help="faster-whisper model（預設 small）")
    a = ap.parse_args()
    whisper_model = None
    if a.vocal:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            ap.error("--vocal 需要 faster-whisper；請用 voiceover/.venv-phrasing/bin/python 執行")
        whisper_model = WhisperModel(a.vocal_model, device="cpu", compute_type="int8")
    bad = 0
    for p in a.files:
        vocals = detect_vocals(p, whisper_model) if whisper_model is not None else None
        g = gate(p, vocals)
        ok = "PASS" if g["pass"] else "REJECT"
        bad += not g["pass"]
        why = []
        if g["drum_r"] >= DRUM_MAX:
            why.append("有鼓")
        if g["bed_low"] > BED_MAX:
            why.append("零星音符")
        if g["dur"] < MIN_DUR:
            why.append(f"太短（排程器需 ≥{MIN_DUR:.0f}s）")
        if g["vocals"]:
            why.append("有可辨識人聲")
        print(f"{p}\n  {g['dur']:8.2f}s  I={g['lufs']:6.1f} LUFS  "
              f"鼓點 r={g['drum_r']:.3f}@{g['bpm']:.0f}BPM (退線 {DRUM_MAX})  "
              f"床樂密度 {g['bed_low'] * 100:.1f}% (退線 {BED_MAX * 100:.0f}%"
              f"；舊版自參考 {g['bed_low_median'] * 100:.1f}%)  → {ok}"
              + (f"  ⛔ {'／'.join(why)}" if why else ""))
        if g["pass"] and g["short"]:
            print(f"  ⚠️ {g['dur']:.1f}s < {FULL_SEG_DUR:.0f}s：可用但切不出 82 s 最長片段"
                  f"（cap={int(min(82, g['dur'] - 30))}s、起點區間僅 "
                  f"{g['dur'] - int(min(82, g['dur'] - 30)) - 2:.0f}s），易逼出重複取用")
        for vocal in g["vocals"]:
            print(f"  🎙️ {vocal['start']:.1f}–{vocal['end']:.1f}s  {vocal['text']} "
                  f"(no_speech={vocal['no_speech_prob']:.2f}, logprob={vocal['avg_logprob']:.2f})")
        if a.loop:
            c = loop_curve(band_feature(p))
            r15, l15 = loop_r(c, 15)
            r30, l30 = loop_r(c, 30)
            r60, l60 = loop_r(c, 60)
            print(f"  循環 r(≥15s)={r15:.3f}@{l15}s  r(≥30s)={r30:.3f}@{l30}s  "
                  f"r(≥60s)={r60:.3f}@{l60}s")
            print("  諧波階梯 " + ", ".join(
                f"{x['k']}×{x['lag']}s r={x['r']:.3f}{'峰' if x['peak'] else ''}"
                for x in harmonic_ladder(c, l60)))
    sys.exit(1 if bad else 0)
