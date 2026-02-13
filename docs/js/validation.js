import { ERROR_CODES, createError } from "./errors.js";

function readControls(config) {
  if (!config || typeof config !== "object") return { steps: NaN, episodes: NaN, seed: NaN };
  if (config.controls && typeof config.controls === "object") {
    return {
      steps: Number(config.controls.steps),
      episodes: Number(config.controls.episodes),
      seed: Number(config.controls.seed),
    };
  }
  return {
    steps: Number(config.steps),
    episodes: Number(config.episodes),
    seed: Number(config.seed),
  };
}

export function validateConfigPayload(config, streamDefs, runLimits) {
  const errors = [];
  if (!config || typeof config !== "object") {
    errors.push(createError(
      ERROR_CODES.validation.CFG_INVALID,
      "Config is missing or invalid.",
      ["Import a valid bundle or reset defaults."],
      { path: "config" }
    ));
    return errors;
  }

  const { steps, episodes, seed } = readControls(config);
  if (!Number.isFinite(steps) || steps < 1) {
    errors.push(createError(ERROR_CODES.validation.STEPS_INVALID, "Steps must be a positive number.", ["Set steps >= 1."], { path: "controls.steps" }));
  }
  if (steps > runLimits.maxSteps) {
    errors.push(createError(ERROR_CODES.validation.STEPS_LIMIT, `Steps exceeds limit (${runLimits.maxSteps}).`, ["Lower steps or split runs."], { path: "controls.steps" }));
  }
  if (!Number.isFinite(episodes) || episodes < 1) {
    errors.push(createError(ERROR_CODES.validation.EPISODES_INVALID, "Episodes must be a positive number.", ["Set episodes >= 1."], { path: "controls.episodes" }));
  }
  if (episodes > runLimits.maxEpisodes) {
    errors.push(createError(ERROR_CODES.validation.EPISODES_LIMIT, `Episodes exceeds limit (${runLimits.maxEpisodes}).`, ["Lower episodes or run multiple batches."], { path: "controls.episodes" }));
  }
  if (!Number.isFinite(seed)) {
    errors.push(createError(ERROR_CODES.validation.CFG_INVALID, "Seed must be numeric.", ["Set a numeric seed value."], { path: "controls.seed" }));
  }

  if (!Array.isArray(config.layers) || !config.layers.length) {
    errors.push(createError(ERROR_CODES.validation.LAYERS_INVALID, "At least one layer is required.", ["Add a layer before running."], { path: "layers" }));
    return errors;
  }

  config.layers.forEach((layer, layerIndex) => {
    if (!Array.isArray(layer) || !layer.length) {
      errors.push(createError(ERROR_CODES.validation.LAYER_EMPTY, "Layer has no streams.", ["Add at least one stream per layer."], { path: `layers[${layerIndex}]` }));
      return;
    }
    layer.forEach((stream, streamIndex) => {
      if (!stream || typeof stream !== "object") {
        errors.push(createError(ERROR_CODES.validation.STREAM_INVALID, "Stream object is invalid.", ["Reset the stream configuration."], { path: `layers[${layerIndex}][${streamIndex}]` }));
        return;
      }
      if (!stream.type || typeof stream.type !== "string") {
        errors.push(createError(ERROR_CODES.validation.TYPE_MISSING, "Stream type is missing.", ["Select a stream type."], { path: `layers[${layerIndex}][${streamIndex}].type` }));
      }
      const defs = streamDefs[stream.type] || [];
      const params = stream.params || {};
      defs.forEach((def) => {
        if (!(def.key in params)) {
          errors.push(createError(
            ERROR_CODES.validation.PARAM_MISSING,
            `Required parameter '${def.key}' is missing.`,
            ["Open the stream editor and save defaults."],
            { path: `layers[${layerIndex}][${streamIndex}].params.${def.key}` }
          ));
        }
      });
    });
  });

  return errors;
}

export function validateRunResultShape(result) {
  if (!result || typeof result !== "object") return false;
  if (!Array.isArray(result.episodes)) return false;
  return result.episodes.every((ep) => ep && typeof ep === "object" && Array.isArray(ep.per_step) && ep.episode && typeof ep.episode === "object");
}
