import { AbsoluteFill, Composition } from "remotion";

const phrases = ["THAT'S EVEN", "IF STATEMENTS.", "50/50 GUESSES"];

const fontCandidates = [
  {
    label: "SHARE TECH MONO",
    family: '"Share Tech Mono", monospace',
    weight: 400,
  },
  {
    label: "SPACE MONO",
    family: '"Space Mono", monospace',
    weight: 700,
  },
  {
    label: "CHAKRA PETCH",
    family: '"Chakra Petch", sans-serif',
    weight: 600,
  },
  {
    label: "IBM PLEX MONO",
    family: '"IBM Plex Mono", monospace',
    weight: 700,
  },
];

const TechnicalPill: React.FC<{
  text: string;
  family: string;
  weight: number;
}> = ({ text, family, weight }) => (
  <div
    style={{
      display: "inline-flex",
      padding: "7px 12px",
      borderRadius: 5,
      background: "#030406",
      color: "#FFFFFF",
      fontFamily: family,
      fontSize: 33,
      fontWeight: weight,
      letterSpacing: "0.01em",
      lineHeight: 1.04,
      textTransform: "uppercase",
      whiteSpace: "nowrap",
    }}
  >
    {text}
  </div>
);

export const FontComparisonFixture: React.FC = () => (
  <AbsoluteFill
    style={{
      padding: "70px 64px",
      background: "#101318",
      color: "#FFFFFF",
      fontFamily: '"Inter Tight", Arial, sans-serif',
    }}
  >
    <div style={{ fontSize: 54, fontWeight: 800 }}>
      REFERENCE #10 FONT COMPARISON
    </div>
    <div
      style={{
        marginTop: 12,
        color: "#AAB4C0",
        fontFamily: '"IBM Plex Mono", monospace',
        fontSize: 20,
      }}
    >
      33 PX • 12/7 PX PADDING • 5 PX RADIUS
    </div>
    <div style={{ display: "grid", gap: 48, marginTop: 72 }}>
      {fontCandidates.map((candidate) => (
        <div
          key={candidate.label}
          data-font-candidate={candidate.label}
          style={{
            minHeight: 320,
            padding: 30,
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 22,
            background: "rgba(255,255,255,0.035)",
          }}
        >
          <div
            style={{
              marginBottom: 30,
              color: "#D7FF64",
              fontFamily: '"IBM Plex Mono", monospace',
              fontSize: 19,
              fontWeight: 700,
              letterSpacing: "0.12em",
            }}
          >
            {candidate.label}
          </div>
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "34px 26px",
            }}
          >
            {phrases.map((phrase) => (
              <TechnicalPill
                key={phrase}
                text={phrase}
                family={candidate.family}
                weight={candidate.weight}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

const familySamples = [
  {
    label: "technical-mono",
    text: "IF STATEMENTS.",
    style: {
      padding: "7px 12px",
      borderRadius: 5,
      background: "#030406",
      fontFamily: '"Share Tech Mono", monospace',
      fontSize: 33,
      fontWeight: 400,
      textTransform: "uppercase" as const,
    },
  },
  {
    label: "documentary-clean",
    text: "In the 2008 Championship",
    style: {
      padding: 0,
      borderRadius: 0,
      background: "transparent",
      fontFamily: '"Inter Tight", sans-serif',
      fontSize: 36,
      fontWeight: 800,
      textTransform: "none" as const,
      textShadow: "0 2px 3px #000, 0 0 14px #000",
    },
  },
  {
    label: "compact-pill",
    text: "Do you know?",
    style: {
      padding: "8px 15px 9px",
      borderRadius: 12,
      background: "rgba(12,13,16,0.9)",
      fontFamily: '"Inter Tight", sans-serif',
      fontSize: 38,
      fontWeight: 800,
      textTransform: "none" as const,
    },
  },
  {
    label: "outlined-demo",
    text: "OPEN THE APP",
    style: {
      padding: 0,
      borderRadius: 0,
      background: "transparent",
      fontFamily: '"Inter Tight", sans-serif',
      fontSize: 58,
      fontWeight: 800,
      textTransform: "uppercase" as const,
      WebkitTextStroke: "4px #050608",
      paintOrder: "stroke fill" as const,
    },
  },
  {
    label: "display-emphasis",
    text: "RISK TURNED THE GAME.",
    style: {
      padding: 0,
      borderRadius: 0,
      background: "transparent",
      fontFamily: '"Inter Tight", sans-serif',
      fontSize: 78,
      fontWeight: 800,
      lineHeight: 0.92,
      textTransform: "uppercase" as const,
      textShadow: "0 3px 3px #000, 0 0 18px #000",
    },
  },
];

export const CaptionFamilyFixture: React.FC = () => (
  <AbsoluteFill
    style={{
      padding: "72px 64px",
      background:
        "radial-gradient(circle at 80% 12%, #163849 0, transparent 34%), #080A0D",
      color: "#FFFFFF",
      fontFamily: '"Inter Tight", sans-serif',
    }}
  >
    <div style={{ fontSize: 54, fontWeight: 800 }}>
      ADAPTIVE CAPTION FAMILIES
    </div>
    <div style={{ display: "grid", gap: 56, marginTop: 78 }}>
      {familySamples.map((sample) => (
        <div
          key={sample.label}
          data-caption-family-fixture={sample.label}
          style={{
            display: "grid",
            gridTemplateColumns: "300px 1fr",
            alignItems: "center",
            minHeight: 250,
            padding: 34,
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 24,
            background: "rgba(3,6,10,0.72)",
          }}
        >
          <div
            style={{
              color: "#00E5FF",
              fontFamily: '"IBM Plex Mono", monospace',
              fontSize: 20,
              fontWeight: 700,
            }}
          >
            {sample.label}
          </div>
          <div style={{ textAlign: "center" }}>
            <span style={sample.style}>{sample.text}</span>
          </div>
        </div>
      ))}
    </div>
  </AbsoluteFill>
);

export const ReferenceFixtureCompositions: React.FC = () => (
  <>
    <Composition
      id="FontComparisonFixture"
      component={FontComparisonFixture}
      durationInFrames={1}
      fps={30}
      width={1080}
      height={1920}
    />
    <Composition
      id="CaptionFamilyFixture"
      component={CaptionFamilyFixture}
      durationInFrames={1}
      fps={30}
      width={1080}
      height={1920}
    />
  </>
);
