# Series Studio — 通用製作慣例（所有系列共用）

> 各 vid-* agent 與 produce-episode 流程都引用本檔。在「系列資料夾」根目錄操作（cwd = 系列根）。
> 系列專屬參數一律從 `./series.yaml` 讀；口吻從 `./voice-style.md`；上下集 context 從 `./series-context.md`。

## 腳本格式（編劇）
- 檔案 `episodes/epNN/script/epNN-script.md`。
- `**【旁白】**` 後一段＝要唸的（本人口吻）；`**【畫面】**/**【字幕】**＝動畫指示（不唸）；`## NN 場景名` 分場景。
- 三段式：00 無音樂前言 →〔C&C/品牌片頭由組裝插入〕→ 本體分場景 → 收尾＋下集預告＋角落 credit（授權署名見 series.yaml）。
- demo 段用素材附帶的程式碼實機演示，**務必留旁白蓋住 demo 播放**。
- 取素材：`source.kind: local` → 讀 `source/epN.md`；`github` → 用 `api.github.com/repos/{repo}/contents/{path}?ref={ref}` 取 base64 解碼（raw.githubusercontent 常逾時）。

## 腳本關（🚪 給使用者過目／編輯）— `python3 tools/build_script_editor.py --ep N`
- 把 `epNN-script.md` 轉成**可編輯的腳本編輯器 HTML**（`epNN-script-editor.html`），open 給使用者。**腳本關一律用這個可編輯模式**，不要只給唯讀 HTML。
- 使用者可逐段改旁白、在任意位置插入自己的段落、刪段、即時看字數/時長，一鍵「匯出 Markdown」成 `epNN-script-edited.md`；自動存 localStorage、可還原原稿、可複製全部旁白。
- 配色自動套 `series.yaml` 的 visual token。使用者改完匯出後，用該 edited.md **覆蓋** `epNN-script.md`（覆蓋前 `diff` 看改了什麼），再交事實查核／往下走。
- 務必停下、等使用者明說 OK 才進配音。

## 配音（vid-voice）— `python3 tools/build_voice.py --ep N`
- **本人配音（`voice.provider: self`）**：跳過 MiniMax 合成；改用 `python3 tools/build_recording_script.py --ep N` 產**錄音唸稿**（大字旁白＋每段建議檔名＋已錄進度），本人對著唸、錄成 `epNN-sceneNN.wav` 放 `episodes/epNN/voiceover/`，再 concat 做純音檔 QC。
- 設定驅動（讀 series.yaml voice）。逐句合成、內容雜湊命名（含詞庫）→ 冪等、改發音自動重合成。
- **純音檔 QC 迴圈**：concat 旁白成 mp3 給使用者聽、先鎖發音再渲染影片。QuickTime 重開要先 `quit` 再 `open`（同路徑不自動 reload）。
- 讀錯字 → 加 `voiceover/tw_lexicon.json`（`詞:"(pin1)(yin1)"`，輕聲用 `(le5)`；別加單字詞條）。頑固破音字（如「當機」）→ 直接換詞。
- **⚠️ pronunciation_dict 會干擾斷句，能不加就不加（2026-06 EP6 定案）**：送 MiniMax 的 `pronunciation_dict` 不只可能無效，還會**把同句其他詞的斷句搞壞**（EP6 替「移植」加 dict→移植仍唸錯、還連帶把「影響」斷壞；移除 dict 後移植本來就唸對 yi2、斷句也順）。**加任何詞庫條目前先確認「不加 dict 時本來就唸錯」**——很多詞（如「移植」，移無他讀）MiniMax 預設就對，加了反而害事。每個新條目都要：①真的會唸錯才加 ②用 clip 給使用者耳朵確認「加了真的修好、且沒弄壞別處」，沒確認別留。
- 斷句怪／詞被切開 → **改寫腳本**（非詞庫）。
- **🚪 斷句 QC（render 前必做，每集沿用；2026-06 EP6 定案）**：MiniMax 常把詞中插微停頓（治療→「治｜療」、約定→「約｜定」）。判官**一律用 `voiceover/verify_phrasing.py`**（ffmpeg 物理偵測真實靜音＋whisper 只定位→jieba 判詞內），**不要信 `phrasing_gate.py`**——後者用 whisper 內插字級時間、±1 字漂移、**大量把標點旁停頓誤報成詞內切（假陽性）**，照它修會狂修假陽性又漏真缺陷。
  - ⚠️ `verify_phrasing.py` 內 `WhisperModel` 必須用 **`"small"`**（"medium" 在本機 CPU 會卡死）。
  - 流程：① `voiceover/.venv-phrasing/bin/python voiceover/verify_phrasing.py <該句純mp3> --fix`（逐句；報「斷錯 N 處」，N>0 時自動剪詞內靜音輸出 `{hash}_fixed.mp3`、原檔不動）→ ② `mv {hash}_fixed.mp3 {hash}.mp3` 覆蓋 → ③ 重跑 builder（re-probe 時長、重排 onset）→ ④ 再 verify 確認「斷錯 0」。
  - 若 fresh-take 也想試：先 `rm` 該 mp3 再跑 builder（hash 不含詞庫/取樣，同文字會重抽一個新 take），再 verify。
  - ⚠️ **含英文的句子**（如 Directed Acyclic Graph）whisper 對齊會亂、verify 結果不可信，別據此亂剪——靠耳朵。
