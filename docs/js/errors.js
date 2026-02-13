export const ERROR_CODES = {
  validation: {
    CFG_INVALID: "validation.cfg_invalid",
    STEPS_INVALID: "validation.steps_invalid",
    STEPS_LIMIT: "validation.steps_limit",
    EPISODES_INVALID: "validation.episodes_invalid",
    EPISODES_LIMIT: "validation.episodes_limit",
    LAYERS_INVALID: "validation.layers_invalid",
    LAYER_EMPTY: "validation.layer_empty",
    STREAM_INVALID: "validation.stream_invalid",
    TYPE_MISSING: "validation.type_missing",
    PARAM_MISSING: "validation.param_missing",
  },
  runtime: {
    LOAD_FAILED: "runtime.load_failed",
    CANCELLED: "runtime.cancelled",
    LIMIT_EXCEEDED: "runtime.limit_exceeded",
    FAILED: "runtime.failed",
    BAD_RESULT_SHAPE: "runtime.bad_result_shape",
  },
  io: {
    IMPORT_LIMIT: "io.import_limit",
    IMPORT_ERROR: "io.import_error",
    EXPORT_ERROR: "io.export_error",
  },
  share: {
    TOO_LARGE: "share.too_large",
    BUILD_FAILED: "share.build_failed",
    URL_IMPORT_FAILED: "share.url_import_failed",
  },
  compat: {
    UNKNOWN_CONFIG_VERSION: "compat.unknown_config_version",
    UNKNOWN_BUNDLE_VERSION: "compat.unknown_bundle_version",
    MIGRATION_FAILED: "compat.migration_failed",
  },
};

export function createError(code, message, hints = [], details = {}) {
  return {
    code,
    message,
    hints: Array.isArray(hints) ? hints : [],
    details: details && typeof details === "object" ? details : {},
  };
}

export function normalizeError(err, fallbackCode, fallbackMessage, fallbackHints = []) {
  if (err && typeof err === "object" && typeof err.code === "string" && typeof err.message === "string") {
    return createError(err.code, err.message, err.hints || [], err.details || {});
  }
  const raw = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
  return createError(fallbackCode, fallbackMessage, fallbackHints, { raw });
}

export function formatErrorForPanel(errorObj) {
  if (!errorObj) return "";
  const hints = Array.isArray(errorObj.hints) ? errorObj.hints : [];
  const lines = [
    `Error (${errorObj.code || "unknown"})`,
    errorObj.message || "Unknown error.",
  ];
  if (hints.length) {
    lines.push("Hints:");
    hints.forEach((hint) => lines.push(`- ${hint}`));
  }
  return lines.join("\n");
}
