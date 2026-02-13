import {
  APP_VERSION,
  EXPORT_BUNDLE_VERSION,
  MODE,
  PLAYGROUND_CONFIG_VERSION,
  PLAYGROUND_RUN_RESULT_VERSION,
  PYODIDE_CDN,
  RUN_LIMITS,
} from "./js/state.js";
import {
  copyText,
  downloadJson,
  fromBase64Url,
  hashText,
  toBase64Url,
} from "./js/io.js";
import { ERROR_CODES, createError, formatErrorForPanel, normalizeError } from "./js/errors.js";
import {
  buildConfigV2,
  buildExportBundleV2,
  buildRunPayload,
  buildRunResultV2,
  migrateIncomingBundle,
  migrateIncomingConfig,
} from "./js/schemas.js";
import { validateConfigPayload } from "./js/validation.js";
import { PlaygroundRuntime } from "./js/runtime.js";
import { renderRunPanels } from "./js/ui-results.js";

const STREAM_TEMPLATES = {
  Custom: {
    name: "Custom Stream",
    type: "Custom",
    params: {},
    primary: { key: "value", label: "Value", type: "number", step: "0.01" },
  },
  GovernmentPolicy: {
    name: "Government Policy",
    type: "GovernmentPolicy",
    params: {
      tax: 0.1,
    },
    primary: { key: "tax", label: "Tax Rate", type: "number", step: "0.01" },
    paramMeta: {
      tax: {
        type: "category",
        kind: "condition",
        options: ["Tax 0.1", "Tax 0.3"],
        value: "Tax 0.1",
        map: { "Tax 0.1": 0.1, "Tax 0.3": 0.3 },
      },
    },
  },
  IndustryRegime: {
    name: "Industry Regime",
    type: "IndustryRegime",
    params: {
      audit_prob: 0.2,
      penalty_intensity: 0.3,
    },
    primary: { key: "audit_prob", label: "Inspection Probability", type: "number", step: "0.05" },
  },
  MarketSignal: {
    name: "Market Signal",
    type: "MarketSignal",
    params: {
      base_demand: 100,
      growth_rate: 0.02,
      market_power: 0.2,
    },
    primary: { key: "base_demand", label: "Base Demand", type: "number", step: "1" },
  },
  FirmGroup: {
    name: "Firm Group",
    type: "FirmGroup",
    params: {
      firm_count: 4,
      costs: 0.4,
      initial_balance: 1.0,
    },
    primary: { key: "firm_count", label: "Firm Count", type: "number", step: "1" },
    agent: { enabled: true, capacity: 1 },
  },
  AllianceMediator: {
    name: "Alliance Mediator (Group)",
    type: "AllianceMediator",
    params: {
      side_payment: 0.0,
    },
    primary: { key: "side_payment", label: "Side Payment", type: "number", step: "0.1" },
  },
  AllianceRule: {
    name: "Alliance Rule",
    type: "AllianceRule",
    params: {
      rule: "Join",
    },
    primary: { key: "rule", label: "Alliance Rule", type: "text" },
    paramMeta: {
      rule: { type: "category", kind: "rule", options: ["Join", "Split"], value: "Join", map: { Join: 1, Split: 0 } },
    },
  },
  GroupGamingRule: {
    name: "Group Gaming Rule",
    type: "GroupGamingRule",
    params: {
      mode: "Cooperate",
    },
    primary: { key: "mode", label: "Group Mode", type: "text" },
    paramMeta: {
      mode: { type: "category", kind: "rule", options: ["Cooperate", "Compete"], value: "Cooperate", map: { Cooperate: 1, Compete: 0 } },
    },
  },
  PayoffAccounting: {
    name: "Payoff Accounting (Micro)",
    type: "PayoffAccounting",
    params: {
      strategy: "Collaborate",
    },
    primary: { key: "strategy", label: "Strategy", type: "text" },
    paramMeta: {
      strategy: {
        type: "category",
        kind: "rule",
        options: ["Collaborate", "Defect"],
        value: "Collaborate",
        map: { Collaborate: 2, Defect: -1 },
      },
    },
  },
  AggregatorFirm: {
    name: "Aggregator Metrics",
    type: "AggregatorFirm",
    params: {
      risk_penalty: 0.2,
    },
    primary: { key: "risk_penalty", label: "Risk Penalty", type: "number", step: "0.05" },
  },
  AggregatorTotalWealth: {
    name: "Total Wealth Aggregator",
    type: "AggregatorTotalWealth",
    params: {
      metric: "Total Wealth",
    },
    primary: { key: "metric", label: "Metric", type: "text" },
  },
  AggregatorInequality: {
    name: "Inequality Aggregator",
    type: "AggregatorInequality",
    params: {
      metric: "Balance Inequality (Gini)",
    },
    primary: { key: "metric", label: "Metric", type: "text" },
  },
  PayoffAccountingGroup: {
    name: "Payoff Accounting (Group)",
    type: "PayoffAccountingGroup",
    params: {
      alliance_weight: 0.5,
    },
    primary: { key: "alliance_weight", label: "Alliance Weight", type: "number", step: "0.05" },
  },
  Climate: {
    name: "Climate Seasonal Driver + Shocks",
    type: "Climate",
    params: {
      amp: 0.4,
      period: 12,
      shock_prob: 0.1,
    },
    primary: { key: "amp", label: "Seasonal Amplitude", type: "number", step: "0.1" },
    paramMeta: {
      amp: {
        type: "category",
        kind: "condition",
        options: ["Seasonal Amplitude 0.4", "Seasonal Amplitude 0.8"],
        value: "Seasonal Amplitude 0.4",
        map: { "Seasonal Amplitude 0.4": 0.4, "Seasonal Amplitude 0.8": 0.8 },
      },
    },
  },
  Landscape: {
    name: "Landscape Patch Quality + Graph",
    type: "Landscape",
    params: {
      n_patches: 12,
      fragmentation: 0.2,
      move_cost: 0.2,
    },
    primary: { key: "fragmentation", label: "Habitat Fragmentation", type: "number", step: "0.05" },
    paramMeta: {
      move_cost: {
        type: "category",
        kind: "condition",
        options: ["Movement Cost 0.2", "Movement Cost 0.5"],
        value: "Movement Cost 0.2",
        map: { "Movement Cost 0.2": 0.2, "Movement Cost 0.5": 0.5 },
      },
    },
  },
  Prey: {
    name: "Prey Density Growth + Risk Foraging",
    type: "PreyRisk",
    params: {
      x0: 40,
      r: 0.55,
      K: 120,
      risk: 0.55,
      betaF: 0.3,
      gammaV: 0.2,
    },
    primary: { key: "risk", label: "Risk Level", type: "number", step: "0.05" },
    agent: { enabled: true, capacity: 1 },
  },
  Predator: {
    name: "Predator Consumption Response",
    type: "PredatorResponse",
    params: {
      y0: 9,
      conv: 0.3,
      mort: 0.1,
    },
    primary: { key: "conv", label: "Conversion Rate", type: "number", step: "0.01" },
    agent: { enabled: true, capacity: 1 },
  },
  Movement: {
    name: "Movement Dispersal on Graph",
    type: "Movement",
    params: {
      dispersal: 0.35,
    },
    primary: { key: "dispersal", label: "Dispersal Rate", type: "number", step: "0.05" },
  },
  Aggregator: {
    name: "Aggregator Metrics",
    type: "Aggregator",
    params: {
      ext_thresh: 1.0,
    },
    primary: { key: "ext_thresh", label: "Extinction Threshold", type: "number", step: "0.1" },
  },
};

const STREAM_DEFS = {
  Custom: [],
  GovernmentPolicy: [
    { key: "tax", label: "Tax Rate", type: "number", step: "0.01", default: 0.1 },
  ],
  IndustryRegime: [
    { key: "audit_prob", label: "Inspection Probability", type: "number", step: "0.05", default: 0.2 },
    { key: "penalty_intensity", label: "Penalty Intensity", type: "number", step: "0.05", default: 0.3 },
  ],
  MarketSignal: [
    { key: "base_demand", label: "Base Demand", type: "number", step: "1", default: 100 },
    { key: "growth_rate", label: "Growth Rate", type: "number", step: "0.01", default: 0.02 },
    { key: "market_power", label: "Market Power Effect", type: "number", step: "0.05", default: 0.2 },
  ],
  FirmGroup: [
    { key: "firm_count", label: "Firm Count", type: "number", step: "1", default: 4 },
    { key: "costs", label: "Costs", type: "number", step: "0.1", default: 0.4 },
    { key: "initial_balance", label: "Initial Balance", type: "number", step: "0.1", default: 1.0 },
  ],
  AllianceMediator: [
    { key: "side_payment", label: "Side Payment", type: "number", step: "0.1", default: 0.0 },
  ],
  AllianceRule: [
    { key: "rule", label: "Alliance Rule", type: "text", default: "Join" },
  ],
  GroupGamingRule: [
    { key: "mode", label: "Group Mode", type: "text", default: "Cooperate" },
  ],
  PayoffAccounting: [
    { key: "strategy", label: "Strategy", type: "text", default: "Collaborate" },
  ],
  PayoffAccountingGroup: [
    { key: "alliance_weight", label: "Alliance Weight", type: "number", step: "0.05", default: 0.5 },
  ],
  AggregatorFirm: [
    { key: "risk_penalty", label: "Risk Penalty", type: "number", step: "0.05", default: 0.2 },
  ],
  AggregatorTotalWealth: [
    { key: "metric", label: "Metric", type: "text", default: "Total Wealth" },
  ],
  AggregatorInequality: [
    { key: "metric", label: "Metric", type: "text", default: "Balance Inequality (Gini)" },
  ],
  Climate: [
    { key: "amp", label: "Seasonal Amplitude", type: "number", step: "0.1", default: 0.4 },
    { key: "period", label: "Seasonal Period", type: "number", step: "1", default: 12 },
    { key: "shock_prob", label: "Shock Probability", type: "number", step: "0.01", default: 0.1 },
  ],
  Landscape: [
    { key: "n_patches", label: "Number of Patches", type: "number", step: "1", default: 12 },
    { key: "fragmentation", label: "Habitat Fragmentation", type: "number", step: "0.05", default: 0.2 },
    { key: "move_cost", label: "Movement Cost", type: "number", step: "0.05", default: 0.2 },
  ],
  PreyRisk: [
    { key: "x0", label: "Initial Prey", type: "number", step: "1", default: 40 },
    { key: "r", label: "Intrinsic Growth Rate", type: "number", step: "0.01", default: 0.55 },
    { key: "K", label: "Carrying Capacity", type: "number", step: "1", default: 120 },
    { key: "risk", label: "Risk Level", type: "number", step: "0.05", default: 0.55 },
    { key: "betaF", label: "Foraging Sensitivity (Beta)", type: "number", step: "0.05", default: 0.3 },
    { key: "gammaV", label: "Visibility Scaling (Gamma)", type: "number", step: "0.05", default: 0.2 },
  ],
  PredatorResponse: [
    { key: "y0", label: "Initial Predator", type: "number", step: "1", default: 9 },
    { key: "conv", label: "Conversion Rate", type: "number", step: "0.01", default: 0.3 },
    { key: "mort", label: "Mortality Rate", type: "number", step: "0.01", default: 0.1 },
  ],
  Movement: [
    { key: "dispersal", label: "Dispersal Rate", type: "number", step: "0.05", default: 0.35 },
  ],
  Aggregator: [
    { key: "ext_thresh", label: "Extinction Threshold", type: "number", step: "0.1", default: 1.0 },
  ],
  Price: [
    { key: "start", label: "Start", type: "number", step: "0.1", default: 100 },
    { key: "drift", label: "Drift", type: "number", step: "0.01", default: 0.03 },
    { key: "noise", label: "Noise", type: "number", step: "0.01", default: 0.05 },
    { key: "out_key", label: "Output Key", type: "text", default: "" },
  ],
  Policy: [
    { key: "alpha", label: "Alpha", type: "number", step: "0.01", default: 0.05 },
    { key: "x_key", label: "Input Key", type: "text", default: "" },
  ],
};

