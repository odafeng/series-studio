import { Audio, Sequence, staticFile } from "remotion";

type Cue = { i: number; src: string; startF: number; durF: number };

export const Narration: React.FC<{ cues: readonly Cue[] }> = ({ cues }) => (
  <>
    {cues.map((c) => (
      <Sequence key={c.i} from={c.startF} durationInFrames={c.durF}>
        <Audio src={staticFile(c.src)} />
      </Sequence>
    ))}
  </>
);
