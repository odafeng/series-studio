# MiniMax 旁白設定

> 下列設定以 Series Studio template 為單一來源，不依賴任何個人專案路徑。
> 本系列沿用同一個既有克隆聲音與逐句合成 pipeline。

## 1. 聲音 / 模型 / 端點

| 項目 | 值 |
|---|---|
| Voice ID（既有克隆聲） | `moss_audio_ae939d41-6788-11f1-a909-feb3e5c18eb0` |
| Model | `speech-02-hd` |
| Endpoint | `POST https://api.minimax.io/v1/t2a_v2` |

## 2. 環境變數（放 gitignored 的 `.env`，本專案需自建）

```
MINIMAX_API_KEY=...     # Bearer token（必要）
MINIMAX_GROUP_ID=...    # t2a_v2 沒用到，但 .env 慣例一起放
```

## 3. 本系列旁白參數（Hello-Agents EP01 暫定，試聽後可調）

```python
voice_setting = {
  "voice_id": "moss_audio_ae939d41-6788-11f1-a909-feb3e5c18eb0",
  "speed": 1.15,      # 科技講解，稍慢於 colon 的 1.2，求清楚
  "vol": 1.0,
  "pitch": 0,
  "emotion": "happy", # 親切清晰；MiniMax 無情緒強度數值，靠 emotion+vol+speed 調
}
audio_setting = {"sample_rate": 44100, "format": "mp3"}
```

> ⚠️ 快取雜湊規則：build script 的檔名 hash 必須涵蓋所有影響聲音的參數
> （CLONE + speed + emotion + **vol + pitch** + text）。改了參數沒進 hash 就不會重合成。

## 4. 逐句合成 pipeline（核心鐵則）

- **逐句合成、不要整段配**——整段再切字幕會嚴重漂移，這是整套設計的理由。
- 合成前**去掉 `「」『』`** 引號（會讓 MiniMax 在引號處斷句、孤立讀錯調）；字幕端保留引號。
- **數字唸法**用「語音/字幕分離」：腳本寫中文數字（唸「零零一」），字幕端 replace 回 `001`。
- 句末標點 `。！？` 為界拆句；同場景句間停 0.14s、換場景停 0.42s；用 `ffprobe` 量實際長度排時間軸 → 字幕釘每句真實起點。
- 輸出：每句 `<sha1前12碼>.mp3` + Remotion manifest + 備用 `.srt`。

## 5. 台灣口音校正詞庫

- 從 template 的 `voiceover/tw_lexicon.json` 開始（破音字、台灣讀音、術語基底），
  再針對本系列**新增 Agent 術語**校正（待補，例如：智能體、循環、範式…先確認台灣讀音再加）。
- 規則：長詞優先；**不要放單字條目**（會把字當獨立 token 斷開）；錯拼音比不加更糟。
- 套用方式：掃描該句，命中的詞塞進 `payload["pronunciation_dict"]["tone"]`。

## 6. 雷點清單

1. 逐句合成（見上）。
2. hash 要涵蓋 vol/pitch（本系列有調，務必加）。
3. 合成前去引號。
4. 數字走語音/字幕分離。
5. 全形標點 `，：；？！`；YouTube 描述拒絕半形 `<>`，用全形 `＜＞`。
6. 字典別放單字；新破音字先查證台灣讀音。
7. 無內建 rate-limit 重試，大量句子建議自己加退避；`timeout=120`。
8. `ffprobe` 路徑 `/opt/homebrew/bin/ffprobe`（Apple Silicon）。

## 待辦（產 audio 前）
- [ ] 本專案建 `.env`（`MINIMAX_API_KEY`）
- [ ] 腳本定稿後，clone `build_cohort_ep1.py` → `build_helloagents_ep01.py`，改路徑常數
- [ ] 補 Agent 術語到 tw_lexicon（確認台灣讀音）
- [ ] 試聽第 01 段 → 調 speed/emotion
