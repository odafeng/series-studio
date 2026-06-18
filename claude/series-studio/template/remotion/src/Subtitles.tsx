import { useCurrentFrame } from "remotion";
import { theme } from "./theme";
import { fontFamily } from "./fonts";

type Cue = { startF: number; durF: number; text: string };

// 把長句在標點處切成短段（不硬切、不切壞詞）；過長的單段就讓它自然折最多兩行
function chunk(text: string, max = 26): string[] {
  const parts = text.split(/(?<=[，、；：。！？])/).filter(Boolean);
  const out: string[] = [];
  let cur = "";
  for (const p of parts) {
    if (cur && (cur + p).length > max) {
      out.push(cur);
      cur = p;
    } else {
      cur += p;
    }
  }
  if (cur) out.push(cur);
  return out;
}

export const Subtitles: React.FC<{ cues: readonly Cue[] }> = ({ cues }) => {
  const f = useCurrentFrame();
  const cue = cues.find((c) => f >= c.startF && f < c.startF + c.durF);
  if (!cue) return null;

  // 在該句時長內，依各段字數比例分配顯示時間
  const chunks = chunk(cue.text);
  const local = f - cue.startF;
  const totalLen = chunks.reduce((a, c) => a + c.length, 0);
  let acc = 0;
  let active = chunks[chunks.length - 1];
  for (const c of chunks) {
    const w = (c.length / totalLen) * cue.durF;
    if (local < acc + w) {
      active = c;
      break;
    }
    acc += w;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        bottom: 60,
        height: 150,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        fontFamily,
        pointerEvents: "none",
      }}
    >
      <span
        style={{
          boxSizing: "border-box",
          maxWidth: 1500,
          background: "rgba(255,255,255,0.92)",
          color: theme.ink,
          fontSize: 40,
          fontWeight: 600,
          padding: "12px 30px",
          borderRadius: 14,
          lineHeight: 1.45,
          textAlign: "center",
          boxShadow: "0 6px 22px rgba(0,0,0,0.07)",
        }}
      >
        {active}
      </span>
    </div>
  );
};
