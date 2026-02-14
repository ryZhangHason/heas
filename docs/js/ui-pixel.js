const PREFERRED_KEYS_BY_TYPE = {
  Climate: ["value"],
  Landscape: ["quality"],
  PreyRisk: ["prey"],
  PredatorResponse: ["pred"],
  Movement: ["dispersal"],
  Aggregator: ["extinct", "prey", "pred"],
  FirmGroup: ["mean_balance"],
  MarketSignal: ["demand_t", "price_signal"],
  GovernmentPolicy: ["tax"],
  IndustryRegime: ["audit_prob"],
  PayoffAccounting: ["delta"],
  AllianceRule: ["alliance_rule"],
  GroupGamingRule: ["group_mode"],
};

function clamp01(value) {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function asFiniteNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function prefixedKey(component, shortKey) {
  return `${component.streamName}.${shortKey}`;
}

export function pickMetricKey(component, row0 = {}) {
  if (!component || !component.streamName || !row0 || typeof row0 !== "object") return null;
  const preferred = PREFERRED_KEYS_BY_TYPE[component.type] || [];
  for (const shortKey of preferred) {
    const full = prefixedKey(component, shortKey);
    if (Object.prototype.hasOwnProperty.call(row0, full) && asFiniteNumber(row0[full]) !== null) {
      return full;
    }
  }

  const prefix = `${component.streamName}.`;
  const keys = Object.keys(row0).filter((key) => key.startsWith(prefix));
  for (const key of keys) {
    if (asFiniteNumber(row0[key]) !== null) {
      return key;
    }
  }
  return null;
}

export function buildNormalizedSeries(perStep = [], metricKey = "") {
  const values = Array.isArray(perStep)
    ? perStep.map((row) => asFiniteNumber(row?.[metricKey]))
    : [];

  const finiteValues = values.filter((value) => value !== null);
  if (!finiteValues.length) {
    return {
      values,
      normalized: values.map(() => 0.5),
      min: null,
      max: null,
    };
  }

  const min = Math.min(...finiteValues);
  const max = Math.max(...finiteValues);
  if (max === min) {
    return {
      values,
      normalized: values.map((value) => (value === null ? 0.5 : 0.5)),
      min,
      max,
    };
  }

  const range = max - min;
  const normalized = values.map((value) => {
    if (value === null) return 0.5;
    return clamp01((value - min) / range);
  });

  return { values, normalized, min, max };
}

export function buildLayout(layers = [], components = {}, canvasWidth = 360, canvasHeight = 220) {
  const pad = 8;
  const gapY = 6;
  const gapX = 4;
  const count = Math.max(1, layers.length || 1);
  const stripHeight = Math.max(18, Math.floor((canvasHeight - (pad * 2) - ((count - 1) * gapY)) / count));
  const strips = [];
  const segments = [];

  layers.forEach((layer, layerIndex) => {
    const ids = Array.isArray(layer) ? layer : [];
    const y = pad + (layerIndex * (stripHeight + gapY));
    const widthAvailable = canvasWidth - (pad * 2);
    const segmentCount = Math.max(1, ids.length || 1);
    const segmentWidth = Math.max(16, Math.floor((widthAvailable - ((segmentCount - 1) * gapX)) / segmentCount));
    const stripSegments = [];

    ids.forEach((componentId, idx) => {
      const component = components[componentId];
      if (!component) return;
      const x = pad + (idx * (segmentWidth + gapX));
      const segment = {
        componentId,
        component,
        layerIndex,
        x,
        y,
        width: segmentWidth,
        height: stripHeight,
        centerX: x + Math.floor(segmentWidth / 2),
        centerY: y + Math.floor(stripHeight / 2),
      };
      segments.push(segment);
      stripSegments.push(segment);
    });

    strips.push({
      layerIndex,
      y,
      height: stripHeight,
      width: widthAvailable,
      x: pad,
      segments: stripSegments,
    });
  });

  return { strips, segments };
}

function buildActivitySeries(normalized = []) {
  return normalized.map((value, index) => {
    if (index === 0) return 0;
    return clamp01(Math.abs(value - normalized[index - 1]) * 4);
  });
}

function deterministicNoise(seed) {
  const value = Math.sin(seed * 12.9898 + 78.233) * 43758.5453;
  return value - Math.floor(value);
}

function drawPixelRect(ctx, x, y, width, height, fill) {
  ctx.fillStyle = fill;
  ctx.fillRect(Math.floor(x), Math.floor(y), Math.floor(width), Math.floor(height));
}

function drawLabel(ctx, text, x, y, fill = "#6a5b4b") {
  ctx.fillStyle = fill;
  ctx.font = '9px "Space Grotesk", sans-serif';
  ctx.fillText(text, x, y);
}

function truncateText(value, maxChars) {
  const text = String(value || "");
  if (!Number.isFinite(maxChars) || maxChars < 3 || text.length <= maxChars) return text;
  return `${text.slice(0, maxChars - 1)}~`;
}

function formatNumberForLegend(value) {
  if (!Number.isFinite(value)) return "na";
  if (Math.abs(value) >= 100) return value.toFixed(1);
  return value.toFixed(3);
}

function formatParamValue(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    if (Math.abs(value) >= 100) return String(Math.round(value));
    return value.toFixed(3).replace(/\.?0+$/, "");
  }
  if (typeof value === "string") return value;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (value === null || value === undefined) return "na";
  return String(value);
}

