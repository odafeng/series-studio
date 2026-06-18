import { Composition } from "remotion";
import { Intro } from "./Intro";

// 動畫師每做一集，加入該集的 composition：
//   import { Episode03 } from "./Episode03";
//   import { EP03 } from "./ep03Data";
//   import { Thumbnail03 } from "./Thumbnail03";
// 然後在下面註冊 <Composition id="Ep03" .../> 與 <Composition id="Thumbnail03" .../>。

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="Intro" component={Intro} durationInFrames={135} fps={30} width={1920} height={1080} />
      {/* EPISODES: 在此註冊各集，例如
      <Composition id="Ep03" component={Episode03} durationInFrames={EP03.total} fps={EP03.fps} width={1920} height={1080} />
      <Composition id="Thumbnail03" component={Thumbnail03} durationInFrames={1} fps={30} width={1280} height={720} />
      */}
    </>
  );
};
