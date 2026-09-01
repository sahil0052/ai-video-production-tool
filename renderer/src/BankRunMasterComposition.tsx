import React from "react";
import {
  AbsoluteFill,
  Composition,
  OffthreadVideo,
  Sequence,
  staticFile,
} from "remotion";

export interface FlowTopHalfBeat {
  startFrame: number;
  durationInFrames: number;
  videoAsset: string;
}

// 6 Core Google Flow AI 3D Motion Graphics Video Segments
export const FLOW_TOP_HALF_BEATS: FlowTopHalfBeat[] = [
  // 01: Hook Passbook (0.00s - 4.70s = 141 frames)
  { startFrame: 0, durationInFrames: 141, videoAsset: "flow_videos/flow_passbook_10lakh.mp4" },
  // 02: Vault Reality (4.70s - 7.88s = 95 frames)
  { startFrame: 141, durationInFrames: 95, videoAsset: "flow_videos/flow_vault_reality.mp4" },
  // 03: Circulation & Scale (7.88s - 16.90s = 271 frames)
  { startFrame: 236, durationInFrames: 271, videoAsset: "flow_videos/flow_liquidity_scale.mp4" },
  // 04: Capital in Motion (16.90s - 22.66s = 173 frames)
  { startFrame: 507, durationInFrames: 173, videoAsset: "flow_videos/vox_moving_car.mp4" },
  // 05: Mob Queue (26.68s - 31.70s = 151 frames)
  { startFrame: 800, durationInFrames: 151, videoAsset: "flow_videos/flow_crowd_queue.mp4" },
  // 06: Bank Run Panic (31.70s - 45.18s = 404 frames)
  { startFrame: 951, durationInFrames: 404, videoAsset: "flow_videos/flow_bankrun_panic.mp4" },
  // 07: Finale Trust & CTA (48.48s - 55.10s = 199 frames)
  { startFrame: 1454, durationInFrames: 199, videoAsset: "flow_videos/flow_vault_reality.mp4" },
];

export const BankRunTopHalfComp: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#000000", width: 1080, height: 960, overflow: "hidden" }}>
      {FLOW_TOP_HALF_BEATS.map((beat, idx) => (
        <Sequence key={idx} from={beat.startFrame} durationInFrames={beat.durationInFrames}>
          <AbsoluteFill style={{ overflow: "hidden" }}>
            <OffthreadVideo
              src={staticFile(beat.videoAsset)}
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

export const BankRunMasterComposition: React.FC = () => {
  return (
    <Composition
      id="BankRunTopHalf"
      component={BankRunTopHalfComp}
      durationInFrames={1653}
      fps={30}
      width={1080}
      height={960}
    />
  );
};
