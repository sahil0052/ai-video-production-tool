import { readFileSync } from "node:fs";
import { createServer } from "node:net";

import { describe, expect, test } from "vitest";

import {
  compositionIdForPlan,
  parseRenderArgs,
  renderMediaColorOptionsForPlan,
} from "./render-args.mjs";

describe("parseRenderArgs", () => {
  test("parses required renderer paths without joining shell strings", () => {
    expect(
      parseRenderArgs([
        "--plan",
        "C:\\jobs\\edit plan.json",
        "--public-dir",
        "C:\\jobs\\public assets",
        "--output",
        "C:\\jobs\\final video.mp4",
      ]),
    ).toEqual({
      plan: "C:\\jobs\\edit plan.json",
      publicDir: "C:\\jobs\\public assets",
      output: "C:\\jobs\\final video.mp4",
    });
  });

  test("rejects missing arguments", () => {
    expect(() => parseRenderArgs(["--plan", "plan.json"])).toThrow(
      /public-dir/i,
    );
  });

  test("all plan-driven diagnostic renderers select the V4 composition dynamically", () => {
    for (const filename of [
      "render-still.mjs",
      "render-range.mjs",
      "render-diagnostics.mjs",
    ]) {
      const source = readFileSync(new URL(filename, import.meta.url), "utf8");
      expect(source).toMatch(/compositionIdForPlan\(rawPlan\)/);
    }
  });

  test("selects a port that is free on both IPv4 and IPv6", async () => {
    const renderArgs = await import("./render-args.mjs");
    expect(renderArgs.findAvailableRendererPort).toBeTypeOf("function");

    const occupied = createServer();
    await new Promise((resolve, reject) => {
      occupied.once("error", reject);
      occupied.listen(
        { host: "::1", port: 0, ipv6Only: true },
        resolve,
      );
    });
    const address = occupied.address();
    if (address == null || typeof address === "string") {
      throw new Error("Expected an IPv6 test listener");
    }

    try {
      const selected = await renderArgs.findAvailableRendererPort({
        preferredPort: address.port,
        maxAttempts: 5,
      });
      expect(selected).not.toBe(address.port);
    } finally {
      await new Promise((resolve, reject) => {
        occupied.close((error) =>
          error == null ? resolve() : reject(error),
        );
      });
    }
  });

  test("all renderer entry points pass the isolated port to Remotion", () => {
    for (const filename of [
      "render.mjs",
      "render-still.mjs",
      "render-range.mjs",
      "render-diagnostics.mjs",
      "render-fixtures.mjs",
    ]) {
      const source = readFileSync(new URL(filename, import.meta.url), "utf8");
      expect(source).toMatch(/findAvailableRendererPort/);
      expect(source).toMatch(/port:\s*rendererPort/);
    }
  });

  test("selects the explicit-layer composition for V4 plans", () => {
    expect(
      compositionIdForPlan({
        version: "2.0",
        profile: "production-tech-story-v4",
      }),
    ).toBe("ProductionTechStoryV4");
    expect(
      compositionIdForPlan({
        version: "1.0",
        profile: "tech-story-v1",
      }),
    ).toBe("TechStory");
  });

  test("renders opaque production plans through high-quality JPEG intermediates in limited BT.709", () => {
    expect(
      renderMediaColorOptionsForPlan({
        version: "2.0",
        profile: "production-tech-story-v4",
      }),
    ).toEqual({
      imageFormat: "jpeg",
      jpegQuality: 95,
      pixelFormat: "yuv420p",
      colorSpace: "bt709",
    });
  });
});
