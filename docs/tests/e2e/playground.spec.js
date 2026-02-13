import { expect, test } from "@playwright/test";

async function waitForReady(page) {
  await page.waitForFunction(() => {
    const el = document.getElementById("status");
    return el && /ready\./i.test(el.textContent || "");
  }, { timeout: 120000 });
}

async function dismissFirstRunOverlays(page) {
  const cookieBtn = page.locator("#cookieAcknowledgeBtn");
  if (await cookieBtn.isVisible().catch(() => false)) {
    await cookieBtn.click();
  }
  const tourSkipBtn = page.locator("#tourSkipBtn");
  if (await tourSkipBtn.isVisible().catch(() => false)) {
    await tourSkipBtn.click();
  }
}

test("loads app and runtime", async ({ page }) => {
  await page.goto("/index.html");
  await expect(page.locator("h1")).toContainText("HEAS Web Playground");
  await waitForReady(page);
});

test("run success path for sample1", async ({ page }) => {
  await page.goto("/index.html");
  await waitForReady(page);
  await dismissFirstRunOverlays(page);
  await page.fill("#stepsInput", "8");
  await page.fill("#episodesInput", "1");
  await page.click("#runBtn");
  await page.waitForFunction(() => /done\./i.test(document.getElementById("status")?.textContent || ""), { timeout: 120000 });
  await expect(page.locator("#runFactsOutput")).toContainText("run_id");
});

test("cancel run path", async ({ page }) => {
  await page.goto("/index.html");
  await waitForReady(page);
  await dismissFirstRunOverlays(page);
  await page.fill("#stepsInput", "500");
  await page.fill("#episodesInput", "20");
  await page.click("#runBtn");
  await page.click("#cancelBtn");
  await expect(page.locator("#status")).toContainText("cancelling");
});

test("import invalid bundle path", async ({ page }) => {
  await page.goto("/index.html");
  await waitForReady(page);
  await dismissFirstRunOverlays(page);
  const payload = Buffer.from("{bad-json}");
  await page.setInputFiles("#importInput", {
    name: "broken.json",
    mimeType: "application/json",
    buffer: payload,
  });
  await expect(page.locator("#runtimeErrors")).toContainText("Failed to import bundle");
});

test("share-link load path", async ({ page, context }) => {
  await page.goto("/index.html");
  await waitForReady(page);
  await dismissFirstRunOverlays(page);
  const cfg = await page.evaluate(() => {
    const url = new URL(window.location.href);
    const payload = {
      config: {
        version: "PlaygroundConfigV2",
        app_version: "1.0.0",
        mode: "sample1",
        controls: { steps: 5, episodes: 1, seed: 123 },
        layers: [[{ name: "L1", type: "Price", params: { start: 100, drift: 0.02, noise: 0.01 } }]],
        created_at: new Date().toISOString(),
        notes: "",
      },
      view: "sample1",
    };
    const encoded = btoa(unescape(encodeURIComponent(JSON.stringify(payload))))
      .replace(/\+/g, "-")
      .replace(/\//g, "_")
      .replace(/=+$/g, "");
    url.searchParams.set("cfg", encoded);
    url.searchParams.set("view", "sample1");
    return url.toString();
  });
  const page2 = await context.newPage();
  await page2.goto(cfg);
  await waitForReady(page2);
  await dismissFirstRunOverlays(page2);
  await expect(page2.locator("#stepsInput")).toHaveValue("5");
});

test("replay last run path", async ({ page }) => {
  await page.goto("/index.html");
  await waitForReady(page);
  await dismissFirstRunOverlays(page);
  await page.fill("#stepsInput", "6");
  await page.fill("#episodesInput", "1");
  await page.click("#runBtn");
  await page.waitForFunction(() => /done\./i.test(document.getElementById("status")?.textContent || ""), { timeout: 120000 });
  await expect(page.locator("#replayBtn")).toBeEnabled();
});

test("new user sees cookie banner and tour", async ({ page, context }) => {
  await context.addInitScript(() => {
    localStorage.clear();
  });
  await page.goto("/index.html");
  await waitForReady(page);
  await expect(page.locator("#cookieBanner")).toBeVisible();
  await expect(page.locator("#tourModal")).toBeVisible();
});

test("acknowledging consent hides banner", async ({ page, context }) => {
  await context.addInitScript(() => {
    localStorage.clear();
  });
  await page.goto("/index.html");
  await waitForReady(page);
  await page.click("#cookieAcknowledgeBtn");
  await expect(page.locator("#cookieBanner")).toBeHidden();
});
