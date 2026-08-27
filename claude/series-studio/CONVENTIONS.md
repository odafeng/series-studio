# Series Studio — 通用製作慣例（所有系列共用）

> 各 vid-* agent 與 produce-episode 流程都引用本檔。在「系列資料夾」根目錄操作（cwd = 系列根）。
> 系列專屬參數一律從 `./series.yaml` 讀；口吻從 `./voice-style.md`；上下集 context 從 `./series-context.md`。

## 集長：⛔ 沒有目標長度這種事——內容有多少就做多長

**作者 2026-08-09 重申（不只講過一次）：不要設 `target_min`、不要開目標字數。**
素材撐得住十分鐘就十分鐘，撐得住二十五分鐘就二十五分鐘。
為了湊長度而稀釋、或為了壓進某個數字而砍掉機制，兩種都是把片子做壞——
而**後者更常發生也更難察覺**，因為砍掉的東西不會出現在成片裡供人檢查。

編劇的長度依據只有一個：**這份素材有多少值得講的機制**。紅線「砍修辭不砍機制」就是它的操作定義。

### 字/秒換算率的正當用途（只有這些）
換算率是**寫完之後**的預估工具，不是寫之前的配額：
- 排 BGM 長度（本體秒數）、算章節時間戳、估渲染時間
- 交稿時對照「素材純 CJK ：旁白字」的濃縮比，看有沒有異常灌水或過度壓縮

**⚠️ 換算率是每個系列自己的數字，不是通用常數。**
本檔原本寫的 5.97 來自某一個系列；ml-for-drs 三集實測（旁白純 CJK ÷ 成片扣掉片頭的秒數）
是 **5.14 / 5.17 / 5.19，真值 5.15**，低 16%。
**新系列第一集出貨後，用 `旁白純 CJK ÷ (成片秒數 − 片頭秒數)` 回算並寫進自己的 `series.yaml`。**
`build_script_editor.py` 的 `BASE_CPS`（speed 1.0 基準 ≈ 5.19）同理，顯示值僅供參考。

歷史事故（都是「拿數字當配額」造成的，留著當警惕）：
- 某系列 EP01 用猜的 3.7 字/秒（＝11 分鐘要 2400 字），**誤差 61%**，編劇照著錯的上限
  把稿子從 3301 字砍到 2500，**砍掉的都是真材料**。錯誤的常數不會報錯，只會讓所有下游決策偏一點。
- ml-for-drs 的 `series.yaml` 照抄 5.97，`target_min: 12` 開出 4298 字配額（實際換算只該 3708）。
  編劇交稿時自己發現對不上、把三個算法都標出來，才沒有照著錯的上限寫。
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
- 設定驅動（讀 `series.yaml voice`）。MiniMax 模型以 `voice.model` 為唯一真相；新系列／新一集目前優先 `speech-2.8-hd`，`--model` 只供 A/B 或一次性覆寫。逐句合成、內容雜湊命名 → 冪等；hash 必須包含 **model、voice/audio settings、實際送 TTS 的文字、詞庫命中與 `tts_replacements`**，避免換模型仍誤吃舊 cache。
- `voice.tts_replacements` 是**語音／字幕分離**：只替換送進 MiniMax 的文字，不改 script、`epNNData.ts` 或字幕。用於 `RL → R L`、`DeepSeek-R1-Zero → Deep Seek, R One, Zero` 這類英文術語黏讀；不要為了發音污染觀眾看到的文案。
- **純音檔 QC 迴圈**：concat 旁白成 mp3 給使用者聽、先鎖發音再渲染影片。QuickTime 重開要先 `quit` 再 `open`（同路徑不自動 reload）。
- 讀錯字 → 加 `voiceover/tw_lexicon.json`（`詞:"(pin1)(yin1)"`，輕聲用 `(le5)`；別加單字詞條）。頑固破音字（如「當機」）→ 直接換詞。
- **⚠️ pronunciation_dict 會干擾斷句，能不加就不加（2026-06 EP6 定案）**：送 MiniMax 的 `pronunciation_dict` 不只可能無效，還會**把同句其他詞的斷句搞壞**（EP6 替「移植」加 dict→移植仍唸錯、還連帶把「影響」斷壞；移除 dict 後移植本來就唸對 yi2、斷句也順）。**加任何詞庫條目前先確認「不加 dict 時本來就唸錯」**——很多詞（如「移植」，移無他讀）MiniMax 預設就對，加了反而害事。每個新條目都要：①真的會唸錯才加 ②用 clip 給使用者耳朵確認「加了真的修好、且沒弄壞別處」，沒確認別留。
- 斷句怪／詞被切開 → 先重抽 take；**重抽解不掉就外科手術，最後才改腳本**。
  EP02 的「視野」被唸成「視｜野」是**系統性**的（前面是「工程，」，MiniMax 固定在逗號後起音、
  再於「視」之後換氣），**連抽 27 次只有 1 次乾淨**。這種靠重抽是浪費 API 費用。
  外科手術做法：用 forced-align 定出詞內靜音的精確區間（EP02 是 1.579–1.921s），
  `atrim`＋`concat` 把它剪掉、**只留 60ms 自然銜接**，再 `apad` 補回原長度。
  結果乾淨、腳本不動、時間軸不動。判準：**重抽 ≥10 次仍不乾淨就別再抽了**。
