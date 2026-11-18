// What the user sees after tapping a circle: a short popup on the map ("mostly …") and the full detail panel.
import { LEVELS, BLOCKS, BLOCK_LABEL, CATEGORY_TH } from "../config.js";
import { fmtKm, fmtPct, fmtSmall, fmtThaiDate, isNum, techText } from "../lib/util.js";
import { topValues, rainShare, peakBlock } from "../lib/forecast.js";
import { BUFFER_M } from "../lib/routeMatch.js";
import { Bars, Dot, ErrorBox, Loading } from "./common.jsx";

const PERIOD = "พ.ศ. 2564–2568";

export function SpotPopup({ spot, title, entry, onMore }) {
  const p = spot.primary;
  const lv = LEVELS[p.level];
  const h = entry && entry.status === "ok" ? entry.history : null;
  const n = h && isNum(h.n_selected_records) ? h.n_selected_records : 0;
  const rs = h ? rainShare(h) : null;
  const w = h ? topValues(h, "weather", 1)[0] : null;
  const types = h ? topValues(h, "accident_type", 2) : [];
  const cause = h ? topValues(h, "presumed_cause", 1)[0] : null;
  const pb = h ? peakBlock(h) : null;
  return (
    <div>
      <div className="pop-level"><Dot hex={p.hex} /><span>{lv.title}</span></div>
      <div className="pop-sub">{title} · คาดว่าผ่าน {fmtThaiDate(p.eta.date)} {p.eta.clock}</div>
      {spot.members.length > 1 && <div className="pop-sub">ตำแหน่งนี้มีข้อมูล {spot.members.length} ช่วงถนนซ้อนกัน (เช่น ฝั่งไป/ฝั่งกลับ) แสดงระดับสูงสุด</div>}
      {(!entry || entry.status === "loading") && <Loading text="กำลังดูว่าที่ผ่านมาส่วนใหญ่เกิดจากอะไร…" />}
      {entry && entry.status === "error" && <div className="pop-note">โหลดสถิติที่ผ่านมาไม่สำเร็จ</div>}
      {h && n === 0 && (
        <>
          <div className="pop-h">ยังไม่มีเหตุที่ถูกบันทึกบนช่วงนี้ ({PERIOD})</div>
          <div className="pop-note">ไม่ได้แปลว่าปลอดภัย — สีมาจากแบบจำลองที่ใช้ปัจจัยอื่นร่วมด้วย</div>
        </>
      )}
      {h && n > 0 && (
        <>
          <div className="pop-h">ที่ผ่านมาส่วนใหญ่เป็นแบบนี้ ({n} เหตุ, {PERIOD})</div>
          <ul className="pop-list">
            {rs !== null && rs > 0
              ? <li>เกิดตอนฝนตก {fmtPct(rs)} ของเหตุที่ทราบสภาพอากาศ</li>
              : w && <li>สภาพอากาศ: {w.value} {fmtPct(w.share)}</li>}
            {types.length > 0 && <li>ลักษณะเหตุ: {types.map((x) => x.value + " " + fmtPct(x.share)).join(", ")}</li>}
            {cause && <li>สาเหตุที่บันทึก: {cause.value} {fmtPct(cause.share)}</li>}
            {pb && <li>ช่วงเวลาที่เกิดบ่อย: {BLOCK_LABEL[pb[0]] || pb[0]} ({pb[1]} จาก {n})</li>}
          </ul>
          {n < 5 && <div className="pop-note">จำนวนเหตุยังน้อย ใช้เป็นข้อสังเกตเท่านั้น</div>}
          <div className="pop-note">เป็นข้อมูลที่บันทึกไว้ ไม่ใช่การพิสูจน์สาเหตุ และไม่ใช่สภาพอากาศวันนี้</div>
        </>
      )}
      <button type="button" className="pop-more" onClick={onMore}>ดูรายละเอียดทั้งหมด</button>
    </div>
  );
}

