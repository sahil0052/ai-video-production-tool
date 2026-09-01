import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  Sequence,
  staticFile,
} from "remotion";
import { Video } from "@remotion/media";

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
const SERIF = '"Bodoni MT", Didot, "Times New Roman", serif';

const clamp = (value: number) => Math.min(1, Math.max(0, value));

const sceneProgress = (scene: Scene, frame: number, fps: number) => {
  const durationFrames = Math.max(
    1,
    Math.round(((scene.end_ms - scene.start_ms) / 1000) * fps),
  );
  return clamp(frame / durationFrames);
};

const ease = (value: number) =>
  Easing.bezier(0.16, 1, 0.3, 1)(clamp(value));

export const getEvidenceCameraTransform = (progress: number) => {
  if (progress < 0.24) {
    const phase = ease(progress / 0.24);
    return {
      translateX: 0,
      translateY: interpolate(phase, [0, 1], [5, -5]),
      scale: interpolate(phase, [0, 1], [1, 1.01]),
    };
  }

  if (progress < 0.68) {
    const phase = ease((progress - 0.24) / 0.44);
    return {
      translateX: interpolate(phase, [0, 1], [4, -4]),
      translateY: interpolate(phase, [0, 1], [4, -4]),
      scale: interpolate(phase, [0, 1], [1.002, 1.012]),
    };
  }

  const phase = ease((progress - 0.68) / 0.32);
  return {
    translateX: interpolate(phase, [0, 1], [4, -4]),
    translateY: interpolate(phase, [0, 1], [3, -3]),
    scale: interpolate(phase, [0, 1], [1.003, 1.012]),
  };
};

export const isReference0806Scene = (scene: Scene | undefined) =>
  Boolean(
    (scene?.treatment?.startsWith("0806-") &&
      !scene?.treatment?.startsWith("0806-v3-")) ||
      scene?.treatment === "automation-vs-risk",
  );

const findSceneAsset = (
  scene: Scene,
  assets: EditPlan["assets"],
): Asset | undefined => {
  if (scene.asset_id) {
    const exact = assets.find((asset) => asset.id === scene.asset_id);
    if (exact) {
      return exact;
    }
  }
  if (
    scene.treatment === "0806-document-scroll-in" ||
    scene.treatment === "0806-championship-evidence"
  ) {
    return assets.find(
      (asset) => asset.id === "metaquotes-atc-history-page",
    );
  }
  if (
    scene.treatment === "0806-document-transition" ||
    scene.treatment === "0806-mql5-evidence"
  ) {
    return assets.find(
      (asset) => asset.id === "mql5-atc-2008-risk-page",
    );
  }
  return undefined;
};

const RealCaptureScene: React.FC<{
  asset: Asset;
  scene: Scene;
  fps: number;
  progress: number;
  showHookHeadline?: boolean;
}> = ({ asset, scene, fps, progress, showHookHeadline = false }) => {
  const from = Math.round((scene.start_ms / 1000) * fps);
  const durationInFrames = Math.max(
    1,
    Math.round(((scene.end_ms - scene.start_ms) / 1000) * fps),
  );
  const splitHook = scene.treatment === "0806-split-hook";
  const navigator = scene.treatment === "0806-ea-label";
  const riskReversal = scene.treatment === "0806-risk-reversal";
  const framed = new Set([
    "0806-terminal-boot",
    "0806-terminal-detail-a",
    "0806-risk-turn",
    "0806-demo-setup",
  ]).has(scene.treatment ?? "");
  const punchCut =
    new Set([
      "0806-code-rule-trace",
      "automation-vs-risk",
      "0806-demo-cta",
    ]).has(scene.treatment ?? "") && progress >= 0.52;
  const objectPosition = navigator
    ? "13% 50%"
    : scene.treatment === "0806-demo-cta"
      ? punchCut
        ? "66% 70%"
        : "48% 72%"
      : scene.treatment === "0806-code-scroll"
        ? "58% 48%"
        : punchCut
          ? "36% 48%"
          : "48% 50%";
  const cameraScale =
    (framed ? 1.01 : 1.07) +
    progress * (framed ? 0.18 : 0.23) +
    (punchCut
      ? scene.treatment === "0806-demo-cta"
        ? 0.13
        : 0.08
      : 0);
  const panDirection = new Set([
    "0806-code-rule-trace",
    "0806-terminal-detail-b",
    "0806-risk-reversal",
    "0806-demo-cta",
  ]).has(scene.treatment ?? "")
    ? -1
    : 1;
  const panX =
    (progress - 0.5) * (framed ? 50 : 75) * panDirection;
  const captureInset = framed
    ? { left: 50, right: 50, top: 170, bottom: 170 }
    : { left: 0, right: 0, top: 0, bottom: 0 };
  return (
    <AbsoluteFill
      data-real-capture={asset.id}
      data-0806-scene={scene.treatment ?? ""}
      style={{
        zIndex: 18,
        height: splitHook ? "58%" : "100%",
        overflow: "hidden",
        background: framed ? "#dfe4e2" : "#222b2f",
      }}
    >
      <div
        style={{
          position: "absolute",
          ...captureInset,
          overflow: "hidden",
          borderRadius: framed ? 18 : 0,
          boxShadow: framed
            ? "0 36px 86px rgba(18,25,28,0.32)"
            : undefined,
          background: "#11171a",
        }}
      >
        <Sequence
          from={from}
          durationInFrames={durationInFrames}
          premountFor={fps}
        >
          <Video
            src={staticFile(asset.path)}
            muted
            objectFit="cover"
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
              objectPosition,
              transform: `translateX(${panX}px) scale(${cameraScale})`,
              filter:
                "contrast(0.9) saturate(1.25) brightness(1.46)",
            }}
          />
        </Sequence>
        <AbsoluteFill
          style={{
            background: "rgba(218,228,230,0.13)",
            mixBlendMode: "screen",
            pointerEvents: "none",
          }}
        />
      </div>
      {showHookHeadline ? (
        <div
          style={{
            position: "absolute",
            left: 48,
            right: 48,
            bottom: 154,
            color: "#f5f1e9",
            textAlign: "center",
            fontFamily: SERIF,
            fontWeight: 500,
            fontSize: 70,
            lineHeight: 0.91,
            letterSpacing: "-0.055em",
            textShadow: "0 5px 28px rgba(0,0,0,0.82)",
          }}
        >
          <div>CAN A ROBOT</div>
          <div>CHOOSE SAFE RISK?</div>
        </div>
      ) : null}
      {riskReversal ? (
        <AbsoluteFill
          style={{
            background:
              "linear-gradient(180deg, rgba(10,5,7,0.08), rgba(28,8,12,0.52))",
            pointerEvents: "none",
          }}
        >
          <svg
            viewBox="0 0 1080 1920"
            style={{ position: "absolute", inset: 0 }}
          >
            <path
              d="M135 1340 C360 1120 590 1080 825 740"
              fill="none"
              stroke="#e47782"
              strokeWidth="14"
              strokeLinecap="round"
            />
            <path
              d="M825 740 L740 770 M825 740 L804 835"
              fill="none"
              stroke="#e47782"
              strokeWidth="14"
              strokeLinecap="round"
            />
            <path
              d="M825 740 C770 990 660 1190 430 1425"
              fill="none"
              stroke="#f0c96b"
              strokeWidth="10"
              strokeDasharray="24 18"
              strokeLinecap="round"
            />
          </svg>
          <div
            style={{
              position: "absolute",
              left: 48,
              right: 48,
              bottom: 120,
              color: "#f7f1e8",
              fontFamily: SANS,
              fontSize: 64,
              fontWeight: 800,
              lineHeight: 0.94,
              letterSpacing: "-0.045em",
              textShadow: "0 5px 28px rgba(0,0,0,0.9)",
            }}
          >
            THE DIRECTION
            <br />
            REVERSES.
          </div>
        </AbsoluteFill>
      ) : null}
    </AbsoluteFill>
  );
};