const TEMPLATE_BY_TYPE = {
  Custom: STREAM_TEMPLATES.Custom,
  GovernmentPolicy: STREAM_TEMPLATES.GovernmentPolicy,
  IndustryRegime: STREAM_TEMPLATES.IndustryRegime,
  MarketSignal: STREAM_TEMPLATES.MarketSignal,
  FirmGroup: STREAM_TEMPLATES.FirmGroup,
  AllianceMediator: STREAM_TEMPLATES.AllianceMediator,
  AllianceRule: STREAM_TEMPLATES.AllianceRule,
  GroupGamingRule: STREAM_TEMPLATES.GroupGamingRule,
  PayoffAccounting: STREAM_TEMPLATES.PayoffAccounting,
  PayoffAccountingGroup: STREAM_TEMPLATES.PayoffAccountingGroup,
  AggregatorFirm: STREAM_TEMPLATES.AggregatorFirm,
  AggregatorTotalWealth: STREAM_TEMPLATES.AggregatorTotalWealth,
  AggregatorInequality: STREAM_TEMPLATES.AggregatorInequality,
  Climate: STREAM_TEMPLATES.Climate,
  Landscape: STREAM_TEMPLATES.Landscape,
  PreyRisk: STREAM_TEMPLATES.Prey,
  PredatorResponse: STREAM_TEMPLATES.Predator,
  Movement: STREAM_TEMPLATES.Movement,
  Aggregator: STREAM_TEMPLATES.Aggregator,
};

const state = {
  layers: [],
  components: {},
  steps: 48,
  episodes: 4,
  seed: 123,
};

let pyodideReady = false;
let pyodide = null;
const runtime = new PlaygroundRuntime({ indexURL: PYODIDE_CDN });
const sampleGridEl = document.getElementById("sampleGrid");
const customGridEl = document.getElementById("customGrid");
const statusEl = document.getElementById("status");
const stepsInput = document.getElementById("stepsInput");
const episodesInput = document.getElementById("episodesInput");
const seedInput = document.getElementById("seedInput");
const runBtn = document.getElementById("runBtn");
const cancelBtn = document.getElementById("cancelBtn");
const replayBtn = document.getElementById("replayBtn");
const exportBtn = document.getElementById("exportBtn");
const importInput = document.getElementById("importInput");
const shareBtn = document.getElementById("shareBtn");
const copyDebugBtn = document.getElementById("copyDebugBtn");
const resetBtn = document.getElementById("resetBtn");
const addLayerBtn = document.getElementById("addLayerBtn");
const addStreamBtn = document.getElementById("addStreamBtn");
const validationErrorsEl = document.getElementById("validationErrors");
const runtimeErrorsEl = document.getElementById("runtimeErrors");
const shareLinkOutput = document.getElementById("shareLinkOutput");
const runFactsOutput = document.getElementById("runFactsOutput");
const episodeSummary = document.getElementById("episodeSummary");
const stepPreview = document.getElementById("stepPreview");
const stepChart = document.getElementById("stepChart");
const episodeChart = document.getElementById("episodeChart");
const interpretationOutput = document.getElementById("interpretationOutput");
const scenarioGrid = document.getElementById("scenarioGrid");
const resultsTabBtns = Array.from(document.querySelectorAll("[data-results-tab]"));
const resultsTabPanes = Array.from(document.querySelectorAll("[data-results-pane]"));
const summaryTableHeadRow = document.getElementById("summaryTableHeadRow");
const summaryTableBody = document.getElementById("summaryTableBody");
const summaryCopyBtn = document.getElementById("summaryCopyBtn");
const summaryCsvBtn = document.getElementById("summaryCsvBtn");
const streamTypeSearchInput = document.getElementById("streamTypeSearch");
const unsavedIndicator = document.getElementById("unsavedIndicator");
const resetPresetBtn = document.getElementById("resetPresetBtn");
const bibtexOutput = document.getElementById("bibtexOutput");
const runMetaOutput = document.getElementById("runMetaOutput");
const modal = document.getElementById("modal");
const closeModalBtn = document.getElementById("closeModalBtn");
const modalForm = document.getElementById("modalForm");
const streamNameInput = document.getElementById("streamName");
const streamTypeInput = document.getElementById("streamType");
const paramFields = document.getElementById("paramFields");
const agentEnabled = document.getElementById("agentEnabled");
const agentCapacity = document.getElementById("agentCapacity");
const deleteBtn = document.getElementById("deleteBtn");
const addParamBtn = document.getElementById("addParamBtn");
const addCatBtn = document.getElementById("addCatBtn");
const encodedPreview = document.getElementById("encodedPreview");
const sample1Btn = document.getElementById("sample1Btn");
const sample2Btn = document.getElementById("sample2Btn");
const customizeBtn = document.getElementById("customizeBtn");
const sample1Section = document.getElementById("sample1Section");
const sample2Section = document.getElementById("sample2Section");
const customizeSection = document.getElementById("customizeSection");
const presetCardsSection = document.getElementById("presetCardsSection");
const runControlsSection = document.getElementById("runControlsSection");
const resultsSection = document.getElementById("resultsSection");
const exportSection = document.getElementById("exportSection");
const publicationExportBtn = document.getElementById("publicationExportBtn");
const sample1GridHost = document.getElementById("sample1GridHost");
const sample2GridHost = document.getElementById("sample2GridHost");

let activeComponentId = null;
let activeMode = MODE.SAMPLE1;
let isRunning = false;
let cancelRequested = false;
let activeRunStartMs = 0;
let activeRunTimer = null;
let lastRunArtifact = null;
let lastRunConfigPayload = null;
let hasUnsavedChanges = false;

function markDirty(dirty = true) {
  hasUnsavedChanges = dirty;
  if (unsavedIndicator) {
    unsavedIndicator.textContent = dirty ? "Unsaved changes" : "All changes saved";
    unsavedIndicator.classList.toggle("dirty", dirty);
  }
}

function activateResultsTab(tabName = "overview") {
  resultsTabBtns.forEach((btn) => {
    const active = btn.dataset.resultsTab === tabName;
    btn.classList.toggle("is-active", active);
    btn.setAttribute("aria-pressed", String(active));
  });
  resultsTabPanes.forEach((pane) => {
    pane.classList.toggle("hidden", pane.dataset.resultsPane !== tabName);
  });
}

function cloneParamMeta(meta = {}) {
  const copy = {};
  Object.entries(meta || {}).forEach(([key, value]) => {
    if (!value || typeof value !== "object") return;
    copy[key] = { ...value };
    if (Array.isArray(value.options)) copy[key].options = [...value.options];
    if (value.map && typeof value.map === "object") copy[key].map = { ...value.map };
  });
  return copy;
}

function getTemplateByType(type) {
  return TEMPLATE_BY_TYPE[type] || STREAM_TEMPLATES.Custom;
}

function getDefaultParamsForType(type) {
  const template = getTemplateByType(type);
  if (template && template.type === type) {
    return { ...(template.params || {}) };
  }
  const defaults = {};
  (STREAM_DEFS[type] || []).forEach((def) => {
    defaults[def.key] = def.default ?? "";
  });
  return defaults;
}

function getDefaultMetaForType(type) {
  const template = getTemplateByType(type);
  if (template && template.type === type) {
    return cloneParamMeta(template.paramMeta || {});
  }
  return {};
}

function getDefaultTemplatesForActiveMode(layerIndex) {
  if (activeMode === MODE.SAMPLE2) return defaultComponentsForSample2(layerIndex);
  if (activeMode === MODE.CUSTOMIZE) return [STREAM_TEMPLATES.Custom];
  return defaultComponentsForLayer(layerIndex);
}

function parseNumberish(value) {
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed) return null;
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeCategoryMeta(info = {}, fallbackValue = "") {
  const rawOptions = Array.isArray(info.options) ? info.options : [];
  const options = rawOptions
    .map((opt) => String(opt).trim())
    .filter(Boolean);

  const fallback = fallbackValue ?? info.value ?? "";
  const fallbackLabel = String(fallback).trim();
  if (!options.length && fallbackLabel) {
    options.push(fallbackLabel);
  }

  const value = options.includes(String(info.value)) ? String(info.value) : options[0] || fallbackLabel;
  const map = {};
  const sourceMap = info.map && typeof info.map === "object" ? info.map : {};
  options.forEach((opt, idx) => {
    if (Object.prototype.hasOwnProperty.call(sourceMap, opt)) {
      const mapped = parseNumberish(sourceMap[opt]);
      map[opt] = mapped ?? sourceMap[opt];
    } else {
      map[opt] = idx;
    }
  });

  return {
    type: "category",
    kind: info.kind || "condition",
    options,
    value,
    map,
  };
}

function normalizeParamMeta(meta = {}, params = {}) {
  const normalized = {};
  Object.entries(meta || {}).forEach(([key, info]) => {
    if (!info || typeof info !== "object") return;
    if (info.type === "category") {
      normalized[key] = normalizeCategoryMeta(info, params[key]);
    } else {
      normalized[key] = { ...info };
    }
  });
  return normalized;
}

function mergeParamMeta(baseMeta = {}, overrideMeta = {}, params = {}) {
  const merged = cloneParamMeta(baseMeta);
  Object.entries(overrideMeta || {}).forEach(([key, value]) => {
    if (!value || typeof value !== "object") return;
    merged[key] = { ...(merged[key] || {}), ...value };
    if (Array.isArray(value.options)) merged[key].options = [...value.options];
    if (value.map && typeof value.map === "object") merged[key].map = { ...value.map };
  });
  return normalizeParamMeta(merged, params);
}