- **🚪 斷句 QC（render 前必做；2026-08 EP08 更新）**：MiniMax 仍可能把詞中插微停頓（上下文→「上｜下文」）。主判官用字級 forced align：
  `voiceover/.venv-phrasing/bin/python voiceover/forced_align_phrasing.py --ep N`
  長集可分批加 `--cue-start A --cue-end B`，但最後必須覆蓋所有 cue。CLI 契約：**exit 0＝乾淨、exit 1＝找到缺陷、exit 2＝aligner crash／對齊錯誤**；exit 2 絕不能當乾淨，要重跑該 cue 或人工查因。
  - 自動修正順序：`retake_until_clean.py` fresh take → `pick_best_take.py` best-of-N（每輪先保留最佳候選）→ 重抽十次以上仍系統性失敗，才用 `surgical_phrasing_fix.py` 剪詞內靜音。修後重跑 `build_voice.py` re-probe／重排 onset，再跑 forced-align 到全片 exit 0。
  - ⚠️ `retake_until_clean.py` 跟 `build_subtitle_cues.py` 都要用 **`voiceover/.venv-phrasing/bin/python`** 跑
    （前者 import `phrasing_score` → `jieba`，後者要 `faster_whisper`）；系統 `python3` 會 ModuleNotFoundError。
  - **🕐 重抽最便宜的時刻是「`scenesNN.tsx` 還不存在」的時候。** 那時沒有任何寫死的 `at={}` 或 `SCENES` 切點，
    重跑 builder 就重算了全部 `startF`，**完全不需要做秒數正規化**。等動畫開工後才重抽，
    就要付下面那四個步驟（快照舊秒數 → 保留最佳候選 → `apad`／`atempo` 正規化 → 重跑 builder 驗歸零）的代價。
    所以斷句 QC 要在動畫開工前跑到全片乾淨，不要拖。
  - `verify_phrasing.py` 可保留作逐句輔助；舊 `phrasing_gate.py` 用 whisper 內插字級時間，±1 字漂移會大量誤報，不作 release gate。
  - **中英文混合術語另做 English QC**：forced align 可能因 tokenizer 對 `DeepSeek-R1-Zero`、`On-Policy Distillation` 顯示 MISS。用 medium 級轉錄 zoom 或耳朵核對實際發音，不能只看 MISS 就亂剪。
  - audio 改動會改 cue duration／後續 onset。旁白全片、manifest hash/audio、英文術語與純音檔使用者 QC 都鎖定後，才產 subtitle cues 與開始 render。
- **改讀音會不會自動重配，取決於你用哪支合成器——先去讀那支的 hash 怎麼算，不要照抄本條**：
  - `build_storyteller.py`：hash **只含文字**，改詞庫後含該詞的句子**不會**重抽 → 要 `rm` 該 mp3 強制重配。
  - `build_voice.py`（ai-agent-eli5 等）：hash 含 model、實際 audio text、voice/audio settings、`lex_entries(text)` 與 `tts_replacements` → 任一合成輸入改變都會自動重抽該句，不必手動 `rm`。
  EP02 一開始照本條的舊敘述以為要手動 `rm`，讀了原始碼才發現這支不用。**文件會跟程式碼脫節，hash 的定義在程式碼裡。**
- 且 MiniMax **不一定吃** `詞/(pin1)(yin1)` 詞庫格式（EP6「移植」設 yi2 仍唸 yi4）；頑固者改測別的格式或**直接換詞**，並用 clip 給使用者耳朵確認。
- 🔴 **2026-08-03 EP07 實證：`pronunciation_dict` 對 MiniMax 這個聲音是死的，不是「常常無效」。**
  A/B 探針（`voiceover/ab_dict_probe.py`：同句同參數，A 臂送 dict、B 臂清空詞庫，各 4 take，
  且先印出 A 臂實際送出的 `pronunciation_dict.tone` 以排除「根本沒注入」）：
  `好處` 詞庫指定 `(hao3)`＝三聲，**A 臂 4/4 個 take 全唸四聲**；`長得` 指定 `(zhang3)` 同樣無效。
  旁證：詞庫裡 `更新` 的值 `(geng4)` 本身是錯的（正確 gēng），而 MiniMax **自己唸對**——
  值錯了卻沒有錯到，代表那個值從頭到尾沒被讀進去。
  ⚠️ **上面 L70 原本寫的「成功案例：EP02 彈性加 dict 一次就修好」已作廢**：
  `build_voice.py` 的 hash 含 `lex_entries(text)`（見上一條），**改詞庫必然觸發重抽**——
  「加詞庫」與「換 take」這兩個變因從來沒有分開過，很可能是重抽的效果被記成了詞庫的效果。
  舊結論「讀音錯用詞庫、斷句錯用重抽」**同時被推翻**。
