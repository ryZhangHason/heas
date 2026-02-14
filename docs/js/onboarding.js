export const ONBOARDING_KEY = "heas_onboarding_state_v1";
export const ONBOARDING_VERSION = "OnboardingStateV1";

let inMemoryOnboarding = null;

function safeGetLocalStorage() {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      return window.localStorage;
    }
  } catch (_err) {
    return null;
  }
  return null;
}

function parseMajor(appVersion) {
  const major = Number(String(appVersion || "0").split(".")[0]);
  return Number.isFinite(major) ? major : 0;
}

function parseState(raw) {
  if (!raw || typeof raw !== "object") return null;
  if (raw.version !== ONBOARDING_VERSION) return null;
  const major = Number(raw.last_seen_major);
  return {
    version: ONBOARDING_VERSION,
    tour_completed: Boolean(raw.tour_completed),
    tour_dismissed: Boolean(raw.tour_dismissed),
    last_seen_major: Number.isFinite(major) ? major : 0,
    updated_at: String(raw.updated_at || ""),
  };
}

function defaultState() {
  return {
    version: ONBOARDING_VERSION,
    tour_completed: false,
    tour_dismissed: false,
    last_seen_major: 0,
    updated_at: new Date().toISOString(),
  };
}

export function loadOnboardingState() {
  const store = safeGetLocalStorage();
  if (!store) return parseState(inMemoryOnboarding) || defaultState();
  try {
    const raw = store.getItem(ONBOARDING_KEY);
    if (raw) {
      const parsed = parseState(JSON.parse(raw));
      if (parsed) return parsed;
    }
    return parseState(inMemoryOnboarding) || defaultState();
  } catch (_err) {
    return parseState(inMemoryOnboarding) || defaultState();
  }
}

export function saveOnboardingState(state) {
  const record = parseState(state) || defaultState();
  record.updated_at = new Date().toISOString();
  const store = safeGetLocalStorage();
  if (!store) {
    inMemoryOnboarding = record;
    return false;
  }
  try {
    store.setItem(ONBOARDING_KEY, JSON.stringify(record));
    inMemoryOnboarding = record;
    return true;
  } catch (_err) {
    inMemoryOnboarding = record;
    return false;
  }
}

export function shouldShowTour(state, appVersion) {
  const current = parseState(state) || defaultState();
  const appMajor = parseMajor(appVersion);
  if (!current.tour_completed && !current.tour_dismissed) return true;
  return appMajor > current.last_seen_major;
}

export function markTourCompleted(state, appVersion) {
  const next = parseState(state) || defaultState();
  next.tour_completed = true;
  next.tour_dismissed = false;
  next.last_seen_major = parseMajor(appVersion);
  next.updated_at = new Date().toISOString();
  saveOnboardingState(next);
  return next;
}

export function markTourDismissed(state, appVersion) {
  const next = parseState(state) || defaultState();
  next.tour_dismissed = true;
  next.last_seen_major = parseMajor(appVersion);
  next.updated_at = new Date().toISOString();
  saveOnboardingState(next);
  return next;
}

export function clearOnboardingForTests() {
  const store = safeGetLocalStorage();
  if (store) {
    try {
      store.removeItem(ONBOARDING_KEY);
    } catch (_err) {
      // ignore
    }
  }
  inMemoryOnboarding = null;
}