- **改讀音不會自動重配**：build_storyteller 的 cache hash 只含文字、**不含 tw_lexicon**，改詞庫後含該詞的句子不會重抽——要 `rm` 該 mp3 強制重配。且 MiniMax **不一定吃** `詞/(pin1)(yin1)` 詞庫格式（EP6「移植」設 yi2 仍唸 yi4）；頑固者改測別的格式或**直接換詞**，並用 clip 給使用者耳朵確認。

## 動畫（vid-animator）— Remotion
- 元件：`remotion/src/components.tsx`(Reveal/SceneTitle/Chip/Card)、`theme.ts`、`fonts.ts`(codeFamily)。每集寫 `scenesNN.tsx` + `EpisodeNN.tsx`（從 manifest `epNNData.ts` 的 EP NN 自動排場景）+ 註冊 `Root.tsx`。
- 共用 `Narration`/`Subtitles`（吃 `cues` prop）。
- **字幕 cues 必用真實語音時間戳（自動校正斷句）**：配音定稿後跑 `python3 tools/build_subtitle_cues.py --ep N`（whisper 每段 wav → srt → `voiceover/cues/epNN_cues.json`，`fromF/toF`＝真實語音時間、依語音停頓自然斷句）。字幕進出時間**一律取自此 cues，嚴禁用字數比例估算**（會「聲音比字幕快／字幕飄」）。cues 的 `text` 是 whisper 轉錄（base 有同音/技術詞錯），技術詞/人名對照 `script.md`【旁白】校正後再上字幕。有 `_short` 剪輯版的場景自動採用其 srt。
- **實機 demo 螢幕錄影**（macOS）：⚠️先把輸入法切 ABC（`osascript ... key code 49 using control`）否則 keystroke 全形；用 `/opt/anaconda3/bin/python3`；`ffmpeg -f avfoundation -i "2"` 錄螢幕（需 Terminal 螢幕錄製權限）→ 裁終端機放大 + `tpad` 凍結補長 → `OffthreadVideo` 嵌入（明確尺寸、別蓋標題）。
- **渲染＝逐場景輸出 + concat（標準流程，所有影片 agent 一律照做）**：本體**不要**整集一次渲染（改一個字得重跑數萬幀）。每個場景渲成獨立 mp4（`render/scenes/sNN.mp4`，全部用**相同編碼參數**：libx264 / yuv420p / 同 fps / 同解析度 / 同音訊參數），本體＝`ffmpeg -f concat -c copy` 拼接這些場景 mp4（拼接僅數秒）。
  - **迭代只重渲改到的場景**：作者挑出「sceneNN 哪裡不對」→ 只重渲那一支 `sNN.mp4`（分鐘級）→ 重 concat（秒級）。嚴禁為了一個小改動重渲整片。
  - 單場景渲染：獨立 composition，或 `npx remotion render src/index.ts EpNN render/scenes/sNN.mp4 --frames=<startF>-<endF>`。
  - **驗證優先用 Remotion Studio 即時預覽**（`npx remotion studio`，拖播放頭到該秒、0 等待），不要為了「看一眼對不對」就渲染；要產檔再渲。審查階段可 `--scale=0.5` 快渲、最後才全解析度跑一次。
  - 仍先 `still` 抽幀驗關鍵時刻。場景之間切點要乾淨（無跨場景動畫），concat 才不破。
  - ⚠️ **重錄/換某場景旁白 wav 時，務必同步更新 `remotion/public/voiceover/`**（`staticFile` 讀 public，不是 `episodes/*/voiceover/`）。只改 episodes 而忘了 public → render 讀到舊音，會出現「畫面對、但旁白在舊長度之後變靜音（-inf）」。重渲前先 `ffprobe` 比對 public 那支 wav 的長度是否＝最新版。