function encodeComponentParams(component, override = {}) {
  const params = { ...(component.params || {}), ...(override || {}) };
  const meta = component.paramMeta || {};
  Object.entries(meta).forEach(([key, info]) => {
    if (info?.type !== "category") return;
    const normalized = normalizeCategoryMeta(info, params[key]);
    const selectedRaw = override[key] ?? normalized.value ?? params[key];
    const selected = String(selectedRaw);

    if (Object.prototype.hasOwnProperty.call(normalized.map, selected)) {
      params[key] = normalized.map[selected];
      return;
    }
    const numeric = parseNumberish(selectedRaw);
    if (numeric !== null) {
      params[key] = numeric;
      return;
    }
    if (normalized.options.length) {
      const fallback = normalized.options[0];
      params[key] = Object.prototype.hasOwnProperty.call(normalized.map, fallback) ? normalized.map[fallback] : 0;
      return;
    }
    params[key] = selectedRaw;
  });
  return params;
}

function setRunButtonState(running) {
  runBtn.disabled = running || !pyodideReady;
  runBtn.classList.toggle("loading", running);
  runBtn.textContent = running ? "Running..." : "Run Simulation";
  if (cancelBtn) cancelBtn.disabled = !running;
  if (replayBtn) replayBtn.disabled = running || !lastRunConfigPayload;
  if (copyDebugBtn) copyDebugBtn.disabled = !lastRunArtifact;
}

function showValidationErrors(errors = []) {
  if (!validationErrorsEl) return;
  if (!errors.length) {
    validationErrorsEl.classList.add("hidden");
    validationErrorsEl.textContent = "";
    return;
  }
  const lines = ["Validation Errors:"];
  errors.forEach((err, i) => {
    lines.push(`${i + 1}. [${err.code}] ${err.message}`);
    if (err.details?.path) lines.push(`   path: ${err.details.path}`);
    (err.hints || []).forEach((hint) => lines.push(`   hint: ${hint}`));
  });
  validationErrorsEl.textContent = lines.join("\n");
  validationErrorsEl.classList.remove("hidden");
}

function showRuntimeError(errorObj = null) {
  if (!runtimeErrorsEl) return;
  if (!errorObj) {
    runtimeErrorsEl.classList.add("hidden");
    runtimeErrorsEl.textContent = "";
    return;
  }
  runtimeErrorsEl.textContent = formatErrorForPanel(errorObj);
  runtimeErrorsEl.classList.remove("hidden");
}

function createRuntimeError(type, message, hints = [], details = {}) {
  return createError(type, message, hints, details);
}

function updateRunFacts(runResult = null) {
  if (!runFactsOutput) return;
  if (!runResult) {
    runFactsOutput.textContent = "No run yet.";
    if (runMetaOutput) runMetaOutput.textContent = "";
    return;
  }
  const engineVersion = runResult.engine?.engine_version || runResult.engine_version || "unknown";
  const lines = [
    `app_version: ${APP_VERSION}`,
    `result_version: ${runResult.version}`,
    `run_id: ${runResult.run_id}`,
    `config_hash: ${runResult.config_hash}`,
    `engine_version: ${engineVersion}`,
    `created_at: ${runResult.created_at || "unknown"}`,
    `episodes: ${runResult.episodes?.length || 0}`,
    `limits_applied: ${JSON.stringify(runResult.limits_applied || {})}`,
    `warnings: ${(runResult.warnings || []).length}`,
    `errors: ${(runResult.errors || []).length}`,
  ];
  runFactsOutput.textContent = lines.join("\n");
  if (runMetaOutput) {
    runMetaOutput.textContent = `run_id=${runResult.run_id}\nconfig_hash=${runResult.config_hash}\nengine=${engineVersion}\napp=${APP_VERSION}`;
  }
}

function sanitizeForDebug(value) {
  try {
    return JSON.parse(JSON.stringify(value));
  } catch (_err) {
    return null;
  }
}

function buildDebugReport() {
  return {
    app_version: APP_VERSION,
    pyodide_ready: pyodideReady,
    pyodide_version: pyodide?.version || "unknown",
    mode: activeMode,
    state_snapshot: sanitizeForDebug({
      steps: state.steps,
      episodes: state.episodes,
      seed: state.seed,
      layer_count: state.layers.length,
      component_count: Object.keys(state.components).length,
    }),
    last_run: sanitizeForDebug(lastRunArtifact),
  };
}

function getConfigPayloadV2() {
  const layers = state.layers.map((layer) =>
    layer.map((componentId) => {
      const component = state.components[componentId];
      return {
        name: component.streamName,
        display_name: component.displayName,
        type: component.type,
        params: encodeComponentParams(component),
        meta: cloneParamMeta(component.paramMeta || {}),
        agent: { ...(component.agent || { enabled: false, capacity: 1 }) },
      };
    })
  );
  return buildConfigV2({
    mode: activeMode,
    layers,
    controls: { steps: state.steps, episodes: state.episodes, seed: state.seed },
    notes: "",
  });
}

function buildExportBundle(runResult = null) {
  return buildExportBundleV2({
    config: getConfigPayloadV2(),
    result: runResult || null,
    report: buildDebugReport(),
    checksums: {},
  });
}

function detectMemoryPressure() {
  if (!performance?.memory) return null;
  const { usedJSHeapSize, jsHeapSizeLimit } = performance.memory;
  if (!Number.isFinite(usedJSHeapSize) || !Number.isFinite(jsHeapSizeLimit) || jsHeapSizeLimit <= 0) return null;
  const ratio = usedJSHeapSize / jsHeapSizeLimit;
  if (ratio >= 0.9) {
    return `High memory pressure detected (${Math.round(ratio * 100)}% heap used).`;
  }
  return null;
}

function buildComponent(layerIndex, componentIndex, template) {
  const streamName = `L${layerIndex + 1}S${componentIndex + 1}`;
  return {
    id: streamName,
    layerIndex,
    streamName,
    displayName: template.name,
    type: template.type,
    params: { ...(template.params || {}) },
    primary: { ...(template.primary || STREAM_TEMPLATES.Custom.primary) },
    paramMeta: cloneParamMeta(template.paramMeta || {}),
    agent: {
      enabled: Boolean(template.agent?.enabled),
      capacity: Number.isFinite(Number(template.agent?.capacity)) ? Number(template.agent.capacity) : 1,
    },
  };
}

function removeComponent(componentId) {
  const component = state.components[componentId];
  if (!component) return;
  const layerIndex = component.layerIndex;
  state.layers[layerIndex] = state.layers[layerIndex].filter((id) => id !== componentId);
  delete state.components[componentId];
  renderAllGrids();
  markDirty(true);
}

function defaultComponentsForLayer(layerIndex) {
  if (layerIndex === 0) return [STREAM_TEMPLATES.Climate, STREAM_TEMPLATES.Landscape];
  if (layerIndex === 1) return [STREAM_TEMPLATES.Prey, STREAM_TEMPLATES.Predator, STREAM_TEMPLATES.Movement];
  if (layerIndex === 2) return [STREAM_TEMPLATES.Aggregator];
  return [STREAM_TEMPLATES.Aggregator];
}

function defaultComponentsForSample2(layerIndex) {
  if (layerIndex === 0) {
    return [STREAM_TEMPLATES.GovernmentPolicy, STREAM_TEMPLATES.IndustryRegime, STREAM_TEMPLATES.MarketSignal];
  }
  if (layerIndex === 1) {
    return [
      STREAM_TEMPLATES.FirmGroup,
      STREAM_TEMPLATES.PayoffAccounting,
    ];
  }
  if (layerIndex === 2) {
    return [STREAM_TEMPLATES.AllianceRule, STREAM_TEMPLATES.GroupGamingRule];
  }
  if (layerIndex === 3) {
    return [STREAM_TEMPLATES.AggregatorTotalWealth, STREAM_TEMPLATES.AggregatorInequality];
  }
  return [STREAM_TEMPLATES.AggregatorTotalWealth, STREAM_TEMPLATES.AggregatorInequality];
}

function initSampleUsage1() {
  state.layers = [];
  state.components = {};
  const layerTemplates = [defaultComponentsForLayer(0), defaultComponentsForLayer(1), defaultComponentsForLayer(2)];
  layerTemplates.forEach((templates, layerIndex) => {
    const layerComponents = [];
    templates.forEach((template, idx) => {
      const component = buildComponent(layerIndex, idx, template);
      state.components[component.id] = component;
      layerComponents.push(component.id);
    });
    state.layers.push(layerComponents);
  });
  syncRunInputs();
  renderAllGrids();
  clearResults();
  markDirty(false);
}

function initCustomizeEmpty() {
  state.layers = [];
  state.components = {};
  const layers = 2;
  const streamsPerLayer = 2;
  for (let layerIndex = 0; layerIndex < layers; layerIndex += 1) {
    const layerComponents = [];
    for (let streamIndex = 0; streamIndex < streamsPerLayer; streamIndex += 1) {
      const component = buildComponent(layerIndex, streamIndex, STREAM_TEMPLATES.Custom);
      state.components[component.id] = component;
      layerComponents.push(component.id);
    }
    state.layers.push(layerComponents);
  }
  syncRunInputs();
  renderAllGrids();
  clearResults();
  markDirty(false);
}

function initSampleUsage2() {
  state.layers = [];
  state.components = {};
  const layerTemplates = [
    defaultComponentsForSample2(0),
    defaultComponentsForSample2(1),
    defaultComponentsForSample2(2),
    defaultComponentsForSample2(3),
  ];
  layerTemplates.forEach((templates, layerIndex) => {
    const layerComponents = [];
    templates.forEach((template, idx) => {
      const component = buildComponent(layerIndex, idx, template);
      state.components[component.id] = component;
      layerComponents.push(component.id);
    });
    state.layers.push(layerComponents);
  });
  syncRunInputs();
  renderAllGrids();
  clearResults();
  markDirty(false);
}

