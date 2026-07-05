---
name: auto-produce-next
description: 無人工關卡、自動製作「下一個還沒做的章節」成一集，上傳為 YouTube 非公開（unlisted），通知使用者連結，等使用者自己審核後手動公開。給排程（launchd）或手動觸發。在系列資料夾根目錄（有 series.yaml）執行。
---

# 自動製作下一集（無人工關 → unlisted）

你是製作總監，但這是 **autonomous 模式**：把 produce-episode 的 3 道人工審核關（🚪腳本 / 🚪純音檔 / 🚪成片）**全部拿掉**，一路跑到上傳成 **unlisted**，通知使用者連結即停。**絕不公開（public）**。置頂留言：**上傳完自動發**（使用者 2026-07-05 指示；API 無法置頂，通知裡提醒手動置頂）。

cwd = 系列資料夾根目錄。先讀 `./series.yaml`、`./series-context.md`、`~/.claude/series-studio/CONVENTIONS.md`、`./voice-style.md`、`./voiceover/tw_lexicon.json`，以及記憶（MEMORY.md）裡的製作學習。

## 選定集數 N
掃 `episodes/ep*/`，找出**最小的、source 有 docs/chapter{N} 但還沒有 `episodes/epNN/` 的章節**＝要做的 N。沒有未做章節就通知「全部做完」並停。

## 流程（保留自動品質迴圈，去掉人工關）
1. **vid-screenwriter**：取第 N 章素材、寫 `episodes/epNN/script/epNN-script.md`。務必接 series-context（不重複、回呼前集、兌現上集預告）。**套用已知學習**：冷開場別用「欸」起頭且各集換句式；程式碼「一行」一律寫成「一句/一段」（MiniMax 不吃「行」破音）。
2. **vid-factchecker**：逐點對素材核。**不過 → 自動退回 vid-screenwriter 重寫，最多 2 次**；仍不過就帶著問題往下但在最終通知裡標明。
3. **vid-voice**：
   - **3a. 破音字 lint（合成前必跑，前景阻塞）**：`voiceover/.venv-phrasing/bin/python voiceover/polyphone_lint.py --ep N`（或對腳本）。列出含高風險破音字、未進詞庫的詞。**逐項判**：MiniMax 預設唸對的（行李/模型/系統…）跳過；預設唸錯的（協調 tiao2、夾 jia2、誰 shei2、重來 chong2…）**先補 tw_lexicon.json**；**含「行」的（執行/一行）詞庫無效→改寫腳本**（執行→處理/做、一行→一句/段）。補完詞庫/改完腳本才合成。這是「主動式」破音字閘，補斷句 gate（被動）抓不到讀音的洞。
   - **3b. 合成**：`python3 tools/build_voice.py --ep N`。靠詞庫+學習，**不做人工純音檔 QC**。旁白／字幕分離用 `{顯示|唸法}` markup（如 `{A2A|A two A}`：字幕顯示 A2A、旁白唸 A two A）——英文縮寫含數字/字母被讀錯時用。
   - **3c. 斷句 QC 關卡（render 前必過；取代人工純音檔關）**：**主用字級 forced-align 偵測器** `voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py --ep N --json episodes/epNN/_auto_logs/faN.json`（exit 1=有缺陷、0=乾淨）。字級對齊（ctc-forced-aligner MMS）拿每字精準時間＋silencedetect＋jieba（**內建 opencc 繁→簡，否則繁體被簡體字典切錯會漏抓**），**精準列出「詞中間被唸斷」的真缺陷、幾乎不噴假陽性**。比舊 whisper `phrasing_gate.py`（±1 字飄移、短句會漏，EP11 就漏了「強化」）可靠太多，舊 gate 可留作輔助。
     - 🚫 **一定要前景阻塞執行**（一個 Bash 呼叫、`timeout` 設 540000）。**絕不可**丟背景再用 `Monitor`／`ScheduleWakeup`／輪詢等它——在 headless `claude -p` 裡，模型一讓出（yield）整個 run 就結束，QC 永遠等不到（EP10 首跑即如此死）。`--model medium` 是為了塞進單次 Bash 9 分鐘上限；83 句約 4–5 分鐘。首次會下載 medium 模型（一次性）。
     - **這是候選清單，不是鐵定缺陷**——whisper 內插時間有 ±1 字誤差，常見假陽性：①逗號漂移（「問題，是」停在逗號卻被標成「問｜題」）②詞邊界（「不過｜給」「萬一｜一個」）③jieba 誤切（把「萬一一個」切出「一一」）。
     - **逐項對回腳本判斷**：只有「停頓真的落在一個詞中間、左右都沒標點、聽起來像把詞切斷」才是真缺陷（如第三種、有關係、好幾天、下指令）。是真的才修：**刪那個 cue 的 mp3**（破音字另補 `tw_lexicon.json`）→ `build_voice.py --ep N` 重合成（fresh take 通常自然修正，比剪靜音乾淨）→ 重跑 gate 確認，最多 2 輪；仍殘留用 `verify_phrasing.py --fix` 剪靜音兜底。
     - 判為假陽性的候選**不要動**（重合成它只是浪費、又可能引入新問題）。把「修了哪幾句、哪些判為假陽性」寫進最終通知。
     - ⚠️ 若被重合成的 cue 落在「第一個正片場景之前」（前言乾聲段），scene01 起點 startF 會位移 → 步驟 5 組裝的 BOUND 要用新 startF 重算。
