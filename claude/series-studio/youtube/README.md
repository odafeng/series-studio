# YouTube 上傳（一次性 OAuth 設定）

上傳影片走 YouTube Data API v3，**一定要 OAuth 使用者授權**（API key 不能上傳）。以下只需做一次。

## 1. 建立 OAuth client（在 Google Cloud Console）
1. 開一個 GCP 專案（或用現成的），到「API 和服務 → 程式庫」啟用 **YouTube Data API v3**。
2. 「OAuth 同意畫面」：User Type 選 **External**，填好 App 名稱/你的 email；
   在 **Test users** 加入你自己的 Google 帳號（= 你的 YouTube 頻道帳號）。
   - 維持「測試中（Testing）」即可上傳；不必送 Google 審核。
3. 「憑證 → 建立憑證 → OAuth 用戶端 ID」：應用程式類型選 **桌面應用程式 (Desktop app)**。
4. 下載 JSON，存成 **`youtube/client_secret.json`**（此檔已 gitignore，勿外流）。

## 2. 授權一次
在 `tutorial_video/` 底下，於本對話輸入框用 `!` 執行（會開瀏覽器讓你登入同意）：

    ! python3 youtube/upload.py --auth-only

成功後會在 `youtube/token.json` 留下權杖，之後上傳免再授權。

## 3. 上傳
    ! python3 youtube/upload.py --privacy public      # 或 unlisted / private

預設上傳 `remotion/out/world_master.mp4`，metadata 取自 `youtube/metadata.json`。

## 注意
- **未驗證 app 限制**：用測試中的 OAuth app 透過 API 上傳，YouTube 可能把影片鎖成「私人」，
  需到 Studio（指令會印出連結）手動改成公開。這是 Google 的政策，不是腳本問題。
- 配額：`videos.insert` 一次約 1600 units（每日預設 10000），個人用綽綽有餘。
- `client_secret.json` 與 `token.json` 都不會進版控。