- **所以讀音錯只有兩條路：① 改寫腳本繞掉（最可靠）② 重抽。**
  既有的 194 條詞庫**不要刪**（hash 含詞庫，刪了會觸發全集無意義重抽），但也不要再新增。
- **轉錄查不出聲調錯誤**（EP07 實證）：`長得` 實際唸 cháng de，寬窗 whisper 照樣輸出「長得」——
  語言模型先驗會把字補對。破音字要判對錯得下到聲學層：
  `voiceover/minimal_pair.py`（**同句只換一個讀音唯一的參照字**，如 `著`→`住`，比 F0 分群）是決定性的；
  `voiceover/tone_probe.py`（純 F0，5-fold CV 僅 62.5%）只能當輔助，不足以單點定罪。
  ⚠️ `pypinyin` 只能當候選產生器，不能當應讀音來源（它把 EP07 的 27 處 `長` 全判 zhǎng、8 處 `調` 全判 diào）。
- **破音字要全片掃，不能靠手挑清單。** EP07 註記手挑了 8 個破音字、全部驗過全部正確，
  但 `長`／`好`／`調`／`著` 不在清單上 → 完全沒有 gate 在看，最後是作者用耳朵在 41 分鐘裡撈出 16 處。
  掃描結果要寫成表進該集製作註記，並把落單的破音詞加進 `voice-style.md` 的破音字表（＝ lint 規則來源）。
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
- `build_subtitle_cues.py --ep N`（whisper 每段 wav → srt → `voiceover/cues/epNN_cues.json`，`fromF/toF`＝真實語音時間、依語音停頓自然斷句）。字幕進出時間**一律取自此 cues，嚴禁用字數比例估算**（會「聲音比字幕快／字幕飄」）。有 `_short` 剪輯版的場景自動採用其 srt。
  - **⚠️ 本條原本寫「cues 的 `text` 是 whisper 轉錄（base 有同音/技術詞錯），要對照【旁白】校正後再上字幕」——那已經過時了。**
    現在的工具是**用腳本原文當文字、只拿 whisper 的停頓當切分依據**，不存在轉錄錯誤。
    ml-for-drs EP03 有 38 個英文詞（`stochastic gradient descent`、`class imbalance`、`confusion matrix`、
    `type 1 error`…），照舊敘述應該慘不忍睹，實際逐句檢查**零錯誤**。
    又一次「文件跟程式碼脫節」——只是這次脫節的方向是文件低估了工具。**看到可疑的敘述先去讀程式碼。**
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

## 畫面／旁白時間軸對不上（現有 gate 全部抓不到，ml-for-drs EP03 定案）

`check_swap_overlap.py` 看的是兩層內容的**顯示區間交集**、`check_content_band.py` 看的是**有沒有墨**，
OCR 看的是成片上**讀得到的字**。以下兩類缺陷三者都抓不到，因為畫面本身完全合法：

1. **指涉物早退**：旁白說「從這四個數字，可以算出兩個核心指標」時，那四個數字已經淡出了（`hideAt` 早於該句）。
2. **術語搶跑**：註解帶已經寫著「precision 看的是…」，但旁白還在講上一句，**兩行文字同時說不同的事**（早 2.7 秒）。

只有把**畫面時間軸跟旁白 cue 時間軸並排逐幀對**才會現形。兩個實務心得：
- **修一個就順手掃同一幀的其他層**：EP03 的第二個缺陷正是在驗證第一個的修正時發現的，比重新掃全片便宜太多。
- **⚠️ 自己寫的掃描判準一定要做陽性對照。** EP03 動畫師第一版判準跑出「命中 0」，
  拿兩個已知缺陷修正**前**的數值餵回去——**都沒命中**（一個消失點落在句子結尾而非中間、一個只比句子起點晚 4 幀）。
  判準是死的，那個 0 毫無意義。換成能通過陽性對照的判準重做，才得到有意義的結果。
  同一次還差點被另一個假象騙：內容帶掃描拿 y=600 當對照掃出 0，一度以為工具瞎了，
  其實那裡本來就空白；改用真的有墨的位置重測才確認掃描器是活的。

## 素材不是免驗證的真相來源（ml-for-drs EP04 定案）

