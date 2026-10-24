import { createOpenAICompatible } from "@ai-sdk/openai-compatible";

/**
 * One switch for the LLM provider (owner: P3, also used by P2 for audit and fixes).
 * Both AIML API and Gemini expose OpenAI-compatible endpoints, so one adapter covers both.
 * Keys are read on the server only; never expose them with NEXT_PUBLIC_.
 * Verify in the Day 1-2 spike: the chosen model supports tool calling and JSON output.
 */
export type AiProviderName = "aiml" | "gemini";

interface ProviderConfig {
  name: AiProviderName;
  baseURL: string;
  apiKey: string;
  model: string;
}

function readConfig(): ProviderConfig {
  const name = (process.env.AI_PROVIDER ?? "aiml") as AiProviderName;
  const prefix = name === "gemini" ? "GEMINI" : "AIML";
  const apiKey = process.env[`${prefix}_API_KEY`];
  const baseURL = process.env[`${prefix}_BASE_URL`];
  const model = process.env[`${prefix}_MODEL`];
  if (!apiKey || !baseURL || !model) {
    throw new Error(`Missing ${prefix}_API_KEY, ${prefix}_BASE_URL or ${prefix}_MODEL in the environment.`);
  }
  return { name, baseURL, apiKey, model };
}

export function getModel() {
  const cfg = readConfig();
  const provider = createOpenAICompatible({
    name: cfg.name,
    baseURL: cfg.baseURL,
    apiKey: cfg.apiKey,
  });
  return provider(cfg.model);
}
