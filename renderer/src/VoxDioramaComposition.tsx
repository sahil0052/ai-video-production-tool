import React from "react";
import {
  AbsoluteFill,
  Composition,
  Img,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { AnimatedBalanceMeter } from "./components/vox/AnimatedBalanceMeter";
import { AnimatedLeverageScale } from "./components/vox/AnimatedLeverageScale";
import { AnimatedStockChart } from "./components/vox/AnimatedStockChart";
import { ChecklistPillars } from "./components/vox/ChecklistPillars";
import { MarkerSwipe } from "./components/vox/MarkerSwipe";
import { RollingNumberTicker } from "./components/vox/RollingNumberTicker";
import { StampSlam } from "./components/vox/StampSlam";

export const VoxDioramaTopHalf: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#C9BB9C", width: 1080, height: 960, overflow: "hidden" }}>
      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 1: 0.0s - 2.06s (0 - 62f) | 90% TRADERS LOSE          */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={0} durationInFrames={62}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/world_map_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover", transform: "scale(1.05)" }} />
          
          <div style={{ position: "absolute", top: 80, width: "100%", textAlign: "center" }}>
            <span
              style={{
                fontFamily: "'Anton', sans-serif",
                fontSize: "44px",
                color: "#1A1A1A",
                letterSpacing: "3px",
                textTransform: "uppercase",
                backgroundColor: "rgba(255, 255, 255, 0.9)",
                padding: "6px 28px",
                borderRadius: "8px",
                border: "3px solid #1A1A1A",
                boxShadow: "0 8px 24px rgba(0,0,0,0.15)",
              }}
            >
              GLOBAL FOREX MARKET
            </span>
          </div>

          {/* Giant Animated Rolling Odometer Number 0% -> 90% */}
          <div style={{ position: "absolute", top: 230, width: "100%", display: "flex", justifyContent: "center" }}>
            <RollingNumberTicker startValue={0} endValue={90} suffix="%" fontSize={190} />
          </div>

          {/* Stamp Slam "FAIL" @ frame 42 */}
          <Sequence from={42} durationInFrames={20}>
            <div style={{ position: "absolute", top: 480, width: "100%", display: "flex", justifyContent: "center" }}>
              <StampSlam text="FAIL" subText="90% OF TRADERS LOSE" rotation={-8} fontSize={72} />
            </div>
          </Sequence>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 2: 2.06s - 2.88s (62 - 87f) | LEKIN KYUN? (WHY?)       */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={62} durationInFrames={25}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/ledger_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 200, width: "100%", display: "flex", justifyContent: "center" }}>
            <StampSlam text="WHY?" subText="LEKIN KYUN?" color="#D62E1F" rotation={6} fontSize={110} />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 3: 2.88s - 3.74s (87 - 113f) | PROBLEM MARKET NAHI     */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={87} durationInFrames={26}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/blueprint_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          
          <div style={{ position: "absolute", top: 180, width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div
              style={{
                position: "relative",
                padding: "24px 72px",
                backgroundColor: "#FFFFFF",
                borderRadius: "20px",
                border: "5px solid #1A1A1A",
                fontFamily: "'Anton', sans-serif",
                fontSize: "80px",
                color: "#1A1A1A",
                boxShadow: "0 24px 60px rgba(0,0,0,0.4)",
              }}
            >
              THE MARKET
              {/* Real-time Red "X" Cross Out */}
              <div style={{ position: "absolute", top: -20, left: 30 }}>
                <MarkerSwipe type="cross_out" width={500} height={220} />
              </div>
            </div>

            <div
              style={{
                marginTop: "36px",
                padding: "12px 40px",
                backgroundColor: "#00E5FF",
                color: "#1A1A1A",
                fontFamily: "'Barlow Condensed', sans-serif",
                fontWeight: 900,
                fontSize: "40px",
                borderRadius: "12px",
                border: "3px solid #1A1A1A",
                boxShadow: "0 10px 30px rgba(0,229,255,0.3)",
              }}
            >
              ✓ NOT THE PROBLEM!
            </div>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 4: 3.74s - 5.58s (113 - 168f) | TRADER MISTAKES        */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={113} durationInFrames={55}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/ledger_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 220, width: "100%", display: "flex", justifyContent: "center" }}>
            <StampSlam text="TRADER MISTAKES" subText="INTERNAL PSYCHOLOGY TRAPS" rotation={-4} fontSize={66} />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 5: 5.58s - 7.44s (168 - 224f) | MISTAKE 1: RISK        */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={168} durationInFrames={56}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/ledger_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 200, width: "100%", display: "flex", justifyContent: "center" }}>
            <StampSlam text="MISTAKE #1" subText="POOR RISK MANAGEMENT" color="#D62E1F" rotation={-5} fontSize={70} />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 6: 7.44s - 11.22s (224 - 337f) | 100% CAPITAL RISK     */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={224} durationInFrames={113}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/ledger_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 200, width: "100%", display: "flex", justifyContent: "center" }}>
            <AnimatedBalanceMeter startBalance={10000} endBalance={0} durationFrames={50} />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 7: 11.22s - 14.98s (337 - 450f) | LEVERAGE 1:500       */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={337} durationInFrames={113}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/blueprint_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 160, width: "100%", display: "flex", justifyContent: "center" }}>
            <AnimatedLeverageScale />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 8: 14.98s - 17.50s (450 - 526f) | CRASH & FAST LOSS    */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={450} durationInFrames={76}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/ledger_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 160, width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ marginBottom: "20px", fontSize: "40px", fontWeight: 900, color: "#D62E1F", fontFamily: "'Anton', sans-serif" }}>
              ⚡ LOSS FAST BADHTA HAI!
            </div>
            <AnimatedStockChart isCrashing={true} durationFrames={55} />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 9: 17.50s - 24.42s (526 - 733f) | EMOTIONS & REVENGE   */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={526} durationInFrames={207}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/ledger_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          
          <div style={{ position: "absolute", top: 160, width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: "36px" }}>
            <StampSlam text="REVENGE TRADING" subText="POST-LOSS IMPULSIVE TRADES" rotation={-6} fontSize={66} />
            
            <Sequence from={65} durationInFrames={142}>
              <StampSlam text="OVERCONFIDENCE" subText="DESTROY STRATEGY" color="#D62E1F" rotation={6} fontSize={66} />
            </Sequence>
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 10: 24.42s - 28.50s (733 - 855f) | UNTESTED STRATEGY   */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={733} durationInFrames={122}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/blueprint_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 220, width: "100%", display: "flex", justifyContent: "center" }}>
            <StampSlam text="UNTESTED" subText="NO TESTED STRATEGY" color="#D62E1F" rotation={8} fontSize={84} />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 11: 28.50s - 34.52s (855 - 1036f) | EA BOT RULES       */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={855} durationInFrames={181}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/blueprint_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          <div style={{ position: "absolute", top: 160, width: "100%", display: "flex", justifyContent: "center" }}>
            <ChecklistPillars />
          </div>
        </AbsoluteFill>
      </Sequence>

      {/* ──────────────────────────────────────────────────────────── */}
      {/* SCENE 12: 34.52s - 38.10s (1036 - 1144f) | FOLLOW CTA        */}
      {/* ──────────────────────────────────────────────────────────── */}
      <Sequence from={1036} durationInFrames={108}>
        <AbsoluteFill>
          <Img src={staticFile("vox_bg/world_map_bg.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          
          <div style={{ position: "absolute", top: 140, width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: "28px" }}>
            <div
              style={{
                display: "flex",
                gap: "20px",
              }}
            >
              {["RISK", "STRATEGY", "DISCIPLINE"].map((p, i) => (
                <div
                  key={i}
                  style={{
                    padding: "12px 28px",
                    backgroundColor: "#FFFFFF",
                    border: "3px solid #1A1A1A",
                    borderRadius: "12px",
                    fontWeight: 900,
                    fontSize: "26px",
                    fontFamily: "'Barlow Condensed', sans-serif",
                    color: "#1A1A1A",
                    boxShadow: "0 8px 20px rgba(0,0,0,0.15)",
                  }}
                >
                  {p}
                </div>
              ))}
            </div>

            <StampSlam text="FOLLOW NOW" subText="DAILY FOREX & EA STRATEGIES" color="#D62E1F" rotation={-3} fontSize={68} />
          </div>
        </AbsoluteFill>
      </Sequence>
    </AbsoluteFill>
  );
};

export const VoxDioramaTopHalfComposition: React.FC = () => {
  return (
    <Composition
      id="VoxDioramaTopHalf"
      component={VoxDioramaTopHalf}
      durationInFrames={1144}
      fps={30}
      width={1080}
      height={960}
    />
  );
};
