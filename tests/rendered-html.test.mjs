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
  assert.match(html, /data-stage="hero"/);
  assert.match(html, /data-stage="about"/);
  assert.match(html, /data-stage="engineering"/);
  assert.match(html, /data-stage="leanmate"/);
  assert.match(html, /data-stage="voya"/);
  assert.match(html, /data-stage="contact"/);
  assert.match(html, /aria-label="滚动章节"/);
  assert.match(html, /https:\/\/byecho\.cn\/projects\/leanmate/);
  assert.match(html, /https:\/\/byecho\.cn\/projects\/roam/);
  assert.doesNotMatch(html, /codex-preview|Your site is taking shape|react-loading-skeleton/);
});
