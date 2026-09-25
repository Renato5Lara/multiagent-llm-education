// Renderiza definiciones Mermaid a SVG REAL con mermaid-cli (mermaid.js dentro de Chrome headless).
// Uso: node render.mjs <jobs.json> <out_dir>      jobs.json = [{"id": "...", "definition": "flowchart TD ..."}]
// Salida: <out_dir>/<id>.svg y un resumen JSON por stdout: [{id, ok, bytes?, error?}]
import fs from "node:fs";
import path from "node:path";
import puppeteer from "puppeteer-core";
import { renderMermaid } from "@mermaid-js/mermaid-cli";

const [jobsPath, outDir] = process.argv.slice(2);
const jobs = JSON.parse(fs.readFileSync(jobsPath, "utf8"));
fs.mkdirSync(outDir, { recursive: true });
const chrome = process.env.MERMAID_CHROME || "/usr/bin/google-chrome";
const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "shell",
  args: ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
});
const results = [];
try {
  for (const job of jobs) {
    try {
      const { data } = await renderMermaid(browser, job.definition, "svg", {
        backgroundColor: "white",
        mermaidConfig: { theme: "default", securityLevel: "strict" },
      });
      const file = path.join(outDir, `${job.id}.svg`);
      fs.writeFileSync(file, data);
      results.push({ id: job.id, ok: true, bytes: data.length });
    } catch (e) {
      results.push({ id: job.id, ok: false, error: String(e.message || e).slice(0, 400) });
    }
  }
} finally {
  await browser.close();
}
process.stdout.write(JSON.stringify(results));
