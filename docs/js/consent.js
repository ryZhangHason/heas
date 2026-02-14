export const CONSENT_KEY = "heas_cookie_prefs_v1";
export const CONSENT_VERSION = "CookiePrefsV1";
export const CONSENT_POLICY_VERSION = "2026-02-13";
const CONSENT_TTL_DAYS = 180;

let inMemoryConsent = null;

function nowIso() {
  return new Date().toISOString();
}

function computeExpiry(from = new Date()) {
  return new Date(from.getTime() + CONSENT_TTL_DAYS * 24 * 60 * 60 * 1000).toISOString();
}

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

function parseConsent(raw) {
  if (!raw || typeof raw !== "object") return null;
  if (raw.version !== CONSENT_VERSION) return null;
  const acknowledged = Boolean(raw.essential_acknowledged);
  const expiresAt = new Date(String(raw.expires_at || ""));
  if (!Number.isFinite(expiresAt.getTime())) return null;
  return {
    version: CONSENT_VERSION,
    essential_acknowledged: acknowledged,
    acknowledged_at: String(raw.acknowledged_at || ""),
    expires_at: expiresAt.toISOString(),
    policy_version: String(raw.policy_version || CONSENT_POLICY_VERSION),
  };
}

export function loadConsentPrefs() {
  const store = safeGetLocalStorage();
  if (!store) return parseConsent(inMemoryConsent);
  try {
    const raw = store.getItem(CONSENT_KEY);
    if (raw) {
      const parsed = parseConsent(JSON.parse(raw));
      if (parsed) return parsed;
    }
    return parseConsent(inMemoryConsent);
  } catch (_err) {
    return parseConsent(inMemoryConsent);
  }
}

export function saveConsentPrefs(record) {
  const parsed = parseConsent(record);
  if (!parsed) return false;
  const store = safeGetLocalStorage();
  if (!store) {
    inMemoryConsent = parsed;
    return true;
  }
  try {
    store.setItem(CONSENT_KEY, JSON.stringify(parsed));
    inMemoryConsent = parsed;
    return true;
  } catch (_err) {
    inMemoryConsent = parsed;
    return false;
  }
}

export function createAcknowledgedConsent() {
  const now = new Date();
  return {
    version: CONSENT_VERSION,
    essential_acknowledged: true,
    acknowledged_at: now.toISOString(),
    expires_at: computeExpiry(now),
    policy_version: CONSENT_POLICY_VERSION,
  };
}

export function isConsentActive(record, at = new Date()) {
  const parsed = parseConsent(record);
  if (!parsed || !parsed.essential_acknowledged) return false;
  if (parsed.policy_version !== CONSENT_POLICY_VERSION) return false;
  const expiresAt = new Date(parsed.expires_at);
  return expiresAt.getTime() > at.getTime();
}

export function acknowledgeConsent() {
  const record = createAcknowledgedConsent();
  saveConsentPrefs(record);
  return record;
}

export function clearConsentForTests() {
  const store = safeGetLocalStorage();
  if (store) {
    try {
      store.removeItem(CONSENT_KEY);
    } catch (_err) {
      // ignore
    }
  }
  inMemoryConsent = null;
}

export function buildConsentDebugSummary() {
  const current = loadConsentPrefs();
  return {
    timestamp: nowIso(),
    has_record: Boolean(current),
    active: isConsentActive(current),
    policy_version: current?.policy_version || null,
  };
}
