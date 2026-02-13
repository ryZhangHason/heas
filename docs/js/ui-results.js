import { copyText, downloadCsv } from "./io.js";

export function formatNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value.toFixed(4);
  }
  return String(value);
}

function clearCanvas(canvas) {
  const ctx = canvas?.getContext?.("2d");
  if (!ctx || !canvas) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
}

function drawAxisLabels(ctx, width, height, padding, xLabel, yLabel, opts = {}) {
  const xLabelBottom = Number.isFinite(opts.xLabelBottom) ? opts.xLabelBottom : 2;
  const yLabelX = Number.isFinite(opts.yLabelX) ? opts.yLabelX : 14;
  ctx.save();
  ctx.fillStyle = "#6a5b4b";
  ctx.font = '12px "Space Grotesk", sans-serif';

  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText(xLabel, padding.left + (width - padding.left - padding.right) / 2, height - xLabelBottom);

  ctx.translate(yLabelX, padding.top + (height - padding.top - padding.bottom) / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.fillText(yLabel, 0, 0);
  ctx.restore();
}

function formatTick(value, decimals = 2) {
  if (!Number.isFinite(value)) return "";
  const abs = Math.abs(value);
  if (abs >= 1000) return value.toFixed(0);
  if (abs >= 100) return value.toFixed(1);
  if (abs >= 1) return value.toFixed(decimals);
  if (abs === 0) return "0";
  return value.toExponential(1);
}

function drawNumericAxes(ctx, {
  width,
  height,
  padding,
  minX,
  maxX,
  minY,
  maxY,
  xTicks = 5,
  yTicks = 5,
  showXTickLabels = true,
  showYTickLabels = true,
  xFormatter = (v) => formatTick(v, 0),
  yFormatter = (v) => formatTick(v, 2),
}) {
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const xRange = maxX - minX || 1;
  const yRange = maxY - minY || 1;

  ctx.save();
  ctx.font = '11px "Space Grotesk", sans-serif';
  ctx.fillStyle = "#6a5b4b";

  // Y tick labels + grid
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i <= yTicks; i += 1) {
    const t = i / yTicks;
    const y = padding.top + plotH - t * plotH;
    const v = minY + t * yRange;
    if (showYTickLabels) ctx.fillText(yFormatter(v), padding.left - 8, y);
    ctx.strokeStyle = "rgba(216,199,182,0.35)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();
  }

  // X tick labels + grid
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= xTicks; i += 1) {
    const t = i / xTicks;
    const x = padding.left + t * plotW;
    const v = minX + t * xRange;
    if (showXTickLabels) ctx.fillText(xFormatter(v), x, height - padding.bottom + 10);
    ctx.strokeStyle = "rgba(216,199,182,0.22)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, padding.top);
    ctx.lineTo(x, height - padding.bottom);
    ctx.stroke();
  }

  ctx.restore();
}

function pickPerStepKeys(rows, layers, components) {
  if (!rows || !rows.length) return [];
  const rowKeys = Object.keys(rows[0]).filter((k) => k !== "t");
  const lastLayerIds = layers[layers.length - 1] || [];
  const finalLayerComponents = lastLayerIds.map((id) => components[id]).filter(Boolean);
  const focus = [];
  finalLayerComponents.forEach((component) => {
    const prefix = `${component.streamName}.`;
    rowKeys.forEach((k) => {
      if (k.startsWith(prefix)) focus.push(k);
    });
  });
  const unique = Array.from(new Set(focus));
  return unique.length ? unique : rowKeys.slice(0, 3);
}

function computeDomain(rows, keys) {
  const xVals = rows.map((row, i) => {
    const t = Number(row.t);
    return Number.isFinite(t) ? t : i + 1;
  });
  const yVals = keys
    .flatMap((k) => rows.map((r) => Number(r[k])))
    .filter((v) => Number.isFinite(v));

  const minX = xVals.length ? Math.min(...xVals) : 1;
  const maxX = xVals.length ? Math.max(...xVals) : 1;
  const minY = yVals.length ? Math.min(...yVals) : 0;
  const maxY = yVals.length ? Math.max(...yVals) : 1;
  return { minX, maxX, minY, maxY, xVals };
}

function mergeDomains(domains) {
  const valid = domains.filter(Boolean);
  if (!valid.length) return { minX: 1, maxX: 1, minY: 0, maxY: 1 };
  return {
    minX: Math.min(...valid.map((d) => d.minX)),
    maxX: Math.max(...valid.map((d) => d.maxX)),
    minY: Math.min(...valid.map((d) => d.minY)),
    maxY: Math.max(...valid.map((d) => d.maxY)),
  };
}