const SourceAttribution: React.FC<{
  asset?: Asset;
  label?: string;
}> = ({ asset, label }) => (
  <div
    style={{
      position: "absolute",
      left: 42,
      right: 42,
      bottom: 34,
      display: "flex",
      justifyContent: "space-between",
      color: "rgba(255,255,255,0.66)",
      background: "rgba(9,12,14,0.74)",
      borderRadius: 6,
      padding: "10px 14px",
      fontFamily: MONO,
      fontSize: 18,
      letterSpacing: "0.08em",
      textTransform: "uppercase",
    }}
  >
    <span>{label ?? "DIRECT OFFICIAL PAGE CAPTURE"}</span>
    <span>{asset?.source_url?.replace(/^https?:\/\//, "") ?? ""}</span>
  </div>
);

const TechnicalLabel: React.FC<{
  children: React.ReactNode;
  color?: string;
  top?: number;
}> = ({ children, color = "#A6DBE6", top = 42 }) => (
  <div
    style={{
      position: "absolute",
      top,
      left: 42,
      padding: "7px 11px",
      borderRadius: 4,
      color,
      background: "rgba(0,0,0,0.78)",
      fontFamily: MONO,
      fontSize: 19,
      letterSpacing: "0.11em",
      textTransform: "uppercase",
    }}
  >
    {children}
  </div>
);

const FineGrid: React.FC<{ opacity?: number }> = ({ opacity = 0.16 }) => (
  <AbsoluteFill
    style={{
      opacity,
      backgroundImage:
        "linear-gradient(rgba(116,170,184,0.18) 1px, transparent 1px), linear-gradient(90deg, rgba(116,170,184,0.18) 1px, transparent 1px)",
      backgroundSize: "58px 58px",
    }}
  />
);

const HookScene: React.FC<{ progress: number }> = ({ progress }) => {
  const reveal = ease(progress / 0.36);
  const chipRotate = interpolate(progress, [0, 1], [-8, -3]);
  const chipScale = interpolate(progress, [0, 1], [1.08, 1.16]);
  const headlineY = interpolate(reveal, [0, 1], [34, 0]);
  return (
    <AbsoluteFill
      data-0806-scene="0806-split-hook"
      style={{
        zIndex: 18,
        height: "58%",
        overflow: "hidden",
        background:
          "radial-gradient(circle at 50% 12%, #24333b 0%, #0d1318 42%, #050607 82%)",
      }}
    >
      <FineGrid opacity={0.11} />
      <div
        style={{
          position: "absolute",
          left: 130,
          top: 74,
          width: 820,
          height: 515,
          transform: `rotate(${chipRotate}deg) scale(${chipScale})`,
          transformOrigin: "50% 50%",
          filter: "drop-shadow(0 34px 52px rgba(0,0,0,0.62))",
        }}
      >
        <div
          style={{
            position: "absolute",
            inset: 58,
            borderRadius: 34,
            border: "2px solid rgba(214,230,234,0.74)",
            background:
              "linear-gradient(145deg, #dfe6e7 0%, #839399 43%, #d4dcdd 100%)",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 42,
              borderRadius: 20,
              border: "3px solid rgba(26,38,43,0.55)",
              background:
                "linear-gradient(155deg, #52636a, #d6dedf 48%, #87999f)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              color: "#172126",
            }}
          >
            <div
              style={{
                fontFamily: SANS,
                fontWeight: 800,
                fontSize: 36,
                letterSpacing: "0.14em",
              }}
            >
              EXPERT ADVISOR
            </div>
            <div
              style={{
                marginTop: 14,
                fontFamily: MONO,
                fontSize: 92,
                lineHeight: 0.9,
              }}
            >
              EA
            </div>
            <div
              style={{
                marginTop: 18,
                fontFamily: MONO,
                fontSize: 20,
                letterSpacing: "0.12em",
              }}
            >
              RULES → EXECUTION
            </div>
          </div>
        </div>
        {Array.from({ length: 11 }).map((_, index) => (
          <div
            key={index}
            style={{
              position: "absolute",
              left: 28 + index * 72,
              top: index % 2 === 0 ? 17 : 476,
              width: 42,
              height: 82,
              borderRadius: 7,
              background: "#9aa8ad",
              boxShadow: "inset 0 0 0 1px rgba(255,255,255,0.35)",
            }}
          />
        ))}
      </div>
      <div
        style={{
          position: "absolute",
          left: 58,
          right: 58,
          bottom: 48,
          opacity: reveal,
          transform: `translateY(${headlineY}px)`,
          color: "#f4f0e8",
          textAlign: "center",
          fontFamily: SERIF,
          fontWeight: 500,
          fontSize: 78,
          lineHeight: 0.91,
          letterSpacing: "-0.055em",
          textShadow: "0 4px 24px rgba(0,0,0,0.72)",
        }}
      >
        <div>CAN A ROBOT</div>
        <div>CHOOSE SAFE RISK?</div>
      </div>
      <TechnicalLabel color="#D9E6E8" top={28}>
        ILLUSTRATIVE SYSTEM OBJECT
      </TechnicalLabel>
    </AbsoluteFill>
  );
};

const codeLines = [
  "input double RiskSetting = SAFE;",
  "bool rulesValid = CheckRules();",
  "bool riskAllowed = CheckRisk();",
  "if (rulesValid && riskAllowed) {",
  "  trade.Execute(signal);",
  "} else {",
  "  system.Wait();",
  "}",
];

const CodeScene: React.FC<{
  progress: number;
  treatment: string;
}> = ({ progress, treatment }) => {
  const lineFloat = progress * (codeLines.length + 1);
  const activeLine = Math.min(
    codeLines.length - 1,
    Math.max(0, Math.floor(lineFloat)),
  );
  const boot = treatment === "0806-terminal-boot";
  const scroll = treatment === "0806-code-scroll";
  const cameraScale = interpolate(progress, [0, 1], [1.02, 1.075]);
  const cameraY = interpolate(progress, [0, 1], [18, scroll ? -62 : -18]);
  const visibleLines = boot
    ? Math.max(1, Math.ceil(progress * 5))
    : codeLines.length;
  return (
    <AbsoluteFill
      data-0806-scene={treatment}
      style={{
        zIndex: 18,
        background:
          "radial-gradient(circle at 78% 16%, rgba(38,72,81,0.28), transparent 36%), #050708",
        overflow: "hidden",
      }}
    >
      <FineGrid opacity={0.075} />
      <div
        style={{
          position: "absolute",
          inset: "102px 46px 142px",
          borderRadius: 18,
          overflow: "hidden",
          background: "#05080a",
          border: "1px solid rgba(159,191,199,0.22)",
          boxShadow: "0 32px 80px rgba(0,0,0,0.55)",
          transform: `translateY(${cameraY}px) scale(${cameraScale})`,
        }}
      >
        <div
          style={{
            height: 66,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "0 22px",
            background: "#11181c",
            borderBottom: "1px solid rgba(255,255,255,0.08)",
            color: "#9daeb4",
            fontFamily: MONO,
            fontSize: 18,
          }}
        >
          <span style={{ color: "#d86c72" }}>●</span>
          <span style={{ color: "#d8bd70" }}>●</span>
          <span style={{ color: "#73ba95" }}>●</span>
          <span style={{ marginLeft: 14 }}>ExpertAdvisor.mq5</span>
          <span style={{ marginLeft: "auto", color: "#6f858d" }}>
            METAEDITOR • DEMO
          </span>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "58px 1fr",
            padding: "54px 22px",
            fontFamily: MONO,
            fontSize: 33,
            lineHeight: 1.72,
          }}
        >
          {codeLines.slice(0, visibleLines).map((line, index) => {
            const highlighted = !boot && index === activeLine;
            const wrongLine =
              treatment === "0806-code-risk-lesson" && index === 0;
            return (
              <div
                key={line}
                style={{ display: "contents" }}
              >
                <div
                  style={{
                    color: "#4e626a",
                    textAlign: "right",
                    paddingRight: 18,
                  }}
                >
                  {String(index + 1).padStart(2, "0")}
                </div>
                <div
                  style={{
                    position: "relative",
                    whiteSpace: "pre",
                    color: wrongLine ? "#e48088" : "#dbe4e6",
                    background: highlighted
                      ? "linear-gradient(90deg, rgba(97,174,191,0.26), rgba(97,174,191,0.02))"
                      : "transparent",
                    boxShadow: highlighted
                      ? "inset 3px 0 #84c7d6"
                      : undefined,
                    paddingLeft: 16,
                  }}
                >
                  {line}
                  {highlighted ? (
                    <span
                      style={{
                        position: "absolute",
                        right: 16,
                        color: "#a9dce7",
                        fontSize: 18,
                        letterSpacing: "0.08em",
                      }}
                    >
                      ACTIVE RULE
                    </span>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
        <div
          style={{
            position: "absolute",
            left: 24,
            right: 24,
            bottom: 24,
            height: 170,
            borderTop: "1px solid rgba(255,255,255,0.09)",
            padding: "22px 16px",
            color: "#92a5ab",
            fontFamily: MONO,
            fontSize: 20,
            lineHeight: 1.6,
          }}
        >
          <div>
            <span style={{ color: "#6da5b2" }}>SYSTEM</span> rules loaded
          </div>
          <div>
            <span style={{ color: "#6da5b2" }}>STATUS</span>{" "}
            {boot ? "initializing…" : "waiting for valid input"}
          </div>
          <div>
            <span style={{ color: "#6da5b2" }}>RESULTS</span> not shown
          </div>
        </div>
      </div>
      <TechnicalLabel>
        ILLUSTRATIVE LOGIC • NO TRADING RESULT
      </TechnicalLabel>
    </AbsoluteFill>
  );
};

export const LegacyEvidencePage: React.FC<{
  asset?: Asset;
  progress: number;
  treatment: string;
}> = ({ asset, progress, treatment }) => {
  const documentProgress = ease(progress);
  const scale = interpolate(documentProgress, [0, 1], [1.0, 1.075]);
  const y = interpolate(documentProgress, [0, 1], [22, -34]);
  const isMql5 =
    treatment === "0806-mql5-evidence" ||
    treatment === "0806-document-transition";
  const focusTop =
    treatment === "0806-ea-label"
      ? 885
      : isMql5
        ? 465
        : 810;
  const focusHeight =
    treatment === "0806-ea-label"
      ? 126
      : isMql5
        ? 108
        : 136;
  const focusOpacity = interpolate(
    progress,
    [0.16, 0.32, 0.92, 1],
    [0, 1, 1, 0.72],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  if (!asset) {
    return (
      <AbsoluteFill
        data-0806-scene={treatment}
        style={{
          zIndex: 18,
          background: "#090b0d",
          color: "white",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: MONO,
          fontSize: 30,
        }}
      >
        SOURCE CAPTURE UNAVAILABLE
      </AbsoluteFill>
    );
  }
  const source = staticFile(asset.path);
  return (
    <AbsoluteFill
      data-0806-scene={treatment}
      style={{ zIndex: 18, overflow: "hidden", background: "#090b0d" }}
    >
      <Img
        src={source}
        style={{
          position: "absolute",
          inset: -80,
          width: "calc(100% + 160px)",
          height: "calc(100% + 160px)",
          objectFit: "cover",
          filter: "blur(34px) brightness(0.34) saturate(0.6)",
          transform: "scale(1.16)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 30,
          right: 30,
          top: 176,
          bottom: 176,
          overflow: "hidden",
          borderRadius: 12,
          background: "#fff",
          boxShadow: "0 42px 90px rgba(0,0,0,0.52)",
          transform: `translateY(${y}px) scale(${scale})`,
        }}
      >
        <Img
          src={source}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            background: "#fff",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 50,
            right: 50,
            top: focusTop,
            height: focusHeight,
            border: `4px solid ${isMql5 ? "#d7b45f" : "#6daebe"}`,
            background: isMql5
              ? "rgba(223,188,91,0.10)"
              : "rgba(89,163,181,0.09)",
            boxShadow: `0 0 0 999px rgba(0,0,0,${
              0.08 + focusOpacity * 0.06
            })`,
            opacity: focusOpacity,
          }}
        />
      </div>
      <TechnicalLabel color={isMql5 ? "#e0c77e" : "#a6d6df"}>
        {isMql5 ? "PRIMARY SOURCE • MQL5" : "OFFICIAL METAQUOTES SOURCE"}
      </TechnicalLabel>
      <SourceAttribution asset={asset} />
    </AbsoluteFill>
  );
};

export const EvidencePage: React.FC<{
  asset?: Asset;
  progress: number;
  treatment: string;
}> = ({ asset, progress, treatment }) => {
  if (!asset) {
    return (
      <AbsoluteFill
        data-0806-scene={treatment}
        style={{
          zIndex: 18,
          background: "#090b0d",
          color: "white",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: MONO,
          fontSize: 30,
        }}
      >
        SOURCE CAPTURE UNAVAILABLE
      </AbsoluteFill>
    );
  }
  const documentProgress = ease(progress);
  const isExpertAdvisor = treatment === "0806-ea-label";
  const isMql5 = treatment === "0806-mql5-evidence";
  const focusX = isMql5 ? 850 : 720;
  const focusY = isExpertAdvisor ? 955 : isMql5 ? 370 : 900;
  const focusTargetY = isExpertAdvisor ? 850 : isMql5 ? 680 : 820;
  const zoomTop = 330;
  const zoomWidth = interpolate(
    documentProgress,
    [0, 1],
    [2380, 2510],
  );
  const imageScale = zoomWidth / 1440;
  const imageLeft =
    540 -
    focusX * imageScale +
    interpolate(documentProgress, [0, 1], [360, -360]);
  const imageTop =
    focusTargetY -
    zoomTop -
    focusY * imageScale +
    interpolate(documentProgress, [0, 1], [24, -26]);
  const focusHeight = isExpertAdvisor ? 164 : isMql5 ? 226 : 176;
  const focusOpacity = interpolate(
    progress,
    [0.12, 0.26, 0.92, 1],
    [0, 1, 1, 0.76],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const source = staticFile(asset.path);
  return (
    <AbsoluteFill
      data-0806-scene={treatment}
      style={{ zIndex: 18, overflow: "hidden", background: "#090b0d" }}
    >
      <Img
        src={source}
        style={{
          position: "absolute",
          inset: -70,
          width: "calc(100% + 140px)",
          height: "calc(100% + 140px)",
          objectFit: "cover",
          filter: "blur(34px) brightness(0.34) saturate(0.6)",
          transform: "scale(1.16)",
        }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 0,
          height: 410,
          overflow: "hidden",
          background: "#fff",
        }}
      >
        <Img
          src={source}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            background: "#fff",
            transform: `translateY(${interpolate(
              documentProgress,
              [0, 1],
              [8, -12],
            )}px) scale(1.02)`,
          }}
        />
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "linear-gradient(180deg, transparent 52%, rgba(5,7,8,0.82) 100%)",
          }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: zoomTop,
          bottom: 62,
          overflow: "hidden",
          background: "#fff",
          borderTop: "3px solid rgba(255,255,255,0.72)",
          boxShadow: "0 -18px 46px rgba(0,0,0,0.45)",
        }}
      >
        <Img
          src={source}
          style={{
            position: "absolute",
            width: zoomWidth,
            height: "auto",
            maxWidth: "none",
            left: imageLeft,
            top: imageTop,
          }}
        />
        <div
          style={{
            position: "absolute",
            left: 32,
            right: 32,
            top: focusTargetY - zoomTop - focusHeight / 2,
            height: focusHeight,
            border: `5px solid ${isMql5 ? "#d7b45f" : "#6daebe"}`,
            background: isMql5
              ? "rgba(223,188,91,0.08)"
              : "rgba(89,163,181,0.07)",
            boxShadow: "0 0 0 999px rgba(7,9,10,0.13)",
            opacity: focusOpacity,
          }}
        />
      </div>
      <TechnicalLabel color={isMql5 ? "#e0c77e" : "#a6d6df"}>
        {isMql5 ? "PRIMARY SOURCE • MQL5" : "OFFICIAL METAQUOTES SOURCE"}
      </TechnicalLabel>
      <SourceAttribution asset={asset} />
    </AbsoluteFill>
  );
};