4. **vid-animator**（＋ vid-art-director 審）：做場景。若該章有可實跑的程式碼且需要 demo → 用 `.env` 的 `LLM_API_KEY/LLM_BASE_URL/LLM_MODEL_ID` 跑真實模型 + asciinema 錄 PTY（不需螢幕授權）+ agg（字體含 `Heiti TC` 才顯示繁體、print 別放 emoji）→ OffthreadVideo 嵌入、tpad 凍結尾；沒有適合的程式碼就用視覺/keynote 呈現。**美術指導退件 → 自動退回動畫師修，最多 2 次**。⚠️ render 輸出到 `episodes/epNN/render/`，別跑到 `remotion/episodes/`。
5. **組裝**（確定性，照 CONVENTIONS）：前言乾聲 + 片頭(intro.mp4) + 本體(BGM ducking，body_volume 從 series.yaml) → `episodes/epNN/render/epNN_final.mp4`。分界＝第一個正片場景 startF（從 epNNData.ts 算）。三段同 codec/48k 再 concat。
6. **vid-seo**：metadata（標題/描述/tags/章節時間戳＝組裝後重算/縮圖文案）、置頂留言文字（**先存檔不發**）。縮圖渲出 `epNN_thumbnail.png`。
7. **上傳 unlisted**：`python3 ~/.claude/series-studio/youtube/upload.py --file episodes/epNN/render/epNN_final.mp4 --metadata episodes/epNN/youtube-metadata.json --privacy unlisted` → 記下 video id/連結 → `--thumb <id> --thumb-file epNN_thumbnail.png` → **接著發置頂留言** `--comment <id> --comment-file episodes/epNN/youtube-pinned-comment.txt`（API 不能置頂，通知裡提醒手動置頂）。**不要設 public。**
8. **回灌**：更新 `series-context.md`（本集標題、核心概念、術語/比喻、demo、回呼點、下集預告）；發音/斷句新學習回寫 `tw_lexicon.json`/`voice-style.md`/記憶。
9. **通知**：把「EP N 已產好、unlisted 連結、一句話摘要、factcheck/美術是否全過、待你審核後公開、置頂留言已發（記得到 Studio 手動置頂）」清楚輸出。

## 硬規則
- **headless `claude -p` 不能非同步等待**：任何長工具（斷句 QC、render…）一律**前景阻塞**在單次 Bash 內跑完（`timeout` 拉到上限、需要就換更快設定）。**禁用 `Monitor`／`ScheduleWakeup`／背景＋輪詢去「等」背景工作**——模型一讓出，整個 `-p` run 就結束、再也不會醒來（EP10 首跑死因）。
- **render 前一定要過斷句 QC 關卡（步驟 3b）**——這關過去從沒被執行，導致斷句錯誤逐集復發；不可略過。
- **永不 public**——公開是使用者的事。置頂留言上傳完即發（無法用 API 置頂→通知提醒手動置頂）。
- 任一階段硬失敗（API/render/上傳）重試一次；仍失敗 → **停下並通知**那一集卡在哪、要人工接手，不要亂上傳或硬湊。
- 一次只做一集（N）。做完即停。
- 成本意識：別無限重渲染；自動迴圈各有次數上限（如上）。
