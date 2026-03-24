const GA_MEASUREMENT_ID = "G-VC2SB71RWJ";
const GA_SCRIPT_ID = "heas-ga4-script";
const GA_INLINE_ID = "heas-ga4-inline";
let analyticsInitialized = false;

function canUseDom() {
  return typeof window !== "undefined" && typeof document !== "undefined";
}

function ensureDataLayer() {
  if (!canUseDom()) return null;
  window.dataLayer = window.dataLayer || [];
  if (typeof window.gtag !== "function") {
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };
  }
  return window.dataLayer;
}

function appendInlineBootstrap() {
  if (!canUseDom() || document.getElementById(GA_INLINE_ID)) return;
  const inlineScript = document.createElement("script");
  inlineScript.id = GA_INLINE_ID;
  inlineScript.textContent =
    "window.dataLayer=window.dataLayer||[];" +
    "function gtag(){dataLayer.push(arguments);}" +
    "window.gtag=window.gtag||gtag;" +
    "gtag('js', new Date());";
  document.head.appendChild(inlineScript);
}

function appendRemoteScript() {
  if (!canUseDom() || document.getElementById(GA_SCRIPT_ID)) return;
  const script = document.createElement("script");
  script.id = GA_SCRIPT_ID;
  script.async = true;
  script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(GA_MEASUREMENT_ID)}`;
  document.head.appendChild(script);
}

export function initAnalytics() {
  if (!canUseDom()) return false;
  ensureDataLayer();
  appendInlineBootstrap();
  appendRemoteScript();
  if (!window.gtag) return false;

  window.gtag("consent", "default", {
    ad_storage: "denied",
    ad_user_data: "denied",
    ad_personalization: "denied",
    analytics_storage: "granted",
  });

  if (!analyticsInitialized) {
    window.gtag("config", GA_MEASUREMENT_ID, {
      anonymize_ip: false,
      allow_google_signals: true,
      allow_ad_personalization_signals: true,
      send_page_view: true,
    });
    analyticsInitialized = true;
  }

  return true;
}

export function grantAnalyticsConsent() {
  if (!canUseDom()) return false;
  if (!analyticsInitialized) {
    return initAnalytics();
  }
  ensureDataLayer();
  if (!window.gtag) return false;
  window.gtag("consent", "update", {
    analytics_storage: "granted",
  });
  window.gtag("event", "page_view", {
    page_title: document.title,
    page_location: window.location.href,
    page_path: window.location.pathname + window.location.search,
  });
  return true;
}

export function getAnalyticsMeasurementId() {
  return GA_MEASUREMENT_ID;
}

export function trackAnalyticsEvent(name, params = {}) {
  if (!canUseDom()) return false;
  ensureDataLayer();
  if (typeof window.gtag !== "function") return false;
  window.gtag("event", name, params);
  return true;
}