const EvidencePageV2: React.FC<{
  asset?: Asset;
  progress: number;
  treatment: string;
}> = ({ asset, progress, treatment }) => {
  if (!asset) {
    return (
      <AbsoluteFill
        data-0806-scene={treatment}
        style={{
          zIndex: 18,
          background: "#eef1f0",
          color: "#172126",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: MONO,
          fontSize: 30,
        }}
      >
        SOURCE CAPTURE UNAVAILABLE
      </AbsoluteFill>
    );
  }
  const isMql5 = treatment === "0806-mql5-evidence";
  const fullPage = progress < 0.24;
  const detailPunch = progress >= 0.68;
  const focusX = isMql5
    ? detailPunch
      ? 1050
      : 820
    : 720;
  const focusY = isMql5
    ? detailPunch
      ? 400
      : 355
    : 900;
  const zoomWidth = isMql5
    ? detailPunch
      ? 2000
      : 1900
    : detailPunch
      ? 2300
      : 1750;
  const imageScale = zoomWidth / 1440;
  const imageLeft = 540 - focusX * imageScale;
  const imageTop = 860 - focusY * imageScale;
  const camera = getEvidenceCameraTransform(progress);
  const focusOpacity = interpolate(
    progress,
    [0.24, 0.32, 0.92, 1],
    [0, 1, 1, 0.76],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    },
  );
  const source = staticFile(asset.path);
  return (
    <AbsoluteFill
      data-0806-scene={treatment}
      style={{ zIndex: 18, overflow: "hidden", background: "#eef1f0" }}
    >
      {fullPage ? (
        <div
          style={{
            position: "absolute",
            left: 56,
            right: 56,
            top: 112,
            bottom: 116,
            overflow: "hidden",
            borderRadius: 12,
            background: "#fff",
            boxShadow: "0 30px 80px rgba(24,34,38,0.20)",
          }}
        >
          <Img
            src={source}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              background: "#fff",
              transform: `translate3d(${camera.translateX}px, ${camera.translateY}px, 0) scale(${camera.scale})`,
            }}
          />
        </div>
      ) : (
        <div
          style={{
            position: "absolute",
            inset: "96px 0 112px",
            overflow: "hidden",
            background: "#fff",
            boxShadow: "0 24px 70px rgba(24,34,38,0.20)",
          }}
        >
          <Img
            src={source}
            style={{
              position: "absolute",
              width: zoomWidth,
              height: "auto",
              maxWidth: "none",
              left: imageLeft,
              top: imageTop,
              transformOrigin: `${focusX * imageScale}px ${focusY * imageScale}px`,
              transform: `translate3d(${camera.translateX}px, ${camera.translateY}px, 0) scale(${camera.scale})`,
            }}
          />
          <div
            style={{
              position: "absolute",
              left: detailPunch && isMql5 ? 36 : detailPunch ? 92 : 46,
              right: detailPunch && isMql5 ? 36 : detailPunch ? 92 : 46,
              top: isMql5 ? 750 : 720,
              height: isMql5 ? 190 : 230,
              border: `6px solid ${isMql5 ? "#c89d30" : "#4f9caf"}`,
              background: isMql5
                ? "rgba(221,176,57,0.08)"
                : "rgba(71,153,174,0.07)",
              boxShadow: "0 0 0 999px rgba(236,240,239,0.08)",
              opacity: focusOpacity,
            }}
          />
        </div>
      )}
      <TechnicalLabel color={isMql5 ? "#f2d987" : "#b8e5ed"}>
        {isMql5 ? "PRIMARY SOURCE • MQL5" : "OFFICIAL METAQUOTES SOURCE"}
      </TechnicalLabel>
      <SourceAttribution asset={asset} />
    </AbsoluteFill>
  );
};

