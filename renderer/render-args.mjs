import { createServer } from "node:net";

const canListenOnHost = (port, host) =>
  new Promise((resolve) => {
    const server = createServer();
    server.unref();
    server.once("error", (error) => {
      resolve(
        error?.code === "EAFNOSUPPORT" ||
          error?.code === "EADDRNOTAVAIL",
      );
    });
    server.listen({ port, host, exclusive: true }, () => {
      server.close(() => resolve(true));
    });
  });

export const findAvailableRendererPort = async ({
  preferredPort = Number.parseInt(
    process.env.CUTLINE_REMOTION_PORT ??
      String(32000 + (process.pid % 20000)),
    10,
  ),
  maxAttempts = 100,
} = {}) => {
  if (
    !Number.isInteger(preferredPort) ||
    preferredPort < 1024 ||
    preferredPort > 65535
  ) {
    throw new Error("Renderer port must be between 1024 and 65535");
  }
  for (let offset = 0; offset < maxAttempts; offset++) {
    const port = preferredPort + offset;
    if (port > 65535) {
      break;
    }
    const availability = await Promise.all([
      canListenOnHost(port, "127.0.0.1"),
      canListenOnHost(port, "::1"),
    ]);
    if (availability.every(Boolean)) {
      return port;
    }
  }
  throw new Error(
    `No renderer port available from ${preferredPort} across ${maxAttempts} attempts`,
  );
};

export const parseRenderArgs = (argumentsList) => {
  const values = new Map();
  for (let index = 0; index < argumentsList.length; index += 2) {
    const flag = argumentsList[index];
    const value = argumentsList[index + 1];
    if (!flag?.startsWith("--") || !value) {
      throw new Error(`Invalid renderer argument near ${flag ?? "end"}`);
    }
    values.set(flag, value);
  }
  const plan = values.get("--plan");
  const publicDir = values.get("--public-dir");
  const output = values.get("--output");
  if (!plan) {
    throw new Error("Missing required --plan argument");
  }
  if (!publicDir) {
    throw new Error("Missing required --public-dir argument");
  }
  if (!output) {
    throw new Error("Missing required --output argument");
  }
  return { plan, publicDir, output };
};

export const isProductionV2Plan = (plan) =>
  plan?.version === "2.0" &&
  plan?.profile === "production-tech-story-v4";

export const compositionIdForPlan = (plan) =>
  isProductionV2Plan(plan) ? "ProductionTechStoryV4" : "TechStory";

export const renderMediaColorOptionsForPlan = (plan) =>
  isProductionV2Plan(plan)
    ? {
        imageFormat: "jpeg",
        jpegQuality: 95,
        pixelFormat: "yuv420p",
        colorSpace: "bt709",
      }
    : {
        pixelFormat: "yuv420p",
      };