function renderChart(rows, canvas, focusKeys = [], opts = {}) {
  if (!rows?.length || !canvas) {
    clearCanvas(canvas);
    return;
  }
  let keys = Object.keys(rows[0] || {}).filter((k) => k !== "t");
  if (focusKeys.length && focusKeys.every((k) => keys.includes(k))) {
    keys = focusKeys;
  }
  if (!keys.length) {
    clearCanvas(canvas);
    return;
  }

  const padding = opts.padding || { left: 62, right: 20, top: 20, bottom: 52 };
  const width = canvas.width;
  const height = canvas.height;
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const domain = opts.domain || computeDomain(rows, keys);
  const { minX, maxX, minY, maxY, xVals = [] } = domain;
  const range = maxY - minY || 1;
  const xRange = maxX - minX || 1;

  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fffaf4";
  ctx.fillRect(0, 0, width, height);

  ctx.strokeStyle = "#d8c7b6";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, height - padding.bottom);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.stroke();
  drawNumericAxes(ctx, {
    width,
    height,
    padding,
    minX,
    maxX,
    minY,
    maxY,
    xTicks: opts.xTicks ?? 5,
    yTicks: opts.yTicks ?? 5,
    showXTickLabels: opts.showXTickLabels ?? true,
    showYTickLabels: opts.showYTickLabels ?? true,
    xFormatter: opts.xFormatter || ((v) => formatTick(v, 0)),
    yFormatter: opts.yFormatter || ((v) => formatTick(v, 2)),
  });
  drawAxisLabels(ctx, width, height, padding, "Step (t)", "Value", {
    xLabelBottom: 4,
    yLabelX: 12,
  });

  const colors = ["#e85d25", "#2c7a7b", "#1f6feb", "#f59e0b", "#9333ea"];
  keys.forEach((key, idx) => {
    ctx.strokeStyle = colors[idx % colors.length];
    ctx.lineWidth = 2;
    ctx.beginPath();
    let started = false;
    rows.forEach((row, i) => {
      const rawX = Number(row.t);
      const xv = Number.isFinite(rawX) ? rawX : i + 1;
      const yv = Number(row[key]);
      if (!Number.isFinite(yv)) return;
      const x = padding.left + ((xv - minX) / xRange) * plotW;
      const y = padding.top + plotH - ((yv - minY) / range) * plotH;
      if (!started) {
        ctx.moveTo(x, y);
        started = true;
      } else {
        ctx.lineTo(x, y);
      }
    });
    ctx.stroke();
  });
}

function renderEpisodeVariation(episodes, canvas) {
  if (!episodes?.length || !canvas) {
    clearCanvas(canvas);
    return;
  }
  const metricsList = episodes.map((ep) => ep.episode || {});
  const keys = Object.keys(metricsList[0] || {});
  if (!keys.length) {
    clearCanvas(canvas);
    return;
  }

  const statsByKey = keys.map((key) => {
    const vals = metricsList.map((m) => Number(m[key])).filter((v) => Number.isFinite(v));
    const minV = vals.length ? Math.min(...vals) : 0;
    const maxV = vals.length ? Math.max(...vals) : 0;
    return { key, variation: maxV - minV };
  });

  const width = canvas.width;
  const height = canvas.height;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#fffaf4";
  ctx.fillRect(0, 0, width, height);

  const padding = { left: 72, right: 18, top: 25, bottom: 104 };
  const plotW = width - padding.left - padding.right;
  const plotH = height - padding.top - padding.bottom;
  const maxV = Math.max(...statsByKey.map((s) => s.variation), 1e-6);

  ctx.strokeStyle = "#d8c7b6";
  ctx.beginPath();
  ctx.moveTo(padding.left, padding.top);
  ctx.lineTo(padding.left, height - padding.bottom);
  ctx.lineTo(width - padding.right, height - padding.bottom);
  ctx.stroke();
  drawNumericAxes(ctx, {
    width,
    height,
    padding,
    minX: 1,
    maxX: Math.max(1, statsByKey.length),
    minY: 0,
    maxY: maxV,
    xTicks: 4,
    yTicks: 5,
    xFormatter: (v) => formatTick(v, 0),
    yFormatter: (v) => formatTick(v, 2),
  });
  drawAxisLabels(ctx, width, height, padding, "Metric", "Variation", {
    xLabelBottom: 6,
    yLabelX: 12,
  });

  const barGap = 12;
  const barW = Math.max(18, (plotW - barGap * (keys.length - 1)) / keys.length);
  statsByKey.forEach((s, i) => {
    const x = padding.left + i * (barW + barGap);
    const h = (s.variation / maxV) * plotH;
    const y = padding.top + (plotH - h);
    ctx.fillStyle = "rgba(44,122,123,0.5)";
    ctx.fillRect(x, y, barW, h);
    ctx.strokeStyle = "#2c7a7b";
    ctx.strokeRect(x, y, barW, h);
  });
}

function buildInterpretation(episodes) {
  if (!episodes?.length) return "No episodes available.";
  const ep0 = episodes[0] || {};
  const perStep = ep0.per_step || [];
  const last = ep0.episode || {};
  const lines = [];
  lines.push("Overview:");
  lines.push(`- Episodes: ${episodes.length}`);
  Object.entries(last).slice(0, 8).forEach(([k, v]) => {
    lines.push(`- ${k}: ${formatNumber(v)}`);
  });
  if (perStep.length > 1) {
    lines.push("Trends:");
    const keys = Object.keys(perStep[0]).filter((k) => k !== "t").slice(0, 4);
    keys.forEach((key) => {
      const start = Number(perStep[0][key]);
      const end = Number(perStep[perStep.length - 1][key]);
      const word = Math.abs(end - start) < 1e-6 ? "stable" : (end > start ? "increasing" : "decreasing");
      lines.push(`- ${key}: ${word} (${formatNumber(start)} -> ${formatNumber(end)})`);
    });
  }
  return lines.join("\n");
}

