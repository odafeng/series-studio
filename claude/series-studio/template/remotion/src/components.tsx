import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { theme } from "./theme";

// 進場：14 幀內以 ease-out 到位，之後「完全靜止」（不用 spring 的無限逼近，避免持續微抖）
// 位移取整數像素，避免次像素 anti-alias 抖動
export const Reveal: React.FC<{
  at?: number;
  y?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ at = 0, y = 26, children, style }) => {
  const f = useCurrentFrame();
  const t = interpolate(f, [at, at + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const ty = Math.round((1 - t) * y);
  // settle 後拿掉 transform，避免 translateY(0) 把元素留在 GPU 合成層造成次像素微抖
  const moving = t < 1;
  return (
    <div style={{ opacity: t, ...(moving ? { transform: `translateY(${ty}px)` } : {}), ...style }}>
      {children}
    </div>
  );
};

export const SceneTitle: React.FC<{ cn: string; en?: string; at?: number }> = ({ cn, en, at = 0 }) => (
  <Reveal at={at}>
    <div style={{ borderLeft: `7px solid ${theme.sky}`, paddingLeft: 26 }}>
      <div style={{ fontSize: 58, fontWeight: 800, color: theme.ink, lineHeight: 1.1 }}>{cn}</div>
      {en && (
        <div style={{ fontSize: 22, color: theme.muted, letterSpacing: 5, marginTop: 8 }}>{en}</div>
      )}
    </div>
  </Reveal>
);

export const Chip: React.FC<{ children: React.ReactNode; tone?: "blue" | "muted" }> = ({
  children,
  tone = "blue",
}) => (
  <span
    style={{
      display: "inline-block",
      padding: "12px 26px",
      borderRadius: 999,
      background: tone === "blue" ? theme.litFill : "#F1F3F7",
      color: tone === "blue" ? theme.blue : theme.muted,
      fontSize: 32,
      fontWeight: 700,
      margin: 8,
    }}
  >
    {children}
  </span>
);

export const Card: React.FC<{
  at?: number;
  title: string;
  children: React.ReactNode;
  w?: number;
}> = ({ at = 0, title, children, w = 480 }) => (
  <Reveal at={at}>
    <div
      style={{
        width: w,
        background: "#FFFFFF",
        border: `1px solid ${theme.line}`,
        borderRadius: 20,
        padding: "32px 34px",
        boxShadow: "0 16px 44px rgba(37,99,235,0.07)",
      }}
    >
      <div style={{ fontSize: 34, fontWeight: 800, color: theme.blue, marginBottom: 16 }}>{title}</div>
      <div style={{ fontSize: 26, color: theme.ink, lineHeight: 1.6 }}>{children}</div>
    </div>
  </Reveal>
);