function summarizeParams(component = {}) {
  const params = component?.params && typeof component.params === "object" ? component.params : {};
  const entries = Object.entries(params);
  if (!entries.length) return "params: none";
  const shown = entries.slice(0, 3).map(([key, value]) => `${key}=${formatParamValue(value)}`);
  const suffix = entries.length > 3 ? ` +${entries.length - 3}` : "";
  return `params: ${shown.join(", ")}${suffix}`;
}

function colorFromLevel(level = 0.5) {
  if (level < 0.35) return "#7aabcc";
  if (level < 0.7) return "#c88a32";
  return "#e66a37";
}

function pickOptionalSeries(component, perStep, row0, shortKey) {
  const key = prefixedKey(component, shortKey);
  if (!Object.prototype.hasOwnProperty.call(row0, key)) return null;
  return {
    key,
    ...buildNormalizedSeries(perStep, key),
  };
}

function extractEpisodeData({ episode, layout }) {
  const perStep = episode?.per_step || [];
  const row0 = perStep[0] || {};
  const byComponentId = {};
  const byType = {};

  layout.segments.forEach((segment) => {
    const component = segment.component;
    const metricKey = pickMetricKey(component, row0);
    const baseSeries = metricKey ? buildNormalizedSeries(perStep, metricKey) : buildNormalizedSeries([], "");
    const extras = {};

    if (component.type === "Aggregator") {
      const preySeries = pickOptionalSeries(component, perStep, row0, "prey");
      const predSeries = pickOptionalSeries(component, perStep, row0, "pred");
      if (preySeries) extras.prey = preySeries;
      if (predSeries) extras.pred = predSeries;
    }
    if (component.type === "MarketSignal") {
      const priceSeries = pickOptionalSeries(component, perStep, row0, "price_signal");
      if (priceSeries) extras.priceSignal = priceSeries;
    }

    byComponentId[segment.componentId] = {
      metricKey,
      component,
      values: baseSeries.values,
      normalized: baseSeries.normalized,
      min: baseSeries.min,
      max: baseSeries.max,
      activity: buildActivitySeries(baseSeries.normalized),
      extras,
    };
    if (!byType[component.type]) byType[component.type] = [];
    byType[component.type].push({ segment, series: byComponentId[segment.componentId] });
  });

  return {
    perStep,
    row0,
    byComponentId,
    byType,
    stepCount: Math.max(1, perStep.length),
  };
}

function drawLayerBackdrop(ctx, layout, stepIndex) {
  const gradient = ctx.createLinearGradient(0, 0, 0, ctx.canvas.height);
  gradient.addColorStop(0, "#fff9f0");
  gradient.addColorStop(1, "#f4e5d1");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, ctx.canvas.width, ctx.canvas.height);

  for (let i = 0; i < 20; i += 1) {
    const nx = deterministicNoise((i * 17) + (stepIndex * 0.12));
    const ny = deterministicNoise((i * 29) + (stepIndex * 0.08) + 3);
    const twinkle = deterministicNoise((stepIndex * 0.7) + i);
    const size = twinkle > 0.75 ? 2 : 1;
    drawPixelRect(
      ctx,
      Math.floor(nx * ctx.canvas.width),
      Math.floor(ny * Math.max(16, ctx.canvas.height * 0.35)),
      size,
      size,
      twinkle > 0.6 ? "rgba(255,255,255,0.9)" : "rgba(255,246,228,0.7)"
    );
  }

  layout.strips.forEach((strip) => {
    drawPixelRect(ctx, strip.x, strip.y, strip.width, strip.height, strip.layerIndex % 2 ? "rgba(243,232,218,0.88)" : "rgba(247,238,227,0.9)");
    const lineY = strip.y + ((stepIndex + strip.layerIndex) % Math.max(1, strip.height));
    drawPixelRect(ctx, strip.x, lineY, strip.width, 1, "rgba(44,122,123,0.22)");
    drawPixelRect(ctx, strip.x, strip.y, strip.width, 1, "rgba(255,255,255,0.6)");
    drawLabel(ctx, `L${strip.layerIndex + 1}`, strip.x + 3, strip.y + 10);
  });
}

