import { ERROR_CODES, createError, normalizeError } from "./errors.js";
import { validateRunResultShape } from "./validation.js";

export class PlaygroundRuntime {
  constructor({ indexURL }) {
    this.indexURL = indexURL;
    this.worker = null;
    this.requestSeq = 0;
    this.pending = new Map();
    this.ready = false;
    this.engineVersion = "unknown";
  }

  ensureWorker() {
    if (this.worker) return;
    this.worker = new Worker("./js/runtime.worker.js");
    this.worker.onmessage = (event) => {
      const { type, requestId, payload } = event.data || {};
      const p = this.pending.get(requestId);
      if (!p) return;
      this.pending.delete(requestId);
      if (type === "error") {
        p.reject(createError(ERROR_CODES.runtime.FAILED, payload?.message || "Runtime worker failed."));
        return;
      }
      p.resolve({ type, payload });
    };
    this.worker.onerror = (event) => {
      const err = createError(ERROR_CODES.runtime.FAILED, "Runtime worker crashed.", ["Reload the page and retry."], { message: event.message });
      this.pending.forEach((entry) => entry.reject(err));
      this.pending.clear();
      this.worker = null;
      this.ready = false;
    };
  }

  request(type, payload) {
    this.ensureWorker();
    const requestId = `r${++this.requestSeq}`;
    const promise = new Promise((resolve, reject) => {
      this.pending.set(requestId, { resolve, reject });
    });
    this.worker.postMessage({ type, requestId, payload });
    return promise;
  }

  async init() {
    try {
      const response = await this.request("init", { indexURL: this.indexURL });
      if (response.type !== "init_ok") {
        throw createError(ERROR_CODES.runtime.LOAD_FAILED, "Runtime failed to initialize.");
      }
      this.ready = true;
      this.engineVersion = response.payload?.version || "unknown";
      return response.payload;
    } catch (err) {
      this.ready = false;
      throw normalizeError(
        err,
        ERROR_CODES.runtime.LOAD_FAILED,
        "Failed to load Pyodide runtime.",
        ["Check network/CDN access.", "Refresh and retry."]
      );
    }
  }

  async run(payload) {
    try {
      const response = await this.request("run", payload);
      if (response.type !== "run_ok") {
        throw createError(ERROR_CODES.runtime.FAILED, "Runtime returned an unexpected message type.");
      }
      if (!validateRunResultShape(response.payload)) {
        throw createError(
          ERROR_CODES.runtime.BAD_RESULT_SHAPE,
          "Runtime returned an invalid result shape.",
          ["Check simulation payload and stream configuration."]
        );
      }
      return response.payload;
    } catch (err) {
      throw normalizeError(
        err,
        ERROR_CODES.runtime.FAILED,
        "Simulation failed.",
        ["Check stream parameters and scenario settings."]
      );
    }
  }

  cancel() {
    this.terminate();
    throw createError(ERROR_CODES.runtime.CANCELLED, "Run cancelled by user.", ["You can replay or adjust settings before running again."]);
  }

  terminate() {
    if (this.worker) {
      this.worker.terminate();
    }
    this.worker = null;
    this.pending.forEach((entry) => entry.reject(createError(ERROR_CODES.runtime.CANCELLED, "Run cancelled by user.")));
    this.pending.clear();
    this.ready = false;
  }
}
