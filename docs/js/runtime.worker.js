let pyodide = null;
let ready = false;
let initError = null;

async function initRuntime(indexURL) {
  if (ready && pyodide) {
    return { ready: true, version: pyodide.version || "unknown" };
  }
  if (initError) {
    throw new Error(initError);
  }
  try {
    importScripts(`${indexURL}pyodide.js`);
    pyodide = await self.loadPyodide({ indexURL });
    const pyUrl = new URL("../py/playground.py", self.location.href);
    pyUrl.searchParams.set("v", String(Date.now()));
    const response = await fetch(pyUrl.toString());
    if (!response.ok) {
      throw new Error(`failed-to-fetch-playground-py:${response.status}`);
    }
    const code = await response.text();
    const trimmed = code.trimStart();
    if (trimmed.startsWith("<!DOCTYPE") || trimmed.startsWith("<html")) {
      throw new Error("invalid-python-source-received-html");
    }
    await pyodide.runPythonAsync(code);
    ready = true;
    return { ready: true, version: pyodide.version || "unknown" };
  } catch (err) {
    initError = String(err);
    throw err;
  }
}

async function runSimulation(payload) {
  if (!ready || !pyodide) {
    throw new Error("runtime-not-ready");
  }
  pyodide.globals.set("cfg", payload);
  await pyodide.runPythonAsync("import json; result = run_sim(cfg); result_json = json.dumps(result)");
  const resultJson = pyodide.globals.get("result_json");
  const parsed = JSON.parse(resultJson);
  if (resultJson?.destroy) resultJson.destroy();
  return parsed;
}

self.onmessage = async (event) => {
  const { type, requestId, payload } = event.data || {};
  try {
    if (type === "init") {
      const info = await initRuntime(payload?.indexURL);
      self.postMessage({ type: "init_ok", requestId, payload: info });
      return;
    }
    if (type === "run") {
      const result = await runSimulation(payload);
      self.postMessage({ type: "run_ok", requestId, payload: result });
      return;
    }
    self.postMessage({ type: "error", requestId, payload: { message: `Unknown worker message type: ${String(type)}` } });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    self.postMessage({ type: "error", requestId, payload: { message } });
  }
};