編劇忠實照抄素材、事實查核照樣抓到方向講反的機制——**因為那句素材本身就是錯的**
（EP04：「懲罰不成比例打在尺度大的特徵上」，實際相反）。忠實度不等於正確性，
**照抄會把錯誤從素材放大到影片**。查核員的職責包含「素材說得對不對」，不只是「腳本有沒有忠於素材」。
修的時候三處都要修：腳本、素材、以及素材的上游（EP04 的錯同時存在於 PWA `hands-on-ml-eli5` ch04，
一併勘誤重新部署）。另外編劇自查時在**測驗解答**裡找到同一句錯誤——查核清單漏列的地方，
交稿者自己掃一遍同義句往往還能再撈到。

## 量測前先確認「被量的東西」符合假設（ml-for-drs EP04）

CONVENTIONS 已經有「gate 要先過陽性對照」（證明工具會叫），EP04 補上對稱的另一半：
**取樣點本身也要驗證符合假設**。

抖動掃描在「靜態幀」量相鄰幀 diff，EP04 有兩個場景初測 0.073 / 0.037，
**其中一個是動態對照的三倍**，diff 又落在內容帶而非字幕帶，看起來就是真抖動。
往前後各掃 10 幀看 diff 輪廓才發現：那兩幀正好是**元件進場的第一幀**
（s02 f1490–1499 只有 ~1e-5，f1499→1500 跳到 0.121、升到 0.215，f1510 後回落 ~0.011）。
改用真正靜止的幀重測後全片 ≈0。**沒做這一步，就會有人去改根本沒壞的動畫。**

判準：靜態幀選點要往前後掃一段確認輪廓平坦；工具會叫（陽性對照）＋樣本符合假設（輪廓檢查），
兩件事都做完，那個數字才有意義。

## Agent 死亡與通知丟失：磁碟狀態才是真相（ml-for-drs EP04）

同一集踩到兩種「看起來在跑，其實沒有」：

1. **subagent 等背景通知而通知丟失**：配音 agent 三次卡在「等待完成通知」，
   而合成的 207 個 mp3、concat 純音檔、whisper 轉錄**早就寫在磁碟上了**，
   最久一次空等 80 分鐘。orchestrator 查檔案後把實際狀態餵回去叫醒即可。
2. **agent 因用量上限死亡，背景 shell 跟著消失，只留孤兒 chrome 進程**：
   `pgrep chrome-headless-shell` 有東西、看起來還在渲，但產物 mtime 停在 4.5 小時前。
   **判斷存活一律看產物 mtime，不要看 process 存在**（`ps` 只證明有東西沒被回收）。
   orchestrator 直接接手：`npx remotion render src/index.ts EpNN out/sNN.mp4 --frames=A-B`，
   幀範圍從 `EpisodeNN.tsx` 的 `<Sequence from=>` 讀。

配套：orchestrator 等長工時用「無 process **且** N 分鐘無檔案寫入」雙訊號判 idle，
單看 process 會在短命探針之間誤報 idle（EP04 誤報過一次）。

## 三個必守的抖動鐵則（vid-art-director 把關）
1. **CJK 標點逐幀抖** → 根容器 `textSpacingTrim:"space-all"` + `fontKerning:"none"`。
2. **進場微飄** → 別用過阻尼 spring；用 14 幀 clamp 的 interpolate、位移取整數、settle 後拿掉 transform。
3. **字幕換句跳** → 固定下三分之一、底部錨定、長句標點切短段。
- QC：相鄰幀 `ffmpeg ...blend=all_mode=difference,eq=contrast=20`；同幀對自己須全黑。不遮擋：標題/字幕不被內容蓋。

## BGM（vid-music）— `python3 tools/generate_bgm.py --preset intro|body`
- 🔴 **2026-08-22：MiniMax 雲端 `music_generation` API 已對新用戶關閉，這條路死了。**
  所有 model（`music-2.6` / `music-1.5` / `music-01` / `music-3`）一律 `HTTP 410`、
  `status_code 2153`：「no longer available to new users」。本專案兩把金鑰都試過，
  含 `MINIMAX_PAY_KEY`——**換付費金鑰不會繞過**。`/v1/audio_generation` 是 404，不存在。
- **現行後端：本機跑 MiniMax Music 3 開源權重**（`tools/music3.py`）。
  官方就是在 2153 的錯誤訊息裡指向 `MiniMaxAI/MiniMax-Music3` 的。
  用社群量化的 `mlx-community/MiniMax-Music3-4bit`（9.2 GB），Apple Silicon 上 `mlx-audio` 推論。
  實測 M4 Pro / 24 GB：30 秒素材約 4 分鐘（含載入模型）、130 秒約 15 分鐘，離線、零費用。
  安裝一次即可，步驟見 `tools/music3.py` 的 docstring。
- **Music 3 吃的是 Structured Caption，不是一行 tag 串。** 三段式：Global Metadata /
  Vocal Details / Arrangement。餵一行 prompt 它會自由發揮（自己加鼓、自己開始唱）。
  `structured_caption()` 會把 series.yaml 既有的一行式 prompt 包成骨架，所以舊設定檔不用改；
  要完整控制就直接把三段式整段寫進 `series.yaml` 的 `bgm.*_prompt`。