function drawCartoonAgent(
  ctx,
  x,
  y,
  { mood = "happy", bounce = 0, tone = "#2c7a7b", blink = false, wiggle = 0, activity = 0 } = {}
) {
  const bx = Math.floor(x + wiggle);
  const by = Math.floor(y - bounce);
  const suitShade = "rgba(20,42,46,0.28)";
  const visor = "#f4d0ab";
  const visorShade = "#e6bb95";
  const outline = "#3a2b20";
  const glow = activity > 0.5 ? "rgba(232,93,37,0.18)" : "rgba(44,122,123,0.14)";

  drawPixelRect(ctx, bx - 1, by + 8, 13, 4, glow);
  drawPixelRect(ctx, bx + 2, by + 11, 8, 2, "rgba(26,26,26,0.24)");

  drawPixelRect(ctx, bx + 1, by + 1, 10, 10, outline);
  drawPixelRect(ctx, bx + 2, by + 2, 8, 8, tone);
  drawPixelRect(ctx, bx + 2, by + 2, 1, 8, suitShade);
  drawPixelRect(ctx, bx + 9, by + 2, 1, 8, "rgba(255,255,255,0.16)");

  drawPixelRect(ctx, bx + 3, by, 6, 2, visor);
  drawPixelRect(ctx, bx + 3, by + 1, 6, 1, visorShade);
  drawPixelRect(ctx, bx + 2, by + 1, 1, 2, visorShade);
  drawPixelRect(ctx, bx + 9, by + 1, 1, 2, visorShade);

  drawPixelRect(ctx, bx + 3, by + 4, 2, 1, "#f7ddc0");
  drawPixelRect(ctx, bx + 7, by + 4, 2, 1, "#f7ddc0");

  if (blink) {
    drawPixelRect(ctx, bx + 4, by + 5, 1, 1, "#1f2a31");
    drawPixelRect(ctx, bx + 7, by + 5, 1, 1, "#1f2a31");
  } else {
    drawPixelRect(ctx, bx + 4, by + 5, 1, 1, "#101820");
    drawPixelRect(ctx, bx + 7, by + 5, 1, 1, "#101820");
    drawPixelRect(ctx, bx + 4, by + 6, 1, 1, "#ffffff");
    drawPixelRect(ctx, bx + 7, by + 6, 1, 1, "#ffffff");
  }

  if (mood === "wow") {
    drawPixelRect(ctx, bx + 5, by + 7, 1, 2, "#6b3f2d");
    drawPixelRect(ctx, bx + 6, by + 7, 1, 2, "#6b3f2d");
  } else if (mood === "calm") {
    drawPixelRect(ctx, bx + 4, by + 8, 4, 1, "#6b3f2d");
  } else {
    drawPixelRect(ctx, bx + 4, by + 8, 1, 1, "#6b3f2d");
    drawPixelRect(ctx, bx + 5, by + 9, 2, 1, "#6b3f2d");
    drawPixelRect(ctx, bx + 7, by + 8, 1, 1, "#6b3f2d");
  }

  drawPixelRect(ctx, bx + 3, by + 10, 2, 2, outline);
  drawPixelRect(ctx, bx + 7, by + 10, 2, 2, outline);
}

