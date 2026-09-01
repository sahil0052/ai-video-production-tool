import React from "react";
import {
  AbsoluteFill,
  Composition,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface MotionSceneConfig {
  startFrame: number;
  durationInFrames: number;
  plateAsset: string;
  type: "passbook" | "vault" | "circulation" | "scale" | "ledger" | "crowd" | "bankrun" | "dominoes" | "trust" | "cta";
  cameraMotion: "push_in_3d" | "pan_tilt_3d" | "shake_impact_3d" | "tilt_roll_3d";
}

export const MOTION_SCENES: MotionSceneConfig[] = [
  // 01: Passbook 10 Lakh (0.00s - 4.70s)
  { startFrame: 0, durationInFrames: 141, plateAsset: "assets/bank_vox_plates/bank01_passbook_10lakh.jpg", type: "passbook", cameraMotion: "push_in_3d" },
  // 02: Vault Reality (4.70s - 7.88s)
  { startFrame: 141, durationInFrames: 95, plateAsset: "assets/bank_vox_plates/bank02_vault_open.jpg", type: "vault", cameraMotion: "pan_tilt_3d" },
  // 03: Circulation Loop (7.88s - 12.48s)
  { startFrame: 236, durationInFrames: 138, plateAsset: "assets/bank_vox_plates/bank03_fractional_circulation.jpg", type: "circulation", cameraMotion: "push_in_3d" },
  // 04: Liquidity Scale (12.48s - 16.90s)
  { startFrame: 374, durationInFrames: 133, plateAsset: "assets/bank_vox_plates/bank04_liquidity_scale.jpg", type: "scale", cameraMotion: "tilt_roll_3d" },
  // 05: The Ledger (16.90s - 22.66s)
  { startFrame: 507, durationInFrames: 173, plateAsset: "assets/bank_vox_plates/bank05_ledger_1crore.jpg", type: "ledger", cameraMotion: "push_in_3d" },
  // 06: Mob Queue (26.68s - 31.70s)
  { startFrame: 800, durationInFrames: 151, plateAsset: "assets/bank_vox_plates/bank06_crowd_queue.jpg", type: "crowd", cameraMotion: "pan_tilt_3d" },
  // 07: BANK RUN Stamp (31.70s - 37.80s)
  { startFrame: 951, durationInFrames: 183, plateAsset: "assets/bank_vox_plates/bank07_bankrun_headline.jpg", type: "bankrun", cameraMotion: "shake_impact_3d" },
  // 08: Panic Dominoes (37.80s - 45.18s)
  { startFrame: 1134, durationInFrames: 221, plateAsset: "assets/bank_vox_plates/bank08_panic_dominoes.jpg", type: "dominoes", cameraMotion: "pan_tilt_3d" },
  // 09: Trust Shield (48.48s - 51.46s)
  { startFrame: 1454, durationInFrames: 90, plateAsset: "assets/bank_vox_plates/bank09_trust_shield.jpg", type: "trust", cameraMotion: "push_in_3d" },
  // 10: CTA (51.46s - 55.10s)
  { startFrame: 1544, durationInFrames: 109, plateAsset: "assets/bank_vox_plates/bank10_follow_cta.jpg", type: "cta", cameraMotion: "shake_impact_3d" },
];

export const Vox3DMotionGraphicsTopHalfComp: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0E0E0E", width: 1080, height: 960, overflow: "hidden" }}>
      {MOTION_SCENES.map((scene, idx) => (
        <Sequence key={idx} from={scene.startFrame} durationInFrames={scene.durationInFrames}>
          <Scene3DLayer scene={scene} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const Scene3DLayer: React.FC<{ scene: MotionSceneConfig }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const dur = scene.durationInFrames;

  // 3D Multi-Axis Camera Motion
  let scale = 1.0;
  let rotateX = 0;
  let rotateY = 0;
  let rotateZ = 0;
  let translateX = 0;
  let translateY = 0;
  let translateZ = 0;

  if (scene.cameraMotion === "push_in_3d") {
    scale = interpolate(frame, [0, dur], [1.0, 1.15], { extrapolateRight: "clamp" });
    translateZ = interpolate(frame, [0, dur], [0, 80]);
    rotateY = interpolate(frame, [0, dur], [-2, 2]);
    rotateX = interpolate(frame, [0, dur], [2, -1]);
  } else if (scene.cameraMotion === "pan_tilt_3d") {
    scale = interpolate(frame, [0, dur], [1.05, 1.18], { extrapolateRight: "clamp" });
    translateX = interpolate(frame, [0, dur], [-30, 30]);
    translateY = interpolate(frame, [0, dur], [15, -15]);
    rotateY = interpolate(frame, [0, dur], [-4, 4]);
  } else if (scene.cameraMotion === "shake_impact_3d") {
    const impact = spring({ frame, fps, config: { damping: 12, stiffness: 200 } });
    scale = interpolate(impact, [0, 1], [1.25, 1.06]);
    rotateZ = Math.sin(frame * 0.8) * Math.max(0, 1 - frame / 20) * 3;
    translateY = Math.cos(frame * 0.9) * Math.max(0, 1 - frame / 20) * 8;
  } else if (scene.cameraMotion === "tilt_roll_3d") {
    scale = interpolate(frame, [0, dur], [1.02, 1.14]);
    rotateZ = interpolate(frame, [0, dur], [-3, 3]);
    rotateX = interpolate(frame, [0, dur], [-2, 3]);
  }

  return (
    <AbsoluteFill
      style={{
        perspective: 1200,
        transformStyle: "preserve-3d",
        overflow: "hidden",
        backgroundColor: "#0A0A0A",
      }}
    >
      {/* 3D Base Plate with Parallax Camera */}
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `translate3d(${translateX}px, ${translateY}px, ${translateZ}px) scale(${scale}) rotateX(${rotateX}deg) rotateY(${rotateY}deg) rotateZ(${rotateZ}deg)`,
          transformOrigin: "center center",
          transition: "transform 0.05s linear",
        }}
      >
        <Img
          src={staticFile(scene.plateAsset)}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      </div>

      {/* Procedural 3D Motion Graphic Overlays */}
      {scene.type === "passbook" && <Passbook3DOverlays frame={frame} dur={dur} />}
      {scene.type === "vault" && <Vault3DOverlays frame={frame} dur={dur} />}
      {scene.type === "circulation" && <Circulation3DOverlays frame={frame} dur={dur} />}
      {scene.type === "scale" && <Scale3DOverlays frame={frame} dur={dur} />}
      {scene.type === "ledger" && <Ledger3DOverlays frame={frame} dur={dur} />}
      {scene.type === "crowd" && <Crowd3DOverlays frame={frame} dur={dur} />}
      {scene.type === "bankrun" && <BankRun3DOverlays frame={frame} dur={dur} />}
      {scene.type === "dominoes" && <Dominoes3DOverlays frame={frame} dur={dur} />}
      {scene.type === "trust" && <Trust3DOverlays frame={frame} dur={dur} />}
      {scene.type === "cta" && <Cta3DOverlays frame={frame} dur={dur} />}
    </AbsoluteFill>
  );
};

// 1. Passbook Floating Banknotes & Pulsing Red Question Marks
const Passbook3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const pulse = Math.sin(frame * 0.2) * 0.1 + 1.0;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* Animated glowing question mark ping */}
      <div
        style={{
          position: "absolute",
          top: 290,
          right: 180,
          width: 140,
          height: 140,
          borderRadius: "50%",
          border: "4px solid rgba(225, 40, 40, 0.7)",
          transform: `scale(${pulse})`,
          boxShadow: "0 0 25px rgba(225, 40, 40, 0.4)",
        }}
      />
      {/* Floating 3D Banknote particle 1 */}
      <div
        style={{
          position: "absolute",
          left: 120 + Math.sin(frame * 0.08) * 20,
          top: 600 - frame * 1.5,
          width: 160,
          height: 80,
          backgroundColor: "#E2ECD8",
          border: "2px solid #3A7D44",
          transform: `rotate(${Math.sin(frame * 0.1) * 15}deg) rotateY(${frame * 2}deg)`,
          opacity: interpolate(frame, [0, 20, 100, 140], [0, 0.85, 0.85, 0]),
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: "bold",
          fontSize: 18,
          color: "#2D6A4F",
          boxShadow: "0 8px 16px rgba(0,0,0,0.3)",
        }}
      >
        ₹ 10,00,000
      </div>
    </AbsoluteFill>
  );
};