- **純樂器靠 lyrics 而不是旗標**：Music 3 沒有 `is_instrumental`。做法是 lyrics 只給
  `[intro]/[instrumental]/[outro]` 段落標籤、一個字都不給。有字它就會唱。
- 接長 `ffmpeg -stream_loop -1 -t <秒>`。
- **⚠️ 生成模型有超過一半的機率無視 prompt 裡的 `no drums no percussion`**
  （EP02 實測 7 支退 4 支、EP05 實測 6 支退 3 支——**是常態不是偶發**）。
  沒有自動 QC 的話，鼓點會直接混進成片、沒有任何人會發現。**每支新素材都要過 `tools/bgm_qc.py` 三關才留用**：
  ① **鼓點** 高頻帶（>2kHz）起音的週期性自相關：乾淨床樂 r≈0.28，有鼓 0.71~0.85 → 退線 0.60。
  ② **床樂密度** 低於「95 百分位幀電平」20 dB 的時間占比 → 退線 **22%**（真素材實測 2–15%）。
  ③ **長度** < 78 s 直接退（門檻推導見下）。
  ④ **可辨識人聲** 用 `voiceover/.venv-phrasing/bin/python tools/bgm_qc.py --vocal <files>` 跑
     faster-whisper；任何高信心語音片段都判退。`is_instrumental:true` 只是生成要求，不是 QC 證據。
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
- **✅ BGM 現在可重生了（2026-08-22 換本機後端之後）。** 舊 MiniMax API 沒有 seed 參數，
  同一條 prompt 再跑一次得到完全不同的音樂，所以 BGM 一度是全 pipeline 唯一「不可重生」的產物。
  Music 3 有 `--seed`：`(caption, lyrics, duration, steps, seed)` 五個值決定輸出，
  `music3.generate()` 會把它們寫成 `<素材>.json` sidecar。**重生靠的是那個 sidecar，不是音檔本身。**
  → `*.mp3` 仍在 `.gitignore` 裡，但 **`*.mp3.json` 必須進版控**（`git add -f`），
  否則 seed 一丟就退回舊世界。`bgm-qc.md` 同理，歷來都是 `-f` 進去的。
  素材本身要不要一起 `git add -f`：現在只是省 15 分鐘 GPU，不再是「刪掉就永久消失」。
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

**⚙️ 這一整節已經寫成 `tools/assemble.py`（ml-for-drs EP03 起）**，含過期檢查、逐項量測與幀數對帳。
新系列直接複製那支，不要再手打 ffmpeg——下面每一條都是它固定下來的判斷。

- **⚠️ 片頭要對齊系列音量，直接 mux 會太大聲。** `intro_bgm.mp3` 整體 −18.0 LUFS，但成片只取**前 4.5 秒的起音段**，
  比整支平均大聲。ml-for-drs EP01/EP02 出貨時片頭都是 **−19.6 LUFS**（比前後兩段高 2.0–2.3 dB），
  EP03 未校正時是 **−17.5**（高 4.3 dB）——連看三集會聽到那一集片頭特別吵。
  `assemble.py` 的做法是先 mux 一支探針、量 LUFS、算差值套 `volume=±X dB` 再正式產出，
  目標值可用 `series.yaml` 的 `bgm.intro_target_lufs` 覆寫。
  ⚠️ 診斷這種問題時**要拿已出貨且作者接受的集數當基準**，而且要抓對片頭位置——
  各集 s00 長度不同（EP1 片頭在 37.03s、EP2 在 58.80s、EP3 在 45.77s），用固定時間點量會量到別的段落。
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
4. **⚠️ 等待迴圈用 `grep -q <完成字串>` 判完成時，先確認那個字串不是 append 進舊 log。**
   ml-for-drs EP03 的動畫師用 `grep -q ALL_SCENES_DONE` 等批次，但上一批已經寫過那行到同一個 log，
   迴圈立刻返回、它對**舊的** s03.mp4 抽了幀，差點回報錯的驗證結論。同一個 log 重複使用時要看出現次數或 mtime。
   同理，`Bash` 背景任務回報的 exit code 是**整條命令**的，不是你關心的那支工具的——
   `cmd | grep -v ...` 之後 `$?` 是 grep 的。**看工具自己印出來的結論，不要看 wrapper。**
5. **審查結論一定要落地成檔案，不能只存在 agent 的 context 裡。**
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

## 片頭位置：前言一長，片頭就被推到沒人看得到的地方（ml-for-drs EP06 定案）

`assemble.py` 原本一律把片頭插在**前言結束處**。歷集前言 37–59 秒，片頭出現得夠早；
ml-for-drs EP06 的 s00 被作者改稿加長到 **136 秒**，片頭就落在 **2:16**——
前兩分鐘沒有任何品牌識別，作者第一句話是「這集你沒有組片頭進去」。

