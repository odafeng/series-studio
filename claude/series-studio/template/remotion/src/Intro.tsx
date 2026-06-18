import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "./fonts";

// 通用品牌片頭（磅礴）。每個系列改 BRAND / TAGLINE，渲染成 brand/intro.mp4 共用。
// 若 series.yaml 已提供現成的 brand/intro.mp4，可忽略此檔。
const BRAND = "Your Brand";        // ← 改成你的頻道/品牌名
const TAGLINE = "副標 · 一句話";    // ← 改成你的 tagline
const NAVY = "#0B1220";

const ease = (f: number, a: number, d = 16) =>
  interpolate(f, [a, a + d], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.out(Easing.cubic) });

export const Intro: React.FC = () => {
  const f = useCurrentFrame();
  const glow = ease(f, 0, 24);
  const word = ease(f, 24, 20);
  const tag = ease(f, 48, 18);
  const out = interpolate(f, [120, 135], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill
      style={{ backgroundColor: NAVY, fontFamily, textSpacingTrim: "space-all", justifyContent: "center", alignItems: "center", opacity: out } as React.CSSProperties}
    >
      <div style={{ position: "absolute", width: 1400, height: 1400, borderRadius: "50%", background: `radial-gradient(circle, #3B82F633 0%, ${NAVY}00 60%)`, opacity: glow }} />
      <div style={{ fontSize: 132, fontWeight: 800, color: "#FFFFFF", letterSpacing: 1, opacity: word, transform: `translateY(${Math.round((1 - word) * 20)}px)` }}>
        {BRAND}
      </div>
      <div style={{ marginTop: 30, fontSize: 28, letterSpacing: 8, color: "#93A4C0", opacity: tag }}>{TAGLINE}</div>
    </AbsoluteFill>
  );
};
