import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { bundle } from "@remotion/bundler";
import {
  renderStill,
  selectComposition,
} from "@remotion/renderer";

import {
  compositionIdForPlan,
  findAvailableRendererPort,
} from "./render-args.mjs";

const values = new Map();
const args = process.argv.slice(2);
for (let index = 0; index < args.length; index += 2) {
  values.set(args[index], args[index + 1]);
}
const planPath = path.resolve(values.get("--plan"));
const publicDir = path.resolve(values.get("--public-dir"));
const output = path.resolve(values.get("--output"));
const frame = Number.parseInt(values.get("--frame") ?? "0", 10);
const rendererRoot = path.dirname(fileURLToPath(import.meta.url));
const rawPlan = JSON.parse(await fs.readFile(planPath, "utf8"));
const rendererPort = await findAvailableRendererPort();
const bundleLocation = await bundle({
  entryPoint: path.join(rendererRoot, "src", "index.ts"),
  publicDir,
  enableCaching: true,
});

try {
  const inputProps = { plan: rawPlan };
  const onBrowserLog = (log) => {
    process.stdout.write(
      `${JSON.stringify({ browser: log })}\n`,
    );
  };
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: compositionIdForPlan(rawPlan),
    inputProps,
    port: rendererPort,
    logLevel: "verbose",
    onBrowserLog,
  });
  await renderStill({
    composition,
    serveUrl: bundleLocation,
    output,
    frame,
    inputProps,
    port: rendererPort,
    imageFormat: "png",
    overwrite: true,
    logLevel: "verbose",
    onBrowserLog,
  });
} finally {
  await fs.rm(bundleLocation, { recursive: true, force: true });
}
