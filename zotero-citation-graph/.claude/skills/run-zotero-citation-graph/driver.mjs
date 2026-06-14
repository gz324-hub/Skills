#!/usr/bin/env node
/*
 * driver.mjs — headless harness for the Zotero citation graph viewer.
 *
 * Loads index.html (over file://) in Playwright Chromium, waits for the
 * vis-network layout to stabilise, screenshots it, and verifies that
 * clicking a node opens that paper's website (by intercepting window.open).
 *
 * Commands:
 *   node driver.mjs verify            full smoke: render + screenshot + click-opens-URL
 *   node driver.mjs shot [out.png]    just render and screenshot
 *   node driver.mjs click <query>     click the node matching <query>, report the URL
 *
 * Env:
 *   ROOT        unit dir (default: resolved 3 levels up from this file)
 *   CHROME_BIN  chromium executable (default: auto-detected under /opt/pw-browsers,
 *               else Playwright's bundled browser)
 *   OUT         screenshot path (default: <ROOT>/out/screenshot.png)
 */
import { chromium } from "playwright";
import { existsSync, readdirSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = process.env.ROOT || resolve(__dirname, "../../../");
const INDEX = resolve(ROOT, "index.html");
const OUT = process.env.OUT || resolve(ROOT, "out", "screenshot.png");

function findChrome() {
  if (process.env.CHROME_BIN && existsSync(process.env.CHROME_BIN))
    return process.env.CHROME_BIN;
  const base = "/opt/pw-browsers";
  if (existsSync(base)) {
    for (const d of readdirSync(base).filter((x) => x.startsWith("chromium-"))) {
      for (const sub of ["chrome-linux/chrome", "chrome-linux64/chrome"]) {
        const p = `${base}/${d}/${sub}`;
        if (existsSync(p)) return p;
      }
    }
  }
  return undefined; // let Playwright use its bundled download
}

async function open() {
  if (!existsSync(INDEX)) {
    console.error(`✗ ${INDEX} not found. Build the graph first:\n` +
      `    python3 build_graph.py --input sample/library.json --out out`);
    process.exit(2);
  }
  const executablePath = findChrome();
  const browser = await chromium.launch({
    executablePath,
    args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
  });
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();
  // capture window.open(...) calls instead of spawning real tabs
  await page.addInitScript(() => {
    window.__opened = [];
    window.open = (url) => { window.__opened.push(url); return null; };
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(pathToFileURL(INDEX).href, { waitUntil: "load" });
  await page.waitForSelector('body[data-stable="1"]', { timeout: 20000 });
  return { browser, page, errors, executablePath };
}

async function nodeDomXY(page, id) {
  return await page.evaluate((nid) => {
    const g = window.__graph;
    const pos = g.network.getPositions([nid])[nid];
    const dom = g.network.canvasToDOM(pos);
    const rect = document.getElementById("net").getBoundingClientRect();
    return { x: rect.left + dom.x, y: rect.top + dom.y };
  }, id);
}

async function pickNode(page, query) {
  return await page.evaluate((q) => {
    const ns = window.GRAPH.nodes;
    if (!q) { // most-cited node
      return ns.slice().sort((a, b) => (b.cited_by || 0) - (a.cited_by || 0))[0];
    }
    const lo = q.toLowerCase();
    return ns.find((n) => (n.title + " " + n.authors + " " + n.label)
      .toLowerCase().includes(lo)) || null;
  }, query);
}

async function shot(page, out) {
  mkdirSync(dirname(out), { recursive: true });
  await page.screenshot({ path: out });
  const stats = await page.evaluate(() => window.GRAPH.stats);
  console.log(`✓ screenshot → ${out}  (${stats.papers} papers, ${stats.edges} edges)`);
  return stats;
}

async function clickNode(page, node) {
  const { x, y } = await nodeDomXY(page, node.id);
  await page.mouse.click(x, y);
  await page.waitForTimeout(150);
  const opened = await page.evaluate(() => window.__opened);
  return opened;
}

const cmd = process.argv[2] || "verify";
const arg = process.argv[3];
const { browser, page, errors, executablePath } = await open();
let code = 0;
try {
  console.log(`• chromium: ${executablePath || "(playwright bundled)"}`);
  if (cmd === "shot") {
    await shot(page, arg ? resolve(arg) : OUT);
  } else if (cmd === "click") {
    const node = await pickNode(page, arg);
    if (!node) throw new Error(`no node matches "${arg}"`);
    const opened = await clickNode(page, node);
    console.log(`• clicked "${node.label}" → ${opened[0] || "(nothing opened!)"}`);
    if (!opened.length) code = 1;
  } else { // verify
    const stats = await shot(page, OUT);
    const node = await pickNode(page, arg); // most-cited
    const opened = await clickNode(page, node);
    const ok = opened.length === 1 && opened[0] === node.url;
    console.log(`• most-cited node: "${node.label}" (cited_by=${node.cited_by})`);
    console.log(`• click opened:   ${opened[0] || "(nothing!)"}`);
    console.log(`• expected URL:   ${node.url}`);
    if (errors.length) { console.error("✗ page errors:", errors); code = 1; }
    if (!stats.papers) { console.error("✗ no papers rendered"); code = 1; }
    if (!ok) { console.error("✗ node click did not open the expected paper URL"); code = 1; }
    console.log(code === 0 ? "\nPASS ✅  graph renders and nodes open their papers"
                           : "\nFAIL ❌");
  }
} catch (e) {
  console.error("✗ driver error:", e.message);
  code = 1;
} finally {
  await browser.close();
}
process.exit(code);