function renderGrid(gridEl) {
  gridEl.innerHTML = "";
  const streamCount = Math.max(0, ...state.layers.map((layer) => layer.length));

  const headerRow = document.createElement("div");
  headerRow.className = "grid-row grid-header";
  headerRow.appendChild(document.createElement("div"));
  for (let s = 0; s < streamCount; s += 1) {
    const header = document.createElement("div");
    header.textContent = `Stream ${s + 1}`;
    headerRow.appendChild(header);
  }
  gridEl.appendChild(headerRow);

  state.layers.forEach((layer, layerIndex) => {
    const row = document.createElement("div");
    row.className = "grid-row";
    const label = document.createElement("div");
    label.className = "layer-label";
    label.textContent = `Layer ${layerIndex + 1}`;
    row.appendChild(label);

    layer.forEach((componentId, streamIndex) => {
      const component = state.components[componentId];
      const paramDef =
        (STREAM_DEFS[component.type] || []).find((def) => def.key === component.primary?.key) ||
        component.primary || { key: "value", label: "Value", type: "number" };

      const cellEl = document.createElement("div");
      cellEl.className = "cell";
      cellEl.dataset.layer = layerIndex;
      cellEl.dataset.stream = streamIndex;
      cellEl.addEventListener("click", () => openModal(component.id));

      const title = document.createElement("h4");
      title.textContent = component.displayName;
      const subtitle = document.createElement("p");
      subtitle.textContent = `${component.streamName} • ${paramDef.label}`;

      const inputsWrap = document.createElement("div");
      inputsWrap.className = "cell-inputs";

      const defs = STREAM_DEFS[component.type] || [];
      const defKeys = defs.map((def) => def.key);
      defs.forEach((def) => {
        const label = document.createElement("label");
        label.className = "cell-input";
        label.textContent = def.label;
        const meta = component.paramMeta?.[def.key];
        if (meta?.type === "category") {
          const select = document.createElement("select");
          (meta.options || []).forEach((opt) => {
            const option = document.createElement("option");
            option.value = opt;
            option.textContent = opt;
            select.appendChild(option);
          });
          select.value = meta.value ?? component.params[def.key] ?? "";
          select.addEventListener("click", (event) => event.stopPropagation());
          select.addEventListener("change", () => {
            component.params[def.key] = select.value;
            meta.value = select.value;
            markDirty(true);
            renderAllGrids();
          });
          label.appendChild(select);
        } else {
          const input = document.createElement("input");
          input.type = def.type;
          if (def.step) input.step = def.step;
          input.value = component.params[def.key] ?? def.default ?? "";
          input.addEventListener("click", (event) => event.stopPropagation());
          input.addEventListener("change", () => {
            component.params[def.key] = input.type === "number" ? Number(input.value) : input.value;
            markDirty(true);
            renderAllGrids();
          });
          label.appendChild(input);
        }
        inputsWrap.appendChild(label);
      });

      Object.entries(component.params || {})
        .filter(([key]) => !defKeys.includes(key))
        .forEach(([key, value]) => {
          const label = document.createElement("label");
          label.className = "cell-input";
          label.textContent = key;
          const meta = component.paramMeta?.[key];
          if (meta?.type === "category") {
            const select = document.createElement("select");
            (meta.options || []).forEach((opt) => {
              const option = document.createElement("option");
              option.value = opt;
              option.textContent = opt;
              select.appendChild(option);
            });
            select.value = meta.value ?? value ?? "";
            select.addEventListener("click", (event) => event.stopPropagation());
            select.addEventListener("change", () => {
              component.params[key] = select.value;
              meta.value = select.value;
              markDirty(true);
              renderAllGrids();
            });
            label.appendChild(select);
          } else {
            const input = document.createElement("input");
            input.type = "text";
            input.value = value ?? "";
            input.addEventListener("click", (event) => event.stopPropagation());
            input.addEventListener("change", () => {
              const raw = input.value.trim();
              const num = Number(raw);
              component.params[key] = raw !== "" && !Number.isNaN(num) ? num : raw;
              markDirty(true);
              renderAllGrids();
            });
            label.appendChild(input);
          }
          inputsWrap.appendChild(label);
        });

      cellEl.appendChild(title);
      cellEl.appendChild(subtitle);
      cellEl.appendChild(inputsWrap);
      row.appendChild(cellEl);
    });

    gridEl.appendChild(row);
  });
}

function renderAllGrids() {
  renderGrid(sampleGridEl);
  renderGrid(customGridEl);
}

function getConfigPayload() {
  return getConfigPayloadV2();
}

function buildPayloadWithOverrides(overrideMap) {
  const overrideLayers = state.layers.map((layer) =>
    layer.map((componentId) => {
      const component = state.components[componentId];
      const override = overrideMap?.[componentId] || {};
      return {
        name: component.streamName,
        type: component.type,
        params: encodeComponentParams(component, override),
      };
    })
  );
  return buildRunPayload(getConfigPayloadV2(), overrideLayers);
}

function assertRunPayloadBridge(payload) {
  if (!payload || typeof payload !== "object") {
    throw createError(ERROR_CODES.runtime.FAILED, "Runtime payload is invalid.");
  }
  if (!Array.isArray(payload.layers) || !payload.layers.length) {
    throw createError(ERROR_CODES.validation.LAYERS_INVALID, "Runtime payload requires at least one layer.");
  }
}

function applyConfigToState(config, modeHint = MODE.CUSTOMIZE) {
  const migrated = migrateIncomingConfig(config);
  state.steps = Math.max(1, Math.floor(Number(migrated.controls?.steps) || 20));
  state.episodes = Math.max(1, Math.floor(Number(migrated.controls?.episodes) || 1));
  state.seed = Number(migrated.controls?.seed) || 123;

  state.layers = [];
  state.components = {};
  migrated.layers.forEach((layer, layerIndex) => {
    const layerIds = [];
    (layer || []).forEach((stream, streamIndex) => {
      const template = getTemplateByType(stream.type || "Custom");
      const component = buildComponent(layerIndex, streamIndex, template);
      component.type = stream.type || template.type || "Custom";
      component.displayName = stream.display_name || stream.name || component.displayName;
      component.streamName = stream.name || component.streamName;
      component.id = component.streamName;
      component.params = mergeDefaultsForType(component.type, stream.params || {});
      component.primary = getPrimaryForType(component.type);
      component.paramMeta = mergeParamMeta(getDefaultMetaForType(component.type), stream.meta || {}, component.params);
      component.agent = {
        enabled: Boolean(stream.agent?.enabled || false),
        capacity: Math.max(1, Math.floor(Number(stream.agent?.capacity || 1))),
      };
      state.components[component.id] = component;
      layerIds.push(component.id);
    });
    state.layers.push(layerIds);
  });
  showSection(modeHint);
  syncRunInputs();
  renderAllGrids();
  markDirty(false);
}

function buildScenarioList() {
  const categories = [];
  Object.values(state.components).forEach((component) => {
    const meta = component.paramMeta || {};
    Object.entries(meta).forEach(([key, info]) => {
      if (info?.type === "category") {
        const normalized = normalizeCategoryMeta(info, component.params?.[key]);
        if ((normalized.kind || "condition") !== "condition") return;
        if (!normalized.options.length) return;
        categories.push({
          componentId: component.id,
          key,
          options: normalized.options,
        });
      }
    });
  });
  if (!categories.length) return [{ label: "Base", overrides: {} }];

  const combos = [];
  const walk = (i, current, labelParts) => {
    if (i >= categories.length) {
      combos.push({ label: labelParts.join(", "), overrides: { ...current } });
      return;
    }
    const { componentId, key, options } = categories[i];
    options.forEach((opt) => {
      const next = { ...current };
      next[`${componentId}::${key}`] = opt;
      walk(i + 1, next, [...labelParts, `${componentId}.${key}=${opt}`]);
    });
  };
  walk(0, {}, []);
  return combos;
}

function renderParamFields(type, params, meta = {}) {
  paramFields.innerHTML = "";
  const defs = STREAM_DEFS[type] || [];
  const defKeys = defs.map((def) => def.key);
  defs.forEach((def) => {
    const label = document.createElement("label");
    label.textContent = def.label;
    if (meta?.[def.key]?.type === "category") {
      const select = document.createElement("select");
      (meta[def.key].options || []).forEach((opt) => {
        const option = document.createElement("option");
        option.value = opt;
        option.textContent = opt;
        select.appendChild(option);
      });
      select.value = meta[def.key].value ?? params?.[def.key] ?? def.default ?? "";
      select.dataset.key = def.key;
      label.appendChild(select);
      const kindSelect = document.createElement("select");
      kindSelect.dataset.catKind = def.key;
      ["condition", "rule"].forEach((k) => {
        const opt = document.createElement("option");
        opt.value = k;
        opt.textContent = k;
        kindSelect.appendChild(opt);
      });
      kindSelect.value = meta[def.key].kind || "condition";
      label.appendChild(kindSelect);
      const optionsInput = document.createElement("input");
      optionsInput.type = "text";
      optionsInput.placeholder = "Category options (comma-separated)";
      optionsInput.value = (meta[def.key].options || []).join(", ");
      optionsInput.dataset.catOptions = def.key;
      const valuesInput = document.createElement("input");
      valuesInput.type = "text";
      valuesInput.placeholder = "Category values (comma-separated)";
      const mapVals = meta[def.key].map
        ? meta[def.key].options.map((opt) => meta[def.key].map[opt])
        : [];
      valuesInput.value = mapVals.length ? mapVals.join(", ") : "";
      valuesInput.dataset.catValues = def.key;
      label.appendChild(optionsInput);
      label.appendChild(valuesInput);
    } else {
      const input = document.createElement("input");
      input.type = def.type;
      if (def.step) input.step = def.step;
      input.value = params?.[def.key] ?? def.default ?? "";
      input.dataset.key = def.key;
      label.appendChild(input);
    }
    paramFields.appendChild(label);
  });

  const extras = Object.entries(params || {}).filter(([k]) => !defKeys.includes(k));
  extras.forEach(([key, value]) => {
    const options = meta?.[key]?.options || [];
    const values = meta?.[key]?.map ? options.map((opt) => meta[key].map[opt]) : [];
    const kind = meta?.[key]?.kind || "condition";
    addCustomParamRow(key, value, meta?.[key]?.type || "text", options, values, kind);
  });
  updateEncodedPreviewFromForm();
}

