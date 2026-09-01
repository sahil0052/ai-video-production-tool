import { existsSync, readFileSync } from "node:fs";

import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test, vi } from "vitest";

vi.mock("remotion", async () => {
  const actual = await vi.importActual<typeof import("remotion")>(
    "remotion",
  );
  return {
    ...actual,
    Img: ({
      src,
      style,
    }: {
      src: string;
      style?: React.CSSProperties;
    }) => <div data-remotion-img={src} style={style} />,
  };
});

import {
  AssetLayer,
  findActiveAsset,
} from "./components/AssetLayer";
import { CaptionLayer } from "./components/CaptionLayer";
import { EditorialVisualLayer } from "./components/EditorialVisualLayer";
import { GraphicLayer } from "./components/GraphicLayer";
import * as reference0806 from "./components/Reference0806VisualLayer";
import {
  getReference0806V3Surface,
} from "./components/Reference0806V3VisualLayer";
import * as reference0806V3Motion from "./components/Reference0806V3VisualLayer";
import type { EditPlan } from "./schema";

const pages: EditPlan["caption_pages"] = [
  {
    start_ms: 0,
    end_ms: 700,
    family: "technical-mono",
    anchor: "center-74",
    transition: "hard-cut",
    max_width: 900,
    tokens: [
      {
        text: "AI",
        start_ms: 0,
        end_ms: 300,
        highlighted: true,
        confidence: 0.99,
      },
      {
        text: "works",
        start_ms: 300,
        end_ms: 700,
        highlighted: false,
        confidence: 0.99,
      },
    ],
  },
];