function drawComponentState(ctx, segment, series, stepIndex) {
  const level = series.normalized[stepIndex] ?? 0.5;
  const value = series.values[stepIndex];
  const activity = series.activity[stepIndex] ?? 0;
  const innerPad = 2;
  const innerX = segment.x + innerPad;
  const innerY = segment.y + innerPad;
  const innerW = Math.max(2, segment.width - (innerPad * 2));
  const innerH = Math.max(2, segment.height - (innerPad * 2));
  const fillH = Math.max(1, Math.floor(innerH * clamp01(level)));
  const fillY = innerY + innerH - fillH;
  const baseColor = activity > 0.35 ? "#f7c170" : colorFromLevel(level);
  const borderColor = activity > 0.5 ? "#e85d25" : "#6a5b4b";

  drawPixelRect(ctx, segment.x, segment.y, segment.width, segment.height, "#fff9f2");
  drawPixelRect(ctx, innerX, innerY, innerW, innerH, "#efe3d4");
  drawPixelRect(ctx, innerX, fillY, innerW, fillH, baseColor);

  ctx.strokeStyle = borderColor;
  ctx.strokeRect(segment.x + 0.5, segment.y + 0.5, segment.width - 1, segment.height - 1);

  const valueLabel = Number.isFinite(value) ? value.toFixed(2) : "na";
  const metricLabel = series.metricKey ? String(series.metricKey).split(".").slice(1).join(".") : "no-metric";
  const streamLabel = segment.component.streamName || segment.component.displayName || "stream";
  const reserveForAgent = segment.component.agent?.enabled ? 14 : 0;
  const textWidth = Math.max(4, innerW - reserveForAgent);
  const maxChars = Math.max(4, Math.floor(textWidth / 5));
  if (innerH >= 12 && textWidth > 10) {
    drawLabel(ctx, truncateText(streamLabel, maxChars), innerX + 1, innerY + 7, "#5f4f40");
    drawLabel(ctx, truncateText(metricLabel, maxChars), innerX + 1, innerY + 14, "#7a6857");
    drawLabel(ctx, valueLabel, innerX + 1, innerY + innerH - 1);
  }

  if (!segment.component.agent?.enabled) return;
  const capacity = Math.max(1, Math.floor(Number(segment.component.agent.capacity || 1)));
  const visibleCount = Math.max(1, Math.min(capacity, 1));
  const tone = level > 0.6 ? "#2c7a7b" : level > 0.35 ? "#4a8f90" : "#7ea3a4";
  const mood = activity > 0.55 ? "wow" : level > 0.45 ? "happy" : "calm";
  const spriteW = 12;
  const spriteH = 13;
  const spriteX = segment.x + segment.width - spriteW - 2;
  const spriteY = segment.y + segment.height - spriteH - 1;
  for (let i = 0; i < visibleCount; i += 1) {
    const sx = spriteX + (i * 10);
    const bob = Math.max(0, Math.round(Math.sin((stepIndex + i) * 0.9) * (0.8 + (activity * 1.9))));
    const wiggle = Math.round(Math.sin((stepIndex * 0.45) + (segment.layerIndex * 0.6) + i) * (0.45 + (activity * 1.2)));
    const blink = deterministicNoise((stepIndex * 0.7) + i + (segment.layerIndex * 3)) > 0.88;
    drawCartoonAgent(ctx, sx, spriteY, { mood, bounce: bob, tone, blink, wiggle, activity });
  }
  if (capacity > visibleCount) {
    drawPixelRect(ctx, segment.x + segment.width - 13, segment.y + 2, 11, 7, "rgba(255,250,243,0.92)");
    drawPixelRect(ctx, segment.x + segment.width - 13, segment.y + 2, 11, 1, "#ad8e71");
    drawPixelRect(ctx, segment.x + segment.width - 13, segment.y + 8, 11, 1, "#ad8e71");
    drawLabel(ctx, `+${capacity - visibleCount}`, segment.x + segment.width - 11, segment.y + 8, "#6c4d38");
  }
}

function clearLegend(legendHost) {
  if (!legendHost) return;
  legendHost.innerHTML = "";
}

