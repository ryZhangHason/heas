export const MODE = {
  SAMPLE1: "sample1",
  SAMPLE2: "sample2",
  CUSTOMIZE: "customize",
};

export const APP_VERSION = "1.0.0";
export const PLAYGROUND_CONFIG_VERSION = "PlaygroundConfigV2";
export const PLAYGROUND_RUN_RESULT_VERSION = "PlaygroundRunResultV2";
export const EXPORT_BUNDLE_VERSION = "PlaygroundExportBundleV2";
export const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";

export const RUN_LIMITS = {
  maxSteps: 500,
  maxEpisodes: 20,
  maxScenarios: 64,
  maxRunMs: 45000,
  maxShareChars: 7000,
  maxImportBytes: 1_000_000,
};
