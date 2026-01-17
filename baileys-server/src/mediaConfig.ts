import * as fs from "fs";
import * as path from "path";

const CONFIG_PATH = path.resolve(
  process.cwd(),
  "..",
  "fastapi-server",
  "db_config.json"
);

let baseFromConfig: string | null = null;
let userFromConfig: string | null = null;

try {
  if (fs.existsSync(CONFIG_PATH)) {
    const raw = fs.readFileSync(CONFIG_PATH, "utf8");
    const parsed = JSON.parse(raw) as {
      base_path?: string;
      user?: string;
    };
    baseFromConfig = parsed.base_path || null;
    userFromConfig = parsed.user || null;
  }
} catch {
  baseFromConfig = null;
  userFromConfig = null;
}

const DEFAULT_MEDIA_BASE = path.join(process.cwd(), "media");

const MEDIA_BASE =
  baseFromConfig && baseFromConfig.length > 0
    ? path.join(baseFromConfig, userFromConfig || "")
    : process.env.MEDIA_BASE || DEFAULT_MEDIA_BASE;

export const INCOMING_MEDIA_DIR = path.join(MEDIA_BASE, "incoming");
export const OUTGOING_MEDIA_DIR = path.join(MEDIA_BASE, "outgoing");

[INCOMING_MEDIA_DIR, OUTGOING_MEDIA_DIR].forEach((dir) => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
});
