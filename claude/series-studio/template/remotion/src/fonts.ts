import { loadFont } from "@remotion/google-fonts/NotoSansTC";
import { loadFont as loadMono } from "@remotion/google-fonts/RobotoMono";

export const { fontFamily } = loadFont("normal", {
  weights: ["400", "600", "700", "800"],
  ignoreTooManyRequestsWarning: true,
});

// 等寬字體給程式碼面板用（Latin 等寬，CJK fallback 回 Noto Sans TC）
const mono = loadMono("normal", {
  weights: ["400", "500"],
  subsets: ["latin"],
  ignoreTooManyRequestsWarning: true,
});
export const codeFamily = `${mono.fontFamily}, ${fontFamily}, monospace`;
