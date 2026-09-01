import React from "react";
import {
  AbsoluteFill,
  Composition,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";

export interface FlowSceneVideoConfig {
  startFrame: number;
  durationInFrames: number;
  videoAsset: string;
}

export const FLOW_TOP_HALF_SCENES: FlowSceneVideoConfig[] = [
  // 01: Passbook 10 Lakh (0.00s - 4.70s = 141 frames)
  { startFrame: 0, durationInFrames: 141, videoAsset: "flow_videos/flow_passbook_10lakh.mp4" },
  // 03: Circulation Loop (7.88s - 12.48s = 138 frames)
  { startFrame: 236, durationInFrames: 138, videoAsset: "flow_videos/flow_circulation_system.mp4" },
  // 05: Ledger / Capital (16.90s - 22.66s = 173 frames)
  { startFrame: 507, durationInFrames: 173, videoAsset: "flow_videos/vox_moving_car.mp4" },
  // 08: BANK RUN Stamp (31.70s - 37.80s = 183 frames)
  { startFrame: 951, durationInFrames: 183, videoAsset: "flow_videos/flow_bankrun_panic.mp4" },
  // 11: Trust & CTA (51.46s - 55.10s = 109 frames)
  { startFrame: 1544, durationInFrames: 109, videoAsset: "flow_videos/flow_vault_reality.mp4" },
];

export const FlowVideoBankTopHalfComp: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000", width: 1080, height: 960, overflow: "hidden" }}>
      {FLOW_TOP_HALF_SCENES.map((scene, idx) => (
        <Sequence key={idx} from={scene.startFrame} durationInFrames={scene.durationInFrames}>
          <AbsoluteFill style={{ overflow: "hidden" }}>
            <OffthreadVideo
              src={staticFile(scene.videoAsset)}
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

export const FlowVideoBankTopHalfComposition: React.FC = () => {
  return (
    <Composition
      id="FlowVideoBankTopHalf"
      component={FlowVideoBankTopHalfComp}
      durationInFrames={1653}
      fps={30}
      width={1080}
      height={960}
    />
  );
};