function renderLegend(legendHost, layout, episodeData) {
  if (!legendHost) return;
  clearLegend(legendHost);
  if (!layout?.segments?.length || !episodeData?.byComponentId) return new Map();

  const valueNodes = new Map();

  layout.strips.forEach((strip) => {
    strip.segments.forEach((segment, segmentIndex) => {
      const series = episodeData.byComponentId[segment.componentId];
      const component = segment.component || {};
      const item = document.createElement("article");
      item.className = "pixel-legend-item";

      const head = document.createElement("div");
      head.className = "pixel-legend-head";
      const boxTag = document.createElement("span");
      boxTag.className = "pixel-legend-box";
      boxTag.textContent = `L${strip.layerIndex + 1}B${segmentIndex + 1}`;
      const swatch = document.createElement("span");
      swatch.className = "pixel-legend-swatch";
      const level = series?.normalized?.[0] ?? 0.5;
      swatch.style.setProperty("--legend-color", colorFromLevel(level));
      const streamTag = document.createElement("span");
      streamTag.className = "pixel-legend-stream";
      streamTag.textContent = component.displayName || component.streamName || "Stream";
      const valueTag = document.createElement("span");
      valueTag.className = "pixel-legend-value";
      valueTag.textContent = formatNumberForLegend(series?.values?.[0]);
      head.appendChild(boxTag);
      head.appendChild(swatch);
      head.appendChild(streamTag);
      head.appendChild(valueTag);

      const key = document.createElement("code");
      key.className = "pixel-legend-key";
      key.textContent = series?.metricKey || "No numeric metric found";

      const meta = document.createElement("div");
      meta.className = "pixel-legend-meta";
      const agentCapacity = Math.max(1, Math.floor(Number(component.agent?.capacity || 1)));
      const agentText = component.agent?.enabled ? `agent x${agentCapacity}` : "non-agent";
      meta.textContent = `${component.type || "Custom"} • ${agentText}`;

      const paramsLine = document.createElement("div");
      paramsLine.className = "pixel-legend-params";
      paramsLine.textContent = summarizeParams(component);

      item.appendChild(head);
      item.appendChild(key);
      item.appendChild(meta);
      item.appendChild(paramsLine);
      legendHost.appendChild(item);
      valueNodes.set(segment.componentId, valueTag);
    });
  });

  return valueNodes;
}

function updateLegendValues(valueNodes, episodeData, stepIndex) {
  if (!valueNodes || !episodeData?.byComponentId) return;
  valueNodes.forEach((valueNode, componentId) => {
    const series = episodeData.byComponentId[componentId];
    const value = series?.values?.[stepIndex];
    valueNode.textContent = formatNumberForLegend(value);
  });
}

function drawSparkles(ctx, segment, activity, stepIndex, baseHue = "#e85d25") {
  const count = Math.max(0, Math.floor(activity * 6));
  for (let i = 0; i < count; i += 1) {
    const n1 = deterministicNoise((stepIndex * 13) + (segment.x * 0.17) + i);
    const n2 = deterministicNoise((stepIndex * 31) + (segment.y * 0.11) + i + 2);
    const x = segment.x + 1 + Math.floor(n1 * Math.max(1, segment.width - 2));
    const y = segment.y + 1 + Math.floor(n2 * Math.max(1, segment.height - 2));
    drawPixelRect(ctx, x, y, 1, 1, baseHue);
  }
}

function drawSimplePulse(ctx, fromSegment, toSegment, color, thickness = 2) {
  if (!fromSegment || !toSegment) return;
  const x1 = fromSegment.centerX;
  const y1 = fromSegment.centerY;
  const x2 = toSegment.centerX;
  const y2 = toSegment.centerY;
  ctx.strokeStyle = color;
  ctx.lineWidth = thickness;
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}

function valueAt(series, stepIndex) {
  if (!series) return null;
  return series.values[stepIndex] ?? null;
}

function deltaAt(series, stepIndex) {
  if (!series || stepIndex <= 0) return 0;
  const current = valueAt(series, stepIndex);
  const previous = valueAt(series, stepIndex - 1);
  if (!Number.isFinite(current) || !Number.isFinite(previous)) return 0;
  return current - previous;
}

function firstByType(typeMap, type) {
  const entries = typeMap[type] || [];
  return entries[0] || null;
}

function drawSample1Effects(ctx, data, stepIndex, layout) {
  const prey = firstByType(data.byType, "PreyRisk");
  const predator = firstByType(data.byType, "PredatorResponse");
  const climate = firstByType(data.byType, "Climate");
  const movement = firstByType(data.byType, "Movement");
  const aggregator = firstByType(data.byType, "Aggregator");

  if (prey && predator) {
    const preyDelta = deltaAt(prey.series, stepIndex);
    const predDelta = deltaAt(predator.series, stepIndex);
    if (preyDelta < 0 && predDelta > 0) {
      drawSimplePulse(ctx, predator.segment, prey.segment, "rgba(232,93,37,0.9)", 2);
    }
  }

  if (climate) {
    const climateValue = Math.abs(valueAt(climate.series, stepIndex) || 0);
    if (climateValue > 0.5) {
      const alpha = Math.min(0.28, 0.08 + (climateValue * 0.15));
      drawPixelRect(ctx, layout.strips[0].x, layout.strips[0].y, layout.strips[0].width, layout.strips[0].height, `rgba(44,122,123,${alpha})`);
    }
  }

  if (movement) {
    const movementLevel = movement.series.normalized[stepIndex] ?? 0;
    if (movementLevel > 0.45) {
      const radius = 3 + Math.floor(movementLevel * 6);
      ctx.strokeStyle = "rgba(33,113,181,0.8)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(movement.segment.centerX, movement.segment.centerY, radius, 0, Math.PI * 1.6);
      ctx.stroke();
    }
  }

  if (aggregator) {
    const extinctValue = valueAt(aggregator.series, stepIndex) || 0;
    if (extinctValue >= 0.5) {
      drawPixelRect(ctx, 0, Math.floor(layout.strips[layout.strips.length - 1].y) - 2, ctx.canvas.width, 10, "rgba(232,93,37,0.34)");
    }
  }
}

