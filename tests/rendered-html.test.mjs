import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function readStaticHomePage() {
  return readFile(new URL("../out/index.html", import.meta.url), "utf8");
}

test("exports the Echo portfolio as static HTML", async () => {
  const html = await readStaticHomePage();
  assert.match(html, /Echo — Frontend Engineer &amp; AI Full-Stack Builder/);
  assert.match(html, /Builds with AI/);
  assert.match(html, /AI 协作研发/);
  assert.match(html, /瘦搭 LeanMate/);
  assert.match(html, /漫游 Voya/);
  assert.match(html, /正在寻找前端与 AI 应用全栈方向的新机会/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/);
});