const IntertitleScene: React.FC<{
  progress: number;
  treatment: string;
  eyebrow: string;
  title: string;
  accent: string;
  light?: boolean;
}> = ({ progress, treatment, eyebrow, title, accent, light = false }) => {
  const reveal = ease(progress / 0.72);
  const lightCanvas = light || treatment.startsWith("0806-document-");
  return (
    <AbsoluteFill
      data-0806-scene={treatment}
      style={{
        zIndex: 18,
        overflow: "hidden",
        background: lightCanvas
          ? "radial-gradient(circle at 82% 18%, rgba(68,126,140,0.18), transparent 34%), #e9eceb"
          : "radial-gradient(circle at 82% 18%, rgba(83,118,126,0.22), transparent 34%), #0b0d0f",
        color: lightCanvas ? "#101619" : "#f4f0e8",
      }}
    >
      <FineGrid opacity={0.08} />
      <div
        style={{
          position: "absolute",
          left: 64,
          right: 64,
          top: 510,
          opacity: reveal,
          transform: `translateY(${(1 - reveal) * 42}px)`,
        }}
      >
        <div
          style={{
            color: accent,
            fontFamily: MONO,
            fontSize: 22,
            letterSpacing: "0.13em",
          }}
        >
          {eyebrow}
        </div>
        <div
          style={{
            marginTop: 34,
            fontFamily: SERIF,
            fontSize: 86,
            lineHeight: 0.92,
            letterSpacing: "-0.055em",
            whiteSpace: "pre-line",
          }}
        >
          {title}
        </div>
        <div
          style={{
            marginTop: 42,
            width: `${Math.max(4, reveal * 100)}%`,
            height: 4,
            background: accent,
          }}
        />
      </div>
      {lightCanvas ? (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 78,
            background: "#111719",
          }}
        />
      ) : null}
      <SourceAttribution label="DIRECT SOURCE PIXELS FOLLOW" />
    </AbsoluteFill>
  );
};

