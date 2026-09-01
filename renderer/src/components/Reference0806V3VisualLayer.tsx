import { Video } from "@remotion/media";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  Sequence,
  staticFile,
} from "remotion";

import type { EditPlan } from "../schema";

type Scene = EditPlan["scenes"][number];
type Asset = EditPlan["assets"][number];

type Props = {
  scene: Scene;
  assets: EditPlan["assets"];
  frame: number;
  fps: number;
};

const MONO = '"Share Tech Mono", "IBM Plex Mono", Consolas, monospace';
const SANS = '"Inter Tight", Arial, sans-serif';
const SERIF = '"Bodoni MT", Didot, Georgia, "Times New Roman", serif';
const LICENSED_PROVENANCE = "internet:coverr-free-video";
const EASE = Easing.bezier(0.16, 1, 0.3, 1);

const clamp = (value: number) => Math.max(0, Math.min(1, value));

export type Reference0806V3Surface =
  | "ink"
  | "paper"
  | "proof-band"
  | "slate";

export const getReference0806V3Surface = (
  treatment: string,
): Reference0806V3Surface => {
  if (treatment === "0806-v3-wrong-rule") {
    return "slate";
  }
  if (
    treatment === "0806-v3-evidence-heading" ||
    treatment === "0806-v3-evidence-year"
  ) {
    return "ink";
  }
  if (treatment === "0806-v3-evidence-number") {
    return "proof-band";
  }
  if (
    treatment === "0806-v3-evidence-overview" ||
    treatment === "0806-v3-evidence-history" ||
    treatment === "0806-v3-evidence-result" ||
    treatment === "0806-v3-risk-input" ||
    treatment === "0806-v3-risk-rise" ||
    treatment === "0806-v3-risk-reversal" ||
    treatment === "0806-v3-demo-input" ||
    treatment === "0806-v3-rule-pipeline" ||
    treatment === "0806-v3-ea-identity" ||
    treatment === "0806-v3-lesson-pipeline"
  ) {
    return "paper";
  }
  return "ink";
};

export const getReference0806V3MotionWashOpacity = (
  surface: Reference0806V3Surface,
) => (surface === "paper" || surface === "proof-band" ? 0.26 : 0.32);

export const getReference0806V3TexturePosition = (frame: number) => {
  const phase = ((Math.floor(frame) % 13) + 13) % 13;
  return {
    x: (phase * 5) % 13,
    y: (phase * 8) % 13,
  };
};

const progressForScene = (
  scene: Scene,
  frame: number,
  fps: number,
) => {
  const duration = Math.max(
    1,
    Math.round(((scene.end_ms - scene.start_ms) / 1000) * fps),
  );
  return clamp(frame / duration);
};

const findAsset = (
  assets: EditPlan["assets"],
  id: string | null | undefined,
) => assets.find((asset) => asset.id === id);

export const isReference0806V3Scene = (
  scene: Scene | undefined,
) => Boolean(scene?.treatment?.startsWith("0806-v3-"));

const TimedVideo: React.FC<{
  asset: Asset;
  scene: Scene;
  fps: number;
  trimSeconds?: number;
  startFrameOffset?: number;
  durationInFramesOverride?: number;
  objectPosition?: string;
  objectFit?: "cover" | "contain" | "fill";
  style?: React.CSSProperties;
}> = ({
  asset,
  scene,
  fps,
  trimSeconds = 0,
  startFrameOffset = 0,
  durationInFramesOverride,
  objectPosition = "50% 50%",
  objectFit = "cover",
  style,
}) => {
  const sceneFrom = Math.round((scene.start_ms / 1000) * fps);
  const sceneDurationInFrames = Math.max(
    1,
    Math.round(((scene.end_ms - scene.start_ms) / 1000) * fps),
  );
  const from = sceneFrom + startFrameOffset;
  const durationInFrames = Math.max(
    1,
    durationInFramesOverride ??
      sceneDurationInFrames - startFrameOffset,
  );
  return (
    <Sequence
      from={from}
      durationInFrames={durationInFrames}
      premountFor={fps}
    >
      <Video
        src={staticFile(asset.path)}
        trimBefore={Math.round(trimSeconds * fps)}
        muted
        objectFit={objectFit}
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          objectPosition,
          ...style,
        }}
      />
    </Sequence>
  );
};

const GrainAndVignette: React.FC<{ light?: boolean }> = ({
  light = false,
}) => (
  <>
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 80,
        background: light
          ? "linear-gradient(rgba(25,31,33,0.10), rgba(25,31,33,0.10)), radial-gradient(circle at 50% 42%, transparent 35%, rgba(27,31,34,0.12) 100%)"
          : "radial-gradient(circle at 50% 42%, transparent 28%, rgba(0,0,0,0.44) 100%)",
      }}
    />
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 81,
        opacity: light ? 0.028 : 0.045,
        mixBlendMode: "overlay",
        backgroundImage:
          "radial-gradient(circle at 20% 20%, rgba(255,255,255,0.8) 0 0.7px, transparent 0.8px)",
        backgroundSize: "5px 5px",
      }}
    />
  </>
);

