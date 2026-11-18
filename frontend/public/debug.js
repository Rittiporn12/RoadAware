"use strict";

// Developer diagnostics: one real request at a time, raw status/JSON via textContent only.

const $ = (id) => document.getElementById(id);
const TIMEOUT_MS = 30000;
const SAMPLE_SEGMENT = "rsv1-rc31f3d87fc7:doh:1036:p0:c0:r2000:00000";

const PRESETS = {
  ready: ["GET", "/ready"],
  metadata: ["GET", "/api/v1/metadata"],
  provinces: ["GET", "/api/v1/provinces"],
  evaluation: ["GET", "/api/v1/evaluation"],
  segments: ["GET", "/api/v1/segments?bbox=100.4,13.6,100.8,14.0&limit=10"],
  predict: ["POST", "/api/v1/spatial/predictions", { unit: "daily", requests: [{ segment_id: SAMPLE_SEGMENT, target_date: "2026-11-12" }] }],
  baseline: ["POST", "/api/v1/spatial/baseline-predictions", { unit: "daily", requests: [{ segment_id: SAMPLE_SEGMENT, target_date: "2026-11-12" }] }],
  history: ["POST", "/api/v1/spatial/history", { segment_id: SAMPLE_SEGMENT, target_date: "2026-11-12", unit: "daily" }],
  bad: ["POST", "/api/v1/spatial/predictions", { unit: "weekly", requests: [] }],
};

let gen = 0;
let controller = null;

function clearOutput(message) {
  gen += 1;
  if (controller) controller.abort();
  controller = null;
  $("outState").textContent = message;
  $("outRequest").textContent = "-";
  $("outHttp").textContent = "-";
  $("outJson").textContent = "-";
}

function baseUrl() {
  const url = new URL($("baseUrl").value.trim());
  if (url.protocol !== "http:" && url.protocol !== "https:") throw new Error("ต้องเป็น http:// หรือ https://");
  return url.origin + url.pathname.replace(/\/+$/, "");
}

async function send() {
  clearOutput("กำลังส่ง…");
  const myGen = gen;
  const method = $("method").value;
  let url;
  let body;
  try {
    url = baseUrl() + $("path").value.trim();
    if (method === "POST") body = $("body").value.trim() ? JSON.parse($("body").value) : undefined;
  } catch (err) {
    $("outState").textContent = "ข้อมูลที่กรอกไม่ถูกต้อง: " + err.message;
    return;
  }
  $("outRequest").textContent = method + " " + url;
  const ctrl = new AbortController();
  controller = ctrl;
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; ctrl.abort(); }, TIMEOUT_MS);
  const init = { method, signal: ctrl.signal, cache: "no-store" };
  if (body !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(body);
  }
  try {
    const res = await fetch(url, init);
    const text = await res.text();
    if (myGen !== gen) return;
    let shown = text;
    try { shown = JSON.stringify(JSON.parse(text), null, 2); } catch (_) { /* keep raw text */ }
    $("outHttp").textContent = res.status + " " + res.statusText;
    $("outJson").textContent = shown;
    $("outState").textContent = res.ok ? "สำเร็จ" : "API ตอบกลับข้อผิดพลาด";
  } catch (err) {
    if (myGen !== gen) return;
    $("outHttp").textContent = "(ไม่มีการตอบกลับ)";
    $("outState").textContent = timedOut ? "หมดเวลารอ " + TIMEOUT_MS / 1000 + " วินาที"
      : "เชื่อมต่อไม่ได้ (server ไม่เปิด, URL ผิด หรือถูก CORS ปฏิเสธ): " + err.message;
  } finally {
    clearTimeout(timer);
    if (controller === ctrl) controller = null;
  }
}

for (const btn of document.querySelectorAll("[data-preset]")) {
  btn.addEventListener("click", () => {
    const [method, path, body] = PRESETS[btn.dataset.preset];
    $("method").value = method;
    $("path").value = path;
    $("body").value = body ? JSON.stringify(body, null, 2) : "";
    send();
  });
}
$("btnSend").addEventListener("click", send);
for (const id of ["baseUrl", "method", "path", "body"]) {
  $(id).addEventListener("input", () => clearOutput("มีการแก้ไขค่า — ผลเดิมถูกล้างแล้ว"));
}