function collectParamsAndMeta() {
  const params = {};
  const meta = {};
  paramFields.querySelectorAll("[data-key]").forEach((input) => {
    const key = input.dataset.key;
    if (input.tagName.toLowerCase() === "select") {
      params[key] = input.value;
    } else if (input.type === "number") {
      params[key] = Number(input.value);
    } else {
      params[key] = input.value;
    }
  });
  paramFields.querySelectorAll("input[data-cat-options]").forEach((input) => {
    const key = input.dataset.catOptions;
    const options = input.value
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
    if (!meta[key]) meta[key] = {};
    meta[key].type = "category";
    meta[key].options = options;
  });
  paramFields.querySelectorAll("input[data-cat-values]").forEach((input) => {
    const key = input.dataset.catValues;
    const values = input.value
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean)
      .map((v) => Number(v));
    if (!meta[key]) meta[key] = {};
    const options = meta[key].options || [];
    const map = {};
    options.forEach((opt, idx) => {
      const val = Number.isFinite(values[idx]) ? values[idx] : idx;
      map[opt] = val;
    });
    meta[key].map = map;
  });
  paramFields.querySelectorAll("select[data-cat-kind]").forEach((input) => {
    const key = input.dataset.catKind;
    if (!meta[key]) meta[key] = {};
    meta[key].kind = input.value;
  });
  paramFields.querySelectorAll(".param-row").forEach((row) => {
    const keyInput = row.querySelector("input[data-custom-key]");
    const valInput = row.querySelector("input[data-custom-value]");
    const typeSelect = row.querySelector("select[data-custom-type]");
    const kindSelect = row.querySelector("select[data-custom-kind]");
    const optionsInput = row.querySelector("input[data-custom-options]");
    const valuesInput = row.querySelector("input[data-custom-values]");
    if (!keyInput || !valInput || !typeSelect) return;
    const key = keyInput.value.trim();
    if (!key) return;
    const type = typeSelect.value;
    if (type === "category") {
      const options = (optionsInput?.value || "")
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean);
      const values = (valuesInput?.value || "")
        .split(",")
        .map((v) => v.trim())
        .filter(Boolean)
        .map((v) => Number(v));
      const raw = valInput.value.trim();
      const value = options.includes(raw) ? raw : options[0] || raw;
      params[key] = value;
      const map = {};
      options.forEach((opt, idx) => {
        const val = Number.isFinite(values[idx]) ? values[idx] : idx;
        map[opt] = val;
      });
      meta[key] = { type: "category", options, value, map, kind: kindSelect?.value || "condition" };
    } else if (type === "number") {
      params[key] = Number(valInput.value);
    } else {
      params[key] = valInput.value;
    }
  });
  return { params, meta: normalizeParamMeta(meta, params) };
}

function getPrimaryForType(type) {
  if (type === "Custom") return STREAM_TEMPLATES.Custom.primary;
  if (type === "GovernmentPolicy") return STREAM_TEMPLATES.GovernmentPolicy.primary;
  if (type === "IndustryRegime") return STREAM_TEMPLATES.IndustryRegime.primary;
  if (type === "MarketSignal") return STREAM_TEMPLATES.MarketSignal.primary;
  if (type === "FirmGroup") return STREAM_TEMPLATES.FirmGroup.primary;
  if (type === "AllianceMediator") return STREAM_TEMPLATES.AllianceMediator.primary;
  if (type === "AllianceRule") return STREAM_TEMPLATES.AllianceRule.primary;
  if (type === "GroupGamingRule") return STREAM_TEMPLATES.GroupGamingRule.primary;
  if (type === "PayoffAccounting") return STREAM_TEMPLATES.PayoffAccounting.primary;
  if (type === "PayoffAccountingGroup") return STREAM_TEMPLATES.PayoffAccountingGroup.primary;
  if (type === "AggregatorFirm") return STREAM_TEMPLATES.AggregatorFirm.primary;
  if (type === "AggregatorTotalWealth") return STREAM_TEMPLATES.AggregatorTotalWealth.primary;
  if (type === "AggregatorInequality") return STREAM_TEMPLATES.AggregatorInequality.primary;
  if (type === "Climate") return STREAM_TEMPLATES.Climate.primary;
  if (type === "Landscape") return STREAM_TEMPLATES.Landscape.primary;
  if (type === "PreyRisk") return STREAM_TEMPLATES.Prey.primary;
  if (type === "PredatorResponse") return STREAM_TEMPLATES.Predator.primary;
  if (type === "Movement") return STREAM_TEMPLATES.Movement.primary;
  if (type === "Aggregator") return STREAM_TEMPLATES.Aggregator.primary;
  if (type === "Price") return { key: "drift", label: "Drift", type: "number", step: "0.01" };
  if (type === "Policy") return { key: "alpha", label: "Alpha", type: "number", step: "0.01" };
  return { key: "value", label: "Value", type: "number", step: "0.01" };
}

function mergeDefaultsForType(type, existing) {
  const defs = STREAM_DEFS[type] || [];
  const merged = {};
  defs.forEach((def) => {
    merged[def.key] = existing?.[def.key] ?? def.default ?? "";
  });
  if (type !== "Custom") {
    return merged;
  }
  Object.entries(existing || {}).forEach(([k, v]) => {
    if (!(k in merged)) merged[k] = v;
  });
  return merged;
}

function addCustomParamRow(key = "", value = "", type = "text", options = [], values = [], kind = "condition") {
  const row = document.createElement("div");
  row.className = "param-row";

  const keyInput = document.createElement("input");
  keyInput.type = "text";
  keyInput.placeholder = "Parameter name";
  keyInput.value = key;
  keyInput.dataset.customKey = "1";

  const typeSelect = document.createElement("select");
  typeSelect.dataset.customType = "1";
  ["number", "text", "category"].forEach((t) => {
    const option = document.createElement("option");
    option.value = t;
    option.textContent = t;
    typeSelect.appendChild(option);
  });
  typeSelect.value = type;

  const kindSelect = document.createElement("select");
  kindSelect.dataset.customKind = "1";
  ["condition", "rule"].forEach((k) => {
    const opt = document.createElement("option");
    opt.value = k;
    opt.textContent = k;
    kindSelect.appendChild(opt);
  });
  kindSelect.value = kind;

  const valueInput = document.createElement("input");
  valueInput.type = "text";
  valueInput.placeholder = "Value";
  valueInput.value = value ?? "";
  valueInput.dataset.customValue = "1";

  const optionsInput = document.createElement("input");
  optionsInput.type = "text";
  optionsInput.placeholder = "Options (comma-separated)";
  optionsInput.value = options.join(", ");
  optionsInput.dataset.customOptions = "1";
  optionsInput.classList.add("param-options");

  const valuesInput = document.createElement("input");
  valuesInput.type = "text";
  valuesInput.placeholder = "Values (comma-separated)";
  valuesInput.value = values.join(", ");
  valuesInput.dataset.customValues = "1";
  valuesInput.classList.add("param-values");

  const toggleOptions = () => {
    const show = typeSelect.value === "category";
    optionsInput.style.display = show ? "block" : "none";
    valuesInput.style.display = show ? "block" : "none";
    kindSelect.style.display = show ? "block" : "none";
  };
  typeSelect.addEventListener("change", toggleOptions);
  toggleOptions();

  row.appendChild(keyInput);
  row.appendChild(typeSelect);
  row.appendChild(kindSelect);
  row.appendChild(valueInput);
  row.appendChild(optionsInput);
  row.appendChild(valuesInput);
  paramFields.appendChild(row);
}

function openModal(componentId) {
  activeComponentId = componentId;
  const component = state.components[componentId];
  if (!component) return;
  streamNameInput.value = component.displayName;
  streamTypeInput.value = component.type;
  if (streamTypeSearchInput) streamTypeSearchInput.value = component.type;
  if (agentEnabled) agentEnabled.checked = Boolean(component.agent?.enabled);
  if (agentCapacity) agentCapacity.value = component.agent?.capacity ?? 1;
  renderParamFields(component.type, component.params, normalizeParamMeta(component.paramMeta || {}, component.params || {}));
  updateEncodedPreviewFromForm();
  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
}

function closeModal() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
}

function updateEncodedPreviewFromForm() {
  if (!encodedPreview) return;
  if (!activeComponentId) {
    encodedPreview.textContent = "";
    return;
  }
  const component = state.components[activeComponentId];
  if (!component) return;
  const nextType = streamTypeInput.value || component.type;
  const { params: nextParams, meta } = collectParamsAndMeta();
  const mergedParams = mergeDefaultsForType(nextType, nextParams);
  const mergedMeta = mergeParamMeta(getDefaultMetaForType(nextType), meta, mergedParams);
  const previewComponent = {
    ...component,
    type: nextType,
    params: mergedParams,
    paramMeta: mergedMeta,
  };
  const encoded = encodeComponentParams(previewComponent);
  encodedPreview.textContent = `Encoded Params Preview\n${JSON.stringify(encoded, null, 2)}`;
}

function updateStreamFromModal() {
  if (!activeComponentId) return;
  const component = state.components[activeComponentId];
  if (!component) return;
  component.displayName = streamNameInput.value.trim() || component.displayName;
  const nextType = streamTypeInput.value;
  const template = getTemplateByType(nextType);
  const { params: nextParams, meta } = collectParamsAndMeta();
  const mergedParams = mergeDefaultsForType(nextType, nextParams);
  component.type = nextType;
  component.params = mergedParams;
  component.primary = getPrimaryForType(nextType);
  component.paramMeta = mergeParamMeta(getDefaultMetaForType(nextType), meta, mergedParams);
  component.agent = {
    enabled: agentEnabled?.checked || Boolean(template.agent?.enabled),
    capacity: Math.max(1, Math.floor(Number(agentCapacity?.value || template.agent?.capacity || 1))),
  };
  renderAllGrids();
  markDirty(true);
  updateEncodedPreviewFromForm();
}

function resetCell() {
  if (!activeComponentId) return;
  const component = state.components[activeComponentId];
  if (!component) return;
  const layerIndex = component.layerIndex;
  const componentIndex = state.layers[layerIndex].indexOf(component.id);
  const defaults = getDefaultTemplatesForActiveMode(layerIndex);
  const template = defaults[componentIndex % defaults.length] || defaults[0];
  const nextComponent = buildComponent(layerIndex, componentIndex, template);
  state.components[component.id] = {
    ...component,
    displayName: nextComponent.displayName,
    type: nextComponent.type,
    params: nextComponent.params,
    primary: nextComponent.primary,
  };
  renderAllGrids();
  markDirty(true);
  closeModal();
}

function addLayer() {
  const newLayerIndex = state.layers.length;
  const templates = getDefaultTemplatesForActiveMode(newLayerIndex);
  const layerComponents = [];
  templates.forEach((template, idx) => {
    const component = buildComponent(newLayerIndex, idx, template);
    state.components[component.id] = component;
    layerComponents.push(component.id);
  });
  state.layers.push(layerComponents);
  renderAllGrids();
  markDirty(true);
}

function addStream() {
  state.layers.forEach((layer, layerIndex) => {
    const nextIndex = layer.length;
    const templates = getDefaultTemplatesForActiveMode(layerIndex);
    const template = templates[nextIndex % templates.length] || templates[0];
    const component = buildComponent(layerIndex, nextIndex, template);
    state.components[component.id] = component;
    layer.push(component.id);
  });
  renderAllGrids();
  markDirty(true);
}

function clearResults() {
  episodeSummary.textContent = "";
  stepPreview.textContent = "";
  if (summaryTableBody) summaryTableBody.innerHTML = "";
  if (shareLinkOutput) {
    shareLinkOutput.textContent = "";
    shareLinkOutput.classList.add("hidden");
  }
  clearChart();
  clearEpisodeChart();
  if (scenarioGrid) scenarioGrid.innerHTML = "";
  if (interpretationOutput) interpretationOutput.textContent = "";
  showValidationErrors([]);
  showRuntimeError(null);
}