const WrongRuleFlow: React.FC<{ progress: number }> = ({ progress }) => {
  const draw = ease(progress / 0.72);
  const branch = ease((progress - 0.36) / 0.48);
  return (
    <AbsoluteFill
      data-0806-scene="0806-wrong-rule-flow"
      style={{
        zIndex: 18,
        background:
          "radial-gradient(circle at 50% 44%, rgba(122,190,201,0.22), transparent 46%), #66313c",
        color: "white",
      }}
    >
      <FineGrid opacity={0.09} />
      <TechnicalLabel>ILLUSTRATIVE RULE FLOW</TechnicalLabel>
      <div
        style={{
          position: "absolute",
          top: 178,
          left: 64,
          right: 64,
          fontFamily: SANS,
          fontSize: 62,
          fontWeight: 800,
          letterSpacing: "-0.045em",
        }}
      >
        WHAT IF THE RULE
        <br />
        IS WRONG?
      </div>
      <svg
        viewBox="0 0 1080 1280"
        style={{
          position: "absolute",
          left: 0,
          top: 410,
          width: 1080,
          height: 1280,
        }}
      >
        <defs>
          <filter id="flow-glow">
            <feGaussianBlur stdDeviation="7" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <path
          d="M540 170 L540 420 L540 650"
          fill="none"
          stroke="#84c7d6"
          strokeWidth="7"
          strokeDasharray="480"
          strokeDashoffset={480 * (1 - draw)}
        />
        <path
          d="M540 650 C540 790 760 770 760 930"
          fill="none"
          stroke="#dc6c76"
          strokeWidth="8"
          strokeDasharray="430"
          strokeDashoffset={430 * (1 - branch)}
          filter="url(#flow-glow)"
        />
        <path
          d="M540 650 C540 790 320 770 320 930"
          fill="none"
          stroke="#7d949b"
          strokeWidth="5"
          strokeDasharray="430"
          strokeDashoffset={430 * (1 - branch)}
        />
        {[
          [540, 110, "MARKET DATA", "#172126", "#9aafb5"],
          [540, 470, "PRESET RULE", "#15282d", "#84c7d6"],
          [320, 1010, "WAIT", "#161b1e", "#71878e"],
          [760, 1010, "WRONG ACTION", "#2b1116", "#dc6c76"],
        ].map(([x, y, label, fill, stroke]) => (
          <g key={String(label)}>
            <rect
              x={Number(x) - 190}
              y={Number(y) - 70}
              width="380"
              height="140"
              rx="16"
              fill={String(fill)}
              stroke={String(stroke)}
              strokeWidth="3"
            />
            <text
              x={Number(x)}
              y={Number(y) + 10}
              textAnchor="middle"
              fill="white"
              fontFamily="Share Tech Mono"
              fontSize="29"
            >
              {String(label)}
            </text>
          </g>
        ))}
      </svg>
      <div
        style={{
          position: "absolute",
          left: 64,
          bottom: 72,
          color: "#8d9da2",
          fontFamily: MONO,
          fontSize: 19,
          letterSpacing: "0.08em",
        }}
      >
        LOGIC DIAGRAM • NO PERFORMANCE CLAIM
      </div>
    </AbsoluteFill>
  );
};

