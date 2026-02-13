import { describe, expect, it } from "vitest";
import {
  acknowledgeConsent,
  clearConsentForTests,
  createAcknowledgedConsent,
  isConsentActive,
  loadConsentPrefs,
} from "../consent.js";

describe("consent", () => {
  it("builds active acknowledged consent", () => {
    const consent = createAcknowledgedConsent();
    expect(consent.version).toBe("CookiePrefsV1");
    expect(consent.essential_acknowledged).toBe(true);
    expect(isConsentActive(consent)).toBe(true);
  });

  it("expires correctly", () => {
    const consent = createAcknowledgedConsent();
    const afterExpiry = new Date(new Date(consent.expires_at).getTime() + 1000);
    expect(isConsentActive(consent, afterExpiry)).toBe(false);
  });

  it("acknowledge stores and loads", () => {
    clearConsentForTests();
    acknowledgeConsent();
    const loaded = loadConsentPrefs();
    expect(loaded?.version).toBe("CookiePrefsV1");
    expect(loaded?.essential_acknowledged).toBe(true);
  });
});