- **`assemble.py --intro-at FRAME`** 把片頭插進前言**內部**。**前言超過約 70 秒就該用。**
- 插入點挑「鉤子剛落地、正要點題」那一刻（EP06 用 frame 1617＝0:53.90，
  猜牛講完、正要說「這件事有個名字叫集成學習」）。
- 總長、章節時間戳、場景切點都不受影響；**只有 SRT 的 `--split` 要跟著改**
  （EP06 從 4089 改成 1617），否則字幕會從錯誤的位置開始位移。

### 🔴 切割前言必須對齊 video timescale，否則容器 duration 會爆掉

切點幾乎不可能落在 keyframe 上，所以兩半都要重編碼——而 **libx264 預設寫 1/15360，
Remotion 出的場景與片頭是 1/90000**。`concat` demuxer 用**第一段**的 timebase 去解讀
後面每一段的 PTS，兩者一差，後段時間戳被放大 `90000/15360 = 5.86` 倍：
EP06 首版 24:51 的內容，容器寫成 **2:25:41**。

- 重編碼一律加 **`-video_track_timescale 90000`**（或與場景一致的值）。
- **⚠️ 幀數對帳抓不到這個**：44734 幀從頭到尾都正確，連音訊串流 duration 都正確，
  **只有視訊串流 duration 是錯的**——而那正是播放器與 YouTube 唯一顯示的東西。
- 所以 `assemble.py` 在幀數對帳之後**多加一道容器時長對帳**：
  視訊 duration／音訊 duration／幀數÷fps 三者差超過 1 秒就中止。
  這種錯不該靠人眼在上架後發現（EP06 因此重傳三次）。

## 驗證方法本身會給假結果（ml-for-drs EP06 補記）

CONVENTIONS 已經記過「判準要先過陽性對照」「量測前先確認被量的東西符合假設」。
EP06 又踩到兩個**工具層**的假結果，兩次都差點做出錯誤結論：

1. **`find -newermt` 在該台 macOS 上回空清單。** 據此判斷「45 分鐘零檔案變動」→
   誤判配音 agent 已死，實際上最新音檔是 30 秒前寫的。
   **判斷檔案新舊一律用 `stat -f "%Sm %N" -t "%H:%M:%S"`。**
2. **`ffmpeg -ss` 在重編碼過的檔案上會對到最近的 keyframe。** 用它抽片頭抽到一片空白，
   差點判定「片頭沒插進去」。**精確抽幀用 `select=eq(n\,FRAME)` 配 `-vsync 0`。**

## 空鏡：畫面全白但旁白已經在講話（ml-for-drs EP06 定案，新增第四支 gate）

現有三支 gate 全部看不到這一類。`tools/check_blank_frames.py`（逐幀量內容帶墨量）在 EP06
抓到 **7 段**，其中 s08 開頭整整 **5.6 秒只有 14 px 墨**。

- **為什麼另外三支抓不到**：`check_swap_overlap` 看區間交集，畫面全白時根本沒有交集；
  `check_content_band` 看有沒有墨越線，內容帶空白時那條帶本來就乾淨；抽 still 抽不中 1.5–5 秒的區間。
- **兩種成因**：①場景的第一個內容 `Appear` 錨到第二句 cue ②panel 外層 `Appear` 進場了、
  子元素卻全部藏在更晚的 `at` 後面。
  **「Swap child 的 `at` 很早」不等於畫面上真的有東西。**
- **必須帶命中分級**（EP06 實測校準：<500px 一定是缺陷／~1700px 通常是／>3500px 約一行字、
  逐筆對回旁白再判）。沒有分級，這支會把正常節拍與真缺陷混在同一份清單裡回報。
- **修完一定要重掃**：EP06 第一輪只抓到「場景開頭」那一類，s10 那兩段 1.8 秒全白是
  **修完重渲後第二輪才浮出來的**。第一輪就收工的話那段會直接出貨。

## forced-align 的兩條規則修訂（ml-for-drs EP06）

1. **「range 內 crash、單獨跑乾淨＝批次狀態污染」有例外。** EP04/EP05 定的這條規則在 EP06
   失效：cue 272 **單獨跑也反覆 crash**（SIGABRT／SIGSEGV／`list index out of range`），
   重新合成那一句就好（3/3 通過）。**先二分定位到單一 cue，再決定是音檔問題還是批次問題。**
2. **jieba 假陽性＝中文版的 tokenizer mismatch。** EP06 被標記的 5 個缺陷有 4 個不是缺陷：
   jieba 的 HMM 在 t2s 轉換後的文字上造出不存在的詞（人拿同／法要／藥要／科在），
   每個都把名詞尾字黏到後面的動詞，於是**真正的詞組邊界換氣被判成詞內斷句**。
   與已知的英文術語 MISS 同類，只是發生在中文。

