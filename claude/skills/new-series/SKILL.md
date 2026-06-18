---
name: new-series
description: 建立一個新的影片系列資料夾骨架（Series Studio）。當使用者說「開新系列」「new series」「建一個新的影片系列」「我要做一個關於 X 的系列」時用。複製模板、裝 Remotion 依賴、引導填設定。
---

# 開一個新影片系列

用 `~/.claude/series-studio/template/` 長出系列骨架。

## 步驟
1. 問（或從使用者話裡取）：系列名稱、放哪個資料夾路徑。
2. `cp -R ~/.claude/series-studio/template/ <目標資料夾>`（含 series.yaml、voice-style.md、series-context.md、source/、brand/、voiceover/tw_lexicon.json、tools/、remotion/）。
3. `cd <目標資料夾>/remotion && npm install`（背景跑）。
4. 引導使用者填：
   - `series.yaml`：title、channel、voice.voice_id（克隆聲）、visual.primary、**source**（local：把素材放 source/epN.md；或 github：填 repo/ref/doc_glob）、license/attribution/source_url、intro。
   - `voice-style.md`：丟一份個人語料給我抽口吻（不存私人內容），或自填。
   - `.env`：放 `MINIMAX_API_KEY`（或放 `~/.claude/series-studio/.env` 讓所有系列共用）。
   - `brand/intro.mp4`：放現成片頭，或之後用 Remotion `Intro`（改 BRAND/TAGLINE）渲染。
5. 完成後告訴使用者：填好上面後，`cd` 進系列資料夾、用 `/produce-episode 1` 做第一集。

## 注意
- Remotion 元件、破音字詞庫、BGM 腳本都是模板種子（已驗證），可直接用、會逐集累積。
- YouTube 上傳沿用 colon-and-code 專案的 OAuth（見 CONVENTIONS.md）。