const SceneMotionWash: React.FC<{
  progress: number;
  surface: Reference0806V3Surface;
}> = ({ progress, surface }) => {
  const translateX = interpolate(progress, [0, 1], [-760, 1320], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const lightSurface =
    surface === "paper" || surface === "proof-band";
  return (
    <div
      data-v3-motion-wash="true"
      style={{
        position: "absolute",
        zIndex: 72,
        pointerEvents: "none",
        top: -260,
        bottom: -260,
        left: 0,
        width: 620,
        opacity: getReference0806V3MotionWashOpacity(surface),
        mixBlendMode: lightSurface ? "multiply" : "screen",
        background: lightSurface
          ? "linear-gradient(90deg, transparent, rgba(28,49,56,0.22), transparent)"
          : "linear-gradient(90deg, transparent, rgba(220,238,240,0.20), transparent)",
        transform: `translateX(${translateX}px) rotate(7deg)`,
      }}
    />
  );
};

const SceneMotionTexture: React.FC<{
  frame: number;
  surface: Reference0806V3Surface;
}> = ({ frame, surface }) => {
  const { x, y } = getReference0806V3TexturePosition(frame);
  const lightSurface =
    surface === "paper" || surface === "proof-band";
  const grain = lightSurface
    ? "rgba(24,38,42,0.74)"
    : "rgba(236,242,240,0.68)";
  return (
    <AbsoluteFill
      data-v3-motion-texture="true"
      style={{
        zIndex: 73,
        pointerEvents: "none",
        opacity: lightSurface ? 0.028 : 0.038,
        mixBlendMode: lightSurface ? "multiply" : "screen",
        backgroundImage: [
          `radial-gradient(circle at 20% 20%, ${grain} 0 0.72px, transparent 0.92px)`,
          `radial-gradient(circle at 72% 68%, ${grain} 0 0.62px, transparent 0.82px)`,
        ].join(","),
        backgroundSize: "7px 7px, 11px 11px",
        backgroundPosition: `${x}px ${y}px, ${-y}px ${x}px`,
      }}
    />
  );
};

const SourceLabel: React.FC<{
  children: React.ReactNode;
  light?: boolean;
}> = ({ children, light = false }) => (
  <div
    style={{
      position: "absolute",
      top: 66,
      left: 54,
      zIndex: 70,
      padding: "8px 12px 7px",
      background: light ? "#f5f1e8" : "rgba(5,7,8,0.86)",
      color: light ? "#111416" : "#eef3f3",
      border: `1px solid ${
        light ? "rgba(17,20,22,0.2)" : "rgba(238,243,243,0.2)"
      }`,
      fontFamily: MONO,
      fontSize: 20,
      letterSpacing: 2.1,
      textTransform: "uppercase",
    }}
  >
    {children}
  </div>
);

const screenOverlayIdForTreatment = (treatment: string) => {
  switch (treatment) {
    case "0806-v3-hook-physical":
    case "0806-v3-hook-presenter":
      return "capture-mt5-hook-action";
    default:
      return null;
  }
};

const screenOverlayTrim = (treatment: string) => {
  switch (treatment) {
    case "0806-v3-hook-physical":
    case "0806-v3-hook-presenter":
      return 0.25;
    default:
      return 0;
  }
};

const physicalClipOffset = (treatment: string) => {
  switch (treatment) {
    case "0806-v3-hook-physical":
      return 1.1;
    case "0806-v3-hook-presenter":
      return 4.4;
    case "0806-v3-demo-establishing":
      return 5.4;
    default:
      return 0;
  }
};

const PhysicalComputerScene: React.FC<{
  scene: Scene;
  assets: EditPlan["assets"];
  fps: number;
  progress: number;
}> = ({ scene, assets, fps, progress }) => {
  const treatment = scene.treatment ?? "";
  const background = findAsset(assets, scene.asset_id);
  const overlay = findAsset(
    assets,
    screenOverlayIdForTreatment(treatment),
  );
  const split = treatment === "0806-v3-hook-presenter";
  const showScreenOverlay =
    treatment === "0806-v3-hook-physical";
  const monitorAngle =
    treatment === "0806-v3-demo-establishing";
  const scale = interpolate(progress, [0, 1], [1.03, 1.11], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const pan = interpolate(progress, [0, 1], [-22, 18], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const screenPulse = interpolate(
    progress,
    [0, 0.22, 1],
    [0.72, 1, 1],
    {
      easing: EASE,
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );

  if (
    !background ||
    background.kind !== "video" ||
    background.provenance !== LICENSED_PROVENANCE
  ) {
    return null;
  }

  return (
    <AbsoluteFill
      data-0806-v3-scene={treatment}
      data-licensed-provenance={LICENSED_PROVENANCE}
      style={{
        zIndex: 18,
        height: split ? "58%" : "100%",
        overflow: "hidden",
        background: "#090b0d",
      }}
    >
      <TimedVideo
        asset={background}
        scene={scene}
        fps={fps}
        trimSeconds={physicalClipOffset(treatment)}
        objectPosition={monitorAngle ? "54% 48%" : "50% 48%"}
        style={{
          transform: `translateX(${pan}px) scale(${scale})`,
          filter: monitorAngle
            ? "brightness(0.98) contrast(1.10) saturate(0.88)"
            : "brightness(1.08) contrast(1.08) saturate(0.88)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.08), transparent 42%, rgba(0,0,0,0.38))",
        }}
      />
      {showScreenOverlay && overlay?.kind === "video" ? (
        <div
          style={{
            position: "absolute",
            zIndex: 28,
            overflow: "hidden",
            opacity: screenPulse,
            ...(monitorAngle
              ? {
                  left: 572,
                  top: 222,
                  width: 520,
                  height: 720,
                  clipPath:
                    "polygon(7% 4%, 96% 0%, 100% 94%, 0% 100%)",
                  transform:
                    "perspective(1100px) rotateY(-10deg) rotateZ(0.5deg)",
                  transformOrigin: "50% 50%",
                }
              : {
                  left: 142,
                  top: 110,
                  width: 796,
                  height: 520,
                  clipPath:
                    "polygon(5% 6%, 96% 1%, 100% 95%, 0% 100%)",
                  transform:
                    "perspective(1100px) rotateX(-3deg) rotateY(1deg)",
                  transformOrigin: "50% 50%",
                }),
            border: monitorAngle
              ? "13px solid #101315"
              : "16px solid #151719",
            boxShadow:
              "0 0 36px rgba(102,190,210,0.20), 0 22px 52px rgba(0,0,0,0.56)",
            background: "#080b0d",
          }}
        >
          <TimedVideo
            asset={overlay}
            scene={scene}
            fps={fps}
            trimSeconds={screenOverlayTrim(treatment)}
            objectPosition="50% 55%"
            style={{
              transform: "scale(1.32)",
              filter: "brightness(1.12) contrast(1.08) saturate(0.88)",
            }}
          />
        </div>
      ) : null}
      {treatment.includes("hook") ? (
        <>
          <div
            style={{
              position: "absolute",
              zIndex: 52,
              top: 720,
              left: 68,
              right: 68,
              color: "#f4efe6",
              fontFamily: SERIF,
              fontSize: split ? 72 : 84,
              lineHeight: 0.92,
              textAlign: "center",
              letterSpacing: -2.8,
              textShadow: "0 10px 28px rgba(0,0,0,0.66)",
            }}
          >
            EXPERT ADVISOR
          </div>
          <div
            style={{
              position: "absolute",
              zIndex: 52,
              top: 656,
              left: 0,
              right: 0,
              textAlign: "center",
              color: "#b9dfe5",
              fontFamily: MONO,
              fontSize: 21,
              letterSpacing: 4,
            }}
          >
            AUTOMATED TRADING SOFTWARE
          </div>
        </>
      ) : (
        <SourceLabel>
          {treatment === "0806-v3-demo-establishing"
            ? "PHYSICAL WORKSTATION"
            : treatment === "0806-v3-demo-attach"
              ? "REAL MT5 ACTION · ATTACH EA"
              : treatment === "0806-v3-demo-input"
                ? "REAL MT5 ACTION · ONE INPUT"
                : "REAL MT5 ACTION · STRATEGY TESTER"}
        </SourceLabel>
      )}
      <GrainAndVignette />
    </AbsoluteFill>
  );
};

const CinematicCodeScene: React.FC<{
  scene: Scene;
  asset: Asset;
  fps: number;
  progress: number;
}> = ({ scene, asset, fps, progress }) => {
  const scale = interpolate(progress, [0, 1], [1.01, 1.08], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const x = interpolate(progress, [0, 1], [-12, 26], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene="0806-v3-code-cinematic"
      data-licensed-provenance={LICENSED_PROVENANCE}
      style={{ zIndex: 18, overflow: "hidden", background: "#030405" }}
    >
      <TimedVideo
        asset={asset}
        scene={scene}
        fps={fps}
        trimSeconds={2.9}
        objectPosition="50% 48%"
        style={{
          transform: `translateX(${x}px) scale(${scale})`,
          filter: "brightness(1.08) contrast(1.14) saturate(0.86)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(0,0,0,0.24), transparent 48%, rgba(0,0,0,0.72))",
        }}
      />
      <SourceLabel>TACTILE CODE INPUT · LICENSED</SourceLabel>
      <GrainAndVignette />
    </AbsoluteFill>
  );
};

const CodeCardScene: React.FC<{
  progress: number;
  mode: "software" | "rule";
}> = ({ progress, mode }) => {
  const entrance = interpolate(progress, [0, 0.22], [24, 0], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const lines =
    mode === "software"
      ? [
          ["01", "void OnTick() {", "#f5f1e8"],
          ["02", "  readMarket();", "#9fb1b6"],
          ["03", "  if (rulesMatch) {", "#84c7d6"],
          ["04", "    executeOrder();", "#dcefc0"],
          ["05", "  }", "#f5f1e8"],
          ["06", "}", "#f5f1e8"],
        ]
      : [
          ["01", "if (signalReady) {", "#f5f1e8"],
          ["02", "  risk = chosenRisk;", "#d7b45f"],
          ["03", "  if (risk <= limit)", "#84c7d6"],
          ["04", "    executeOrder();", "#dcefc0"],
          ["05", "}", "#f5f1e8"],
        ];
  const activeLine = Math.min(
    lines.length - 1,
    Math.floor(progress * lines.length),
  );
  return (
    <AbsoluteFill
      data-0806-v3-scene={
        mode === "software" ? "0806-v3-code-card" : "0806-v3-rule-card"
      }
      style={{
        zIndex: 18,
        background:
          "radial-gradient(circle at 72% 12%, rgba(132,199,214,0.10), transparent 35%), #050607",
      }}
    >
      <SourceLabel>ILLUSTRATIVE MQL5 LOGIC</SourceLabel>
      <div
        style={{
          position: "absolute",
          top: 300,
          left: 74,
          right: 74,
          height: 920,
          borderRadius: 26,
          overflow: "hidden",
          background: "#090c0f",
          boxShadow: "0 36px 100px rgba(0,0,0,0.58)",
          border: "1px solid rgba(180,210,216,0.18)",
          transform: `translateY(${entrance}px)`,
        }}
      >
        <div
          style={{
            height: 82,
            display: "flex",
            alignItems: "center",
            gap: 14,
            padding: "0 26px",
            background: "#11161a",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          {["#d86c74", "#d7b45f", "#7caf91"].map((color) => (
            <div
              key={color}
              style={{
                width: 15,
                height: 15,
                borderRadius: "50%",
                background: color,
              }}
            />
          ))}
          <div
            style={{
              marginLeft: 18,
              color: "#8f9ba1",
              fontFamily: MONO,
              fontSize: 21,
            }}
          >
            ExpertAdvisor.mq5
          </div>
        </div>
        <div style={{ padding: "54px 34px 40px" }}>
          {lines.map(([number, text, color], index) => (
            <div
              key={`${number}-${text}`}
              style={{
                display: "grid",
                gridTemplateColumns: "64px 1fr",
                alignItems: "center",
                height: 108,
                padding: "0 20px",
                borderRadius: 12,
                background:
                  index === activeLine
                    ? "rgba(132,199,214,0.11)"
                    : "transparent",
                borderLeft:
                  index === activeLine
                    ? "3px solid #84c7d6"
                    : "3px solid transparent",
              }}
            >
              <span
                style={{
                  color: "#52616a",
                  fontFamily: MONO,
                  fontSize: 25,
                }}
              >
                {number}
              </span>
              <span
                style={{
                  color,
                  fontFamily: MONO,
                  fontSize: 37,
                  whiteSpace: "pre",
                }}
              >
                {text}
              </span>
            </div>
          ))}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 1310,
          left: 84,
          right: 84,
          color: "#eef1ec",
          fontFamily: SANS,
          fontSize: 55,
          fontWeight: 750,
          letterSpacing: -1.5,
          lineHeight: 1.02,
        }}
      >
        {mode === "software"
          ? "The software repeats the same logic."
          : "The rule can be exact—and still be wrong."}
      </div>
      <GrainAndVignette />
    </AbsoluteFill>
  );
};

const PipelineScene: React.FC<{
  progress: number;
  lesson?: boolean;
}> = ({ progress, lesson = false }) => {
  const nodes = lesson
    ? ["SIGNAL", "CHECK RULES", "EXECUTE"]
    : ["READ MARKET", "DECIDE", "EXECUTE / WAIT"];
  const active = Math.min(2, Math.floor(progress * 3));
  const lightMode = true;
  const dotY = interpolate(progress, [0, 1], [440, 1120], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene={
        lesson
          ? "0806-v3-lesson-pipeline"
          : "0806-v3-rule-pipeline"
      }
      style={{
        zIndex: 18,
        background: "#f1f2ef",
      }}
    >
      <SourceLabel light>
        {lesson
          ? "DETERMINISTIC EXECUTION"
          : "ILLUSTRATIVE AUTOMATION PIPELINE"}
      </SourceLabel>
      <div
        style={{
          position: "absolute",
          top: 250,
          left: 0,
          right: 0,
          textAlign: "center",
          color: "#15191b",
          fontFamily: SANS,
          fontWeight: 760,
          fontSize: 58,
          letterSpacing: -1.4,
        }}
      >
        {lesson ? "THE EA EXECUTES." : "READ → DECIDE → ACT"}
      </div>
      <div
        style={{
          position: "absolute",
          left: 537,
          top: 455,
          width: 5,
          height: 670,
          background: "#a8b1b3",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 523,
          top: dotY,
          width: 33,
          height: 33,
          borderRadius: "50%",
          background: "#15191b",
          boxShadow: "0 0 0 8px rgba(21,25,27,0.08)",
        }}
      />
      {nodes.map((node, index) => {
        const top = 390 + index * 350;
        const isActive = index <= active;
        return (
          <div
            key={node}
            style={{
              position: "absolute",
              top,
              left: 172,
              width: 736,
              height: 170,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: 18,
              border: `2px solid ${
                isActive
                  ? "#15191b"
                  : "#c4cbcc"
              }`,
              background: isActive
                ? "#ffffff"
                : "#e3e7e5",
              color: isActive
                ? "#15191b"
                : "#708086",
              fontFamily: MONO,
              fontSize: 34,
              letterSpacing: 2,
              boxShadow: isActive
                ? "0 22px 54px rgba(0,0,0,0.16)"
                : undefined,
            }}
          >
            <span style={{ marginRight: 30, opacity: 0.48 }}>
              0{index + 1}
            </span>
            {node}
          </div>
        );
      })}
      {lesson ? (
        <div
          style={{
            position: "absolute",
            left: 114,
            right: 114,
            top: 1450,
            padding: "34px 40px",
            background: "#15191b",
            color: "#f3f0e8",
            fontFamily: SANS,
            fontSize: 40,
            fontWeight: 700,
            textAlign: "center",
          }}
        >
          HUMAN CHOICE: SELECT THE RISK
        </div>
      ) : null}
      <GrainAndVignette light={lightMode} />
    </AbsoluteFill>
  );
};

const NavigatorMacroScene: React.FC<{
  scene: Scene;
  asset: Asset;
  fps: number;
  progress: number;
}> = ({ scene, asset, fps, progress }) => {
  const x = interpolate(progress, [0, 1], [-20, -95], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene="0806-v3-navigator-macro"
      style={{
        zIndex: 18,
        overflow: "hidden",
        background: "#e9ece8",
      }}
    >
      <AbsoluteFill
        data-single-decode-background="navigator"
        style={{
          background:
            "radial-gradient(circle at 28% 30%, rgba(132,199,214,0.28), transparent 38%), linear-gradient(145deg, #dfe5e1, #c9d2cf)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 64,
          top: 180,
          width: 930,
          height: 1240,
          overflow: "hidden",
          borderRadius: 24,
          border: "1px solid rgba(198,223,228,0.22)",
          boxShadow: "0 36px 90px rgba(0,0,0,0.56)",
          background: "#101617",
        }}
      >
        <TimedVideo
          asset={asset}
          scene={scene}
          fps={fps}
          objectPosition="left center"
          objectFit="fill"
          style={{
            width: 3800,
            height: 2138,
            left: x,
            top: -690,
            filter: "brightness(1.05) contrast(1.08) saturate(0.82)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 34,
            top: 710,
            width: 660,
            height: 245,
            border: "4px solid #84c7d6",
            boxShadow: "0 0 34px rgba(132,199,214,0.35)",
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: 84,
          top: 1480,
          color: "#15191b",
          fontFamily: SANS,
          fontSize: 58,
          fontWeight: 760,
          lineHeight: 0.98,
        }}
      >
        ONE PRODUCT.
        <br />
        ONE IDENTIFIABLE ITEM.
      </div>
      <SourceLabel light>
        REAL METATRADER 5 · NAVIGATOR MACRO
      </SourceLabel>
      <GrainAndVignette light />
    </AbsoluteFill>
  );
};

const EaIdentityScene: React.FC<{ progress: number }> = ({
  progress,
}) => {
  const ring = interpolate(progress, [0, 1], [0.88, 1.06], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene="0806-v3-ea-identity"
      style={{
        zIndex: 18,
        background:
          "radial-gradient(circle at 50% 37%, rgba(132,199,214,0.22), transparent 34%), #eef0ed",
      }}
    >
      <SourceLabel light>METATRADER PRODUCT IDENTITY</SourceLabel>
      <div
        style={{
          position: "absolute",
          top: 320,
          left: 310,
          width: 460,
          height: 460,
          borderRadius: "50%",
          border: "2px solid rgba(132,199,214,0.45)",
          transform: `scale(${ring})`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#15191b",
          fontFamily: MONO,
          fontSize: 150,
          letterSpacing: -6,
          background: "rgba(255,255,255,0.78)",
          boxShadow:
            "0 0 0 34px rgba(132,199,214,0.07), 0 0 100px rgba(132,199,214,0.20)",
        }}
      >
        EA
      </div>
      <div
        style={{
          position: "absolute",
          top: 910,
          left: 0,
          right: 0,
          textAlign: "center",
          color: "#15191b",
          fontFamily: SERIF,
          fontSize: 94,
          lineHeight: 0.9,
          letterSpacing: -3,
        }}
      >
        EXPERT
        <br />
        ADVISOR
      </div>
      <div
        style={{
          position: "absolute",
          top: 1190,
          left: 0,
          right: 0,
          textAlign: "center",
          color: "#52666c",
          fontFamily: MONO,
          fontSize: 25,
          letterSpacing: 4,
        }}
      >
        RULES-BASED AUTOMATED PROGRAM
      </div>
      <GrainAndVignette light />
    </AbsoluteFill>
  );
};

const WrongRuleScene: React.FC<{ progress: number }> = ({
  progress,
}) => {
  const branch = interpolate(progress, [0.35, 0.9], [0, 1], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene="0806-v3-wrong-rule"
      data-v3-surface="slate"
      style={{
        zIndex: 18,
        background:
          "radial-gradient(circle at 76% 16%, rgba(255,255,255,0.12), transparent 34%), #4a5356",
      }}
    >
      <SourceLabel>ILLUSTRATIVE RULE BRANCH</SourceLabel>
      <div
        style={{
          position: "absolute",
          top: 250,
          left: 74,
          color: "#f2eee7",
          fontFamily: SANS,
          fontSize: 62,
          fontWeight: 760,
          lineHeight: 0.95,
        }}
      >
        THE CODE CAN BE
        <br />
        RIGHT ABOUT A
        <br />
        WRONG RULE.
      </div>
      <div
        style={{
          position: "absolute",
          top: 630,
          left: 340,
          width: 400,
          height: 128,
          border: "2px solid #708086",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#e9efee",
          fontFamily: MONO,
          fontSize: 30,
          background: "#20282b",
        }}
      >
        PRESET RULE
      </div>
      <div
        style={{
          position: "absolute",
          top: 758,
          left: 537,
          width: 5,
          height: 190,
          background: "#c2cbcd",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 945,
          left: 258,
          width: 564,
          height: 5,
          background: "#c2cbcd",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 945,
          left: 258,
          width: 5,
          height: 160,
          background: "#c2cbcd",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 945,
          left: 817,
          width: 5,
          height: 160,
          background: "#dc6c76",
          transform: `scaleY(${branch})`,
          transformOrigin: "top",
          boxShadow: "0 0 28px rgba(220,108,118,0.45)",
        }}
      />
      {[
        {
          left: 90,
          text: "WAIT",
          border: "#526168",
          color: "#aab6ba",
        },
        {
          left: 650,
          text: "WRONG ACTION",
          border: "#dc6c76",
          color: "#f2c7cb",
        },
      ].map((item) => (
        <div
          key={item.text}
          style={{
            position: "absolute",
            top: 1105,
            left: item.left,
            width: 340,
            height: 150,
            border: `2px solid ${item.border}`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: item.color,
            fontFamily: MONO,
            fontSize: 27,
            background: "#20282b",
            opacity: item.text === "WRONG ACTION" ? branch : 1,
          }}
        >
          {item.text}
        </div>
      ))}
      <GrainAndVignette light />
    </AbsoluteFill>
  );
};

const EvidenceScene: React.FC<{
  scene: Scene;
  asset: Asset | undefined;
  progress: number;
}> = ({ scene, asset, progress }) => {
  const treatment = scene.treatment ?? "";
  const overview = treatment === "0806-v3-evidence-overview";
  const heading = treatment === "0806-v3-evidence-heading";
  const history = treatment === "0806-v3-evidence-history";
  const year = treatment === "0806-v3-evidence-year";
  const result = treatment === "0806-v3-evidence-result";
  const number = treatment === "0806-v3-evidence-number";
  const surface = getReference0806V3Surface(treatment);
  const ink = surface === "ink";
  const camera = interpolate(
    progress,
    [0, 1],
    overview ? [1, 1.025] : [1.015, 1.09],
    {
      easing: EASE,
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const cameraX = interpolate(progress, [0, 1], [-18, 22], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const cameraY = interpolate(progress, [0, 1], [10, -24], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      data-0806-v3-scene={treatment}
      data-v3-surface={surface}
      style={{
        zIndex: 18,
        background: ink
          ? "#172025"
          : number
            ? "#dce8e6"
            : history || result
              ? "#efe8dc"
              : "#e9e8e2",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: ink
            ? "radial-gradient(circle at 74% 14%, rgba(132,199,214,0.16), transparent 34%), linear-gradient(180deg, #202b30 0%, #151c20 100%)"
            : number
              ? "linear-gradient(180deg, #e7efed 0%, #d6e3e1 100%)"
              : history || result
                ? "linear-gradient(180deg, #f4eee4 0%, #e9e1d4 100%)"
                : "linear-gradient(180deg, #f4f3ee 0%, #e8e7e0 100%)",
        }}
      />
      <SourceLabel light={!ink}>
        {year
          ? "PRIMARY SOURCE · MQL5 · 2008"
          : result || number
            ? "PRIMARY SOURCE · MQL5 INTERVIEW"
            : "OFFICIAL METAQUOTES SOURCE"}
      </SourceLabel>
      {asset?.kind === "image" ? (
        <div
          style={{
            position: "absolute",
            left: overview ? 44 : 58,
            right: overview ? 44 : 58,
            top: overview ? 180 : heading || history ? 180 : 210,
            height: overview ? 1450 : heading || history ? 280 : 620,
            overflow: "hidden",
            background: "#fff",
            boxShadow: "0 30px 76px rgba(25,31,34,0.20)",
          }}
        >
          <Img
            src={staticFile(asset.path)}
            style={{
              position: "absolute",
              maxWidth: "none",
              ...(overview
                ? {
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    transform: `translate(${cameraX}px, ${cameraY}px) scale(${camera})`,
                  }
                : heading || history
                  ? {
                      width: heading ? 2100 : 2300,
                      left: heading ? -565 : -100,
                      top: heading ? -1200 : -1430,
                      transform: `translate(${cameraX}px, ${cameraY}px) scale(${camera})`,
                      transformOrigin: "50% 50%",
                    }
                  : {
                      width: 2560,
                      left: -1600,
                      top: -510,
                      transform: `translate(${cameraX}px, ${cameraY}px) scale(${camera})`,
                      transformOrigin: "50% 50%",
                    }),
            }}
          />
          {heading ? (
            <div
              style={{
                position: "absolute",
                left: 150,
                right: 150,
                top: 24,
                height: 84,
                border: "4px solid #84c7d6",
                boxShadow: "0 0 0 9999px rgba(255,255,255,0.08)",
              }}
            />
          ) : null}
          {history ? (
            <div
              style={{
                position: "absolute",
                left: 54,
                right: 54,
                top: 42,
                height: 118,
                borderLeft: "8px solid #84c7d6",
                background: "rgba(132,199,214,0.10)",
              }}
            />
          ) : null}
          {result || number ? (
            <div
              style={{
                position: "absolute",
                left: 38,
                right: 38,
                top: 76,
                height: 146,
                borderLeft: `9px solid ${
                  number ? "#d7b45f" : "#84c7d6"
                }`,
                background: number
                  ? "rgba(215,180,95,0.16)"
                  : "rgba(132,199,214,0.11)",
              }}
            />
          ) : null}
        </div>
      ) : null}
      {year ? (
        <>
          <div
            style={{
              position: "absolute",
              top: 510,
              left: 0,
              right: 0,
              color: "#f3efe7",
              textAlign: "center",
              fontFamily: SERIF,
              fontSize: 230,
              letterSpacing: -10,
              lineHeight: 0.84,
            }}
          >
            2008
          </div>
          <div
            style={{
              position: "absolute",
              top: 830,
              left: 130,
              right: 130,
              color: "#b8cace",
              textAlign: "center",
              fontFamily: MONO,
              fontSize: 26,
              lineHeight: 1.35,
              letterSpacing: 2,
            }}
          >
            AUTOMATED TRADING CHAMPIONSHIP
            <br />
            VERIFIED SOURCE BEAT
          </div>
        </>
      ) : null}
      {number ? (
        <div
          style={{
            position: "absolute",
            top: 780,
            left: 54,
            right: 54,
            height: 430,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#f4f0e8",
            background: "#172025",
            textAlign: "center",
            fontFamily: SERIF,
            fontSize: 132,
            letterSpacing: -5,
            lineHeight: 0.9,
          }}
        >
          $110,000
        </div>
      ) : null}
      {heading || history ? (
        <div
          style={{
            position: "absolute",
            left: 78,
            right: 78,
            top: 520,
            color: ink ? "#f3efe7" : "#1c2225",
            fontFamily: SERIF,
            fontSize: heading ? 82 : 68,
            fontWeight: 500,
            lineHeight: 0.94,
            letterSpacing: -2.4,
          }}
        >
          {heading
            ? "AUTOMATED TRADING CHAMPIONSHIP"
            : "OFFICIAL HISTORY: ROBOTS COMPETED FOR THREE MONTHS."}
        </div>
      ) : null}
      {result ? (
        <div
          style={{
            position: "absolute",
            left: 82,
            right: 82,
            top: 920,
            color: "#15191b",
            fontFamily: SERIF,
            fontSize: 77,
            lineHeight: 0.98,
            letterSpacing: -2.5,
          }}
        >
          “I MANAGED TO EARN 110,000”
        </div>
      ) : null}
      {number ? (
        <div
          style={{
            position: "absolute",
            left: 100,
            right: 100,
            top: 1245,
            color: "#324044",
            textAlign: "center",
            fontFamily: MONO,
            fontSize: 24,
            letterSpacing: 1.6,
          }}
        >
          EXACT FIGURE SHOWN WITH ITS PRIMARY-SOURCE EXCERPT
        </div>
      ) : null}
      <GrainAndVignette light={!ink} />
    </AbsoluteFill>
  );
};

const RiskScene: React.FC<{
  treatment: string;
  progress: number;
}> = ({ treatment, progress }) => {
  const turn = treatment === "0806-v3-risk-turn";
  const control = treatment === "0806-v3-risk-control";
  const reverse = treatment === "0806-v3-risk-reversal";
  const surface = getReference0806V3Surface(treatment);
  const lightRisk = surface === "paper";
  const pathProgress = interpolate(progress, [0.08, 0.9], [0, 1], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const knob = interpolate(progress, [0, 1], [180, 770], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene={treatment}
      data-risk-palette="reference-04-dark"
      data-v3-surface={surface}
      style={{
        zIndex: 18,
        background: lightRisk
          ? `radial-gradient(circle at 70% 18%, ${
              reverse
                ? "rgba(220,108,118,0.16)"
                : "rgba(132,199,214,0.14)"
            }, transparent 34%), #edf0ed`
          : `radial-gradient(circle at 70% 18%, ${
              reverse
                ? "rgba(220,108,118,0.16)"
                : "rgba(132,199,214,0.12)"
            }, transparent 34%), #121719`,
      }}
    >
      <SourceLabel light={lightRisk}>
        ILLUSTRATIVE RISK RELATIONSHIP
      </SourceLabel>
      {turn ? (
        <>
          <div
            style={{
              position: "absolute",
              top: 470,
              left: 0,
              right: 0,
              textAlign: "center",
              color: lightRisk ? "#15191b" : "#f2efe8",
              fontFamily: SERIF,
              fontSize: 126,
              lineHeight: 0.86,
              letterSpacing: -5,
            }}
          >
            THEN RISK
            <br />
            CHANGED IT.
          </div>
          <div
            style={{
              position: "absolute",
              top: 980,
              left: 440,
              width: 200,
              height: 200,
              borderRadius: "50%",
              background: "#dc6c76",
              border: "3px solid #f0a4aa",
              boxShadow: "0 0 90px rgba(220,108,118,0.42)",
            }}
          />
        </>
      ) : control ? (
        <>
          <div
            style={{
              position: "absolute",
              top: 330,
              left: 90,
              color: "#f2efe8",
              fontFamily: SANS,
              fontSize: 64,
              fontWeight: 760,
              lineHeight: 0.96,
            }}
          >
            ONE VARIABLE.
            <br />
            DIFFERENT OUTCOME.
          </div>
          <div
            style={{
              position: "absolute",
              top: 810,
              left: 130,
              width: 820,
              height: 18,
              borderRadius: 20,
              background:
                "linear-gradient(90deg, #84c7d6 0%, #d7b45f 55%, #dc6c76 100%)",
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 764,
              left: knob,
              width: 105,
              height: 105,
              borderRadius: "50%",
              background: "#f4f0e8",
              border: "12px solid #121719",
              boxShadow: "0 18px 44px rgba(0,0,0,0.48)",
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 930,
              left: 130,
              width: 820,
              display: "flex",
              justifyContent: "space-between",
              color: "#8b9aa0",
              fontFamily: MONO,
              fontSize: 24,
              letterSpacing: 2,
            }}
          >
            <span>CONSERVATIVE</span>
            <span>AGGRESSIVE</span>
          </div>
        </>
      ) : (
        <>
          <div
            style={{
              position: "absolute",
              top: 290,
              left: 80,
              color: lightRisk ? "#15191b" : "#f2efe8",
              fontFamily: SANS,
              fontSize: 58,
              fontWeight: 760,
              lineHeight: 0.98,
            }}
          >
            {reverse ? "THE PATH REVERSES." : "THE RESULT RISES."}
          </div>
          <svg
            width="920"
            height="760"
            viewBox="0 0 920 760"
            style={{
              position: "absolute",
              left: 80,
              top: 520,
              overflow: "visible",
            }}
          >
            <path
              d={
                reverse
                  ? "M70 610 C220 540 330 390 470 230 C610 80 720 160 850 650"
                  : "M70 610 C240 560 340 430 490 290 C640 150 730 95 850 80"
              }
              fill="none"
              stroke={reverse ? "#dc6c76" : "#84c7d6"}
              strokeWidth="18"
              strokeLinecap="round"
              pathLength="1"
              strokeDasharray="1"
              strokeDashoffset={1 - pathProgress}
            />
            <circle
              cx={reverse ? 850 : 850}
              cy={reverse ? 650 : 80}
              r="22"
              fill={reverse ? "#dc6c76" : "#84c7d6"}
            />
          </svg>
          <div
            style={{
              position: "absolute",
              top: 1370,
              left: 96,
              right: 96,
              color: lightRisk ? "#526168" : "#89979b",
              fontFamily: MONO,
              fontSize: 22,
              letterSpacing: 2,
              textAlign: "center",
            }}
          >
            NOT PERFORMANCE DATA · CONCEPTUAL RELATIONSHIP ONLY
          </div>
        </>
      )}
      <GrainAndVignette light={lightRisk} />
    </AbsoluteFill>
  );
};

const ProductMacroScene: React.FC<{
  scene: Scene;
  asset: Asset;
  fps: number;
  progress: number;
}> = ({ scene, asset, fps, progress }) => {
  const alternate =
    scene.treatment === "0806-v3-risk-alternate";
  const surface = getReference0806V3Surface(scene.treatment ?? "");
  const lightMacro = surface === "paper";
  const scale = interpolate(progress, [0, 1], [1.36, 1.58], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene={scene.treatment ?? ""}
      data-v3-surface={surface}
      style={{
        zIndex: 18,
        background: lightMacro ? "#edf0ed" : "#121719",
        overflow: "hidden",
      }}
    >
      <AbsoluteFill
        data-single-decode-background="product-macro"
        style={{
          background:
            lightMacro
              ? "radial-gradient(circle at 72% 24%, rgba(132,199,214,0.20), transparent 34%), #edf0ed"
              : "radial-gradient(circle at 72% 24%, rgba(215,180,95,0.13), transparent 34%), #121719",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: lightMacro ? 70 : 30,
          right: lightMacro ? 70 : 30,
          top: lightMacro ? 230 : 170,
          height: lightMacro ? 1180 : 1320,
          overflow: "hidden",
          borderRadius: 18,
          boxShadow: "0 38px 90px rgba(0,0,0,0.56)",
          border: "1px solid rgba(218,236,239,0.18)",
        }}
      >
        <TimedVideo
          asset={asset}
          scene={scene}
          fps={fps}
          trimSeconds={alternate ? 0.25 : 1.4}
          objectPosition="50% 50%"
          objectFit="fill"
          style={{
            width: 3400,
            height: 1913,
            left: -1110,
            top: -190,
            transform: `scale(${interpolate(
              scale,
              [1.36, 1.58],
              [1, 1.04],
            )})`,
            filter: "brightness(1.18) contrast(1.04) saturate(0.66)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 110,
            right: 90,
            top: alternate ? 470 : 500,
            height: alternate ? 410 : 390,
            border: "4px solid #d7b45f",
            boxShadow: "0 0 32px rgba(215,180,95,0.34)",
          }}
        />
      </div>
      <SourceLabel light={lightMacro}>
        REAL METATRADER INPUT · ONE ACTION
      </SourceLabel>
      <GrainAndVignette light={lightMacro} />
    </AbsoluteFill>
  );
};

const DemoActionScene: React.FC<{
  scene: Scene;
  assets: EditPlan["assets"];
  fps: number;
  progress: number;
}> = ({ scene, assets, fps, progress }) => {
  const treatment = scene.treatment ?? "";
  const surface = getReference0806V3Surface(treatment);
  const lightDemo = surface === "paper";
  const contextToSource = treatment === "0806-v3-demo-attach";
  const contextAsset = contextToSource
    ? findAsset(assets, scene.asset_id)
    : undefined;
  const captureId =
    treatment === "0806-v3-demo-attach"
      ? "capture-mt5-attach-ea"
      : scene.asset_id;
  const captureAsset = findAsset(assets, captureId);
  const sceneDurationInFrames = Math.max(
    1,
    Math.round(((scene.end_ms - scene.start_ms) / 1000) * fps),
  );
  const contextFrames = Math.round(sceneDurationInFrames * 0.42);
  const showContext = contextToSource && progress < 0.42;
  const trimSeconds =
    treatment === "0806-v3-demo-input" ? 1.4 : 0.35;
  const label =
    treatment === "0806-v3-demo-attach"
      ? "ATTACH EXPERT ADVISOR"
      : treatment === "0806-v3-demo-input"
        ? "ONE REAL INPUT"
        : "STRATEGY TESTER SETUP";

  if (showContext) {
    if (
      !contextAsset ||
      contextAsset.kind !== "video" ||
      contextAsset.provenance !== LICENSED_PROVENANCE
    ) {
      return null;
    }
    return (
      <AbsoluteFill
        data-0806-v3-scene={treatment}
        data-demo-action="context-to-source"
        style={{ zIndex: 18, background: "#060809", overflow: "hidden" }}
      >
        <TimedVideo
          asset={contextAsset}
          scene={scene}
          fps={fps}
          trimSeconds={7.2}
          durationInFramesOverride={contextFrames}
          objectPosition="50% 48%"
          style={{
            transform: "scale(1.12)",
            filter: "brightness(0.82) contrast(1.15) saturate(0.78)",
          }}
        />
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(180deg, rgba(0,0,0,0.08), transparent 46%, rgba(0,0,0,0.78))",
          }}
        />
        <SourceLabel>PHYSICAL CONTEXT · REAL ACTION NEXT</SourceLabel>
        <GrainAndVignette />
      </AbsoluteFill>
    );
  }

  if (!captureAsset || captureAsset.kind !== "video") {
    return null;
  }
  const startFrameOffset = contextToSource ? contextFrames : 0;
  const zoom = interpolate(progress, [0, 1], [1, 1.035], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const strategy = treatment === "0806-v3-demo-strategy";
  return (
    <AbsoluteFill
      data-0806-v3-scene={treatment}
      data-v3-surface={surface}
      data-demo-action={
        contextToSource ? "context-to-source" : "direct-source"
      }
      style={{
        zIndex: 18,
        background: lightDemo ? "#edf0ed" : "#121719",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: lightDemo ? 66 : 28,
          right: lightDemo ? 66 : 28,
          top: lightDemo ? 220 : 150,
          height: lightDemo ? 1190 : 1360,
          overflow: "hidden",
          border: "1px solid rgba(180,210,216,0.24)",
          boxShadow: "0 38px 100px rgba(0,0,0,0.62)",
          background: "#080b0d",
        }}
      >
        <TimedVideo
          asset={captureAsset}
          scene={scene}
          fps={fps}
          trimSeconds={trimSeconds}
          startFrameOffset={startFrameOffset}
          objectFit="fill"
          style={{
            width: strategy ? 4000 : 3300,
            height: strategy ? 2250 : 1856,
            left: strategy ? -50 : -1080,
            top: strategy ? -890 : -180,
            transform: `scale(${zoom})`,
            filter: "brightness(1.18) contrast(1.04) saturate(0.68)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: strategy ? 220 : 160,
            right: strategy ? 70 : 120,
            top: strategy ? 760 : 500,
            height: strategy ? 260 : 390,
            border: `${strategy ? 3 : 4}px solid #84c7d6`,
            borderRadius: strategy ? 8 : 0,
            boxShadow: strategy
              ? "0 0 24px rgba(132,199,214,0.28)"
              : "0 0 34px rgba(132,199,214,0.36)",
            pointerEvents: "none",
          }}
        />
      </div>
      <SourceLabel light={lightDemo}>
        REAL METATRADER 5 · {label}
      </SourceLabel>
      <GrainAndVignette light={lightDemo} />
    </AbsoluteFill>
  );
};

const LessonContrastScene: React.FC<{
  scene: Scene;
  asset: Asset;
  fps: number;
  progress: number;
}> = ({ scene, asset, fps, progress }) => {
  const divider = interpolate(progress, [0, 0.3], [0, 1], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = interpolate(progress, [0, 1], [1.04, 1.12], {
    easing: EASE,
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      data-0806-v3-scene="0806-v3-lesson-contrast"
      data-lesson-treatment="tactile-contrast"
      style={{ zIndex: 18, background: "#060809", overflow: "hidden" }}
    >
      <TimedVideo
        asset={asset}
        scene={scene}
        fps={fps}
        trimSeconds={1.6}
        objectPosition="50% 48%"
        style={{
          transform: `scale(${scale})`,
          filter: "brightness(0.92) contrast(1.08) saturate(0.64)",
        }}
      />
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(180deg, rgba(4,6,7,0.08), rgba(4,6,7,0.24) 45%, rgba(4,6,7,0.76) 100%)",
        }}
      />
      <SourceLabel>LESSON · CLEAR RESPONSIBILITY</SourceLabel>
      <div
        style={{
          position: "absolute",
          top: 270,
          left: 70,
          right: 70,
          color: "#f2efe8",
          fontFamily: SERIF,
          fontSize: 92,
          lineHeight: 0.88,
          letterSpacing: -4,
          textShadow: "0 18px 44px rgba(0,0,0,0.58)",
        }}
      >
        THE EA HAS
        <br />
        NO EMOTIONS.
      </div>
      <div
        style={{
          position: "absolute",
          top: 1040,
          left: 70,
          width: 450,
          height: 360,
          padding: "42px 38px",
          background: "rgba(8,12,14,0.90)",
          color: "#f4f0e8",
          boxSizing: "border-box",
          border: "1px solid rgba(132,199,214,0.38)",
        }}
      >
        <div
          style={{
            color: "#84c7d6",
            fontFamily: MONO,
            fontSize: 23,
            letterSpacing: 3,
          }}
        >
          MACHINE
        </div>
        <div
          style={{
            marginTop: 58,
            fontFamily: SANS,
            fontWeight: 760,
            fontSize: 46,
            lineHeight: 0.98,
          }}
        >
          READ · RULES
          <br />
          EXECUTE
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 1040,
          right: 70,
          width: 450,
          height: 360,
          padding: "42px 38px",
          background: "rgba(8,12,14,0.90)",
          color: "#f4f0e8",
          boxSizing: "border-box",
          border: "1px solid rgba(220,108,118,0.42)",
        }}
      >
        <div
          style={{
            color: "#b45560",
            fontFamily: MONO,
            fontSize: 23,
            letterSpacing: 3,
          }}
        >
          HUMAN
        </div>
        <div
          style={{
            marginTop: 58,
            fontFamily: SANS,
            fontWeight: 760,
            fontSize: 46,
            lineHeight: 0.98,
          }}
        >
          CHOOSE
          <br />
          THE RISK
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          top: 1010,
          left: 537,
          width: 6,
          height: 420 * divider,
          background: "#d7b45f",
        }}
      />
      <GrainAndVignette />
    </AbsoluteFill>
  );
};

export const Reference0806V3VisualLayer: React.FC<Props> = ({
  scene,
  assets,
  frame,
  fps,
}) => {
  if (!isReference0806V3Scene(scene)) {
    return null;
  }
  const treatment = scene.treatment ?? "";
  const progress = progressForScene(scene, frame, fps);
  const asset = findAsset(assets, scene.asset_id);
  const content = (() => {
    switch (treatment) {
      case "0806-v3-hook-physical":
      case "0806-v3-hook-presenter":
      case "0806-v3-demo-establishing":
        return (
          <PhysicalComputerScene
            scene={scene}
            assets={assets}
            fps={fps}
            progress={progress}
          />
        );
      case "0806-v3-demo-attach":
      case "0806-v3-demo-input":
      case "0806-v3-demo-strategy":
        return (
          <DemoActionScene
            scene={scene}
            assets={assets}
            fps={fps}
            progress={progress}
          />
        );
      case "0806-v3-code-cinematic":
        return asset?.kind === "video" ? (
          <CinematicCodeScene
            scene={scene}
            asset={asset}
            fps={fps}
            progress={progress}
          />
        ) : null;
      case "0806-v3-code-card":
        return <CodeCardScene progress={progress} mode="software" />;
      case "0806-v3-rule-card":
        return <CodeCardScene progress={progress} mode="rule" />;
      case "0806-v3-rule-pipeline":
        return <PipelineScene progress={progress} />;
      case "0806-v3-navigator-macro":
        return asset?.kind === "video" ? (
          <NavigatorMacroScene
            scene={scene}
            asset={asset}
            fps={fps}
            progress={progress}
          />
        ) : null;
      case "0806-v3-ea-identity":
        return <EaIdentityScene progress={progress} />;
      case "0806-v3-wrong-rule":
        return <WrongRuleScene progress={progress} />;
      case "0806-v3-evidence-overview":
      case "0806-v3-evidence-heading":
      case "0806-v3-evidence-history":
      case "0806-v3-evidence-year":
      case "0806-v3-evidence-result":
      case "0806-v3-evidence-number":
        return (
          <EvidenceScene
            scene={scene}
            asset={asset}
            progress={progress}
          />
        );
      case "0806-v3-risk-turn":
      case "0806-v3-risk-control":
      case "0806-v3-risk-rise":
      case "0806-v3-risk-reversal":
        return (
          <RiskScene treatment={treatment} progress={progress} />
        );
      case "0806-v3-risk-input":
      case "0806-v3-risk-alternate":
        return asset?.kind === "video" ? (
          <ProductMacroScene
            scene={scene}
            asset={asset}
            fps={fps}
            progress={progress}
          />
        ) : null;
      case "0806-v3-lesson-contrast":
        return asset?.kind === "video" ? (
          <LessonContrastScene
            scene={scene}
            asset={asset}
            fps={fps}
            progress={progress}
          />
        ) : null;
      case "0806-v3-lesson-pipeline":
        return <PipelineScene progress={progress} lesson />;
      case "0806-v3-presenter-reset":
      case "0806-v3-presenter-ending":
      case "0806-v3-clean-ending":
      default:
        return null;
    }
  })();
  if (content == null) {
    return null;
  }
  const surface = getReference0806V3Surface(treatment);
  const usesMotionWash = ![
    "0806-v3-hook-physical",
    "0806-v3-hook-presenter",
    "0806-v3-code-cinematic",
    "0806-v3-navigator-macro",
    "0806-v3-risk-input",
    "0806-v3-risk-alternate",
    "0806-v3-lesson-contrast",
    "0806-v3-demo-establishing",
    "0806-v3-demo-attach",
    "0806-v3-demo-input",
    "0806-v3-demo-strategy",
  ].includes(treatment);
  return (
    <AbsoluteFill
      data-v3-production-grade="reference-10"
      style={{
        zIndex: 18,
        filter: "saturate(0.72)",
      }}
    >
      {content}
      {usesMotionWash ? (
        <SceneMotionWash progress={progress} surface={surface} />
      ) : null}
      <SceneMotionTexture frame={frame} surface={surface} />
    </AbsoluteFill>
  );
};
