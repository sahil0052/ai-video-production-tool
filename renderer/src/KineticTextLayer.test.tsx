import { readFileSync } from "node:fs";

import { describe, expect, test } from "vitest";

import {
  kineticFamilyStyles,
  resolveKineticCueMotion,
} from "./components/KineticTextLayer";

describe("KineticTextLayer", () => {
  test("uses human-reference display typography geometry", () => {
    expect(kineticFamilyStyles["serif-hook"].fontFamily).toContain(
      "Georgia",
    );
    expect(kineticFamilyStyles["serif-hook"].fontSize).toBeGreaterThanOrEqual(
      82,
    );
    expect(kineticFamilyStyles["hero-condensed"].fontSize).toBeGreaterThanOrEqual(
      170,
    );
    expect(kineticFamilyStyles["hero-condensed"].fontSize).toBeLessThanOrEqual(
      220,
    );
    expect(kineticFamilyStyles["outlined-stack"].fontSize).toBeGreaterThanOrEqual(
      100,
    );
    expect(kineticFamilyStyles["gradient-number"].fontSize).toBeGreaterThanOrEqual(
      140,
    );
    expect(kineticFamilyStyles["gradient-number"].stroke).toContain("2px");
    expect(kineticFamilyStyles["gradient-number"].textShadow).not.toContain(
      "24px",
    );
    expect(kineticFamilyStyles["micro-source"].fontSize).toBe(24);
    expect(kineticFamilyStyles["cta-quote"].fontSize).toBeGreaterThanOrEqual(
      120,
    );
    expect(kineticFamilyStyles["hero-condensed"].gradient).toContain(
      "#EEFF00",
    );
    expect(kineticFamilyStyles["cta-quote"].gradient).toContain(
      "#FFE85A",
    );
    expect(kineticFamilyStyles["hero-condensed"].textShadow).not.toContain(
      "#4B3900",
    );
    expect(kineticFamilyStyles["hero-condensed"].textShadow).not.toContain(
      "#424600",
    );
    expect(kineticFamilyStyles["cta-quote"].textShadow).not.toContain(
      "#6B5600",
    );
    expect(kineticFamilyStyles["hero-condensed"].textShadow).toBe("none");
    expect(kineticFamilyStyles["cta-quote"].textShadow).toBe("none");
    expect(kineticFamilyStyles["hero-condensed"]).toHaveProperty(
      "foregroundFilter",
    );
    expect(kineticFamilyStyles["cta-quote"]).toHaveProperty(
      "foregroundFilter",
    );
  });

  test("separates bright gradient glyphs from dark extrusion paint", () => {
    const source = readFileSync(
      new URL("./components/KineticTextLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toContain('data-kinetic-paint="extrusion"');
    expect(source).toContain('data-kinetic-paint="foreground"');
  });

  test("renders micro-source evidence as a fitted high-contrast strip", () => {
    const source = readFileSync(
      new URL("./components/KineticTextLayer.tsx", import.meta.url),
      "utf8",
    );

    expect(source).toContain("isMicroSource");
    expect(source).toContain("rgba(3, 18, 42, 0.9)");
    expect(source).toContain("inline-block");
  });

  test("derives deterministic slam motion from frame time", () => {
    const opening = resolveKineticCueMotion("slam", 0, 700);
    const settled = resolveKineticCueMotion("slam", 240, 700);

    expect(opening.opacity).toBe(0);
    expect(opening.scale).toBeGreaterThan(settled.scale);
    expect(settled.opacity).toBe(1);
    expect(settled.scale).toBe(1);
  });

  test("fades correction typography gradually enough to avoid a false cut", () => {
    const fading = resolveKineticCueMotion("draw", 800, 1000);

    expect(fading.opacity).toBeGreaterThan(0);
    expect(fading.opacity).toBeLessThan(1);
  });
});