const RiskScene: React.FC<{
  progress: number;
  treatment: string;
}> = ({ progress, treatment }) => {
  const reversal = treatment === "0806-risk-reversal";
  const turn = treatment === "0806-risk-turn";
  const amount = turn
    ? interpolate(progress, [0, 1], [0.18, 0.38])
    : reversal
      ? interpolate(progress, [0, 0.48, 1], [0.44, 0.9, 0.28])
      : interpolate(progress, [0, 1], [0.28, 0.82]);
  const knobX = 132 + amount * 704;
  const pathProgress = ease(progress);
  return (
    <AbsoluteFill
      data-0806-scene={treatment}
      style={{
        zIndex: 18,
        background:
          "radial-gradient(circle at 76% 26%, rgba(100,40,48,0.24), transparent 38%), #050607",
        color: "white",
      }}
    >
      <FineGrid opacity={0.07} />
      <TechnicalLabel color="#e39aa1">
        ILLUSTRATIVE RISK INPUT
      </TechnicalLabel>
      <div
        style={{
          position: "absolute",
          top: 168,
          left: 64,
          right: 64,
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 66,
          lineHeight: 0.94,
          letterSpacing: "-0.05em",
        }}
      >
        {reversal ? (
          <>
            THE DIRECTION
            <br />
            REVERSES.
          </>
        ) : (
          <>
            RISK CHANGES
            <br />
            THE OUTCOME.
          </>
        )}
      </div>
      <div
        style={{
          position: "absolute",
          top: 510,
          left: 72,
          right: 72,
          height: 320,
          borderRadius: 22,
          border: "1px solid rgba(226,130,141,0.34)",
          background: "rgba(21,10,13,0.86)",
          padding: "48px 58px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontFamily: MONO,
            fontSize: 22,
            color: "#c7a2a7",
            letterSpacing: "0.08em",
          }}
        >
          <span>RISK INPUT</span>
          <span>{amount > 0.7 ? "AGGRESSIVE" : "REVIEW REQUIRED"}</span>
        </div>
        <div
          style={{
            position: "relative",
            marginTop: 76,
            height: 12,
            borderRadius: 8,
            background:
              "linear-gradient(90deg, #7ca7af 0%, #d6b35e 58%, #dc6c76 100%)",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: -20,
              left: knobX,
              width: 52,
              height: 52,
              marginLeft: -26,
              borderRadius: "50%",
              background: "#f4f0e8",
              border: "6px solid #51232a",
              boxShadow: "0 10px 24px rgba(0,0,0,0.45)",
            }}
          />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: 44,
            color: "#7e9298",
            fontFamily: MONO,
            fontSize: 18,
          }}
        >
          <span>LOWER</span>
          <span>MANUAL DECISION</span>
          <span>HIGHER</span>
        </div>
      </div>
      <svg
        viewBox="0 0 920 520"
        style={{
          position: "absolute",
          left: 80,
          top: 930,
          width: 920,
          height: 520,
        }}
      >
        <path
          d={
            reversal
              ? "M30 400 C180 360 260 250 390 180 C515 112 620 88 710 170 C785 240 810 330 885 430"
              : "M30 400 C200 360 280 285 400 245 C520 205 650 165 885 90"
          }
          fill="none"
          stroke={reversal ? "#df747e" : "#d6b35e"}
          strokeWidth="12"
          strokeLinecap="round"
          pathLength="1"
          strokeDasharray="1"
          strokeDashoffset={1 - pathProgress}
        />
        <path
          d="M30 455 H890"
          stroke="#304047"
          strokeWidth="2"
          strokeDasharray="8 16"
        />
      </svg>
      <div
        style={{
          position: "absolute",
          left: 72,
          bottom: 78,
          fontFamily: MONO,
          fontSize: 19,
          color: "#8b9a9f",
          letterSpacing: "0.08em",
        }}
      >
        CONCEPTUAL CONTROL • NO BALANCE OR PROFIT DATA
      </div>
    </AbsoluteFill>
  );
};