function episodesToRows(episodes = []) {
  return episodes.map((ep, idx) => {
    const row = { episode_index: idx + 1, seed: ep.seed };
    Object.entries(ep.episode || {}).forEach(([k, v]) => {
      row[k] = v;
    });
    return row;
  });
}

function prettifyHeader(key) {
  if (key === "episode_index") return "Episode";
  if (key === "seed") return "Seed";
  return key.replaceAll("_", " ");
}

function renderSummaryTable(episodes, tableHeadRow, tableBody, copyBtn, downloadBtn) {
  if (!tableBody || !tableHeadRow) return;
  tableHeadRow.innerHTML = "";
  tableBody.innerHTML = "";
  const rows = episodesToRows(episodes);
  const headers = rows.length ? Object.keys(rows[0]) : ["episode_index", "seed"];

  headers.forEach((header) => {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = prettifyHeader(header);
    if (header !== "episode_index" && header !== "seed") {
      th.classList.add("is-metric");
      th.title = header;
    }
    tableHeadRow.appendChild(th);
  });

  if (!rows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = headers.length;
    td.textContent = "No episodes available.";
    td.className = "table-empty";
    tr.appendChild(td);
    tableBody.appendChild(tr);
  }

  rows.forEach((row) => {
    const tr = document.createElement("tr");
    headers.forEach((header) => {
      const value = row[header];
      const td = document.createElement("td");
      td.textContent = typeof value === "number" ? formatNumber(value) : String(value);
      if (header !== "episode_index" && header !== "seed") {
        td.classList.add("is-metric");
      }
      tr.appendChild(td);
    });
    tableBody.appendChild(tr);
  });

  if (copyBtn) {
    copyBtn.onclick = async () => {
      const lines = [headers.join(",")];
      rows.forEach((row) => lines.push(headers.map((h) => JSON.stringify(row[h] ?? "")).join(",")));
      await copyText(lines.join("\n"));
    };
  }
  if (downloadBtn) {
    downloadBtn.onclick = () => {
      downloadCsv("heas-episode-summary.csv", rows);
    };
  }
}

export function renderRunPanels({ result, scenarioResults = [], layers, components, elements }) {
  const episodes = result?.episodes || [];
  const {
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
  } = elements;

  if (!episodes.length) {
    if (episodeSummary) episodeSummary.textContent = "No episodes returned.";
    if (stepPreview) stepPreview.textContent = "";
    if (interpretationOutput) interpretationOutput.textContent = "";
    if (scenarioGrid) scenarioGrid.innerHTML = "";
    clearCanvas(stepChart);
    clearCanvas(episodeChart);
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
  const focusKeys = pickPerStepKeys(previewRows, layers, components);
  const previewText = previewRows
    .map((row, i) => {
      const parts = focusKeys.map((k) => `${k}=${formatNumber(row[k])}`);
      return `${i + 1}. ${parts.join(" | ")}`;
    })
    .join("\n");

  if (episodeSummary) episodeSummary.textContent = summaryText;
  if (stepPreview) stepPreview.textContent = previewText || "No per-step data.";
  if (interpretationOutput) interpretationOutput.textContent = buildInterpretation(episodes);

  renderChart(previewRows, stepChart, focusKeys, {
    padding: { left: 86, right: 24, top: 20, bottom: 78 },
    xTicks: 6,
    yTicks: 5,
  });
  renderEpisodeVariation(episodes, episodeChart);
  renderSummaryTable(episodes, summaryTableHeadRow, summaryTableBody, summaryCopyBtn, summaryCsvBtn);

  if (scenarioGrid) {
    scenarioGrid.innerHTML = "";
    const scenarioDomains = scenarioResults.map((entry) => {
      const rows = entry.result?.episodes?.[0]?.per_step || [];
      return rows.length ? computeDomain(rows, focusKeys) : null;
    });
    const sharedScenarioDomain = mergeDomains(scenarioDomains);
    scenarioResults.forEach((entry, idx) => {
      const card = document.createElement("div");
      card.className = "scenario-card";
      const title = document.createElement("div");
      title.className = "scenario-title";
      title.textContent = entry.label || `Scenario ${idx + 1}`;
      const canvas = document.createElement("canvas");
      canvas.width = 280;
      canvas.height = 190;
      card.appendChild(title);
      card.appendChild(canvas);
      scenarioGrid.appendChild(card);
      const rows = entry.result?.episodes?.[0]?.per_step || [];
      renderChart(rows, canvas, focusKeys, {
        domain: sharedScenarioDomain,
        padding: { left: 74, right: 16, top: 14, bottom: 70 },
        xTicks: 4,
        yTicks: 4,
      });
    });
  }
}