function showSection(mode) {
  activeMode = mode;
  const showSample1 = mode === MODE.SAMPLE1;
  const showSample2 = mode === MODE.SAMPLE2;
  const showCustomize = mode === MODE.CUSTOMIZE;
  const showPresets = !showCustomize;

  if (presetCardsSection) presetCardsSection.classList.toggle("hidden", !showPresets);

  sample1Section.classList.toggle("hidden", !showSample1);
  sample2Section.classList.toggle("hidden", !showSample2);
  customizeSection.classList.toggle("hidden", !showCustomize);

  // Keep outputs visible for all modes so custom runs are inspectable.
  const showResults = true;
  resultsSection.classList.toggle("hidden", !showResults);
  if (exportSection) exportSection.classList.toggle("hidden", !showResults);

  if (showSample2 && sample2GridHost && sampleGridEl) {
    sample2GridHost.appendChild(sampleGridEl);
  }
  if (showSample1 && sample1GridHost && sampleGridEl) {
    sample1GridHost.appendChild(sampleGridEl);
  }

  sample1Btn.classList.toggle("is-active", showSample1);
  sample2Btn.classList.toggle("is-active", showSample2);
  customizeBtn.classList.toggle("is-active", showCustomize);
  sample1Btn.setAttribute("aria-pressed", String(showSample1));
  sample2Btn.setAttribute("aria-pressed", String(showSample2));
  customizeBtn.setAttribute("aria-pressed", String(showCustomize));

  const orderByMode = {
    [MODE.SAMPLE1]: [sample1Section, runControlsSection, resultsSection, exportSection, sample2Section, customizeSection],
    [MODE.SAMPLE2]: [sample2Section, runControlsSection, resultsSection, exportSection, sample1Section, customizeSection],
    [MODE.CUSTOMIZE]: [customizeSection, runControlsSection, resultsSection, exportSection, sample1Section, sample2Section],
  };
  const ordered = orderByMode[mode] || orderByMode[MODE.SAMPLE1];
  ordered.forEach((section, index) => {
    if (!section) return;
    section.style.order = String(index + 1);
  });
}

function syncRunInputs() {
  stepsInput.value = Math.min(state.steps, RUN_LIMITS.maxSteps);
  episodesInput.value = Math.min(state.episodes, RUN_LIMITS.maxEpisodes);
  seedInput.value = state.seed;
}

function setStatus(message) {
  statusEl.textContent = message;
}

async function loadPyodideAndCode() {
  try {
    setStatus("loading runtime...");
    const info = await runtime.init();
    pyodide = { version: info?.version || "unknown" };
    pyodideReady = true;
    setStatus("ready.");
  } catch (err) {
    pyodideReady = false;
    setStatus("runtime load failed.");
    showRuntimeError(normalizeError(
      err,
      ERROR_CODES.runtime.LOAD_FAILED,
      "Failed to load Pyodide runtime.",
      ["Check internet/CDN access.", "Refresh and retry."]
    ));
    console.error(err);
  }
  setRunButtonState(false);
}

async function runSimulation() {
  if (isRunning) return;
  if (!pyodideReady) {
    setStatus("runtime not ready.");
    return;
  }
  showValidationErrors([]);
  showRuntimeError(null);
  state.steps = Math.max(1, Math.min(RUN_LIMITS.maxSteps, Number(stepsInput.value) || 0));
  state.episodes = Math.max(1, Math.min(RUN_LIMITS.maxEpisodes, Number(episodesInput.value) || 0));
  state.seed = Number(seedInput.value) || 0;
  syncRunInputs();

  const configV2 = getConfigPayloadV2();
  const validationErrors = validateConfigPayload(configV2, STREAM_DEFS, RUN_LIMITS);
  if (validationErrors.length) {
    setStatus("validation failed.");
    showValidationErrors(validationErrors);
    clearResults();
    return;
  }

  const allScenarios = buildScenarioList();
  if (!allScenarios.length) {
    setStatus("No valid scenarios found. Check category options.");
    clearResults();
    return;
  }
  const scenarios = allScenarios.slice(0, RUN_LIMITS.maxScenarios);
  const truncated = allScenarios.length > scenarios.length;
  const warnings = [];
  const memoryWarning = detectMemoryPressure();
  if (memoryWarning) warnings.push(memoryWarning);
  const runStartedAt = new Date();
  const runStartMs = Date.now();
  activeRunStartMs = runStartMs;
  cancelRequested = false;
  const configHash = await hashText(JSON.stringify(configV2));
  const runId = `${runStartedAt.toISOString().replace(/[^\d]/g, "").slice(0, 14)}-${configHash.slice(-8)}`;

  try {
    isRunning = true;
    setRunButtonState(true);
    if (activeRunTimer) clearInterval(activeRunTimer);
    activeRunTimer = setInterval(() => {
      const elapsed = Date.now() - activeRunStartMs;
      if (isRunning) setStatus(`running... ${Math.floor(elapsed / 1000)}s elapsed`);
    }, 500);

    const results = [];
    setStatus("validating -> running...");
    for (let i = 0; i < scenarios.length; i += 1) {
      if (cancelRequested) {
        throw createError(
          ERROR_CODES.runtime.CANCELLED,
          "Run cancelled by user.",
          ["You can replay or adjust settings before running again."]
        );
      }
      const elapsed = Date.now() - runStartMs;
      if (elapsed > RUN_LIMITS.maxRunMs) {
        throw createError(ERROR_CODES.runtime.LIMIT_EXCEEDED, `Run exceeded ${RUN_LIMITS.maxRunMs}ms limit.`, [
          "Reduce steps/episodes/scenarios.",
          "Run fewer condition combinations.",
        ]);
      }
      const scenario = scenarios[i];
      setStatus(`running scenario ${i + 1}/${scenarios.length}...`);
      const overrideMap = {};
      Object.entries(scenario.overrides).forEach(([compound, value]) => {
        const [cid, key] = compound.split("::");
        if (!overrideMap[cid]) overrideMap[cid] = {};
        overrideMap[cid][key] = value;
      });
      const payload = buildPayloadWithOverrides(overrideMap);
      assertRunPayloadBridge(payload);
      const result = await runtime.run(payload);
      results.push({ label: scenario.label, result });
    }
    if (!results.length) {
      setStatus("No simulation output produced.");
      clearResults();
      return;
    }
    const durationMs = Date.now() - runStartMs;
    const runResultV2 = buildRunResultV2({
      runId,
      configHash,
      engineVersion: pyodide?.version || runtime.engineVersion || "pyodide-unknown",
      limitsApplied: {
        max_steps: RUN_LIMITS.maxSteps,
        max_episodes: RUN_LIMITS.maxEpisodes,
        max_scenarios: RUN_LIMITS.maxScenarios,
        max_run_ms: RUN_LIMITS.maxRunMs,
      },
      episodes: results[0].result.episodes || [],
      warnings: [
        ...(truncated ? [`Scenario count capped at ${RUN_LIMITS.maxScenarios}.`] : []),
        ...warnings,
      ],
      errors: durationMs > RUN_LIMITS.maxRunMs ? [createError(ERROR_CODES.runtime.LIMIT_EXCEEDED, "Runtime limit exceeded.")] : [],
    });
    lastRunArtifact = runResultV2;
    lastRunConfigPayload = configV2;
    updateRunFacts(runResultV2);
    if (bibtexOutput) {
      bibtexOutput.textContent = `@article{zhang2025heas,\n  title={HEAS: Hierarchical Evolutionary Agent Simulation Framework for Cross-Scale Modeling and Multi-Objective Search},\n  author={Zhang, Ruiyu and Nie, Lin and Zhao, Xin},\n  journal={arXiv preprint arXiv:2508.15555},\n  year={2025}\n}`;
    }
    markDirty(false);
    setStatus(truncated ? `done. showing first ${scenarios.length} of ${allScenarios.length} scenarios.` : "done.");
    renderRunPanels({
      result: results[0].result,
      scenarioResults: results,
      layers: state.layers,
      components: state.components,
      elements: {
        episodeSummary,
        stepPreview,
        stepChart,
        episodeChart,
        interpretationOutput,
        scenarioGrid,
        summaryTableHeadRow,
        summaryTableBody,
        summaryCopyBtn,
        summaryCsvBtn,
      },
    });
    if (replayBtn) replayBtn.disabled = false;
    activateResultsTab("overview");
  } catch (err) {
    const normalized = normalizeError(
      err,
      ERROR_CODES.runtime.FAILED,
      "Simulation failed.",
      ["Check stream parameters and scenario settings.", "Reduce run size if your browser is resource constrained."]
    );
    setStatus("run failed.");
    showRuntimeError(normalized);
    episodeSummary.textContent = normalized.message || String(err);
    stepPreview.textContent = "";
    clearChart();
    clearEpisodeChart();
    if (scenarioGrid) scenarioGrid.innerHTML = "";
    if (interpretationOutput) interpretationOutput.textContent = "";
  } finally {
    if (activeRunTimer) {
      clearInterval(activeRunTimer);
      activeRunTimer = null;
    }
    isRunning = false;
    cancelRequested = false;
    setRunButtonState(false);
    if (!runtime.ready) {
      await loadPyodideAndCode();
    }
  }
}

function renderResults(result) {
  const episodes = result.episodes || [];
  if (!episodes.length) {
    episodeSummary.textContent = "No episodes returned.";
    stepPreview.textContent = "";
    clearChart();
    clearEpisodeChart();
    if (scenarioGrid) scenarioGrid.innerHTML = "";
    if (interpretationOutput) interpretationOutput.textContent = "";
    return;
  }

  const summaryText = episodes
    .map((ep, idx) => {
      const lines = [`Episode ${idx + 1} (seed=${ep.seed})`];
      Object.entries(ep.episode || {}).forEach(([k, v]) => {
        lines.push(`  ${k}: ${formatNumber(v)}`);
      });
      return lines.join("\n");
    })
    .join("\n\n");

  const previewRows = episodes[0].per_step || [];
  const focusKeys = pickPerStepKeys(previewRows);
  const previewText = previewRows
    .map((row, i) => {
      const entries = focusKeys.every((k) => k in row) ? focusKeys.map((k) => [k, row[k]]) : Object.entries(row);
      const parts = entries.map(([k, v]) => `${k}=${formatNumber(v)}`);
      return `${i + 1}. ${parts.join(" | ")}`;
    })
    .join("\n");

  episodeSummary.textContent = summaryText;
  stepPreview.textContent = previewText || "No per-step data.";
  renderChart(episodes[0].per_step || [], focusKeys);
  renderEpisodeChart(episodes);
  if (interpretationOutput) {
    interpretationOutput.textContent = buildInterpretation(episodes);
  }
}