## 素材錯誤的第三種型態：hedge 被改寫成斷言（ml-for-drs EP06）

CONVENTIONS 已記「素材不是免驗證的真相來源」（EP04：機制方向寫反）。EP06 又出兩種新型態：

1. **原書的 hedge 在改寫時被抹掉。** 原書寫 "hope for **up to** 75%"，素材抄成「會逼近 75%」。
   精確二項是 **0.7261**，要 75% 需約 1,236 個成員。
   **凡是引自原書的數字，要回頭確認原文有沒有 up to／about／can／hope 這類限定詞。**
2. **繼承學界流傳百年的錯誤引用。** Galton 猜牛的「中位數 1207／實際 1198／差 9 磅／
   比任何專家準」四項全錯（Wallis, *Statistical Science* 2014, 29(3):420–424，
   arXiv:1410.3989，調 UCL Galton Archive 手稿：1208／1197／11 磅，且有一位參賽者猜中 1197）。
   **這一種特別危險：查證時 Google 出來的全是錯的版本。**
   凡是「廣為流傳的經典故事」，要找有沒有人做過檔案考據，不要只比對二手來源。

## BGM：模擬排名 ≠ 實測排名（ml-for-drs EP06）

選 montage 排程時，**模擬第一名不一定是實測第一名，而且落差不是常數**：
EP06 模擬 10.24 → 實測 12.36（+2.12），模擬第二名 10.78 → 實測 **13.76**（+2.98）。
**前兩名都渲出來實測再定案**，多花四分鐘換掉「相信模擬」這個假設。

另：whisper 的**非語音註記 token**（`Music`／`[Music]`／`♪♪♪`／`（音樂）`／`Applause`）
會被人聲關誤判成人聲。`bgm_qc.py` 已加 `is_nonspeech_annotation()`。
**判斷「是不是真的混進人聲」的決定性證據**：同一批樣本切成不同長度的獨立檔案跑同一支 gate
（內容一個位元沒變，只有容器長度變了）——若兩次都 PASS，命中就是 gate 自己的問題。

## 上架鏈的隱性依賴（ml-for-drs EP06 踩到）

`upload.py` 缺 `google.auth` 時，**系統上可能沒有任何 python 有它**——整條上架鏈是壞的，
而且要到真的要上架那一刻才會發現。ml-for-drs 的根因是 `/opt/anaconda3` 從機器上消失，
同時打壞了 `voiceover/.venv-phrasing`（builder 與 aligner）與 `upload.py`。

- 上傳工具建議自帶 venv：`~/.claude/series-studio/youtube/.venv`（全系列共用）。
- **`upload.py` 沒有切 privacy 的開關，`yt_schedule.py` 只能設 publishAt。**
  要純 private（不排程）用 `tools/yt_set_privacy.py`；刪影片用 `tools/yt_delete_video.py`
  （後者強制傳入一個「絕不能刪」的 id 並在刪除前印出標題與長度供核對）。

## 上架（vid-seo + 發布）
- metadata：標題(**鉤子前置**≤100，見下「觸及與入口」)、描述(hook→摘要→章節→出處連結→授權)、tags、章節(本體時間=原始+片頭長度)、縮圖、置頂留言。
- 合規：描述含來源連結與授權(series.yaml license/attribution/source_url)，commercial:false → 不開營利。
- 上傳用共用工具 `~/.claude/series-studio/youtube/upload.py`（OAuth creds 同夾、已快取，全系列共用）：`--file --metadata --privacy` → `--thumb` → `--comment`（API 不能置頂，提醒手動）。

## 廣告 Short 產線（ml-for-drs 2026-08-19 定案，可複製到其他系列）

系列廣告 Short（垂直 1080×1920、約 30–60s、燒字幕）的一站式流程，固化成一支命令：

```bash
python3 tools/build_short.py          # 配音 → 渲染 → BGM 混音
python3 tools/build_short.py --upload # 上一步全做 + 上傳 unlisted
```

四份檔案各管一件事（要改哪邊改哪邊）：
- `tools/build_short_intro_voice.py`：旁白文案 `NARRATION` 與 `SHORT_TTS`（唸法替換）。
- `remotion/src/ShortIntro.tsx`：畫面與動效（Sequence 硬切 + `Pop` spring 彈跳 + `Float` 微浮動）。
- `brand/shortIntro-metadata.json`：標題／描述／tags。
- `tools/build_short.py`：產線本體（配音 → BGM → 渲染 → 混音 → 上傳）。

**廣告語言（作者 2026-08-19 強調，與正片講課腔完全分開）**：
- 鉤子＝痛點／慾望的日常問句，**不用術語當鉤子**。例：「在 AI 充斥的時代，是不是常常聽不懂大家在聊什麼術語？」「想寫點跟傳統統計不一樣的研究，卻不知道怎麼開始？」
- **不要寫「第一集免費」**——每一集都免費，講「免費」反而不知所云；CTA 直接講行動（「從第一集開始看」）。
- 不要把讀本/PWA 網址當 CTA——作者不公開 PWA，描述裡也不放。

