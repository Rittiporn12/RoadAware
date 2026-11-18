import { CONFIG, LEVELS, LEVEL_ORDER } from "../config.js";
import { fmtKm, fmtDuration, epochToBkk, bkkToEpoch } from "../lib/util.js";
import { Dot } from "./common.jsx";

export default function RouteSummary({ route, date, time, items }) {
  const depart = bkkToEpoch(date, time);
  const far = route.snaps
    .map((d, i) => (d > CONFIG.snapWarnM ? (i === 0 ? "ต้นทาง" : "ปลายทาง") + "อยู่ห่างถนนที่ใกล้ที่สุดราว " + fmtKm(d) : null))
    .filter(Boolean);
  const counts = {};
  for (const it of items || []) counts[it.level] = (counts[it.level] || 0) + 1;
  return (
    <div>
      <div className="stats">
        <div className="stat"><span className="stat-label">ระยะทาง</span><span className="stat-value">{fmtKm(route.distance)}</span></div>
        <div className="stat"><span className="stat-label">เวลาขับโดยประมาณ</span><span className="stat-value">{fmtDuration(route.duration)}</span></div>
      </div>
      <div className="route-ends">
        <div><span className="pin pin-a">A</span><span>{route.origin.name} · ออก {epochToBkk(depart).clock}</span></div>
        <div><span className="pin pin-b">B</span><span>{route.dest.name} · ถึงราว {epochToBkk(depart + route.duration * 1000).clock}</span></div>
      </div>
      <p className="help">เวลาขับมาจากบริการเส้นทาง ไม่รวมสภาพจราจรจริง</p>
      {far.length > 0 && <p className="notice">{far.join(" · ")} — เส้นทางเริ่ม/สิ้นสุดที่ถนนนั้น ไม่ได้ขับเข้าถึงจุดที่เลือกโดยตรง</p>}
      {items && items.length > 0 && (
        <>
          <div className="level-chips">
            <span className="chip">ประเมินได้ {items.length} ช่วงถนน</span>
            {LEVEL_ORDER.filter((lv) => counts[lv]).map((lv) => (
              <span className="chip" key={lv}><Dot hex={LEVELS[lv].hex} />{LEVELS[lv].title} {counts[lv]}</span>
            ))}
          </div>
          <p className="help">ส่วนเส้นทางสีเทา = ยังไม่มีข้อมูลประเมิน (ไม่ใช่ความเสี่ยงศูนย์) · การจับคู่ช่วงถนนกับเส้นทางเป็นการประมาณ</p>
        </>
      )}
    </div>
  );
}