describe("caption and graphic layers", () => {
  test("keeps direct evidence captures moving within restrained bounds", () => {
    const cameraTransform = (
      reference0806 as unknown as Record<string, unknown>
    ).getEvidenceCameraTransform;

    expect(cameraTransform).toBeTypeOf("function");
    if (typeof cameraTransform !== "function") {
      return;
    }

    const sample = cameraTransform as (
      progress: number,
    ) => { translateX: number; translateY: number; scale: number };
    const fullPageStart = sample(0.05);
    const fullPageEnd = sample(0.2);
    const excerptStart = sample(0.3);
    const excerptEnd = sample(0.6);
    const detailStart = sample(0.7);
    const detailEnd = sample(0.95);

    expect(fullPageEnd).not.toEqual(fullPageStart);
    expect(excerptEnd).not.toEqual(excerptStart);
    expect(detailEnd).not.toEqual(detailStart);

    for (const transform of [
      fullPageStart,
      fullPageEnd,
      excerptStart,
      excerptEnd,
      detailStart,
      detailEnd,
    ]) {
      expect(Math.abs(transform.translateX)).toBeLessThanOrEqual(8);
      expect(Math.abs(transform.translateY)).toBeLessThanOrEqual(8);
      expect(transform.scale).toBeGreaterThanOrEqual(1);
      expect(transform.scale).toBeLessThanOrEqual(1.012);
    }
  });

  test("routes 0806 scenes through a bespoke visual layer", () => {
    const compositionSource = readFileSync(
      new URL("./Composition.tsx", import.meta.url),
      "utf8",
    );
    const layerUrl = new URL(
      "./components/Reference0806VisualLayer.tsx",
      import.meta.url,
    );

    expect(compositionSource).toContain("Reference0806VisualLayer");
    expect(compositionSource).toContain("isReference0806Scene");
    expect(existsSync(layerUrl)).toBe(true);
    if (!existsSync(layerUrl)) {
      return;
    }

    const layerSource = readFileSync(layerUrl, "utf8");
    expect(layerSource).toContain("local-safe-demo-capture");
    expect(layerSource).toContain("data-real-capture");
    expect(layerSource).toContain("<Video");
    expect(layerSource).toContain("0806-code-rule-trace");
    expect(layerSource).toContain("0806-championship-evidence");
    expect(layerSource).toContain("0806-mql5-evidence");
    expect(layerSource).toContain("0806-risk-reversal");
    expect(layerSource).toContain("0806-demo-cta");
  });

  test("routes the audited 0806 v3 scenes through a separate visual layer", () => {
    const compositionSource = readFileSync(
      new URL("./Composition.tsx", import.meta.url),
      "utf8",
    );
    const layerUrl = new URL(
      "./components/Reference0806V3VisualLayer.tsx",
      import.meta.url,
    );

    expect(compositionSource).toContain("Reference0806V3VisualLayer");
    expect(compositionSource).toContain("isReference0806V3Scene");
    expect(existsSync(layerUrl)).toBe(true);
    if (!existsSync(layerUrl)) {
      return;
    }

    const layerSource = readFileSync(layerUrl, "utf8");
    expect(layerSource).toContain("internet:coverr-free-video");
    expect(layerSource).toContain("0806-v3-hook-physical");
    expect(layerSource).toContain("0806-v3-code-cinematic");
    expect(layerSource).toContain("0806-v3-evidence-result");
    expect(layerSource).toContain("0806-v3-risk-reversal");
    expect(layerSource).toContain("0806-v3-demo-attach");
    expect(layerSource).toContain("<Video");
    expect(layerSource).toContain("<Img");
  });

  test("alternates V3 proof and product surfaces at audio-aligned cuts", () => {
    expect(getReference0806V3Surface("0806-v3-wrong-rule")).toBe(
      "slate",
    );
    expect(getReference0806V3Surface("0806-v3-evidence-heading")).toBe(
      "ink",
    );
    expect(getReference0806V3Surface("0806-v3-evidence-history")).toBe(
      "paper",
    );
    expect(getReference0806V3Surface("0806-v3-evidence-year")).toBe(
      "ink",
    );
    expect(getReference0806V3Surface("0806-v3-evidence-number")).toBe(
      "proof-band",
    );
    expect(getReference0806V3Surface("0806-v3-risk-input")).toBe(
      "paper",
    );
    expect(getReference0806V3Surface("0806-v3-risk-alternate")).toBe(
      "ink",
    );
    expect(getReference0806V3Surface("0806-v3-risk-reversal")).toBe(
      "paper",
    );
    expect(getReference0806V3Surface("0806-v3-demo-input")).toBe(
      "paper",
    );
    expect(getReference0806V3Surface("0806-v3-demo-strategy")).toBe(
      "ink",
    );
  });

  test("uses the measured restrained motion-wash strength", () => {
    const getOpacity = (
      reference0806V3Motion as {
        getReference0806V3MotionWashOpacity?: (
          surface: "ink" | "paper" | "proof-band" | "slate",
        ) => number;
      }
    ).getReference0806V3MotionWashOpacity;

    expect(getOpacity).toBeTypeOf("function");
    expect(getOpacity?.("paper")).toBe(0.26);
    expect(getOpacity?.("proof-band")).toBe(0.26);
    expect(getOpacity?.("ink")).toBe(0.32);
    expect(getOpacity?.("slate")).toBe(0.32);
  });

  test("drives the V3 screen texture from deterministic video frames", () => {
    const getPosition = (
      reference0806V3Motion as {
        getReference0806V3TexturePosition?: (
          frame: number,
        ) => { x: number; y: number };
      }
    ).getReference0806V3TexturePosition;

    expect(getPosition).toBeTypeOf("function");
    expect(getPosition?.(0)).not.toEqual(getPosition?.(1));
    expect(getPosition?.(0)).toEqual(getPosition?.(13));

    const layerSource = readFileSync(
      new URL(
        "./components/Reference0806V3VisualLayer.tsx",
        import.meta.url,
      ),
      "utf8",
    );
    expect(layerSource).toContain('data-v3-motion-texture="true"');
  });

  test("avoids decoding hidden or duplicated video layers in V3", () => {
    const compositionSource = readFileSync(
      new URL("./Composition.tsx", import.meta.url),
      "utf8",
    );
    const v3Source = readFileSync(
      new URL(
        "./components/Reference0806V3VisualLayer.tsx",
        import.meta.url,
      ),
      "utf8",
    );

    expect(compositionSource).not.toContain(
      "opacity: presenterLayout.visible ? 1 : 0",
    );
    expect(compositionSource).toContain(
      "presenterLayout.visible ? (",
    );
    expect(compositionSource).not.toContain(
      "blur(24px) brightness(0.48)",
    );
    expect(v3Source).toContain(
      'data-single-decode-background="navigator"',
    );
    expect(v3Source).toContain(
      'data-single-decode-background="product-macro"',
    );
    expect(v3Source).toContain("const showScreenOverlay =");
    expect(v3Source).toContain("const DemoActionScene");
    expect(v3Source).toContain(
      'data-demo-action="context-to-source"',
    );
    expect(v3Source).toContain('data-demo-action={');
    expect(v3Source).toContain('"direct-source"');
    expect(v3Source).toContain(
      'data-risk-palette="reference-04-dark"',
    );
    expect(v3Source).toContain(
      'data-lesson-treatment="tactile-contrast"',
    );

    const rendererSource = readFileSync(
      new URL("../render.mjs", import.meta.url),
      "utf8",
    );
    expect(rendererSource).toContain(
      ": Math.max(1, productionConcurrency)",
    );
  });

  test("renders measured technical captions without karaoke effects", () => {
    const markup = renderToStaticMarkup(
      <CaptionLayer
        pages={pages}
        timeMs={350}
        styleVariant="technical-explanation"
        entranceProgress={1}
      />,
    );

    expect(markup).toContain('data-caption-page="true"');
    expect(markup).toContain('data-caption-family="technical-mono"');
    expect(markup).toContain("AI");
    expect(markup).toContain("works");
    expect(markup).toContain("Share Tech Mono");
    expect(markup).toContain("font-size:33px");
    expect(markup).toContain("top:74%");
    expect(markup).toContain('data-static-highlight="true"');
    expect(markup).toContain("color:white");
    expect(markup).not.toContain("color:#D9FF45");
    expect(markup).not.toContain("data-active");
    expect(markup).not.toContain("scale(1.035)");
  });

  test("renders large reference captions at the lower safe anchor", () => {
    const reference = structuredClone(pages);
    reference[0].family = "outlined-demo";
    reference[0].anchor = "lower-82";
    reference[0].max_width = 940;

    const markup = renderToStaticMarkup(
      <CaptionLayer
        pages={reference}
        timeMs={350}
        styleVariant="technical-explanation"
        entranceProgress={1}
      />,
    );

    expect(markup).toContain('data-caption-family="outlined-demo"');
    expect(markup).toContain("font-size:58px");
    expect(markup).toContain("top:82%");
    expect(markup).toContain("AI");
    expect(markup).toContain("works");
  });

  test("reserves active-word color for display emphasis only", () => {
    const display = structuredClone(pages);
    display[0].family = "display-emphasis";

    const markup = renderToStaticMarkup(
      <CaptionLayer
        pages={display}
        timeMs={350}
        styleVariant="technical-explanation"
        entranceProgress={1}
      />,
    );

    expect(markup).toContain("color:#D9FF45");
  });

  test("renders documentary captions without a universal pill", () => {
    const documentary = structuredClone(pages);
    documentary[0].family = "documentary-clean";
    documentary[0].anchor = "center-71";
    documentary[0].transition = "hard-cut";
    documentary[0].max_width = 920;

    const markup = renderToStaticMarkup(
      <CaptionLayer
        pages={documentary}
        timeMs={350}
        styleVariant="technical-explanation"
        entranceProgress={1}
      />,
    );

    expect(markup).toContain('data-caption-family="documentary-clean"');
    expect(markup).toContain("font-size:36px");
    expect(markup).toContain("background:transparent");
    expect(markup).toContain("top:71%");
  });

  test("renders only graphics active at the current time", () => {
    const markup = renderToStaticMarkup(
      <GraphicLayer
        graphics={[
          {
            id: "hook",
            start_ms: 0,
            end_ms: 1200,
            kind: "headline",
            text: "THE NEW AI CHIP",
            accent: "#D7FF64",
          },
          {
            id: "later",
            start_ms: 1500,
            end_ms: 2500,
            kind: "callout",
            text: "12% FASTER",
            accent: "#00E5FF",
          },
        ]}
        timeMs={500}
        entranceProgress={1}
      />,
    );

    expect(markup).toContain('data-graphic-kind="headline"');
    expect(markup).toContain("THE NEW AI CHIP");
    expect(markup).not.toContain("12% FASTER");
  });

  test("renders product and browser graphics as UI templates", () => {
    const markup = renderToStaticMarkup(
      <GraphicLayer
        graphics={[
          {
            id: "browser",
            start_ms: 0,
            end_ms: 1000,
            kind: "browser",
            text: "Search results",
            accent: "#D7FF64",
          },
        ]}
        timeMs={500}
        entranceProgress={1}
      />,
    );

    expect(markup).toContain('data-ui-template="browser"');
    expect(markup).toContain("Search results");
    expect(markup).toContain("● ● ●");
    expect(markup).toContain("min-height:620px");
  });

  test("renders a scheduled image asset inside a social-safe frame", () => {
    const asset = findActiveAsset(
      [
        {
          id: "asset-1",
          kind: "image",
          path: "assets/asset-1.png",
          keywords: ["ai"],
          provenance: "local-library",
          license: "Internal",
          provider: null,
          remote_id: null,
          creator: null,
          source_url: null,
          license_url: null,
          search_query: null,
          start_ms: 500,
          end_ms: 1500,
        },
      ],
      900,
    );

    expect(asset?.kind).toBe("image");
    expect(asset?.path).toBe("assets/asset-1.png");
  });

  test("renders internet assets as dominant full-frame scenes", () => {
    const markup = renderToStaticMarkup(
      <AssetLayer
        assets={[
          {
            id: "internet-asset-1",
            kind: "image",
            path: "assets/internet-asset-1.jpg",
            keywords: ["forex"],
            provenance: "internet:wikimedia-commons",
            license: "CC BY-SA 4.0",
            provider: "wikimedia-commons",
            remote_id: "10",
            creator: "Creator",
            source_url:
              "https://commons.wikimedia.org/wiki/File:Forex.jpg",
            license_url:
              "https://creativecommons.org/licenses/by-sa/4.0/",
            search_query: "forex market",
            start_ms: 0,
            end_ms: 1200,
          },
        ]}
        timeMs={500}
        entranceProgress={1}
        layout="asset-full"
      />,
    );

    expect(markup).toContain('data-asset-layout="asset-full"');
    expect(markup).toContain("inset:0");
    expect(markup).toContain("internet-asset-1.jpg");
  });

  test("renders semantic trading visuals as dominant editorial scenes", () => {
    const markup = renderToStaticMarkup(
      <EditorialVisualLayer
        visual={{
          id: "visual-1",
          start_ms: 0,
          end_ms: 1800,
          kind: "trading-chart",
          title: "FOREX RULE ENGINE",
          subtitle: "Fixed rules execute every trade",
          accent: "#00E5FF",
          value: null,
          items: ["MARKET DATA", "RULES", "TRADE"],
          direction: "up",
        } as never}
        layout="graphic"
        frame={18}
        fps={30}
      />,
    );

    expect(markup).toContain('data-editorial-visual="trading-chart"');
    expect(markup).toContain("FOREX RULE ENGINE");
    expect(markup).toContain("MARKET DATA");
    expect(markup).toContain("<svg");
  });

  test("keeps editorial backgrounds moving after the entrance settles", () => {
    const visual = {
      id: "visual-1",
      start_ms: 0,
      end_ms: 1800,
      kind: "trading-chart",
      title: "FOREX RULE ENGINE",
      subtitle: "Fixed rules execute every trade",
      accent: "#00E5FF",
      value: null,
      items: ["MARKET DATA", "RULES", "TRADE"],
      direction: "up",
    } as never;
    const frame30 = renderToStaticMarkup(
      <EditorialVisualLayer
        visual={visual}
        layout="graphic"
        frame={30}
        fps={30}
      />,
    );
    const frame45 = renderToStaticMarkup(
      <EditorialVisualLayer
        visual={visual}
        layout="graphic"
        frame={45}
        fps={30}
      />,
    );

    expect(frame30).toContain("background-position");
    expect(frame30).not.toBe(frame45);
  });

  test("labels generated evidence summaries and code as illustrative", () => {
    const evidence = renderToStaticMarkup(
      <EditorialVisualLayer
        visual={{
          id: "visual-evidence",
          start_ms: 0,
          end_ms: 1800,
          kind: "evidence-card",
          title: "2008 AUTOMATED TRADING CHAMPIONSHIP",
          subtitle: "A sourced event summary",
          accent: "#00E5FF",
          value: "2008",
          items: ["RULES", "RISK"],
          direction: "neutral",
        } as never}
        layout="graphic"
        frame={18}
        fps={30}
      />,
    );
    const code = renderToStaticMarkup(
      <EditorialVisualLayer
        visual={{
          id: "visual-code",
          start_ms: 0,
          end_ms: 1800,
          kind: "code-terminal",
          title: "EXPERT ADVISOR",
          subtitle: "Illustrative logic",
          accent: "#00E5FF",
          value: null,
          items: ["if (rule)", "executeTrade();"],
          direction: "neutral",
        } as never}
        layout="graphic"
        frame={18}
        fps={30}
      />,
    );

    expect(evidence).toContain("ILLUSTRATIVE EDITORIAL SUMMARY");
    expect(evidence).not.toContain("PERFORMANCE REPORT");
    expect(code).toContain("ILLUSTRATIVE LOGIC");
  });
});
