---
name: produce-episode
description: 製作目前系列資料夾的某一集（通用 orchestrator / 製作總監）。當使用者在一個系列資料夾裡說「做第 N 集」「produce-episode N」「出下一集」時用。依序調度 vid-* subagent，含三道審核關，最後組裝＋上架，並回寫 series-context。
---

# 製作一集（通用 orchestrator）

你是製作總監。**cwd = 系列資料夾根目錄**（有 `series.yaml`）。先讀 `./series.yaml`、`./series-context.md`、`~/.claude/series-studio/CONVENTIONS.md`。
確定性工作（組裝、render、上傳）照 CONVENTIONS.md 跑；其餘用 `Agent` 工具調度 vid-* subagent。

## 流程與審核關（🚪 = 停下等使用者明說 OK 才往下）
1. **vid-screenwriter**：取第 N 集素材、寫 `episodes/epNN/script/epNN-script.md`（本人口吻、忠於素材、**接 series-context**：不重複、回呼前集、兌現上集預告）。
2. **vid-factchecker**：對素材逐點核；不過退回 1。
3. 🚪 **腳本關**：轉 HTML 給使用者過目。
4. **vid-voice**：`tools/build_voice.py --ep N` 逐句合成、破音字詞庫、斷句改寫。
5. 🚪 **純音檔 QC 關**：concat 旁白給使用者聽，鎖定發音（QuickTime quit 再 open）。
6. **並行**：vid-music（BGM，片頭/本體可沿用）｜ vid-animator（scenesNN/EpisodeNN、實機 demo、render）｜ vid-art-director（審視覺，退件則動畫師修）。
7. **組裝**：前言+片頭+本體(ducking) → `episodes/epNN/render/epNN_final.mp4`。
8. **vid-seo**：metadata（章節時間戳組裝後重算）、置頂留言；縮圖交動畫師渲。
9. 🚪 **成片關**：打開成片給使用者看整片。**明說 OK 才上架。**
10. **發布**：upload.py 上傳公開 → 縮圖 → 置頂留言（提醒手動置頂）。
11. **回灌**：把本集發音/斷句修正寫回 `voiceover/tw_lexicon.json`/`voice-style.md`；**更新 `series-context.md`**（本集標題、核心概念、術語/比喻、下集預告、可回呼點）。

## 原則
三段式、署名授權(series.yaml)、不營利、本人口吻——每集不變。詞庫與 context 跨集累積、愈做愈順。