## 三個必守的抖動鐵則（vid-art-director 把關）
1. **CJK 標點逐幀抖** → 根容器 `textSpacingTrim:"space-all"` + `fontKerning:"none"`。
2. **進場微飄** → 別用過阻尼 spring；用 14 幀 clamp 的 interpolate、位移取整數、settle 後拿掉 transform。
3. **字幕換句跳** → 固定下三分之一、底部錨定、長句標點切短段。
- QC：相鄰幀 `ffmpeg ...blend=all_mode=difference,eq=contrast=20`；同幀對自己須全黑。不遮擋：標題/字幕不被內容蓋。

## BGM（vid-music）— `python3 tools/generate_bgm.py --preset intro|body`
- MiniMax `music-2.6` + `is_instrumental:true`。接長 `ffmpeg -stream_loop -1 -t <秒>`。

## 組裝（確定性）
三段 concat：前言(乾聲) + 片頭(intro.mp4 或渲染的 Intro) + 本體(輕 BGM ducking)。
- 本體 ducking：`[0:a]asplit=2[nar][key];[1:a]volume={body_volume}[bg];[bg][key]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[bgd];[nar][bgd]amix=inputs=2:normalize=0:duration=first[a]`
- 三段同 codec/fps/音訊參數，concat demuxer `-c copy`。
- **配合逐場景輸出**：前言＝`scenes/s00.mp4` 直接用（乾聲）、本體＝`concat(s01..sNN)` 再混 BGM ducking，不必再從整片切「前言/本體分界 startF」（分界天然落在場景檔邊界）。改某場景只重渲該 `sNN.mp4`→重 concat 本體→重混 BGM→三段重組，整片只在交付前需要時跑。

## 上架（vid-seo + 發布）
- metadata：標題(關鍵字前置≤100)、描述(hook→摘要→章節→出處連結→授權)、tags、章節(本體時間=原始+片頭長度)、縮圖、置頂留言。
- 合規：描述含來源連結與授權(series.yaml license/attribution/source_url)，commercial:false → 不開營利。
- 上傳用共用工具 `~/.claude/series-studio/youtube/upload.py`（OAuth creds 同夾、已快取，全系列共用）：`--file --metadata --privacy` → `--thumb` → `--comment`（API 不能置頂，提醒手動）。

## 完工回灌
每集做完：把發音/斷句修正回灌 `tw_lexicon.json`/`voice-style.md`；更新 `series-context.md`（本集講了什麼、術語、下集預告、可回呼點）。
- **框架自身也要回灌**：本檔（CONVENTIONS.md）、`~/.claude/agents/*.md`（含 colon-and-code / ai-storyteller 兩個主理人）、skills（new-series / produce-episode / auto-produce-next）、`template/` 有任何修改，同步回 series-studio repo（`~/Desktop/Projects/YouTube-Channel/series-studio/claude/…`）並 commit + push。活檔是唯一真相，repo 不同步＝白學。⚠️ 金鑰不進 repo（`.env`、`youtube/token.json`、`client_secret.json`）。