// 2. Vault Rotating Dial Gear Overlays
const Vault3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const rot = frame * 1.8;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 450,
          top: 400,
          width: 180,
          height: 180,
          borderRadius: "50%",
          border: "6px dashed rgba(225, 45, 45, 0.8)",
          transform: `rotate(${rot}deg)`,
        }}
      />
    </AbsoluteFill>
  );
};

// 3. Circulation Energy Pulse Arrows
const Circulation3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const offset = (frame * 6) % 100;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: "20%",
          bottom: 120,
          padding: "8px 24px",
          backgroundColor: "rgba(225, 40, 40, 0.9)",
          color: "#FFF",
          fontWeight: 900,
          fontSize: 24,
          borderRadius: 6,
          letterSpacing: 2,
          transform: `translateY(${Math.sin(frame * 0.15) * 6}px)`,
          boxShadow: "0 6px 20px rgba(225, 40, 40, 0.5)",
        }}
      >
        ⚡ CASH VELOCITY: ACTIVE
      </div>
    </AbsoluteFill>
  );
};

// 4. Scale 3D Physics Tilting Indicator
const Scale3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const flash = frame % 12 < 6;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          right: 60,
          top: 140,
          padding: "10px 20px",
          backgroundColor: flash ? "#D90429" : "#1A1A1A",
          color: "#FFF",
          fontWeight: "bold",
          fontSize: 26,
          borderRadius: 4,
          border: "2px solid #FFF",
          boxShadow: "0 8px 25px rgba(217, 4, 41, 0.6)",
        }}
      >
        ⚠️ 90% ILLIQUID DEBT
      </div>
    </AbsoluteFill>
  );
};

