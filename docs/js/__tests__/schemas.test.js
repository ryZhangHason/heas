import { describe, expect, it } from "vitest";
import { migrateIncomingConfig, buildConfigV2, buildRunPayload } from "../schemas.js";

describe("schemas", () => {
  it("migrates V1 config to V2", () => {
    const migrated = migrateIncomingConfig({
      version: "PlaygroundConfigV1",
      steps: 12,
      episodes: 3,
      seed: 7,
      layers: [[{ name: "L1", type: "Price", params: { start: 100, drift: 0.02, noise: 0.01 } }]],
    });
    expect(migrated.version).toBe("PlaygroundConfigV2");
    expect(migrated.controls.steps).toBe(12);
    expect(migrated.controls.episodes).toBe(3);
    expect(migrated.controls.seed).toBe(7);
  });

  it("builds V2 config and run payload", () => {
    const config = buildConfigV2({
      mode: "sample1",
      layers: [[{ name: "L1", type: "Price", params: { start: 100, drift: 0.02, noise: 0.01 } }]],
      controls: { steps: 8, episodes: 2, seed: 42 },
      notes: "test",
    });
    const payload = buildRunPayload(config);
    expect(payload.steps).toBe(8);
    expect(payload.episodes).toBe(2);
    expect(payload.seed).toBe(42);
    expect(Array.isArray(payload.layers)).toBe(true);
  });
});
