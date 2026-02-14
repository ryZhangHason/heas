import { describe, expect, it } from "vitest";
import { buildLayout, buildNormalizedSeries, pickMetricKey } from "../ui-pixel.js";

describe("ui-pixel helpers", () => {
  it("picks preferred known metric key", () => {
    const component = {
      streamName: "Prey",
      type: "PreyRisk",
    };
    const row0 = {
      "Prey.prey": 41.2,
      "Prey.other": 10,
    };
    expect(pickMetricKey(component, row0)).toBe("Prey.prey");
  });

  it("falls back to first numeric prefixed metric key", () => {
    const component = {
      streamName: "CustomComp",
      type: "Custom",
    };
    const row0 = {
      "CustomComp.label": "n/a",
      "CustomComp.energy": 0.72,
      "Other.value": 1.0,
    };
    expect(pickMetricKey(component, row0)).toBe("CustomComp.energy");
  });

  it("builds deterministic normalized series", () => {
    const rows = [
      { "A.value": 10 },
      { "A.value": 20 },
      { "A.value": 15 },
    ];
    const first = buildNormalizedSeries(rows, "A.value");
    const second = buildNormalizedSeries(rows, "A.value");

    expect(first.values.length).toBe(3);
    expect(first.normalized.length).toBe(3);
    expect(first).toEqual(second);
    expect(first.normalized[0]).toBe(0);
    expect(first.normalized[1]).toBe(1);
  });

  it("builds layer strip layout with segment geometry", () => {
    const layout = buildLayout(
      [["L1S1", "L1S2"], ["L2S1"]],
      {
        L1S1: { streamName: "L1S1", type: "Climate" },
        L1S2: { streamName: "L1S2", type: "Landscape" },
        L2S1: { streamName: "L2S1", type: "Aggregator" },
      },
      360,
      220
    );
    expect(layout.strips.length).toBe(2);
    expect(layout.segments.length).toBe(3);
    expect(layout.segments[0].width).toBeGreaterThan(0);
    expect(layout.segments[0].height).toBeGreaterThan(0);
  });
});