function renderScenarioText(results) {
  if (!stepPreview) return;
  if (!results || results.length <= 1) return;
  const blocks = results.map((entry, idx) => {
    const rows = entry.result?.episodes?.[0]?.per_step || [];
    const label = entry.label || `Scenario ${idx + 1}`;
    const focusKeys = pickPerStepKeys(rows);
    const lines = rows.slice(0, 6).map((row, i) => {
      const entries = focusKeys.every((k) => k in row) ? focusKeys.map((k) => [k, row[k]]) : Object.entries(row);
      const parts = entries.slice(0, 6).map(([k, v]) => `${k}=${formatNumber(v)}`);
      return `${i + 1}. ${parts.join(" | ")}`;
    });
    return `${label}\n${lines.join("\n")}`;
  });
  stepPreview.textContent = blocks.join("\n\n");
}

function formatNumber(value) {
  if (typeof value === "number") {
    return value.toFixed(4);
  }
  return String(value);
}

function clearChart() {
  const ctx = stepChart.getContext("2d");
  ctx.clearRect(0, 0, stepChart.width, stepChart.height);
}

function clearEpisodeChart() {
  const ctx = episodeChart.getContext("2d");
  ctx.clearRect(0, 0, episodeChart.width, episodeChart.height);
}

function renderChart(rows, focusKeys = [], canvas = stepChart) {
  if (!rows.length) {
    const ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    return;
  }
  let keys = Object.keys(rows[0] || {}).filter((k) => k !== "t");
  if (focusKeys.length && focusKeys.every((k) => keys.includes(k))) {
    keys = focusKeys;
  }
  if (!keys.length) {
    clearChart();
    return;
  }
  const rightAxisKeys = keys.filter((k) => k.includes("extinct"));
  const leftAxisKeys = keys.filter((k) => !rightAxisKeys.includes(k));
  const seriesKeys = [...leftAxisKeys, ...rightAxisKeys];
  const series = seriesKeys.map((key) => rows.map((r) => Number(r[key])));

  const padding = { left: 48, right: 52, top: 16, bottom: 28 };
  const width = canvas.width;
  const height = canvas.height;
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const leftVals = leftAxisKeys.length
    ? leftAxisKeys.flatMap((k) => rows.map((r) => Number(r[k]))).filter((v) => Number.isFinite(v))
    : [];
  const rightVals = rightAxisKeys.length
    ? rightAxisKeys.flatMap((k) => rows.map((r) => Number(r[k]))).filter((v) => Number.isFinite(v))
    : [];
  const minLeft = leftVals.length ? Math.min(...leftVals) : 0;
  const maxLeft = leftVals.length ? Math.max(...leftVals) : 1;
  const rangeLeft = maxLeft - minLeft || 1;
  const minRight = rightVals.length ? Math.min(...rightVals) : 0;
  const maxRight = rightVals.length ? Math.max(...rightVals) : 1;
  const rangeRight = maxRight - minRight || 1;

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fffaf4";
  ctx.fillRect(0, 0, width, height);

  // axes
  ctx.strokeStyle = "#d8c7b6";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, height - padding.bottom);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.moveTo(width - padding.right, padding.top);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.stroke();

  // left y labels
  ctx.fillStyle = "#6a5b4b";
  ctx.font = "12px \"Space Grotesk\", sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i += 1) {
    const t = i / yTicks;
    const y = padding.top + plotH - t * plotH;
    const v = minLeft + t * rangeLeft;
    ctx.fillText(v.toFixed(2), padding.left - 6, y);
    ctx.strokeStyle = "rgba(216,199,182,0.4)";
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  // right y labels (extinction)
  if (rightAxisKeys.length) {
    ctx.fillStyle = "#6a5b4b";
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    for (let i = 0; i <= yTicks; i += 1) {
      const t = i / yTicks;
      const y = padding.top + plotH - t * plotH;
      const v = minRight + t * rangeRight;
      ctx.fillText(v.toFixed(2), width - padding.right + 6, y);
    }
  }

  const colors = ["#e85d25", "#2c7a7b", "#7a4b8f", "#1f6feb", "#0f8b8d", "#f59e0b", "#9333ea"];
  seriesKeys.forEach((key, idx) => {
    const vals = series[idx];
    const onRight = rightAxisKeys.includes(key);
    ctx.strokeStyle = onRight ? "#1f6feb" : colors[idx % colors.length];
    ctx.lineWidth = 2;
    ctx.setLineDash(onRight ? [6, 4] : []);
    ctx.beginPath();
    vals.forEach((v, i) => {
      const x = padding.left + (i / Math.max(vals.length - 1, 1)) * plotW;
      const base = onRight ? minRight : minLeft;
      const range = onRight ? rangeRight : rangeLeft;
      const y = padding.top + plotH - ((v - base) / range) * plotH;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();
    ctx.setLineDash([]);
  });

  // legend
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  seriesKeys.forEach((key, idx) => {
    const x = padding.left + idx * 160;
    const y = height - padding.bottom + 8;
    const onRight = rightAxisKeys.includes(key);
    ctx.fillStyle = onRight ? "#1f6feb" : colors[idx % colors.length];
    ctx.fillRect(x, y + 3, 10, 10);
    ctx.fillStyle = "#1a1a1a";
    ctx.fillText(key, x + 16, y);
  });
}

function renderScenarioGrid(results) {
  if (!scenarioGrid) return;
  scenarioGrid.innerHTML = "";
  if (results.length <= 1) return;
  results.forEach((entry, idx) => {
    const card = document.createElement("div");
    card.className = "scenario-card";
    const title = document.createElement("div");
    title.className = "scenario-title";
    title.textContent = entry.label || `Scenario ${idx + 1}`;
    const canvas = document.createElement("canvas");
    canvas.width = 320;
    canvas.height = 200;
    card.appendChild(title);
    card.appendChild(canvas);
    scenarioGrid.appendChild(card);
    const rows = entry.result?.episodes?.[0]?.per_step || [];
    const focusKeys = pickPerStepKeys(rows);
    renderChart(rows, focusKeys, canvas);
  });
}

function pickPerStepKeys(rows) {
  if (!rows || !rows.length) return [];
  const rowKeys = Object.keys(rows[0]).filter((k) => k !== "t");
  const lastLayerIds = state.layers[state.layers.length - 1] || [];
  const finalLayerComponents = lastLayerIds.map((id) => state.components[id]).filter(Boolean);
  const agentComponents = Object.values(state.components).filter((component) => component?.agent?.enabled);
  const focus = [];
  finalLayerComponents.forEach((component) => {
    const prefix = `${component.streamName}.`;
    rowKeys.forEach((k) => {
      if (k.startsWith(prefix)) focus.push(k);
    });
  });
  agentComponents.forEach((component) => {
    const prefix = `${component.streamName}.`;
    rowKeys.forEach((k) => {
      if (k.startsWith(prefix)) focus.push(k);
    });
  });
  const unique = Array.from(new Set(focus));
  if (unique.length) return unique;
  const focusKeysPreferred = ["L3S1.welfare", "L3S1.compliance", "L3S1.stability"];
  if (focusKeysPreferred.every((k) => k in rows[0])) return focusKeysPreferred;
  return rowKeys.slice(0, 3);
}

function renderEpisodeChart(episodes) {
  if (!episodes.length) {
    clearEpisodeChart();
    return;
  }
  const metricsList = episodes.map((ep) => ep.episode || {});
  const keys = Object.keys(metricsList[0] || {});
  if (!keys.length) {
    clearEpisodeChart();
    return;
  }
  const statsByKey = keys.map((key) => {
    const vals = metricsList.map((m) => Number(m[key])).filter((v) => Number.isFinite(v));
    if (!vals.length) {
      return { key, variation: 0 };
    }
    const minV = Math.min(...vals);
    const maxV = Math.max(...vals);
    return { key, variation: maxV - minV };
  });
  const width = episodeChart.width;
  const height = episodeChart.height;
  const ctx = episodeChart.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fffaf4";
  ctx.fillRect(0, 0, width, height);

  const padding = { left: 48, right: 16, top: 25, bottom: 90 };

  // title
  ctx.fillStyle = "#1a1a1a";
  ctx.font = "13px \"Space Grotesk\", sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText("Cross-Episode Variation (Smaller Bars = More Consistent)", padding.left, 0);
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const variations = statsByKey.map((s) => s.variation);
  const maxV = Math.max(...variations, 1e-6);
  const range = maxV || 1;

  // axes
  ctx.strokeStyle = "#d8c7b6";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, height - padding.bottom);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.stroke();

  // y labels
  ctx.fillStyle = "#6a5b4b";
  ctx.font = "12px \"Space Grotesk\", sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  const yTicks = 4;
  for (let i = 0; i <= yTicks; i += 1) {
    const t = i / yTicks;
    const y = padding.top + plotH - t * plotH;
    const v = t * range;
    ctx.fillText(v.toFixed(2), padding.left - 6, y);
    ctx.strokeStyle = "rgba(216,199,182,0.4)";
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  const barGap = 12;
  const barW = Math.max(18, (plotW - barGap * (keys.length - 1)) / keys.length);
  statsByKey.forEach((s, i) => {
    const x = padding.left + i * (barW + barGap);
    const h = (s.variation / range) * plotH;
    const y = padding.top + (plotH - h);
    ctx.fillStyle = "rgba(44,122,123,0.5)";
    ctx.fillRect(x, y, barW, h);
    ctx.strokeStyle = "#2c7a7b";
    ctx.strokeRect(x, y, barW, h);
  });

  // labels
  ctx.fillStyle = "#6a5b4b";
  ctx.font = "11px \"Space Grotesk\", sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  statsByKey.forEach((s, i) => {
    const x = padding.left + i * (barW + barGap) + barW / 2;
    const y = height - padding.bottom + 10;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(-Math.PI / 4);
    ctx.fillText(s.key, 0, 0);
    ctx.restore();
  });
}