export function SpotDetail({ spot, title, entry, onRetryHistory }) {
  const p = spot.primary;
  const lv = LEVELS[p.level];
  const h = entry && entry.status === "ok" ? entry.history : null;
  const n = h && isNum(h.n_selected_records) ? h.n_selected_records : 0;
  const tb = (h && h.counts_by_time_block) || {};
  const years = Object.entries((h && h.counts_by_year) || {}).filter(([, v]) => isNum(v)).sort();
  const maxYear = Math.max(1, ...years.map(([, v]) => v));
  const sa = p.pred.source_availability;
  return (
    <div>
      <div className="level-banner" style={{ borderLeftColor: p.hex }}>
        <div><strong>{lv.title}</strong><span>{lv.desc}</span></div>
      </div>
      <dl className="kv">
        <dt>ถนน</dt><dd>{title}</dd>
        <dt>ระยะจากต้นทาง</dt><dd>ประมาณ {fmtKm(p.alongM)}</dd>
        <dt>คาดว่าผ่าน</dt><dd>{fmtThaiDate(p.eta.date)} {p.eta.clock} (ประเมินช่วง {BLOCK_LABEL[p.eta.block]})</dd>
        <dt>ค่าที่แบบจำลองคาด</dt><dd>{fmtSmall(p.pred.expected_recorded_count)} เหตุที่ถูกบันทึก ในช่วง 6 ชม. บนช่วงถนน ~{fmtSmall(p.pred.segment_km)} กม.</dd>
        {p.pred.research_scenario && (<><dt>สถานะ</dt><dd>คาดการณ์เชิงวิจัย (ยังไม่มีข้อมูลจริงให้เทียบ)</dd></>)}
      </dl>
      {spot.members.length > 1 && (
        <p className="help">ตำแหน่งเดียวกันมีอีก {spot.members.length - 1} ช่วงถนนซ้อนกัน: {spot.members.slice(1).map((m) => LEVELS[m.level].title).join(", ")}</p>
      )}

      {(!entry || entry.status === "loading") && <Loading text="กำลังโหลดสถิติเหตุที่ผ่านมาบนช่วงถนนนี้…" />}
      {entry && entry.status === "error" && (
        <ErrorBox title="โหลดสถิติที่ผ่านมาไม่สำเร็จ" text="ค่าประเมินด้านบนยังใช้ได้" onRetry={onRetryHistory} technical={techText(entry.failure)} />
      )}
      {h && (
        <>
          <div className="cause-block">
            <h3>ส่วนใหญ่เกิดจากอะไร (เหตุที่บันทึกบนช่วงนี้ {PERIOD})</h3>
            <p className="help">
              {n === 0 ? "ยังไม่มีเหตุที่ถูกบันทึกและเชื่อมกับช่วงถนนนี้ — ไม่ได้แปลว่าปลอดภัย" : "ทั้งหมด " + n + " เหตุ" + (n < 5 ? " (จำนวนน้อย ใช้เป็นข้อสังเกต)" : "")}
            </p>
          </div>
          {n > 0 && ["weather", "accident_type", "presumed_cause"].map((cat) => {
            const vals = topValues(h, cat, 5);
            if (!vals.length) return null;
            const c = h.categories[cat];
            return (
              <Bars key={cat} title={CATEGORY_TH[cat]}
                rows={vals.map((v) => ({ label: v.value, right: fmtPct(v.share), frac: v.share }))}
                note={c.unknown_records > 0 ? "ไม่ทราบ/ไม่ระบุ " + c.unknown_records + " เหตุ (ไม่นับในเปอร์เซ็นต์)" : null} />
            );
          })}
          {n > 0 && (
            <Bars title="ช่วงเวลาที่เกิดเหตุ"
              rows={BLOCKS.filter((k) => isNum(tb[k])).map((k) => ({ label: BLOCK_LABEL[k] + (k === p.eta.block ? " ← ช่วงที่คุณผ่าน" : ""), right: String(tb[k]), frac: tb[k] / n }))} />
          )}
          {n > 0 && years.length > 0 && (
            <Bars title="จำนวนตามปี" rows={years.map(([y, v]) => ({ label: "พ.ศ. " + (Number(y) + 543), right: String(v), frac: v / maxYear }))} />
          )}
          <p className="help">เป็นคุณลักษณะที่บันทึกไว้ในรายงานอุบัติเหตุ ไม่ใช่การพิสูจน์สาเหตุ สภาพอากาศคือขณะเกิดเหตุในอดีต ไม่ใช่สภาพอากาศวันนี้</p>
        </>
      )}

      <details className="more">
        <summary>ข้อมูลทางเทคนิคของการประเมิน</summary>
        <dl className="kv">
          <dt>รหัสช่วงถนน</dt><dd className="mono">{p.id}</dd>
          <dt>การจับคู่กับเส้นทาง</dt><dd>{fmtPct(p.match.fraction)} ของช่วงถนนอยู่ภายใน {BUFFER_M} ม. จากเส้นทาง</dd>
          <dt>ความหนาแน่นที่คาด</dt><dd>{fmtSmall(p.pred.density_per_km)} ต่อ กม.</dd>
          {p.pred.issue_time_local && (<><dt>ออกผล ณ</dt><dd>{String(p.pred.issue_time_local)}</dd></>)}
          {p.pred.model_version && (<><dt>รุ่นแบบจำลอง</dt><dd className="mono">{String(p.pred.model_version)}</dd></>)}
          {p.pred.routing_reason && (<><dt>ส่วนประกอบที่ใช้</dt><dd className="mono">{String(p.pred.component_used || "")} · {String(p.pred.routing_reason)}</dd></>)}
          {p.pred.colour_text && (<><dt>คำอธิบายสี (API)</dt><dd>{String(p.pred.colour_text)}</dd></>)}
          {sa && typeof sa === "object" && (<><dt>แหล่งข้อมูลประกอบ</dt><dd className="mono">{Object.entries(sa).map(([k, v]) => k + ": " + v).join(" · ")}</dd></>)}
        </dl>
      </details>
    </div>
  );
}
