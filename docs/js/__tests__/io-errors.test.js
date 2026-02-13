import { describe, expect, it } from "vitest";
import { toBase64Url, fromBase64Url } from "../io.js";
import { createError, normalizeError } from "../errors.js";

describe("io and errors", () => {
  it("round-trips share payload", () => {
    const payload = JSON.stringify({ mode: "sample1", controls: { steps: 10 } });
    const encoded = toBase64Url(payload);
    const decoded = fromBase64Url(encoded);
    expect(decoded).toBe(payload);
  });

  it("normalizes raw errors", () => {
    const e = normalizeError(new Error("boom"), "runtime.failed", "failed");
    expect(e.code).toBe("runtime.failed");
    expect(e.message).toBe("failed");
  });

  it("keeps structured errors", () => {
    const e = createError("validation.cfg_invalid", "bad cfg", ["fix it"]);
    const normalized = normalizeError(e, "runtime.failed", "fallback");
    expect(normalized.code).toBe("validation.cfg_invalid");
  });
});