function drawRuleIcon(ctx, segment, isPositive, positiveColor, negativeColor) {
  const x = segment.x + segment.width - 9;
  const y = segment.y + 2;
  drawPixelRect(ctx, x, y, 7, 7, "rgba(255,255,255,0.88)");
  if (isPositive) {
    drawPixelRect(ctx, x + 1, y + 3, 5, 1, positiveColor);
    drawPixelRect(ctx, x + 4, y + 1, 1, 5, positiveColor);
  } else {
    drawPixelRect(ctx, x + 1, y + 3, 5, 1, negativeColor);
    drawPixelRect(ctx, x + 2, y + 1, 1, 5, negativeColor);
  }
}

function drawSample2Effects(ctx, data, stepIndex) {
  const gov = firstByType(data.byType, "GovernmentPolicy");
  const firm = firstByType(data.byType, "FirmGroup");
  const market = firstByType(data.byType, "MarketSignal");
  const payoff = firstByType(data.byType, "PayoffAccounting");
  const alliance = firstByType(data.byType, "AllianceRule");
  const groupMode = firstByType(data.byType, "GroupGamingRule");

  if (gov && firm && deltaAt(gov.series, stepIndex) > 0) {
    drawSimplePulse(ctx, gov.segment, firm.segment, "rgba(232,93,37,0.85)", 2);
  }
  if (market && firm && deltaAt(market.series, stepIndex) > 0) {
    drawSimplePulse(ctx, market.segment, firm.segment, "rgba(44,122,123,0.85)", 2);
  }
  if (payoff && firm) {
    const payoffDelta = valueAt(payoff.series, stepIndex) || 0;
    const flashColor = payoffDelta >= 0 ? "rgba(52,168,83,0.18)" : "rgba(214,90,75,0.2)";
    drawPixelRect(ctx, firm.segment.x, firm.segment.y, firm.segment.width, firm.segment.height, flashColor);
  }
  if (alliance) {
    const positive = (valueAt(alliance.series, stepIndex) || 0) >= 0.5;
    drawRuleIcon(ctx, alliance.segment, positive, "#2c7a7b", "#e85d25");
  }
  if (groupMode) {
    const positive = (valueAt(groupMode.series, stepIndex) || 0) >= 0.5;
    drawRuleIcon(ctx, groupMode.segment, positive, "#4f8c2f", "#9333ea");
  }
}

function drawGenericEffects(ctx, data, stepIndex, layout) {
  layout.segments.forEach((segment) => {
    const series = data.byComponentId[segment.componentId];
    const activity = series?.activity?.[stepIndex] ?? 0;
    drawSparkles(ctx, segment, activity, stepIndex, "rgba(232,93,37,0.85)");
  });
}

function drawFrame(ctx, layout, episodeData, stepIndex) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  drawPixelRect(ctx, 0, 0, ctx.canvas.width, ctx.canvas.height, "#fffaf4");
  drawLayerBackdrop(ctx, layout, stepIndex);

  layout.segments.forEach((segment) => {
    const series = episodeData.byComponentId[segment.componentId];
    if (!series) return;
    drawComponentState(ctx, segment, series, stepIndex);
    drawSparkles(ctx, segment, series.activity[stepIndex] ?? 0, stepIndex, "rgba(44,122,123,0.9)");
  });

  const hasSample1 =
    Boolean(episodeData.byType.PreyRisk?.length) &&
    Boolean(episodeData.byType.PredatorResponse?.length) &&
    Boolean(episodeData.byType.Climate?.length);
  const hasSample2 =
    Boolean(episodeData.byType.GovernmentPolicy?.length) &&
    Boolean(episodeData.byType.FirmGroup?.length) &&
    Boolean(episodeData.byType.MarketSignal?.length);

  if (hasSample1) drawSample1Effects(ctx, episodeData, stepIndex, layout);
  if (hasSample2) drawSample2Effects(ctx, episodeData, stepIndex);
  if (!hasSample1 && !hasSample2) drawGenericEffects(ctx, episodeData, stepIndex, layout);
}

