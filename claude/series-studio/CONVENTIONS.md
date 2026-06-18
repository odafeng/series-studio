# Series Studio — 通用製作慣例（所有系列共用）

> 各 vid-* agent 與 produce-episode 流程都引用本檔。在「系列資料夾」根目錄操作（cwd = 系列根）。
> 系列專屬參數一律從 `./series.yaml` 讀；口吻從 `./voice-style.md`；上下集 context 從 `./series-context.md`。

## 腳本格式（編劇）
- 檔案 `episodes/epNN/script/epNN-script.md`。
- `**【旁白】**` 後一段＝要唸的（本人口吻）；`**【畫面】**/**【字幕】**＝動畫指示（不唸）；`## NN 場景名` 分場景。
- 三段式：00 無音樂前言 →〔C&C/品牌片頭由組裝插入〕→ 本體分場景 → 收尾＋下集預告＋角落 credit（授權署名見 series.yaml）。
- demo 段用素材附帶的程式碼實機演示，**務必留旁白蓋住 demo 播放**。
- 取素材：`source.kind: local` → 讀 `source/epN.md`；`github` → 用 `api.github.com/repos/{repo}/contents/{path}?ref={ref}` 取 base64 解碼（raw.githubusercontent 常逾時）。

## 配音（vid-voice）— `python3 tools/build_voice.py --ep N`
- 設定驅動（讀 series.yaml voice）。逐句合成、內容雜湊命名（含詞庫）→ 冪等、改發音自動重合成。
- **純音檔 QC 迴圈**：concat 旁白成 mp3 給使用者聽、先鎖發音再渲染影片。QuickTime 重開要先 `quit` 再 `open`（同路徑不自動 reload）。
- 讀錯字 → 加 `voiceover/tw_lexicon.json`（`詞:"(pin1)(yin1)"`，輕聲用 `(le5)`；別加單字詞條）。頑固破音字（如「當機」）→ 直接換詞。
- 斷句怪／詞被切開 → **改寫腳本**（非詞庫）。

## 動畫（vid-animator）— Remotion
- 元件：`remotion/src/components.tsx`(Reveal/SceneTitle/Chip/Card)、`theme.ts`、`fonts.ts`(codeFamily)。每集寫 `scenesNN.tsx` + `EpisodeNN.tsx`（從 manifest `epNNData.ts` 的 EP NN 自動排場景）+ 註冊 `Root.tsx`。
- 共用 `Narration`/`Subtitles`（吃 `cues` prop）。
- **實機 demo 螢幕錄影**（macOS）：⚠️先把輸入法切 ABC（`osascript ... key code 49 using control`）否則 keystroke 全形；用 `/opt/anaconda3/bin/python3`；`ffmpeg -f avfoundation -i "2"` 錄螢幕（需 Terminal 螢幕錄製權限）→ 裁終端機放大 + `tpad` 凍結補長 → `OffthreadVideo` 嵌入（明確尺寸、別蓋標題）。
- 渲染：`npx remotion render src/index.ts EpNN out.mp4`。先 `still` 抽幀驗。

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
- 三段同 codec/fps/音訊參數，concat demuxer `-c copy`。前言/本體分界＝第一個正片場景 startF。

## 上架（vid-seo + 發布）
- metadata：標題(關鍵字前置≤100)、描述(hook→摘要→章節→出處連結→授權)、tags、章節(本體時間=原始+片頭長度)、縮圖、置頂留言。
- 合規：描述含來源連結與授權(series.yaml license/attribution/source_url)，commercial:false → 不開營利。
- 上傳沿用 `~/Desktop/Projects/colon-and-code-youtube/youtube/upload.py`（OAuth 已快取）：`--file --metadata --privacy` → `--thumb` → `--comment`（API 不能置頂，提醒手動）。

## 完工回灌
每集做完：把發音/斷句修正回灌 `tw_lexicon.json`/`voice-style.md`；更新 `series-context.md`（本集講了什麼、術語、下集預告、可回呼點）。
