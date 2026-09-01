import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { bundle } from "@remotion/bundler";
import { renderStill, selectComposition } from "@remotion/renderer";

import { findAvailableRendererPort } from "./render-args.mjs";

const rendererRoot = path.dirname(fileURLToPath(import.meta.url));
const outputDir = path.resolve(process.argv[2] ?? "../storage/qa/fixtures");
await fs.mkdir(outputDir, { recursive: true });
const rendererPort = await findAvailableRendererPort();

const bundleLocation = await bundle({
  entryPoint: path.join(rendererRoot, "src", "index.ts"),
  enableCaching: true,
});

try {
  for (const [id, filename] of [
    ["FontComparisonFixture", "font-comparison.png"],
    ["CaptionFamilyFixture", "caption-families.png"],
  ]) {
    const composition = await selectComposition({
      serveUrl: bundleLocation,
      id,
      inputProps: {},
      port: rendererPort,
    });
    await renderStill({
      composition,
      serveUrl: bundleLocation,
      output: path.join(outputDir, filename),
      imageFormat: "png",
      frame: 0,
      inputProps: {},
      port: rendererPort,
      overwrite: true,
    });
  }
} finally {
  await fs.rm(bundleLocation, { recursive: true, force: true });
}
