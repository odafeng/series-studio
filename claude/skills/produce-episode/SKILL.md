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
3. 🚪 **腳本關**：`python3 tools/build_script_editor.py --ep N` 產**可編輯**的腳本編輯器 HTML，open 給使用者直接改旁白／插入自己的段落；使用者「匯出 Markdown」後用 edited.md 覆蓋 `epNN-script.md`（先 diff）。等使用者明說 OK 才往下。
4. **vid-voice**：`python3 tools/build_voice.py --ep N` 逐句合成。模型以 `series.yaml voice.model` 為唯一真相；MiniMax 目前優先用 `speech-2.8-hd`，臨時 A/B 才傳 `--model`，不要把舊 `speech-02-hd` 寫死在 agent 或 skill。
   - builder 的 cache hash 必須包含 model、voice/audio settings、實際送 TTS 的文字、詞庫命中與 `tts_replacements`。`tts_replacements` 只改 MiniMax input，`epNNData.ts`／字幕仍保留原稿；適合 `RL`、`DeepSeek-R1-Zero` 等模型容易黏讀的英文術語。
   - **4b. 斷句 QC 關卡（render 前必跑，別省）**：主判官用 `voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py --ep N`。長集分批可加 `--cue-start A --cue-end B`；**exit 0＝乾淨、1＝找到缺陷、2＝對齊器錯誤**。exit 2 不可當 PASS，要重跑該 cue 或人工查明。
   - 修法依序：fresh take（`retake_until_clean.py`）→ best-of-N（`pick_best_take.py`，最佳候選先留存）→ 系統性詞內斷句才用 `surgical_phrasing_fix.py`。任何 audio 改動後都重跑 builder，確認 manifest/hash/audio 齊全，再重跑 forced-align 到全片 exit 0。
   - forced-align 對中英文混合術語可能 tokenizer mismatch；英文字本身另用 medium 級轉錄 zoom 或耳朵核對，不能因 aligner 顯示 MISS 就亂剪。旁白、字幕、scene timeline 一律在這關與純音檔 QC 都通過後才鎖定。
5. 🚪 **純音檔 QC 關**：concat 旁白給使用者聽，鎖定發音（QuickTime quit 再 open）。斷句已由 4b 把關，這關專注**發音／破音字／語氣**。
6. **並行**：vid-music（BGM，片頭/本體可沿用；素材與成品必過 `tools/bgm_qc.py --vocal`，有可辨識人聲就重生或換 seed）｜ vid-animator（scenesNN/EpisodeNN、實機 demo、render）｜ vid-art-director（審視覺，退件則動畫師修）。
7. **組裝**：前言+片頭+本體(ducking) → `episodes/epNN/render/epNN_final.mp4`。
8. **vid-seo**：metadata（章節時間戳組裝後重算）、置頂留言；縮圖交動畫師渲。
9. 🚪 **成片關**：打開成片給使用者看整片。**明說 OK 才上架。**
10. **發布**：upload.py 上傳公開 → 縮圖 → 置頂留言（提醒手動置頂）。
11. **回灌**：把本集發音/斷句修正寫回 `voiceover/tw_lexicon.json`/`voice-style.md`；**更新 `series-context.md`**（本集標題、核心概念、術語/比喻、下集預告、可回呼點）。

## 原則
三段式、署名授權(series.yaml)、不營利、本人口吻——每集不變。詞庫與 context 跨集累積、愈做愈順。