const LessonScene: React.FC<{ progress: number }> = ({ progress }) => {
  const highlight = Math.floor(progress * 4) % 4;
  return (
    <AbsoluteFill
      data-0806-scene="automation-vs-risk"
      style={{
        zIndex: 18,
        background: "#050607",
        color: "white",
      }}
    >
      <FineGrid opacity={0.08} />
      <TechnicalLabel>FINAL TECHNICAL LESSON • ILLUSTRATIVE</TechnicalLabel>
      <div
        style={{
          position: "absolute",
          top: 165,
          left: 58,
          right: 58,
          fontFamily: SANS,
          fontWeight: 800,
          fontSize: 63,
          lineHeight: 0.96,
          letterSpacing: "-0.045em",
        }}
      >
        AUTOMATION FOLLOWS RULES.
        <br />
        RISK IS STILL AN INPUT.
      </div>
      <div
        style={{
          position: "absolute",
          left: 54,
          right: 54,
          top: 470,
          bottom: 180,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 22,
        }}
      >
        <div
          style={{
            borderRadius: 20,
            border: "1px solid rgba(125,173,184,0.38)",
            background: "rgba(10,21,25,0.9)",
            padding: "34px 28px",
          }}
        >
          <div
            style={{
              color: "#87c5d3",
              fontFamily: MONO,
              fontSize: 21,
              letterSpacing: "0.1em",
            }}
          >
            RULE ENGINE
          </div>
          {[
            "READ SIGNAL",
            "CHECK RULES",
            "CHECK INPUT",
            "EXECUTE / WAIT",
          ].map((item, index) => (
            <div
              key={item}
              style={{
                marginTop: 38,
                padding: "24px 20px",
                borderRadius: 10,
                color: index === highlight ? "#fff" : "#819197",
                background:
                  index === highlight
                    ? "rgba(91,154,169,0.22)"
                    : "rgba(255,255,255,0.025)",
                boxShadow:
                  index === highlight
                    ? "inset 3px 0 #87c5d3"
                    : undefined,
                fontFamily: MONO,
                fontSize: 24,
              }}
            >
              {String(index + 1).padStart(2, "0")} {item}
            </div>
          ))}
        </div>
        <div
          style={{
            borderRadius: 20,
            border: "1px solid rgba(218,105,117,0.38)",
            background: "rgba(29,11,15,0.9)",
            padding: "34px 28px",
          }}
        >
          <div
            style={{
              color: "#de7a84",
              fontFamily: MONO,
              fontSize: 21,
              letterSpacing: "0.1em",
            }}
          >
            RISK INPUT
          </div>
          <div
            style={{
              marginTop: 68,
              color: "#f4f0e8",
              fontFamily: SANS,
              fontWeight: 800,
              fontSize: 45,
              lineHeight: 1.02,
            }}
          >
            NOT CHOSEN
            <br />
            BY EMOTION.
          </div>
          <div
            style={{
              marginTop: 88,
              height: 14,
              borderRadius: 8,
              background:
                "linear-gradient(90deg, #769ba3, #d1b25e 60%, #d96c77)",
            }}
          />
          <div
            style={{
              marginTop: 64,
              color: "#d9aeb3",
              fontFamily: SANS,
              fontSize: 34,
              fontWeight: 700,
              lineHeight: 1.12,
            }}
          >
            SAFE RISK MUST
            <br />
            BE SET EXPLICITLY.
          </div>
        </div>
      </div>
      <SourceAttribution label="EVIDENCE-DERIVED CONCEPT • NO RESULT CLAIM" />
    </AbsoluteFill>
  );
};

