import React from "react";
import {
  AbsoluteFill,
  Composition,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  interpolate,
} from "remotion";

export interface FlowSceneSegment {
  videoFile: string;
  startFrame: number;
  durationInFrames: number;
  label?: string;
}

interface FlowVideoExplainerProps {
  scenes?: FlowSceneSegment[];
}

export const FlowVideoExplainerTopHalf: React.FC<FlowVideoExplainerProps> = ({
  scenes = [
    { videoFile: "flow_videos/scene01_hook.mp4", startFrame: 0, durationInFrames: 88 },
    { videoFile: "flow_videos/scene02_fear.mp4", startFrame: 88, durationInFrames: 74 },
    { videoFile: "flow_videos/scene03_greed.mp4", startFrame: 162, durationInFrames: 55 },
    { videoFile: "flow_videos/scene04_ego.mp4", startFrame: 217, durationInFrames: 98 },
    { videoFile: "flow_videos/scene05_trap.mp4", startFrame: 315, durationInFrames: 90 },
    { videoFile: "flow_videos/scene06_streak.mp4", startFrame: 405, durationInFrames: 90 },
    { videoFile: "flow_videos/scene07_leverage.mp4", startFrame: 495, durationInFrames: 90 },
    { videoFile: "flow_videos/scene08_loss.mp4", startFrame: 585, durationInFrames: 90 },
    { videoFile: "flow_videos/scene09_revenge.mp4", startFrame: 675, durationInFrames: 90 },
    { videoFile: "flow_videos/scene10_market.mp4", startFrame: 765, durationInFrames: 90 },
    { videoFile: "flow_videos/scene11_damage.mp4", startFrame: 855, durationInFrames: 75 },
    { videoFile: "flow_videos/scene12_ea.mp4", startFrame: 930, durationInFrames: 84 },
    { videoFile: "flow_videos/scene13_cta.mp4", startFrame: 1014, durationInFrames: 80 },
  ],
}) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#111111", width: 1080, height: 960, overflow: "hidden" }}>
      {scenes.map((scene, idx) => (
        <Sequence key={idx} from={scene.startFrame} durationInFrames={scene.durationInFrames}>
          <AbsoluteFill style={{ overflow: "hidden" }}>
            <OffthreadVideo
              src={staticFile(scene.videoFile)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
            />
          </AbsoluteFill>
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

export const FlowVideoExplainerTopHalfComposition: React.FC = () => {
  return (
    <Composition
      id="FlowVideoExplainerTopHalf"
      component={FlowVideoExplainerTopHalf}
      durationInFrames={1094}
      fps={30}
      width={1080}
      height={960}
    />
  );
};
