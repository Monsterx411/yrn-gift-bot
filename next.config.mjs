import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  serverExternalPackages: ["pino-pretty"],
  webpack(config) {
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "pino-pretty": path.resolve(__dirname, "src/pino-pretty.js"),
    };
    return config;
  },
};

export default nextConfig;
