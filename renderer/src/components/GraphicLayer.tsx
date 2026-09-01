import type { EditPlan } from "../schema";

type Props = {
  graphics: EditPlan["graphics"];
  timeMs: number;
  entranceProgress: number;
};

export const GraphicLayer: React.FC<Props> = ({
  graphics,
  timeMs,
  entranceProgress,
}) => {
  const active = graphics.filter(
    (graphic) =>
      graphic.start_ms <= timeMs && graphic.end_ms > timeMs,
  );
  if (active.length === 0) {
    return null;
  }
  return (
    <>
      {active.map((graphic, index) => {
        const headline = graphic.kind === "headline";
        const uiTemplate =
          graphic.kind === "browser" ||
          graphic.kind === "phone" ||
          graphic.kind === "chat"
            ? graphic.kind
            : undefined;
        return (
          <div
            key={graphic.id}
            data-graphic-kind={graphic.kind}
            data-ui-template={uiTemplate}
            style={{
              position: "absolute",
              zIndex: 30 + index,
              top:
                headline
                  ? 116
                  : graphic.kind === "browser"
                    ? 110
                  : graphic.kind === "phone"
                    ? 90
                    : 250 + index * 130,
              left:
                headline
                  ? 64
                  : graphic.kind === "browser"
                    ? 54
                  : graphic.kind === "phone"
                    ? 245
                    : 72,
              right:
                headline
                  ? 64
                  : graphic.kind === "browser"
                    ? 54
                  : graphic.kind === "phone"
                    ? 245
                    : "auto",
              maxWidth:
                headline || graphic.kind === "browser" ? undefined : 760,
              minHeight:
                graphic.kind === "browser"
                  ? 620
                  : graphic.kind === "phone"
                    ? 650
                    : undefined,
              padding:
                headline
                  ? "0 22px"
                  : graphic.kind === "browser"
                    ? "0 0 28px"
                    : graphic.kind === "phone"
                      ? "58px 26px"
                      : "14px 20px",
              border: headline ? undefined : `2px solid ${graphic.accent}`,
              borderRadius:
                headline ? undefined : graphic.kind === "phone" ? 48 : 14,
              background: headline
                ? "transparent"
                : "rgba(8, 10, 13, 0.82)",
              color: headline ? "#FFFFFF" : graphic.accent,
              fontFamily: '"Inter Tight", Arial, sans-serif',
              fontSize: headline ? 82 : 42,
              fontWeight: 850,
              letterSpacing: headline ? "-0.055em" : "-0.035em",
              lineHeight: headline ? 0.96 : 1.05,
              textAlign: headline ? "center" : "left",
              textTransform: headline ? "uppercase" : "none",
              textShadow: "0 10px 30px rgba(0, 0, 0, 0.65)",
              opacity: entranceProgress,
              transform: `translateY(${(1 - entranceProgress) * -24}px) scale(${0.94 + entranceProgress * 0.06})`,
              transformOrigin: headline ? "center top" : "left center",
            }}
          >
            {graphic.kind === "browser" ? (
              <>
                <div
                  style={{
                    padding: "13px 18px",
                    borderBottom: "1px solid rgba(255,255,255,0.15)",
                    color: "#FF766D",
                    fontSize: 17,
                    letterSpacing: "0.3em",
                  }}
                >
                  ● ● ●
                </div>
                <div
                  style={{
                    margin: "24px 24px 0",
                    padding: "16px 20px",
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.09)",
                    color: "#FFFFFF",
                    fontSize: 34,
                  }}
                >
                  {graphic.text}
                </div>
                <div
                  style={{
                    width: "54%",
                    height: 8,
                    margin: "30px 24px 0",
                    borderRadius: 999,
                    background: graphic.accent,
                  }}
                />
                <div
                  style={{
                    margin: "28px 24px 0",
                    display: "grid",
                    gridTemplateColumns: "1.2fr 0.8fr",
                    gap: 18,
                  }}
                >
                  <div
                    style={{
                      height: 210,
                      borderRadius: 18,
                      background:
                        "linear-gradient(135deg, rgba(215,255,100,0.22), rgba(255,255,255,0.04))",
                    }}
                  />
                  <div
                    style={{
                      display: "grid",
                      gap: 14,
                    }}
                  >
                    <div
                      style={{
                        borderRadius: 14,
                        background: "rgba(255,255,255,0.08)",
                      }}
                    />
                    <div
                      style={{
                        borderRadius: 14,
                        background: "rgba(255,255,255,0.05)",
                      }}
                    />
                  </div>
                </div>
              </>
            ) : graphic.kind === "phone" ? (
              <>
                <div
                  style={{
                    width: 76,
                    height: 8,
                    margin: "-34px auto 150px",
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.3)",
                  }}
                />
                <div
                  style={{
                    color: "#FFFFFF",
                    fontSize: 48,
                    textAlign: "center",
                  }}
                >
                  {graphic.text}
                </div>
              </>
            ) : graphic.kind === "counter" ? (
              <div
                style={{
                  color: "#FFFFFF",
                  fontSize: 84,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {graphic.text}
              </div>
            ) : graphic.kind === "progress" ? (
              <>
                <div>{graphic.text}</div>
                <div
                  style={{
                    width: 520,
                    height: 16,
                    marginTop: 18,
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.12)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${Math.max(8, entranceProgress * 100)}%`,
                      height: "100%",
                      background: graphic.accent,
                    }}
                  />
                </div>
              </>
            ) : (
              graphic.text
            )}
            {headline ? (
              <div
                style={{
                  width: `${Math.max(18, entranceProgress * 72)}%`,
                  height: 8,
                  margin: "18px auto 0",
                  borderRadius: 999,
                  background: graphic.accent,
                  boxShadow: `0 0 28px ${graphic.accent}66`,
                }}
              />
            ) : null}
          </div>
        );
      })}
    </>
  );
};