function toScenarioEntries(result, scenarioResults) {
  if (Array.isArray(scenarioResults) && scenarioResults.length) {
    return scenarioResults.map((entry, index) => ({
      label: entry.label || `Scenario ${index + 1}`,
      result: entry.result || { episodes: [] },
    }));
  }
  return [{ label: "Scenario 1", result: result || { episodes: [] } }];
}

function readIndex(selectElement, maxExclusive) {
  const value = Number(selectElement?.value);
  if (!Number.isFinite(value)) return 0;
  return Math.min(Math.max(0, Math.floor(value)), Math.max(0, maxExclusive - 1));
}

export function createPixelPlayer(elements) {
  const {
    canvas,
    scenarioSelect,
    episodeSelect,
    playBtn,
    scrubInput,
    speedSelect,
    stepLabel,
    legendHost,
  } = elements || {};

  if (!canvas) {
    return {
      loadRun: () => {},
      play: () => {},
      pause: () => {},
      setStep: () => {},
      setSpeed: () => {},
      dispose: () => {},
    };
  }

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return {
      loadRun: () => {},
      play: () => {},
      pause: () => {},
      setStep: () => {},
      setSpeed: () => {},
      dispose: () => {},
    };
  }
  ctx.imageSmoothingEnabled = false;

  const state = {
    layout: null,
    scenarioEntries: [],
    activeEpisodeData: null,
    legendValueNodes: new Map(),
    activeScenarioIndex: 0,
    activeEpisodeIndex: 0,
    stepIndex: 0,
    speed: 1,
    playing: false,
    rafId: null,
    lastFrameAt: null,
    layers: [],
    components: {},
  };

  function setPlayLabel() {
    if (!playBtn) return;
    playBtn.textContent = state.playing ? "Pause" : "Play";
  }

  function updateStepLabel() {
    if (!stepLabel) return;
    stepLabel.textContent = `t=${state.stepIndex}`;
  }

  function setStep(stepIndex) {
    const maxStep = Math.max(0, (state.activeEpisodeData?.stepCount || 1) - 1);
    state.stepIndex = Math.min(Math.max(0, Math.floor(stepIndex)), maxStep);
    if (scrubInput) scrubInput.value = String(state.stepIndex);
    updateStepLabel();
    if (!state.layout || !state.activeEpisodeData) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      clearLegend(legendHost);
      return;
    }
    drawFrame(ctx, state.layout, state.activeEpisodeData, state.stepIndex);
    updateLegendValues(state.legendValueNodes, state.activeEpisodeData, state.stepIndex);
  }

  function rebuildEpisodeData() {
    const scenario = state.scenarioEntries[state.activeScenarioIndex];
    const episodes = scenario?.result?.episodes || [];
    state.activeEpisodeIndex = Math.min(state.activeEpisodeIndex, Math.max(0, episodes.length - 1));
    const episode = episodes[state.activeEpisodeIndex] || { per_step: [] };
    state.activeEpisodeData = extractEpisodeData({ episode, layout: state.layout });
    state.legendValueNodes = renderLegend(legendHost, state.layout, state.activeEpisodeData);
    const stepCount = Math.max(1, state.activeEpisodeData.stepCount);

    if (scrubInput) {
      scrubInput.disabled = stepCount <= 1;
      scrubInput.min = "0";
      scrubInput.max = String(stepCount - 1);
      scrubInput.step = "1";
    }
    setStep(0);
    if (playBtn) playBtn.disabled = stepCount <= 1;
  }

  function rebuildEpisodeOptions() {
    if (!episodeSelect) return;
    const scenario = state.scenarioEntries[state.activeScenarioIndex];
    const episodes = scenario?.result?.episodes || [];
    episodeSelect.innerHTML = "";
    episodes.forEach((_, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = `Episode ${index + 1}`;
      episodeSelect.appendChild(option);
    });
    if (!episodes.length) {
      const option = document.createElement("option");
      option.value = "0";
      option.textContent = "Episode 1";
      episodeSelect.appendChild(option);
    }
    episodeSelect.disabled = episodes.length <= 1;
    episodeSelect.value = String(Math.min(state.activeEpisodeIndex, Math.max(0, episodes.length - 1)));
  }

  function rebuildScenarioOptions() {
    if (!scenarioSelect) return;
    scenarioSelect.innerHTML = "";
    state.scenarioEntries.forEach((entry, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = entry.label || `Scenario ${index + 1}`;
      scenarioSelect.appendChild(option);
    });
    scenarioSelect.disabled = state.scenarioEntries.length <= 1;
    if (scenarioSelect.parentElement) {
      scenarioSelect.parentElement.hidden = state.scenarioEntries.length <= 1;
    }
    scenarioSelect.value = String(state.activeScenarioIndex);
  }

  function tick(timestamp) {
    if (!state.playing) return;
    if (!state.activeEpisodeData) {
      state.playing = false;
      setPlayLabel();
      return;
    }

    const frameDurationMs = 240 / Math.max(0.1, state.speed);
    if (state.lastFrameAt === null) {
      state.lastFrameAt = timestamp;
    }

    if (timestamp - state.lastFrameAt >= frameDurationMs) {
      state.lastFrameAt = timestamp;
      const stepCount = Math.max(1, state.activeEpisodeData.stepCount);
      const next = (state.stepIndex + 1) % stepCount;
      setStep(next);
    }
    state.rafId = requestAnimationFrame(tick);
  }

  function play() {
    if (state.playing) return;
    state.playing = true;
    state.lastFrameAt = null;
    setPlayLabel();
    state.rafId = requestAnimationFrame(tick);
  }

  function pause() {
    state.playing = false;
    setPlayLabel();
    if (state.rafId !== null) {
      cancelAnimationFrame(state.rafId);
      state.rafId = null;
    }
  }

  function setSpeed(speed) {
    const value = Number(speed);
    state.speed = Number.isFinite(value) && value > 0 ? value : 1;
    if (speedSelect) speedSelect.value = String(state.speed);
  }

  function loadRun({ result, scenarioResults = [], layers = [], components = {} }) {
    state.layers = Array.isArray(layers) ? layers : [];
    state.components = components || {};
    state.layout = buildLayout(state.layers, state.components, canvas.width, canvas.height);
    state.scenarioEntries = toScenarioEntries(result, scenarioResults);
    state.activeScenarioIndex = 0;
    state.activeEpisodeIndex = 0;
    rebuildScenarioOptions();
    rebuildEpisodeOptions();
    rebuildEpisodeData();
    setSpeed(speedSelect?.value || 1);
    setPlayLabel();
  }

  const listeners = [];

  if (scenarioSelect) {
    const onScenarioChange = () => {
      state.activeScenarioIndex = readIndex(scenarioSelect, state.scenarioEntries.length);
      state.activeEpisodeIndex = 0;
      rebuildEpisodeOptions();
      rebuildEpisodeData();
    };
    scenarioSelect.addEventListener("change", onScenarioChange);
    listeners.push(() => scenarioSelect.removeEventListener("change", onScenarioChange));
  }

  if (episodeSelect) {
    const onEpisodeChange = () => {
      const scenario = state.scenarioEntries[state.activeScenarioIndex];
      const episodeCount = scenario?.result?.episodes?.length || 1;
      state.activeEpisodeIndex = readIndex(episodeSelect, episodeCount);
      rebuildEpisodeData();
    };
    episodeSelect.addEventListener("change", onEpisodeChange);
    listeners.push(() => episodeSelect.removeEventListener("change", onEpisodeChange));
  }

  if (scrubInput) {
    const onScrub = () => {
      pause();
      setStep(Number(scrubInput.value));
    };
    scrubInput.addEventListener("input", onScrub);
    listeners.push(() => scrubInput.removeEventListener("input", onScrub));
  }

  if (speedSelect) {
    const onSpeedChange = () => {
      setSpeed(speedSelect.value);
    };
    speedSelect.addEventListener("change", onSpeedChange);
    listeners.push(() => speedSelect.removeEventListener("change", onSpeedChange));
  }

  if (playBtn) {
    const onPlayToggle = () => {
      if (state.playing) {
        pause();
      } else {
        play();
      }
    };
    playBtn.addEventListener("click", onPlayToggle);
    listeners.push(() => playBtn.removeEventListener("click", onPlayToggle));
  }

  setPlayLabel();
  updateStepLabel();

  return {
    loadRun,
    play,
    pause,
    setStep,
    setSpeed,
    dispose: () => {
      pause();
      listeners.forEach((release) => release());
      listeners.length = 0;
    },
  };
}
