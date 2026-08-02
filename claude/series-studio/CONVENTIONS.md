# Series Studio — 通用製作慣例（所有系列共用）

> 各 vid-* agent 與 produce-episode 流程都引用本檔。在「系列資料夾」根目錄操作（cwd = 系列根）。
> 系列專屬參數一律從 `./series.yaml` 讀；口吻從 `./voice-style.md`；上下集 context 從 `./series-context.md`。

## 集長換算（實測，別再用猜的）
**MiniMax 克隆聲 @ speed 1.15 ＝ 5.97 字/秒**（EP01 實測：2525 字 / 422.9 秒）。
換算成 speed 1.0 的基準 ≈ **5.19 字/秒**，這是 `build_script_editor.py` 的 `BASE_CPS`。
- 目標字數 = `target_min` × 60 × 5.97
- ⚠️ EP01 一開始用猜的 3.7 字/秒（＝11 分鐘要 2400 字），**誤差 61%**，導致編劇照著錯的上限
  把稿子從 3301 字砍到 2500，砍掉的都是真材料。錯誤的常數不會報錯，只會讓所有下游決策偏一點。
- **各集目標長度不該一律相同**：引言/後記的素材量可能只有大章的 1/7，硬套同一個長度就是灌水。
  在 `series.yaml` 的 `episode_map` 逐集設 `target_min`。
