import { describe, expect, it } from "vitest";
import { validateConfigPayload } from "../validation.js";

const STREAM_DEFS = {
  Price: [
    { key: "start" },
    { key: "drift" },
    { key: "noise" },
  ],
};

const RUN_LIMITS = { maxSteps: 500, maxEpisodes: 20 };

describe("validation", () => {
  it("accepts valid V2 config", () => {
    const cfg = {
      version: "PlaygroundConfigV2",
      controls: { steps: 10, episodes: 2, seed: 123 },
      layers: [[{ type: "Price", params: { start: 100, drift: 0.02, noise: 0.01 } }]],
    };
    expect(validateConfigPayload(cfg, STREAM_DEFS, RUN_LIMITS)).toEqual([]);
  });

  it("rejects step limit overflow", () => {
    const cfg = {
      version: "PlaygroundConfigV2",
      controls: { steps: 9999, episodes: 2, seed: 123 },
      layers: [[{ type: "Price", params: { start: 100, drift: 0.02, noise: 0.01 } }]],
    };
    const errors = validateConfigPayload(cfg, STREAM_DEFS, RUN_LIMITS);
    expect(errors.some((e) => e.code === "validation.steps_limit")).toBe(true);
  });
});