const DemoScene: React.FC<{
  progress: number;
  treatment: string;
}> = ({ progress, treatment }) => {
  const cursorX = interpolate(progress, [0, 0.55, 0.78, 1], [770, 735, 540, 540]);
  const cursorY = interpolate(progress, [0, 0.55, 0.78, 1], [420, 970, 1180, 1180]);
  const clicked = progress > 0.78;
  const setup = treatment === "0806-demo-setup";
  return (
    <AbsoluteFill
      data-0806-scene={treatment}
      style={{
        zIndex: 18,
        background:
          "radial-gradient(circle at 80% 10%, rgba(48,81,89,0.24), transparent 40%), #050607",
        color: "white",
      }}
    >
      <FineGrid opacity={0.07} />
      <TechnicalLabel color="#9fd2dc">
        ILLUSTRATIVE PRODUCT DEMO • NO RESULTS
      </TechnicalLabel>
      <div
        style={{
          position: "absolute",
          inset: "128px 38px 126px",
          borderRadius: 18,
          overflow: "hidden",
          border: "1px solid rgba(147,180,188,0.26)",
          background: "#0b1013",
          boxShadow: "0 34px 90px rgba(0,0,0,0.6)",
        }}
      >
        <div
          style={{
            height: 70,
            display: "flex",
            alignItems: "center",
            padding: "0 24px",
            gap: 22,
            color: "#9aabb0",
            background: "#141b1f",
            fontFamily: MONO,
            fontSize: 18,
          }}
        >
          <span>META TRADING TERMINAL</span>
          <span style={{ color: "#73939b" }}>DEMO MODE</span>
          <span style={{ marginLeft: "auto" }}>Expert Advisor</span>
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "64% 36%",
            height: "calc(100% - 70px)",
          }}
        >
          <div
            style={{
              position: "relative",
              borderRight: "1px solid rgba(255,255,255,0.08)",
              background:
                "linear-gradient(180deg, rgba(19,31,36,0.9), rgba(6,10,12,0.96))",
            }}
          >
            <svg
              viewBox="0 0 620 900"
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
            >
              {Array.from({ length: 10 }).map((_, index) => (
                <line
                  key={`h-${index}`}
                  x1="0"
                  x2="620"
                  y1={90 + index * 72}
                  y2={90 + index * 72}
                  stroke="#223239"
                  strokeWidth="1"
                />
              ))}
              <path
                d="M30 560 C110 500 160 535 225 440 C300 330 360 390 430 265 C490 170 545 235 600 150"
                fill="none"
                stroke="#89b8c3"
                strokeWidth="5"
                pathLength="1"
                strokeDasharray="1"
                strokeDashoffset={1 - ease(progress)}
              />
              {Array.from({ length: 12 }).map((_, index) => {
                const x = 42 + index * 47;
                const up = index % 3 !== 1;
                const y = 610 - index * 34 + (index % 2) * 50;
                return (
                  <g key={index}>
                    <line
                      x1={x}
                      x2={x}
                      y1={y - 34}
                      y2={y + 46}
                      stroke={up ? "#759ca5" : "#a96b73"}
                      strokeWidth="3"
                    />
                    <rect
                      x={x - 10}
                      y={up ? y - 16 : y}
                      width="20"
                      height="34"
                      fill={up ? "#759ca5" : "#a96b73"}
                    />
                  </g>
                );
              })}
            </svg>
            <div
              style={{
                position: "absolute",
                top: 26,
                left: 26,
                color: "#a6bbc0",
                fontFamily: MONO,
                fontSize: 19,
                lineHeight: 1.55,
              }}
            >
              <div>DEMO CHART</div>
              <div style={{ color: "#687d84" }}>NO PRICE OR PROFIT DATA</div>
            </div>
          </div>
          <div style={{ padding: "28px 24px", fontFamily: MONO }}>
            <div
              style={{
                color: "#8fbec8",
                fontSize: 20,
                letterSpacing: "0.08em",
              }}
            >
              EXPERT ADVISOR
            </div>
            <div
              style={{
                marginTop: 28,
                color: "#e4eaeb",
                fontSize: 29,
              }}
            >
              RulesBasedDemo
            </div>
            {[
              ["MODE", "DEMO ONLY"],
              ["RULES", "LOADED"],
              ["RISK", "REVIEW MANUALLY"],
              ["RESULTS", "HIDDEN"],
            ].map(([label, value]) => (
              <div
                key={label}
                style={{
                  marginTop: 24,
                  padding: "18px 16px",
                  borderRadius: 8,
                  background: "rgba(255,255,255,0.035)",
                }}
              >
                <div style={{ color: "#647980", fontSize: 16 }}>{label}</div>
                <div
                  style={{
                    marginTop: 8,
                    color: label === "RISK" ? "#db9ca3" : "#c9d3d5",
                    fontSize: 20,
                  }}
                >
                  {value}
                </div>
              </div>
            ))}
            <div
              style={{
                marginTop: 42,
                padding: "22px 12px",
                borderRadius: 8,
                textAlign: "center",
                color: clicked ? "#071013" : "#c9d8db",
                background: clicked ? "#91c3cd" : "#24343a",
                fontSize: 20,
              }}
            >
              {clicked ? "DEMO STARTED" : setup ? "ATTACH EA" : "RUN DEMO"}
            </div>
          </div>
        </div>
        <div
          style={{
            position: "absolute",
            left: cursorX,
            top: cursorY,
            width: 0,
            height: 0,
            borderTop: "22px solid #f4f0e8",
            borderRight: "15px solid transparent",
            filter: "drop-shadow(0 3px 5px rgba(0,0,0,0.7))",
            transform: "rotate(-22deg)",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

export const Reference0806VisualLayer: React.FC<Props> = ({
  scene,
  assets,
  frame,
  fps,
}) => {
  if (!isReference0806Scene(scene)) {
    return null;
  }
  const treatment = scene.treatment ?? "";
  const progress = sceneProgress(scene, frame, fps);
  const asset = findSceneAsset(scene, assets);
  const isApprovedRealCapture =
    asset?.kind === "video" &&
    asset.provenance === "local-safe-demo-capture";

  if (isApprovedRealCapture && asset) {
    return (
      <RealCaptureScene
        asset={asset}
        scene={scene}
        fps={fps}
        progress={progress}
        showHookHeadline={treatment === "0806-split-hook"}
      />
    );
  }

  switch (treatment) {
    case "0806-split-hook":
      return <HookScene progress={progress} />;
    case "0806-terminal-boot":
    case "0806-code-rule-trace":
    case "0806-code-scroll":
    case "0806-terminal-detail-a":
    case "0806-terminal-detail-b":
      return <CodeScene progress={progress} treatment={treatment} />;
    case "0806-ea-label":
    case "0806-championship-evidence":
    case "0806-mql5-evidence":
      return (
        <EvidencePageV2
          asset={asset}
          progress={progress}
          treatment={treatment}
        />
      );
    case "0806-document-scroll-in":
      return (
        <IntertitleScene
          progress={progress}
          treatment={treatment}
          eyebrow="OFFICIAL METAQUOTES HISTORY"
          title={"AUTOMATED TRADING\nCHAMPIONSHIP"}
          accent="#84c7d6"
        />
      );
    case "0806-document-transition":
      return (
        <IntertitleScene
          progress={progress}
          treatment={treatment}
          eyebrow="PRIMARY-SOURCE INTERVIEW"
          title={"THE RESULT.\nTHEN THE REVERSAL."}
          accent="#d7b45f"
        />
      );
    case "0806-wrong-rule-flow":
      return <WrongRuleFlow progress={progress} />;
    case "0806-risk-turn":
      return (
        <IntertitleScene
          progress={progress}
          treatment={treatment}
          eyebrow="RISK TURN"
          title={"RISK CHANGED\nTHE DIRECTION."}
          accent="#dc6c76"
        />
      );
    case "0806-risk-control":
    case "0806-risk-reversal":
      return <RiskScene progress={progress} treatment={treatment} />;
    case "automation-vs-risk":
      return <LessonScene progress={progress} />;
    case "0806-demo-setup":
      return (
        <IntertitleScene
          progress={progress}
          treatment={treatment}
          eyebrow="ILLUSTRATIVE DEMO"
          title={"ATTACH THE EA.\nSHOW NO RESULTS."}
          accent="#84c7d6"
          light
        />
      );
    case "0806-demo-cta":
      return <DemoScene progress={progress} treatment={treatment} />;
    case "0806-presenter-reset":
    case "0806-presenter-ending":
    case "0806-clean-tail":
      return null;
    default:
      return null;
  }
};