- `build_recording_script.py` 的 4.3 字/秒是**真人唸稿**語速，跟 TTS 是兩回事，不要混用。
- **⚠️ 量素材規模一律用「扣掉程式碼區塊的純 CJK 字數」，不要用全文字元數。**
  只講概念的系列（紅線＝不逐行導讀程式碼）裡，程式碼字元對旁白長度的貢獻是**零**，
  拿全文字元數比較會系統性灌水。ai-agent-eli5 EP04 踩到：第 2 章「140k 字元、全書最厚」
  vs 第 3 章「108k」，看起來差 23%；但第 2 章有 **263 行程式碼**、第 3 章只有 69 行，
  扣掉後的純中文是 34,038 vs 27,787（只差 18%），而編劇據此開出的稿子反而比前一集**長 18%**。
  ```
  awk '/^```/{f=!f; next} !f{print}' ch.md | python3 -c "import sys,re;print(len(re.findall(r'[一-鿿]',sys.stdin.read())))"
  ```
  實測濃縮比（純 CJK 原文 : 旁白字）：EP02 **2.07:1**／EP03 **2.68:1**。新一集落在區間外就要有理由。
- **⚠️ 「概念顆粒度」這種論據要查對等性。** 同上那次，編劇主張「前一章 7 個骨幹 vs 本章 19 個概念，
  所以本章要更長」——但「7」是前一集編劇**自己歸納的敘事單位**，「19」是原書的**三級標題數**，
  兩個數不同源。實際數下去：前一章有 33 個三級標題，比本章多 74%，結論整個反過來。
  **subagent 拿數字論證時，先確認兩邊的數是同一把尺量的**，不要照單全收。

## 腳本格式（編劇）
- 檔案 `episodes/epNN/script/epNN-script.md`。
- `**【旁白】**` 後一段＝要唸的（本人口吻）；`**【畫面】**/**【字幕】**＝動畫指示（不唸）；`## NN 場景名` 分場景。
- 三段式：00 無音樂前言 →〔C&C/品牌片頭由組裝插入〕→ 本體分場景 → 收尾＋下集預告＋角落 credit（授權署名見 series.yaml）。
- demo 段用素材附帶的程式碼實機演示，**務必留旁白蓋住 demo 播放**。
- 取素材：`source.kind: local` → 讀 `source/epN.md`；`github` → 用 `api.github.com/repos/{repo}/contents/{path}?ref={ref}` 取 base64 解碼（raw.githubusercontent 常逾時）。

## 腳本 lint（編劇交稿後、開編輯器前必跑）— `python3 tools/lint_script.py --ep N`
- 掃【旁白】：破音字（表格真相在 `voice-style.md`，工具直接解析）、破折號、實作召喚、出題、導讀腔＝**ERROR**；長串無標點（>28 字）、小數點＝warn。exit 1 表示有 ERROR，退回編劇改。
- 順便產**耳朵確認清單**（旁白裡所有英文詞／人名）給配音師——含英文的句子 `verify_phrasing.py` 對齊會亂、結果不可信，只能靠聽。
- 這些雷要死在編劇桌上：`pronunciation_dict` 常常無效還會弄壞同句斷句（EP6 定案），事後修比事前避開貴得多。
- 改規則＝改 `voice-style.md` 那張表，不要改工具。`--selftest` 可驗規則沒被改壞。

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
- 斷句怪／詞被切開 → 先重抽 take；**重抽解不掉就外科手術，最後才改腳本**。
  EP02 的「視野」被唸成「視｜野」是**系統性**的（前面是「工程，」，MiniMax 固定在逗號後起音、
  再於「視」之後換氣），**連抽 27 次只有 1 次乾淨**。這種靠重抽是浪費 API 費用。
  外科手術做法：用 forced-align 定出詞內靜音的精確區間（EP02 是 1.579–1.921s），
  `atrim`＋`concat` 把它剪掉、**只留 60ms 自然銜接**，再 `apad` 補回原長度。
  結果乾淨、腳本不動、時間軸不動。判準：**重抽 ≥10 次仍不乾淨就別再抽了**。
- **🚪 斷句 QC（render 前必做，每集沿用；2026-06 EP6 定案）**：MiniMax 常把詞中插微停頓（治療→「治｜療」、約定→「約｜定」）。判官**一律用 `voiceover/verify_phrasing.py`**（ffmpeg 物理偵測真實靜音＋whisper 只定位→jieba 判詞內），**不要信 `phrasing_gate.py`**——後者用 whisper 內插字級時間、±1 字漂移、**大量把標點旁停頓誤報成詞內切（假陽性）**，照它修會狂修假陽性又漏真缺陷。
  - ⚠️ `verify_phrasing.py` 內 `WhisperModel` 必須用 **`"small"`**（"medium" 在本機 CPU 會卡死）。
  - 流程：① `voiceover/.venv-phrasing/bin/python voiceover/verify_phrasing.py <該句純mp3> --fix`（逐句；報「斷錯 N 處」，N>0 時自動剪詞內靜音輸出 `{hash}_fixed.mp3`、原檔不動）→ ② `mv {hash}_fixed.mp3 {hash}.mp3` 覆蓋 → ③ 重跑 builder（re-probe 時長、重排 onset）→ ④ 再 verify 確認「斷錯 0」。
  - 若 fresh-take 也想試：先 `rm` 該 mp3 再跑 builder（hash 不含詞庫/取樣，同文字會重抽一個新 take），再 verify。
  - ⚠️ **含英文的句子**（如 Directed Acyclic Graph）whisper 對齊會亂、verify 結果不可信，別據此亂剪——靠耳朵。
- **改讀音會不會自動重配，取決於你用哪支合成器——先去讀那支的 hash 怎麼算，不要照抄本條**：
  - `build_storyteller.py`：hash **只含文字**，改詞庫後含該詞的句子**不會**重抽 → 要 `rm` 該 mp3 強制重配。
  - `build_voice.py`（ai-agent-eli5 等）：hash **含 `lex_entries(text)`** → 改詞庫**會自動**重抽該句，不必手動 `rm`。
  EP02 一開始照本條的舊敘述以為要手動 `rm`，讀了原始碼才發現這支不用。**文件會跟程式碼脫節，hash 的定義在程式碼裡。**
- 且 MiniMax **不一定吃** `詞/(pin1)(yin1)` 詞庫格式（EP6「移植」設 yi2 仍唸 yi4）；頑固者改測別的格式或**直接換詞**，並用 clip 給使用者耳朵確認。
  ✅ 也有成功案例：EP02「彈性」加 `(tan2)(xing4)` 一次就修好（原本唸 dàn），且沒弄壞同句斷句。
  **判斷準則不是「詞庫沒用」，而是「讀音錯用詞庫、斷句錯用重抽」**——兩種缺陷的修法不同，別混用。
- **⚠️ 加詞庫不是零成本：它會改變句子長度，進而動到整條下游時間軸。**
  EP02 替「執行」加 dict 後，那 13 句普遍變慢，其中一句多了 **1.2 秒**、重抽 10 次都回不去
  （dict 干擾的是整句節奏，不只那個詞）。而 `scenesNN.tsx` 的 `at={}` 與 `EpisodeNN.tsx` 的
  `SCENES` 切點**都是寫死的常數**，句長一變，後面所有動畫就相對旁白飄掉。
  **正解：重抽後把 mp3 正規化回原本的精確秒數**，`startF`／`durF` 就一格都不動，
  所有寫死的時間點、字幕、章節、SRT 全部繼續有效：
  1. 先快照受影響 cue 的舊 mp3 秒數（改詞庫會換 hash，舊檔不會被覆蓋，可直接 `ffprobe`）
  2. 重抽時**保留目前最好的候選**（EP02 同一個 session 犯了三次：迴圈寫成「不夠好就丟掉」，
     把 cue74 的 8.975s、cue223 唯一乾淨的那個 take 全洗掉了，白跑十幾輪）。
     best-of-N 取樣一律先存最佳候選，最後再決定用不用。
  3. 比原本短 → `apad` 補靜音到精確秒數；比原本長 → 先裁尾端靜音，剩餘用 `atempo`（≤3% 聽不出來）吸收
  4. 重跑 builder 重新 probe，驗 `total` 與所有 `startF`／`durF` 歸零偏移
  殘差：補靜音只能到毫秒級，次幀誤差沿 `t += dur + GAP` 累積，偶爾讓某個 `round(t*30)` 翻 1 幀（33ms）。
  EP02 實測 15 個場景切點只有 2 個各飄 1 幀——相較於不做正規化的**累積 178 幀（5.9 秒）漂移**，這是可接受的代價。
- **⚠️「這些詞 MiniMax 讀得對」的白名單本身要存疑。** ai-agent-eli5 的 `voice-style.md` 曾把「執行」
  列進「讀得對、不用閃」，EP02 實測唸成 zhí **háng**。沒有實聽過就別把任何詞放進白名單——
  「常見搭配所以應該沒問題」是猜測不是證據。錯誤的白名單比沒有白名單危險，因為它讓人不去查證。

## 動畫（vid-animator）— Remotion
- 元件：`remotion/src/components.tsx`(Reveal/SceneTitle/Chip/Card)、`theme.ts`、`fonts.ts`(codeFamily)。每集寫 `scenesNN.tsx` + `EpisodeNN.tsx`（從 manifest `epNNData.ts` 的 EP NN 自動排場景）+ 註冊 `Root.tsx`。
- **⛔ 畫面上不要出現內部場景編號（`SCENE 01 — …`）。** 那是製作用的鷹架，不是給觀眾看的。
  EP02 把 14 處終端機視窗標題與 Kicker 都寫成 `SCENE NN — 描述`，作者看片時退件。
  保留描述文字即可（`title="介面決定上限"`），版面不變。
- 共用 `Narration`/`Subtitles`（吃 `cues` prop）。
- **字幕 cues 必用真實語音時間戳**：配音定稿後跑 `python3 tools/build_subtitle_cues.py --ep N`，
  它會**同時**產 `voiceover/cues/epNN_cues.json`（來源）與 `remotion/src/epNNCues.ts`（Remotion 吃的）。
  ⚠️ 這兩份以前是手工轉的，EP01 重配音後 json 更新了、ts 沒跟上，**差點讓整集字幕跑在舊講稿的時間軸上**——
  沒有任何檢查會發現。現在一步到位，不要手改 ts。
- （舊版說明）`build_subtitle_cues.py --ep N`（whisper 每段 wav → srt → `voiceover/cues/epNN_cues.json`，`fromF/toF`＝真實語音時間、依語音停頓自然斷句）。字幕進出時間**一律取自此 cues，嚴禁用字數比例估算**（會「聲音比字幕快／字幕飄」）。cues 的 `text` 是 whisper 轉錄（base 有同音/技術詞錯），技術詞/人名對照 `script.md`【旁白】校正後再上字幕。有 `_short` 剪輯版的場景自動採用其 srt。
- **實機 demo（終端類）預設用合成 asciicast 鏈**（2026-06 EP6 起）：`generate_*_cast.py` 手工合成 asciicast v2（模仿 Claude Code TUI）→ `agg`（字體必含 Heiti TC）→ ffmpeg mp4。**鐵則：數字必須由實機真跑回填、絕不捏造**；畫面可合成。可重跑、無輸入法/睡眠/權限雷。工具鏈範例：colon-and-code `tools/capture/`（含 README、安全護欄：中性 prompt、不露 email/hostname）。
- **真錄螢幕**（GUI/需要真螢幕的橋段，macOS）：⚠️先把輸入法切 ABC（`osascript ... key code 49 using control`）否則 keystroke 全形；用 `/opt/anaconda3/bin/python3`；`ffmpeg -f avfoundation -i "2"` 錄螢幕（需 Terminal 螢幕錄製權限）→ 裁終端機放大 + `tpad` 凍結補長 → `OffthreadVideo` 嵌入（明確尺寸、別蓋標題）。
- **渲染＝逐場景輸出 + concat（標準流程，所有影片 agent 一律照做）**：本體**不要**整集一次渲染（改一個字得重跑數萬幀）。每個場景渲成獨立 mp4（`render/scenes/sNN.mp4`，全部用**相同編碼參數**：libx264 / yuv420p / 同 fps / 同解析度 / 同音訊參數），本體＝`ffmpeg -f concat -c copy` 拼接這些場景 mp4（拼接僅數秒）。
  - **迭代只重渲改到的場景**：作者挑出「sceneNN 哪裡不對」→ 只重渲那一支 `sNN.mp4`（分鐘級）→ 重 concat（秒級）。嚴禁為了一個小改動重渲整片。
  - **⚠️ 逐場景渲染要配逐場景 commit。** 只做前者等於只做一半：產物(mp4)一直在變、來源(tsx)卻沒有任何快照，
    美術指導拿到不一致的兩者時只能回報「這是共用元件庫，我無法判斷剛才改了什麼」——EP01 因此白跑一輪 QC。
    每支場景渲完就 `git add` 該場景相關的檔案並 commit，讓 QC 能指著 diff 說「就是這行」。
  - 單場景渲染：獨立 composition，或 `npx remotion render src/index.ts EpNN render/scenes/sNN.mp4 --frames=<startF>-<endF>`。
  - **驗證優先用 Remotion Studio 即時預覽**（`npx remotion studio`，拖播放頭到該秒、0 等待），不要為了「看一眼對不對」就渲染；要產檔再渲。審查階段可 `--scale=0.5` 快渲、最後才全解析度跑一次。
  - 仍先 `still` 抽幀驗關鍵時刻。場景之間切點要乾淨（無跨場景動畫），concat 才不破。
  - ⛔ **渲染進行中絕對不要動素材。** Remotion 是從 `http://localhost:3000/public/...` 逐幀抓音檔的，
    你在另一條線 `rm` 掉一支 mp3 去重抽，正在渲那一句的場景會拿到 **404 直接中止**（EP02 的 s08 就這樣掛掉、
    連帶 s09–s14 全部沒渲成）。**素材（音檔／cues／manifest）定案之後才開渲；渲染中只能讀不能寫。**
  - ⚠️ **重錄/換某場景旁白 wav 時，務必同步更新 `remotion/public/voiceover/`**（`staticFile` 讀 public，不是 `episodes/*/voiceover/`）。只改 episodes 而忘了 public → render 讀到舊音，會出現「畫面對、但旁白在舊長度之後變靜音（-inf）」。重渲前先 `ffprobe` 比對 public 那支 wav 的長度是否＝最新版。

## 三個必守的抖動鐵則（vid-art-director 把關）
1. **CJK 標點逐幀抖** → 根容器 `textSpacingTrim:"space-all"` + `fontKerning:"none"`。
2. **進場微飄** → 別用過阻尼 spring；用 14 幀 clamp 的 interpolate、位移取整數、settle 後拿掉 transform。
3. **字幕換句跳** → 固定下三分之一、底部錨定、長句標點切短段。
- QC：相鄰幀 `ffmpeg ...blend=all_mode=difference,eq=contrast=20`；同幀對自己須全黑。不遮擋：標題/字幕不被內容蓋。

## BGM（vid-music）— `python3 tools/generate_bgm.py --preset intro|body`
- MiniMax `music-2.6` + `is_instrumental:true`。接長 `ffmpeg -stream_loop -1 -t <秒>`。
- **⚠️ `music-2.6` 有超過一半的機率無視 prompt 裡的 `no drums no percussion`**
  （EP02 實測 7 支退 4 支、EP05 實測 6 支退 3 支——**是常態不是偶發**）。
  沒有自動 QC 的話，鼓點會直接混進成片、沒有任何人會發現。**每支新素材都要過 `tools/bgm_qc.py` 三關才留用**：
  ① **鼓點** 高頻帶（>2kHz）起音的週期性自相關：乾淨床樂 r≈0.28，有鼓 0.71~0.85 → 退線 0.60。
  ② **床樂密度** 低於「95 百分位幀電平」20 dB 的時間占比 → 退線 **22%**（真素材實測 2–15%）。
  ③ **長度** < 78 s 直接退（門檻推導見下）。
- **⚠️ 關卡②在 EP05 之前是壞的，而且壞的方向是「放行最爛的素材」。**
  舊版寫「低於**自身中位數** 10 dB 的占比 >20% 就退」。參考點是檔案自己的中位數，
  所以**靜音一旦過半，中位數就塌進靜音地板**，讀數變 0.0%——素材越爛分數越漂亮：
  ```
  duty(有聲比例)  1.00   0.90   0.70   0.60   0.50   0.40   0.30
  舊(中位數)      6.0%  14.7%  32.3%  41.2%  48.4%   0.0%   0.0%   ← 非單調，0.40/0.30 誤放行
  新(95 百分位)   9.1%  17.5%  34.2%  43.3%  52.2%  61.1%  70.4%   ← 全程單調
  ```
  **改門檻時尺換了刻度就要跟著換**：22% 是拿「必須 PASS 的真素材最高值（seed_h 15.1%）」與
  「必須 REJECT 的最低值（seed_r 28.6%）」取中點重新校準的，不是沿用舊版的 20%。
  校準後在 13 支真素材上判定與舊版**逐支一致**——修的只有盲區，不動既有結論。
- **⚠️ 素材長度門檻要從 `build_bgm_montage.py` 的排程器推導，不要憑 SEG_MAX 猜。**
  `Source.cap = int(min(SEG_MAX, dur - 30))`，而 `make_schedule` 跑 `rng.integers(SEG_MIN, cap+1)`：
  - `cap ≥ SEG_MIN(48)` ⇒ **dur ≥ 78 s**，低於此排程器根本用不了 → 硬退。
  - `cap ≥ SEG_MAX(82)` ⇒ **dur ≥ 112 s**，低於此切不出最長片段 → 只警告不退
    （EP02–04 的 seed_b 90 s 就卡在這區間：cap 僅 60 s、起點區間僅 28 s，EP04 因此逼出近乎重複的取用）。
  「SEG_MAX 82 + 2×GUARD = 84」是**錯的**常見誤推（只看 GUARD、漏掉 `dur-30` 那個 cap）。
- **⚠️ 用 gate 之前先證明 gate 是活的——這是「gate 會說謊」的第八例。**
  兩件事都要做，缺一不可：
  1. **陽性對照**：合成一個一定該被退的素材（疊打點、挖成零星音符），確認真的 `exit 1`。
  2. **證明注入真的發生**：EP04 用 ffmpeg `volume=...:eval=frame` 疊打點，衰減被量化成 23 ms 階梯、
     峰值掉 20 dB，等於什麼都沒加——「加了 X 之後指標沒動」會被讀成「素材乾淨」，結論剛好相反。
     用 null-test（乾淨版與注入版走同一條編碼路徑、解碼相減，殘差 RMS 要≈注入訊號）證明它進去了。
  3. **掃一條階梯而不是只測一個點**：單點看不出非單調。關卡②的缺陷正是靠 duty 掃描才現形——
     它在 0.50–0.70 完全正常，只在最嚴重的那一端崩掉。
  ⚠️ 鼓點階梯的「判退線對應多大聲的打點」**與合成配方綁定**：EP04（8 ms 無尾巴）0.60 線在 k≈1.3，
  EP05（8 ms + 60 ms 衰減尾）在 k≈1.09。**換配方要重跑自己的階梯，不同報告的校準表不可並排比較。**
  兩次都證實的共同盲區：k≲0.5（埋在床樂 RMS 之下）抓不到——那個強度在 0.15 音量 ＋ ducking 後
  也聽不見，可以接受，但**不能宣稱「這關能抓到所有鼓」**。
- **⚠️ BGM 素材是全 pipeline 唯一「不可重生」的產物，但 `.gitignore` 把它當可重生的媒體排除掉了。**
  配音（內容雜湊）與成片（Remotion）都能重跑重建，**但 MiniMax `music_generation` 沒有 seed 參數**——
  同一條 prompt 再跑一次得到的是完全不同的音樂。而 `*.mp3` ＋ `episodes/*/render/` 都在 ignore 裡，
  所以素材池是**單一副本、刪掉就永久消失、git 救不回來**，報告裡的「重建指令」也跟著失效。
  素材要嘛 `git add -f` 納管、要嘛放進不被 ignore 的常設素材庫。（`bgm-qc.md` 同理，歷來都是 `-f` 進去的。）
- **⚠️ 集長超過 ~12 分鐘就不要用 `-stream_loop` 接長單一樂段。**
  循環可偵測度會隨圈數暴增，而且會露出諧波階梯——那是「同一段一直繞」的數學指紋，觀眾說不出哪裡怪但會疲勞。
  EP02 實測（100 秒樂段）：循環 4 次 r=0.743、只露 2 階；循環 16 次 r=0.938、露 5 階以上且階階都強。
  正解：**產 3–4 段不同素材，切成長度不一的片段（各 48–82s）交錯排列，6 秒等功率交叉淡接**，
  每個素材出現次數相近但**間隔不固定**（耳朵抓不到預期點）。EP02 這樣做完 r=0.189、無諧波階梯。
  最後套一道 20 秒尺度的緩慢增益修正，讓接縫不留 dB 台階。
  ⚠️ 保留一段前集用過的素材（EP02 留了 EP01 那支）可以維持系列聽感連續性。
- **試聽片段要抓「最差的接縫」，不是隨便一段**：把所有交叉淡接依「頻譜差 + 電平落差」排名，
  取最差那處前後各 15 秒給作者聽。聽不出來就等於整條都穩——而且試聽是原始音量，
  實際上片還要再吃 `body_volume` 0.15 + sidechain ducking（約再壓 16 dB）。
- **BGM 長度＝本體長度，不含乾聲前言**。別拿 manifest 的 `total`（含前言）去算。
  EP01 佐證：出貨的 `bgm_body_403.mp3` = 403.008s = `body_nobgm.mp4`，而 total 是 427.63s。

## 組裝（確定性）

**🚪 組裝前必跑 `python3 tools/check_staleness.py --ep N`（exit 1 就不要組）。**
組裝完再跑一次 `--assembled` 驗收。EP01 踩了三次同一個坑：mp4 看起來新、幀數也對，
但它比 `scenes01.tsx` 舊，或比其他場景舊（另一個 agent 在你組裝後又重渲了兩支），
**成片默默混著兩個版本、不會報錯**。兩次把過期成片交給作者看，都是這樣來的。
- 該工具用檔案級 mtime，`scenes01.tsx` 一改會讓 8 個場景全部看起來過期（假陽性）。
  它是保守的擋門員，不是重渲範圍的精算器。要精算得看 `git diff -U0` 的行號落在哪個 `Scene` 範圍——
  **前提是每個場景改完就 commit**，否則中間版本無跡可循，只能全部重渲。

三段 concat：前言(乾聲) + 片頭(intro.mp4 或渲染的 Intro) + 本體(輕 BGM ducking)。
- **片頭長度取視訊串流的幀數，不要取容器 duration**：容器可能因尾巴掛靜音音軌而較長
  （EP01 是 4.500s 畫面 vs 4.544s 容器）。信容器會讓整條字幕系統性偏 44ms。
  組裝時取 `intro.mp4` 的**視訊軌**配 `intro_bgm.mp3`，那條靜音軌本來就用不到。
- 三段拼完量一次各段 LUFS，確認沒有 3 dB 台階（mono→stereo 升混路徑不同會產生）。
- 本體 ducking：`[0:a]asplit=2[nar][key];[1:a]volume={body_volume}[bg];[bg][key]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[bgd];[nar][bgd]amix=inputs=2:normalize=0:duration=first[a]`
- 三段同 codec/fps/音訊參數，concat demuxer `-c copy`。
- **配合逐場景輸出**：前言＝`scenes/s00.mp4` 直接用（乾聲）、本體＝`concat(s01..sNN)` 再混 BGM ducking，不必再從整片切「前言/本體分界 startF」（分界天然落在場景檔邊界）。改某場景只重渲該 `sNN.mp4`→重 concat 本體→重混 BGM→三段重組，整片只在交付前需要時跑。

## 多 agent 並行（EP01 定案，代價很貴的一課）

同一個系列資料夾常有多條線同時在寫（編劇/動畫/美術/BGM，甚至多個 Claude session）。三條鐵則：

1. **只 `git add` 自己動過的路徑，絕不 `git add -A`。** 後者會把別人正在做、還沒 commit 的在製品
   一起掃進你的 commit，訊息與內容對不上。EP01 有個「只寫了 BGM」的 commit 實際包含 18 個檔案。
2. **「沒有動作」不等於「已經死亡」。** 用檔案時間戳判斷 agent 存活會誤判——它可能正在跑長渲染。
   要接手別人的工作範圍前**先發訊息問它**。EP01 誤判一個停了 1 小時 45 分的動畫師已死、派了第二個，
   結果兩條線改同一批檔案、互相覆蓋渲染產物，還製造出「mp4 與原始碼不同調」這種本來不存在的問題。
3. **審查者不要改被審者的原始碼。** 美術指導直接改 `scenes01.tsx` 並重渲覆蓋動畫師的產出，
   它自己報告裡的「不同調」正是這個動作造成的。**退件要具體到檔案與行號，修改由原作者做。**
4. **審查結論一定要落地成檔案，不能只存在 agent 的 context 裡。**
   EP02 的動畫師渲完 15 支場景、自審找出 4 個 must-fix，還沒套用就撞到 API 用量上限被中斷，
   **transcript 沒留下來，那份清單直接消失**——產物在磁碟上、commit 在 git 裡，但「我知道哪裡有問題」
   是整條 pipeline 最脆弱的資產。凡是「已發現但未修復」的清單，一律當場寫成
   `episodes/epNN/render/art-review.md` 這類檔案。重跑一次審查比回憶便宜，但前提是你知道要重跑。

## 改腳本的連鎖代價（配音後才改，成本差一個量級）

腳本一改，下游全部失效，而且**沒有任何機制會自動告訴你**：

    腳本 → 配音(API 費用) → cues(whisper 對齊) → SCENES01 切點 → 場景重新對時(人工判斷) → 8 支重渲(20 分) → 重組

- **`SCENES01` 的切點必須依 manifest 重算**（每個場景 from = 該場景第一句的 `startF`），不是寫死的常數。
- **場景長度會變** → `scenes01.tsx` 裡每個 `at={}` 都是對著舊旁白節奏寫的，必須逐一重新錨定到新的 cue onset。
  EP01 改一輪後 s03 多 4.5 秒、s02 少 3.3 秒，不重新對時的話畫面會在旁白講完後才動。
- 所以**腳本關要卡在配音之前**，那是唯一改動成本趨近於零的時刻。

## 上架（vid-seo + 發布）
- metadata：標題(關鍵字前置≤100)、描述(hook→摘要→章節→出處連結→授權)、tags、章節(本體時間=原始+片頭長度)、縮圖、置頂留言。
- 合規：描述含來源連結與授權(series.yaml license/attribution/source_url)，commercial:false → 不開營利。
- 上傳用共用工具 `~/.claude/series-studio/youtube/upload.py`（OAuth creds 同夾、已快取，全系列共用）：`--file --metadata --privacy` → `--thumb` → `--comment`（API 不能置頂，提醒手動）。

## 完工回灌
每集做完：把發音/斷句修正回灌 `tw_lexicon.json`/`voice-style.md`；更新 `series-context.md`（本集講了什麼、術語、下集預告、可回呼點）。
- **框架自身也要回灌**：本檔（CONVENTIONS.md）、`~/.claude/agents/*.md`（含 colon-and-code / ai-storyteller 兩個主理人）、skills（new-series / produce-episode / auto-produce-next）、`template/` 有任何修改，同步回 series-studio repo（`~/Desktop/Projects/YouTube-Channel/series-studio/claude/…`）並 commit + push。活檔是唯一真相，repo 不同步＝白學。⚠️ 金鑰不進 repo（`.env`、`youtube/token.json`、`client_secret.json`）。