function buildInterpretation(episodes) {
  const ep0 = episodes[0] || {};
  const perStep = ep0.per_step || [];
  const last = ep0.episode || {};
  const lines = [];

  lines.push("Overview:");
  lines.push(`- Episodes: ${episodes.length}`);
  const focusKeys = pickPerStepKeys(perStep);
  const finalKeys = focusKeys
    .map((k) => {
      const parts = k.split(".");
      if (parts.length < 2) return null;
      return `${parts[0]}.final_${parts.slice(1).join(".")}`;
    })
    .filter(Boolean);
  const availableFinal = finalKeys.filter((k) => k in last);
  if (availableFinal.length) {
    const finalParts = availableFinal.map((k) => {
      const label = k.replace(".final_", ".");
      return `${label}=${formatNumber(last[k])}`;
    });
    lines.push(`- Final state (Episode 1): ${finalParts.join(", ")}`);
  }

  if (perStep.length) {
    const first = perStep[0];
    const lastStep = perStep[perStep.length - 1];
    if (focusKeys.length && focusKeys.every((k) => k in first) && focusKeys.every((k) => k in lastStep)) {
      lines.push("Trends:");
      focusKeys.slice(0, 4).forEach((key) => {
        const start = Number(first[key]);
        const end = Number(lastStep[key]);
        lines.push(`- ${key} ${trendWord(start, end)} from ${formatNumber(start)} to ${formatNumber(end)}.`);
      });
    }
  }

  if (episodes.length > 1) {
    const consistentKeys = availableFinal.length ? availableFinal : Object.keys(last).slice(0, 3);
    const ranges = consistentKeys
      .map((k) => {
        const vals = episodes.map((ep) => Number(ep.episode?.[k])).filter((v) => Number.isFinite(v));
        if (!vals.length) return null;
        return { key: k.replace(".final_", "."), min: Math.min(...vals), max: Math.max(...vals) };
      })
      .filter(Boolean);
    if (ranges.length) {
      lines.push("Consistency:");
      ranges.forEach((entry) => {
        lines.push(`- ${entry.key} range: ${formatNumber(entry.min)} to ${formatNumber(entry.max)}.`);
      });
    }
  }

  return lines.join("\n");
}

function trendWord(start, end) {
  if (!Number.isFinite(start) || !Number.isFinite(end)) return "changes";
  if (Math.abs(end - start) < 1e-6) return "stays stable";
  return end > start ? "increases" : "decreases";
}

async function exportCurrentBundle() {
  const config = getConfigPayloadV2();
  const checksums = {
    config_hash: await hashText(JSON.stringify(config)),
    result_hash: lastRunArtifact ? await hashText(JSON.stringify(lastRunArtifact)) : null,
  };
  const bundle = buildExportBundleV2({
    config,
    result: lastRunArtifact,
    report: buildDebugReport(),
    checksums,
  });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  downloadJson(`heas-publication-bundle-${stamp}.json`, bundle);
  setStatus("publication bundle exported.");
}

function inferMode(input) {
  if (input === MODE.SAMPLE1 || input === MODE.SAMPLE2 || input === MODE.CUSTOMIZE) return input;
  return MODE.SAMPLE1;
}

async function importBundleFromFile(file) {
  if (!file) return;
  if (file.size > RUN_LIMITS.maxImportBytes) {
    showRuntimeError(createError(ERROR_CODES.io.IMPORT_LIMIT, `Import file exceeds ${RUN_LIMITS.maxImportBytes} bytes.`, [
      "Use a smaller bundle.",
      "Export config-only files for very large runs.",
    ]));
    return;
  }
  const text = await file.text();
  const parsed = JSON.parse(text);
  if (!parsed || typeof parsed !== "object") {
    throw new Error("Invalid bundle.");
  }
  const migrated = migrateIncomingBundle(parsed);
  applyConfigToState(migrated.config, inferMode(migrated.mode));
  showValidationErrors(validateConfigPayload(getConfigPayloadV2(), STREAM_DEFS, RUN_LIMITS));
  if (migrated.result && migrated.result.version === PLAYGROUND_RUN_RESULT_VERSION) {
    lastRunArtifact = migrated.result;
    lastRunConfigPayload = migrated.config;
    updateRunFacts(lastRunArtifact);
    if (replayBtn) replayBtn.disabled = false;
    setRunButtonState(false);
  }
  setStatus("bundle imported.");
}

function buildShareLink() {
  const payload = {
    config: getConfigPayloadV2(),
    view: activeMode,
  };
  const encoded = toBase64Url(JSON.stringify(payload));
  const url = new URL(window.location.href);
  url.searchParams.set("cfg", encoded);
  url.searchParams.set("view", activeMode);
  const link = url.toString();
  if (link.length > RUN_LIMITS.maxShareChars) {
    throw createError(ERROR_CODES.share.TOO_LARGE, `Share link exceeds ${RUN_LIMITS.maxShareChars} chars.`, [
      "Use Export Bundle for large configurations.",
    ]);
  }
  return link;
}

function loadConfigFromUrlIfPresent() {
  const url = new URL(window.location.href);
  const cfg = url.searchParams.get("cfg");
  const view = inferMode(url.searchParams.get("view"));
  if (!cfg) {
    showSection(view);
    return;
  }
  try {
    const decoded = JSON.parse(fromBase64Url(cfg));
    const migrated = migrateIncomingBundle(decoded);
    applyConfigToState(migrated.config, view);
    setStatus("loaded config from URL.");
    showValidationErrors(validateConfigPayload(getConfigPayloadV2(), STREAM_DEFS, RUN_LIMITS));
  } catch (err) {
    console.error(err);
    showRuntimeError(normalizeError(
      err,
      ERROR_CODES.share.URL_IMPORT_FAILED,
      "Failed to load config from URL.",
      ["Check if the share link is complete.", "Use bundle import as fallback."]
    ));
  }
}

resetBtn.addEventListener("click", initCustomizeEmpty);
addLayerBtn.addEventListener("click", addLayer);
addStreamBtn.addEventListener("click", addStream);

runBtn.addEventListener("click", runSimulation);
if (cancelBtn) {
  cancelBtn.addEventListener("click", () => {
    if (!isRunning) return;
    cancelRequested = true;
    runtime.terminate();
    setStatus("cancelling...");
  });
}
if (replayBtn) {
  replayBtn.addEventListener("click", async () => {
    if (!lastRunConfigPayload) return;
    applyConfigToState(lastRunConfigPayload, activeMode);
    await runSimulation();
  });
}
if (exportBtn) {
  exportBtn.addEventListener("click", async () => {
    await exportCurrentBundle();
  });
}
if (publicationExportBtn) {
  publicationExportBtn.addEventListener("click", async () => {
    await exportCurrentBundle();
  });
}
if (importInput) {
  importInput.addEventListener("change", async () => {
    const file = importInput.files?.[0];
    if (!file) return;
    try {
      await importBundleFromFile(file);
    } catch (err) {
      console.error(err);
      showRuntimeError(normalizeError(
        err,
        ERROR_CODES.io.IMPORT_ERROR,
        "Failed to import bundle.",
        ["Ensure the file is valid JSON.", "Export a fresh bundle and retry."]
      ));
    } finally {
      importInput.value = "";
    }
  });
}
if (shareBtn) {
  shareBtn.addEventListener("click", async () => {
    try {
      const link = buildShareLink();
      if (shareLinkOutput) {
        shareLinkOutput.textContent = `Share Link\n${link}`;
        shareLinkOutput.classList.remove("hidden");
      }
      try {
        await copyText(link);
        setStatus("share link copied.");
      } catch (_copyErr) {
        setStatus("share link generated (clipboard blocked).");
      }
    } catch (err) {
      console.error(err);
      const normalized = normalizeError(
        err,
        ERROR_CODES.share.BUILD_FAILED,
        "Failed to build share link.",
        ["Use Export Bundle if config is large."]
      );
      showRuntimeError(normalized);
    }
  });
}
if (copyDebugBtn) {
  copyDebugBtn.addEventListener("click", async () => {
    const report = buildDebugReport();
    await copyText(JSON.stringify(report, null, 2));
    setStatus("debug report copied.");
  });
}

streamTypeInput.addEventListener("change", () => {
  const nextType = streamTypeInput.value;
  if (streamTypeSearchInput) streamTypeSearchInput.value = nextType;
  const activeComponent = activeComponentId ? state.components[activeComponentId] : null;
  const params = mergeDefaultsForType(nextType, activeComponent?.params || getDefaultParamsForType(nextType));
  const meta = getDefaultMetaForType(nextType);
  renderParamFields(nextType, params, meta);
  const template = getTemplateByType(nextType);
  if (agentEnabled) agentEnabled.checked = Boolean(template.agent?.enabled);
  if (agentCapacity) agentCapacity.value = template.agent?.capacity ?? 1;
  updateEncodedPreviewFromForm();
});

modalForm.addEventListener("submit", (event) => {
  event.preventDefault();
  updateStreamFromModal();
  closeModal();
});

closeModalBtn.addEventListener("click", closeModal);
modal.addEventListener("click", (event) => {
  if (event.target === modal) closeModal();
});
modal.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeModal();
  }
  if (event.key !== "Tab") return;
  const focusable = modal.querySelectorAll("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
  const nodes = Array.from(focusable).filter((el) => !el.disabled && el.offsetParent !== null);
  if (!nodes.length) return;
  const first = nodes[0];
  const last = nodes[nodes.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
});

addParamBtn.addEventListener("click", () => {
  addCustomParamRow();
  updateEncodedPreviewFromForm();
});
addCatBtn.addEventListener("click", () => {
  addCustomParamRow("", "", "category", []);
  updateEncodedPreviewFromForm();
});
if (paramFields) {
  paramFields.addEventListener("input", () => updateEncodedPreviewFromForm());
  paramFields.addEventListener("change", () => updateEncodedPreviewFromForm());
}
if (agentEnabled) agentEnabled.addEventListener("change", () => updateEncodedPreviewFromForm());
if (agentCapacity) agentCapacity.addEventListener("input", () => updateEncodedPreviewFromForm());

deleteBtn.addEventListener("click", () => {
  if (!activeComponentId) return;
  removeComponent(activeComponentId);
  closeModal();
});

sample1Btn.addEventListener("click", () => {
  showSection(MODE.SAMPLE1);
  initSampleUsage1();
});

sample2Btn.addEventListener("click", () => {
  showSection(MODE.SAMPLE2);
  initSampleUsage2();
});

customizeBtn.addEventListener("click", () => {
  showSection(MODE.CUSTOMIZE);
  initCustomizeEmpty();
});

if (streamTypeSearchInput) {
  streamTypeSearchInput.addEventListener("input", () => {
    const needle = streamTypeSearchInput.value.trim().toLowerCase();
    if (!needle) return;
    const option = Array.from(streamTypeInput.options).find((opt) => opt.value.toLowerCase().includes(needle));
    if (option) {
      streamTypeInput.value = option.value;
      streamTypeInput.dispatchEvent(new Event("change"));
    }
  });
}

resultsTabBtns.forEach((btn) => {
  btn.addEventListener("click", () => activateResultsTab(btn.dataset.resultsTab));
});

if (resetPresetBtn) {
  resetPresetBtn.addEventListener("click", () => {
    if (activeMode === MODE.SAMPLE1) initSampleUsage1();
    else if (activeMode === MODE.SAMPLE2) initSampleUsage2();
    else initCustomizeEmpty();
    setStatus("preset reset.");
  });
}

setRunButtonState(false);
activateResultsTab("overview");
initSampleUsage1();
loadConfigFromUrlIfPresent();
loadPyodideAndCode();