// 5. Ledger Central Liabilities Matrix
const Ledger3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const scanY = (frame * 4) % 600 + 200;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 60,
          top: scanY,
          width: 960,
          height: 4,
          backgroundColor: "rgba(225, 40, 40, 0.8)",
          boxShadow: "0 0 15px rgba(225, 40, 40, 0.8)",
        }}
      />
    </AbsoluteFill>
  );
};

// 6. Crowd Soundwave Waves
const Crowd3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const r1 = (frame * 5) % 180;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 280 - r1 / 2,
          top: 480 - r1 / 2,
          width: r1,
          height: r1,
          borderRadius: "50%",
          border: "3px solid rgba(225, 30, 30, 0.8)",
          opacity: 1 - r1 / 180,
        }}
      />
    </AbsoluteFill>
  );
};

// 7. Bank Run Stamp Impact
const BankRun3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 80,
          padding: "6px 18px",
          backgroundColor: "#D90429",
          color: "#FFF",
          fontWeight: 900,
          fontSize: 22,
          letterSpacing: 3,
        }}
      >
        CRISIS ALERT // 1954
      </div>
    </AbsoluteFill>
  );
};

// 8. Dominoes Falling Shockwave
const Dominoes3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const ring = (frame * 7) % 240;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 540 - ring / 2,
          top: 480 - ring / 2,
          width: ring,
          height: ring,
          borderRadius: "50%",
          border: "4px solid rgba(225, 40, 40, 0.7)",
          opacity: 1 - ring / 240,
        }}
      />
    </AbsoluteFill>
  );
};

// 9. Trust Shield Glow
const Trust3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const glow = Math.sin(frame * 0.2) * 15 + 25;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          left: 360,
          top: 240,
          width: 360,
          height: 480,
          boxShadow: `0 0 ${glow}px rgba(235, 200, 110, 0.6)`,
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};

// 10. CTA Follow Button Bounce
const Cta3DOverlays: React.FC<{ frame: number; dur: number }> = ({ frame }) => {
  const bounce = Math.sin(frame * 0.25) * 8;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: "50%",
          transform: `translateX(-50%) translateY(${bounce}px)`,
          padding: "12px 32px",
          backgroundColor: "#D90429",
          color: "#FFF",
          fontWeight: 900,
          fontSize: 28,
          borderRadius: 8,
          boxShadow: "0 8px 30px rgba(217, 4, 41, 0.7)",
        }}
      >
        🔔 SUBSCRIBE & FOLLOW
      </div>
    </AbsoluteFill>
  );
};

export const Vox3DMotionGraphicsTopHalfComposition: React.FC = () => {
  return (
    <Composition
      id="Vox3DMotionGraphicsTopHalf"
      component={Vox3DMotionGraphicsTopHalfComp}
      durationInFrames={1653}
      fps={30}
      width={1080}
      height={960}
    />
  );
};
