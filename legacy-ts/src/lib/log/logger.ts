import pino from "pino";

/** Structured logs. Secrets are redacted by path; still never log raw keys or tokens on purpose. */
export const logger = pino({
  level: process.env.LOG_LEVEL ?? "info",
  redact: {
    paths: ["*.apiKey", "*.agentKey", "*.secret", "*.token", "req.headers.authorization"],
    censor: "[redacted]",
  },
});

export function childLogger(requestId: string) {
  return logger.child({ requestId });
}
