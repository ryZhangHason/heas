import { describe, expect, it } from "vitest";
import {
  clearOnboardingForTests,
  loadOnboardingState,
  markTourCompleted,
  markTourDismissed,
  shouldShowTour,
} from "../onboarding.js";

describe("onboarding", () => {
  it("shows tour on first visit", () => {
    clearOnboardingForTests();
    const state = loadOnboardingState();
    expect(shouldShowTour(state, "1.0.0")).toBe(true);
  });

  it("hides tour after completion in same major", () => {
    clearOnboardingForTests();
    const state = markTourCompleted(loadOnboardingState(), "1.0.0");
    expect(shouldShowTour(state, "1.2.0")).toBe(false);
  });

  it("re-shows tour on major bump", () => {
    clearOnboardingForTests();
    const state = markTourDismissed(loadOnboardingState(), "1.0.0");
    expect(shouldShowTour(state, "2.0.0")).toBe(true);
  });
});