**BGM**：與正片「cold ambient、無鼓」相反，Short 用 **upbeat**（prompt 寫在 `build_short.py` 的 `SHORT_BGM_PROMPT`，後端同樣是本機 Music 3；`gen_bgm()` 會把 `structured_caption()` 的「無鼓」預設**蓋掉**換成 driving groove）；鼓點是**加分不是退件**，正片的 bgm_qc 三關不套用。成品裁到成片長度＋尾段 3.5s 淡出，`volume 0.16` 墊在旁白下（不做 sidechain ducking，短片的輕床樂固定音量即可）。

**轉場**：Sequence 硬切，不用 crossfade（跨疊會雙重曝光）；進場用 `spring` overshoot（悶的元凶是「卡片淡入淡出＋無配樂＋節奏慢」）。

## 觸及與入口（作者 2026-08-03 指示，五條）

> 前提：**內容深度不是問題，槓桿在「開頭 5 秒、標題前 8 個字、縮圖、能不能獨立看懂」。**
> 好故事已經有了，問題是放在觀眾看不到的地方。以下五條對**所有系列**生效。

1. **標題：故事鉤子在前，術語在後。**
   ❌ `上下文工程：多打一句話，帳單差點翻倍｜KV Cache…`
   ✅ `多打一句話，AI 帳單翻倍｜上下文工程 · KV Cache…`
   前 8 個字要是**具體後果或反常識**，不是章節名。術語往後放照樣吃得到 SEO。
   ⚠️ **本條推翻舊規則「標題關鍵字前置」**（舊理由是「前 40 字元會被搜尋結果截斷」）。
   推翻的依據：**搜尋不是主要流量來源，推薦才是**；被演算法推到陌生人眼前時，
   決定點不點的是鉤子不是關鍵字。看到舊理由不要改回去。
   → `series.yaml` 的 `episode_title_pattern` 要跟著改成鉤子在前。

2. **每一集都要能被陌生人單獨看懂，且刻意做幾支「無需前情」的入口影片。**
   - 每集：開場不預設看過前面任何一集；**回呼不能代替解釋**
     （「這是上一集講的 X」對沒看過的人等於沒講 → 拿掉集數，直接把 X 講清楚）。
   - 入口影片：挑能單獨成立的主題（「為什麼 AI 會一本正經亂講話」
     「關聯不等於因果，一個雷聲就懂」），**全片不提「上一集」**，
     片中與資訊欄導流回系列。
   - 分工：**入口影片負責帶新人進來，系列影片負責留住人。**

3. **每一集都要產出 Shorts 候選。**
   每支長片裡都有 30 秒講得完的絕妙比喻（宙斯換心、吃素訂牛排、便當盒配菜、
   萬用轉接頭）——那些天生就是 Shorts，成本極低，而 Shorts 是目前最有效的
   **新觀眾發現管道**。
   → 腳本的製作註記已經逐條列出本集新立的比喻，**vid-seo 從那份清單挑 2–3 個**
     產出 `episodes/epNN/shorts-candidates.md`：每則含比喻名、對應場景與時間碼、
     30 秒講法、導流到哪一集。

4. **縮圖：一句大字 ＋ 一個具體畫面，全系列統一。**
   一眼看懂「這集在講什麼痛點」，不要密集文字。大字＝標題那個鉤子（可更短），
   不是章節名。同系列的字級、位置、配色固定，讓觀眾在推薦牆上認得出是同一個節目。
   ⚠️ 授權 credit 仍必須在縮圖上可讀（逐元素量對比，不要挑代表量）。

5. **每個系列的 EP01 是主力入口，不要平均用力。**
   實測：EP01 觀看永遠最高、之後遞減 → **新觀眾從 EP01 進場**。
   所以 EP01 要最獨立、鉤子最強、打磨最久；後續集靠系列完整性留人。
   → `new-series` 建立新系列時就要把這條寫進該系列的 series-context。

## 完工回灌
每集做完：把發音/斷句修正回灌 `tw_lexicon.json`/`voice-style.md`；更新 `series-context.md`（本集講了什麼、術語、下集預告、可回呼點）。
- **框架自身也要回灌**：本檔（CONVENTIONS.md）、`~/.claude/agents/*.md`（含 colon-and-code / ai-storyteller 兩個主理人）、skills（new-series / produce-episode / auto-produce-next）、`template/` 有任何修改，同步回 series-studio repo（`~/Desktop/Projects/YouTube-Channel/series-studio/claude/…`）並 commit + push。活檔是唯一真相，repo 不同步＝白學。⚠️ 金鑰不進 repo（`.env`、`youtube/token.json`、`client_secret.json`）。
