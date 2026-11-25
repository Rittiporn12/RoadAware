// "ย้อนดูผล" result: where the model pointed vs where recorded accidents actually happened, for a past period.
import { LEVELS } from "../config.js";
import { fmtThaiDate, fmtKm, techText } from "../lib/util.js";
import { ErrorBox, Progress } from "./common.jsx";

const shortPlace = (s) => String(s || "").replace(/^จังหวัด/, "");
const pct = (x) => (x * 100 >= 10 ? Math.round(x * 100) : Math.round(x * 1000) / 10) + "%";

export function reviewSummary(items, zones, bySeg) {
  const segKm = (it) => Math.max(0, it.endM - it.startM) / 1000;
  const evalKm = items.reduce((a, it) => a + segKm(it), 0);
  const zoneIds = new Set();
  let zoneKm = 0;
  for (const z of zones) for (const m of z.members) if (!zoneIds.has(m.id)) { zoneIds.add(m.id); zoneKm += segKm(m); }
  let total = 0, inZone = 0;
  for (const it of items) {
    const n = bySeg.get(it.id) || 0;
    total += n;
    if (zoneIds.has(it.id)) inZone += n;
  }
  const perZone = zones.map((z) => z.members.reduce((a, m) => a + (bySeg.get(m.id) || 0), 0));
  const lenShare = evalKm > 0 ? zoneKm / evalKm : 0;
  const hitShare = total > 0 ? inZone / total : 0;
  return { evalKm, zoneKm, total, inZone, perZone, lenShare, hitShare, lift: lenShare > 0 && total > 0 ? hitShare / lenShare : null };
}

export default function ReviewResult({ route, period, review, zones, summary, selectedKey, onSelectZone, onEdit, onRetry, onAbout }) {
  const test = period.start >= "2026-01-01";
  return (
    <div className="briefing review">
      <section className="trip-line" aria-label="เส้นทางที่เลือก">
        <div className="tl-route">
          <span className="tl-names"><span className="pin pin-a" aria-hidden="true">A</span><span className="tl-name">{route.origin.name}</span></span>
          <span className="tl-names"><span className="pin pin-b" aria-hidden="true">B</span><span className="tl-name">{route.dest.name}</span></span>
          <span className="tl-meta">{fmtKm(route.distance)}</span>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onEdit}>แก้ไข</button>
      </section>

      <div className="rv-head">
        <span className="rv-kicker">ย้อนดูผล</span>
        <h2 className="answer-title">{period.label || "ช่วงที่เลือก"}</h2>
        <p className="answer-sub">{fmtThaiDate(period.start)} – {fmtThaiDate(period.end)}</p>
        <span className={"pill " + (test ? "pill-good" : "pill-info")}>{test ? "ข้อมูลปี 2569 ที่โมเดลไม่เคยเห็น" : "ปีที่ใช้ตรวจโมเดล (ไม่ได้ใช้ฝึก)"}</span>
      </div>

      {review.status === "loading" && <Progress text={review.text} frac={review.frac} />}
      {review.status === "error" && <ErrorBox title="ย้อนดูผลไม่สำเร็จ" text="ลองอีกครั้ง" technical={techText(review.failure)} onRetry={onRetry} />}
      {review.status === "done" && review.items.length === 0 && <p className="notice">เส้นทางนี้ไม่ผ่านทางหลวงที่มีข้อมูล</p>}

      {review.status === "done" && review.items.length > 0 && (
        <>
          <div className="rv-stats">
            <div className="rv-stat"><b>{summary.total}</b><span>เหตุที่เกิดจริงบนเส้นทาง</span></div>
            <div className="rv-stat rv-stat-hit"><b>{summary.inZone}</b><span>เกิดในจุดที่โมเดลชี้{summary.total > 0 ? " (" + pct(summary.hitShare) + ")" : ""}</span></div>
          </div>
          {summary.total === 0 ? (
            <p className="notice">ช่วงนี้ไม่มีเหตุที่ถูกบันทึกบนทางหลวงของเส้นทางนี้ ลองช่วงอื่นหรือเส้นทางที่ยาวขึ้น</p>
          ) : (
            <p className="rv-explain">
              จุดที่โมเดลชี้ยาวรวม <b>{Math.round(summary.zoneKm)} กม.</b> หรือ <b>{pct(summary.lenShare)}</b> ของทางหลวงที่ประเมินบนเส้นนี้
              {" "}แต่มีเหตุเกิดในจุดเหล่านั้น <b>{pct(summary.hitShare)}</b>
              {summary.lift && summary.lift >= 1.2 ? <> — มากกว่าการสุ่มเลือกถนนยาวเท่ากันราว <b>{summary.lift.toFixed(1)} เท่า</b></> : null}
            </p>
          )}

          <div className="rv-key">
            <span><b className="mk-num" style={{ background: LEVELS.red.hex }}>1</b>จุดที่โมเดลชี้</span>
            <span><i className="rv-dot" />จุดที่เกิดเหตุจริง</span>
          </div>

          {zones.length > 0 && (
            <section className="block" aria-labelledby="rvZones">
              <div className="block-head"><h3 id="rvZones">จุดที่โมเดลชี้</h3><span className="block-hint">เทียบกับเหตุที่เกิดจริงในช่วงนี้</span></div>
              <ol className="zone-list">
                {zones.map((z, i) => (
                  <li key={z.key} className={"zone-card" + (z.key === selectedKey ? " is-open" : "")}>
                    <button type="button" className="zone-head" onClick={() => onSelectZone(z.key === selectedKey ? null : z.key)}>
                      <span className="zone-badge" style={{ background: LEVELS[z.level].hex, color: LEVELS[z.level].ink }}>{z.n}</span>
                      <span className="zone-main">
                        <span className="zone-name">{z.road}</span>
                        <span className="zone-sub">{z.provinces.map(shortPlace).join("–")}</span>
                      </span>
                      <span className={"rv-count" + (summary.perZone[i] > 0 ? " is-hit" : "")}>{summary.perZone[i] > 0 ? "เกิดจริง " + summary.perZone[i] : "ไม่มีเหตุ"}</span>
                    </button>
                  </li>
                ))}
              </ol>
            </section>
          )}

          <p className="fine">
            จุดที่โมเดลชี้คิดจากค่าคาดรวมทั้งวัน ทุกวันในช่วงนี้ ด้วยกฎเดียวกับหน้าวางแผน · เหตุจริงนับเฉพาะที่ถูกบันทึกบนทางหลวงและจับคู่กับถนนได้
            {" "}(แสดงที่กึ่งกลางช่วงถนน ไม่ใช่พิกัดจริง) · <button type="button" className="link-btn link-inline" onClick={onAbout}>ข้อมูลนี้มาจากไหน</button>
          </p>
        </>
      )}
    </div>
  );
}
