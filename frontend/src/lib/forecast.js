// Route → forecast pipeline (no React).
//   loadRouteMatches: every page of model road segments in the route's bbox, kept only when they really run
//                     along the route (routeMatch.js rule). Done once per route.
//   predictMatches:   estimated pass time per segment → its date + 6-hour block → selected-model rows,
//                     ≤128 per batch; any failed batch throws (no partial picture).
import { CONFIG, ENVELOPE, DATE_MIN, DATE_MAX, LEVELS } from "../config.js";
import { api, sleep, isNum, bkkToEpoch, epochToBkk, RequestFailure } from "./util.js";
import { matchFeature } from "./routeMatch.js";

// หาช่วงถนน 2 กม. ที่อยู่บนเส้นทาง
export async function loadRouteMatches(route, { signal, onProgress }) {
  // กรอบสี่เหลี่ยมที่ครอบเส้นทาง
  const bb = route.index.bbox;
  // ขยายกรอบออก 0.01° (ประมาณ 1 กม.) แต่ไม่เกินขอบเขตประเทศ แล้วปัดทศนิยม 4 ตำแหน่ง
  const bbox = [
    Math.max(ENVELOPE.west, bb.west - 0.01), Math.max(ENVELOPE.south, bb.south - 0.01),
    Math.min(ENVELOPE.east, bb.east + 0.01), Math.min(ENVELOPE.north, bb.north + 0.01),
  ].map((v) => Math.round(v * 10000) / 10000);

  // ช่วงถนนที่ได้จาก API
  const features = [];
  // ตัวแปรสำหรับแบ่งหน้า
  let cursor = null, page = 0, total = null;
  // วนขอทีละหน้า
  do {
    page += 1;
    // อัปเดตแถบความคืบหน้าบนหน้าจอ
    onProgress("กำลังหาช่วงถนนที่มีข้อมูลบนเส้นทาง…", total ? (features.length / total) * 0.4 : 0.05);
    // สร้างพารามิเตอร์: bbox, จำนวนต่อหน้า และ cursor ของหน้าถัดไป
    const qs = "?bbox=" + bbox.join(",") + "&limit=" + CONFIG.segmentPageSize + (cursor !== null ? "&cursor=" + encodeURIComponent(cursor) : "");
    // เรียก API GET /api/v1/segments
    const json = await api("/api/v1/segments" + qs, { signal });
    // เก็บช่วงถนนของหน้านี้
    for (const f of Array.isArray(json.features) ? json.features : []) features.push(f);
    // จำนวนทั้งหมด (ใช้คำนวณความคืบหน้า)
    total = json.page && isNum(json.page.total_matched) ? json.page.total_matched : total;
    // cursor ของหน้าถัดไป ถ้าไม่มีแปลว่าหมดแล้ว
    cursor = json.page && json.page.next_cursor != null ? json.page.next_cursor : null;
  // วนจนหมด หรือไม่เกิน 200 หน้า
  } while (cursor !== null && page < 200);

  // จากนั้นวัดว่าแต่ละช่วงอยู่บนเส้นทางจริงไหม (matchFeature ใน routeMatch.js)
  const matches = [];
  for (let i = 0; i < features.length; i++) {
    const f = features[i];
    const m = matchFeature(route.index, f);
    if (m) {
      const props = f.properties || {};
      const segM = isNum(props.segment_km) ? props.segment_km * 1000 : 2000;
      const frac = route.index.length > 0 ? m.along / route.index.length : 0;
      const alongM = frac * route.distance;
      matches.push({
        id: String(f.id ?? props.segment_id), feature: f, props, match: m, frac, alongM,
        startM: Math.max(0, alongM - segM / 2), endM: Math.min(route.distance, alongM + segM / 2),
      });
    }
    if (i % 300 === 299) {
      onProgress("กำลังจับคู่ช่วงถนนกับเส้นทาง…", 0.4 + (i / features.length) * 0.15);
      await sleep(0);
      if (signal.aborted) throw new RequestFailure("aborted");
    }
  }
  matches.sort((a, b) => a.alongM - b.alongM);
  return matches;
}

// คำนวณเวลาที่ขับผ่านแต่ละช่วงถนน แล้วส่งไปทำนาย
export async function predictMatches(matches, route, { date, time, signal, onProgress }) {
  // เวลาออกเดินทาง (เวลาไทย) แปลงเป็นมิลลิวินาที
  const depart = bkkToEpoch(date, time);
  // ช่วงที่จะส่งไปทำนาย
  const rows = [];
  // นับช่วงที่วันที่อยู่นอกช่วงที่รองรับ
  let outOfRange = 0;
  // วนทุกช่วงถนนบนเส้นทาง
  for (const mt of matches) {
    // เวลาที่ถึงช่วงนี้ = เวลาออก + (สัดส่วนระยะทาง × เวลาเดินทางทั้งหมด) แล้วแปลงเป็นวันที่ + ช่วง 6 ชม.
    const eta = epochToBkk(depart + mt.frac * route.duration * 1000);
    // เก็บเฉพาะวันที่ที่รองรับ
    if (eta.date >= DATE_MIN && eta.date <= DATE_MAX) rows.push({ mt, eta }); else outOfRange += 1;
  }
  // ผลการทำนายที่ใช้ได้
  const items = [];
  // ส่งทีละชุด ชุดละไม่เกิน 128 ช่วง
  for (let i = 0; i < rows.length; i += CONFIG.predictionBatch) {
    // อัปเดตความคืบหน้า
    if (onProgress) onProgress("กำลังประเมินความเสี่ยง " + Math.min(i + CONFIG.predictionBatch, rows.length) + "/" + rows.length + " ช่วงถนน…", 0.55 + (i / rows.length) * 0.45);
    // ตัดชุดปัจจุบัน
    const batch = rows.slice(i, i + CONFIG.predictionBatch);
    // สร้างคำขอ: หน่วย 6h และ (segment_id, target_date, time_block) ของแต่ละช่วง
    const body = { unit: "6h", requests: batch.map(({ mt, eta }) => ({ segment_id: mt.id, target_date: eta.date, time_block: eta.block })) };
    // เรียก API POST /api/v1/spatial/predictions
    const json = await api("/api/v1/spatial/predictions", { method: "POST", body, signal });
    // ผลลัพธ์
    const res = Array.isArray(json.results) ? json.results : [];
    // จำนวนผลต้องเท่ากับคำขอ ถ้าไม่เท่าถือว่าผิด (ไม่แสดงผลบางส่วน)
    if (res.length !== batch.length) throw new RequestFailure("invalid", 200, null);
    // วนผลแต่ละช่วง
    res.forEach((pred, k) => {
      // ระดับสีจาก API (ปกติ / ส้ม / แดง)
      const level = pred && LEVELS[pred.colour] ? pred.colour : null;
      // เก็บช่วงถนน + เวลาที่ถึง + ค่าทำนาย + ระดับ
      if (level) items.push({ ...batch[k].mt, eta: batch[k].eta, pred, level });
    });
  }
  // คืนผลทั้งหมด
  return { items, outOfRange };
}

export async function fetchSegmentHistory(segmentId, targetDate, signal) {
  const json = await api("/api/v1/spatial/history", {
    method: "POST",
    signal,
    body: { segment_id: segmentId, target_date: targetDate, unit: "daily", lookback_days: CONFIG.historyLookbackDays, top_k: 10 },
  });
  return json.history || null;
}
