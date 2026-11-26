// Trip briefing, designed to be read in a few seconds:
//   1. the answer   — how many points to watch, the worst one, and the main action (start the trip)
//   2. suggestions  — only when they really help (a calmer route of similar time, a better departure time)
//   3. the points   — a short list in the order you reach them; tap one for what usually happens there
//   4. more detail  — national comparison, all departure times, all routes, how to read: folded away
// Desktop: a point expands in place. Phone: a point opens as its own screen inside the sheet.
import { CONFIG, LEVELS, BLOCK_LABEL, DEPART_OPTIONS, HOT_HEX } from "../config.js";
import { fmtKm, fmtDuration, fmtThaiDate, fmtPct, fmtSmall, epochToBkk, bkkToEpoch, techText } from "../lib/util.js";
import { topValues, rainShare, peakBlock, tipsFor } from "../lib/zones.js";
import { BUFFER_M } from "../lib/routeMatch.js";
import { ErrorBox, Loading, Progress } from "./common.jsx";

const kmRange = (z) => {
  const a = Math.round(z.startM / 1000);
  return a + "–" + Math.max(Math.round(z.endM / 1000), a + 1);
};
export const zoneTitle = (z) => z.road + (z.provinces.length ? " · " + z.provinces.join("–") : "");
const shortPlace = (s) => String(s || "").replace(/^จังหวัด/, "");

// ---------------------------------------------------------------- 1. the answer
function Verdict({ forecast, zones, coverage }) {
  if (forecast.status === "loading") return <div className="verdict-loading"><Progress text={forecast.text} frac={forecast.frac} /></div>;
  if (forecast.status !== "done") return null;
  const covered = Math.round(coverage * 100);
  if (forecast.items.length === 0) {
    return (
      <div className="answer answer-none">
        <div>
          <h2 className="answer-title">ยังประเมินเส้นทางนี้ไม่ได้</h2>
          <p className="answer-sub">ตอนนี้ระบบประเมินเฉพาะทางหลวงของกรมทางหลวง เส้นทางนี้ส่วนใหญ่เป็นถนนอื่น</p>
        </div>
      </div>
    );
  }
  if (zones.length === 0) {
    return (
      <div className="answer answer-ok">
        <span className="answer-count answer-count-ok" aria-hidden="true">✓</span>
        <div>
          <h2 className="answer-title">ไม่มีจุดที่เด่นเป็นพิเศษ</h2>
          <p className="answer-sub">ขับขี่ด้วยความระมัดระวังตามปกติ</p>
        </div>
      </div>
    );
  }
  const worst = zones.reduce((a, b) => (b.maxDensity > a.maxDensity ? b : a));
  const nRed = zones.filter((z) => z.level === "red").length;
  const nOrange = zones.length - nRed;
  return (
    <div className="answer">
      <span className={"answer-count" + (nRed ? "" : " answer-count-orange")} aria-hidden="true">{zones.length}</span>
      <div>
        <h2 className="answer-title">จุดที่ควรระวังบนเส้นทางนี้</h2>
        <p className="answer-sub">
          หนักสุดคือ <b>จุดที่ {worst.n}</b> · {worst.road}{worst.provinces.length ? " " + shortPlace(worst.provinces[0]) : ""} · ผ่านราว <b className="nowrap">{worst.eta.clock}</b>
        </p>
        <p className="answer-levels">
          {nRed > 0 && <span><i style={{ background: LEVELS.red.hex }} />สูงมาก {nRed} จุด</span>}
          {nOrange > 0 && <span><i style={{ background: LEVELS.orange.hex }} />สูง {nOrange} จุด</span>}
        </p>
        {covered < 80 && <p className="answer-note">ประเมินได้ {covered}% ของเส้นทาง ส่วนที่เหลือเป็นถนนที่ยังไม่มีข้อมูล</p>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- 2. suggestions (shown only when they help)
function altVerdict(a, main) {
  if (a.status !== "ok" || a.coverage < CONFIG.altMinCoverage) return null;
  const diff = main.redKm - a.redKm;
  if (diff >= Math.max(5, main.redKm * 0.2)) return { kind: "better", diff };
  if (-diff >= Math.max(5, main.redKm * 0.2)) return { kind: "worse", diff };
  return { kind: "same", diff };
}

function Suggestions({ alts, main, compare, when, altFocus, onFocusAlt, onUseAlt, onPickTime }) {
  const tips = [];
  // a calmer route of similar time
  (alts || []).forEach((a) => {
    const v = altVerdict(a, main);
    if (!v || v.kind !== "better" || tips.some((t) => t.kind === "route")) return;
    const dt = Math.round((a.duration - main.duration) / 60);
    const on = altFocus === a.id;
    tips.push({
      kind: "route", key: a.id,
      title: "มีเส้นทางที่ผ่านช่วงเสี่ยงน้อยกว่า",
      text: <><span className="nowrap">{dt === 0 ? "ใช้เวลาเท่ากัน" : dt > 0 ? "ช้ากว่า " + dt + "\u00a0นาที" : "เร็วกว่า " + -dt + "\u00a0นาที"}</span> · <span className="nowrap">ช่วงเสี่ยงสูงมากน้อยลง {Math.round(v.diff)}{"\u00a0"}กม.</span></>,
      actions: (
        <>
          <button type="button" className="btn btn-ghost btn-sm" aria-pressed={on} onClick={() => onFocusAlt(on ? null : a.id)}>{on ? "ซ่อนบนแผนที่" : "ดูบนแผนที่"}</button>
          <button type="button" className="btn btn-sm btn-dark" onClick={() => onUseAlt(a.id)}>ใช้เส้นนี้</button>
        </>
      ),
    });
  });
  // other routes exist but none is clearly calmer: still say so, so the person knows they were checked
  const list = alts || [];
  if (list.length && !tips.some((t) => t.kind === "route")) {
    const loading = list.some((a) => a.status === "loading");
    const vs = list.map((a) => altVerdict(a, main)).filter(Boolean);
    const first = list.find((a) => a.status === "ok") || list[0];
    const on = altFocus === first.id;
    const dt = Math.round((first.duration - main.duration) / 60);
    tips.push({
      kind: "route-info", key: "route-info",
      title: loading ? "กำลังเทียบเส้นทางอื่น…" : "เส้นทางอื่นที่เวลาใกล้กัน " + list.length + "\u00a0เส้น",
      text: loading ? "เส้นทางอื่นที่ใช้เวลาไม่ต่างกันมาก กำลังประเมินอยู่"
        : !vs.length ? <span className="nowrap">{dt === 0 ? "เวลาเท่ากัน" : dt > 0 ? "ช้ากว่า " + dt + "\u00a0นาที" : "เร็วกว่า " + -dt + "\u00a0นาที"}</span>
        : vs.some((v) => v.kind === "worse") && !vs.some((v) => v.kind === "same") ? "ผ่านช่วงเสี่ยงมากกว่าเส้นที่เลือก — เส้นที่เลือกดีกว่าแล้ว"
        : <>ผ่านช่วงเสี่ยงพอ ๆ กับเส้นที่เลือก · <span className="nowrap">{dt === 0 ? "เวลาเท่ากัน" : dt > 0 ? "ช้ากว่า " + dt + "\u00a0นาที" : "เร็วกว่า " + -dt + "\u00a0นาที"}</span></>,
      actions: loading ? null : <button type="button" className="btn btn-ghost btn-sm" aria-pressed={on} onClick={() => onFocusAlt(on ? null : first.id)}>{on ? "ซ่อนบนแผนที่" : "ดูบนแผนที่"}</button>,
    });
  }
  // a better departure time (same route, same date)
  const ok = DEPART_OPTIONS.map((o) => ({ ...o, r: compare.results[o.time] })).filter((o) => o.r && o.r.status === "ok");
  if (ok.length === DEPART_OPTIONS.length) {
    const best = ok.reduce((a, b) => (b.r.red < a.r.red ? b : a));
    const diff = main.redKm - best.r.red;
    if (best.time !== when.time && diff >= Math.max(5, main.redKm * 0.25)) {
      tips.push({
        kind: "time", key: "time",
        title: "ออก " + best.time + "\u00a0น. จะเสี่ยงน้อยกว่า",
        text: <><span className="nowrap">ช่วงเสี่ยงสูงมากน้อยลง {Math.round(diff)}{"\u00a0"}กม.</span> <span className="nowrap">(เทียบกับออก {when.time}{"\u00a0"}น.)</span></>,
        actions: <button type="button" className="btn btn-sm btn-dark" onClick={() => onPickTime(best.time)}>เปลี่ยนเป็น {best.time}{"\u00a0"}น.</button>,
      });
    }
  }
  if (!tips.length) return list.length ? null : <p className="fine">ไม่พบเส้นทางอื่นที่ใช้เวลาใกล้กัน (ช้ากว่าไม่เกิน {Math.round((CONFIG.altMaxTimeRatio - 1) * 100)}%)</p>;
  return (
    <section className="tips-list" aria-label="คำแนะนำ">
      {!list.length && <p className="fine">ไม่พบเส้นทางอื่นที่ใช้เวลาใกล้กัน</p>}
      {tips.map((t) => (
        <div key={t.key} className={"tip-card tip-" + t.kind}>
          <span className="tip-icon" aria-hidden="true">
            {t.kind !== "time"
              ? <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="19" r="2" /><circle cx="18" cy="5" r="2" /><path d="M8 19h7a3.5 3.5 0 0 0 0-7H9a3.5 3.5 0 0 1 0-7h7" /></svg>
              : <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>}
          </span>
          <div className="tip-body">
            <p className="tip-title">{t.title}</p>
            <p className="tip-text">{t.text}</p>
            {t.actions && <div className="tip-actions">{t.actions}</div>}
          </div>
        </div>
      ))}
    </section>
  );
}

// ---------------------------------------------------------------- 3. the points
function ZoneDetail({ zone, entry, onRetry }) {
  const hasData = entry && entry.status === "ok";
  const agg = hasData ? entry.agg : null;
  const n = agg ? agg.n : 0;
  const rain = agg ? rainShare(agg) : null;
  const type = agg ? topValues(agg, "accident_type", 1)[0] : null;
  const peak = agg ? peakBlock(agg) : null;
  const tips = agg ? tipsFor(agg).slice(0, 2) : [];
  const lv = LEVELS[zone.level];
  return (
    <div className="zone-detail">
      <p className="zd-line">ผ่านราว <b>{zone.eta.clock}</b> · ยาวราว {fmtKm(zone.lengthM)} · กม. {kmRange(zone)} ของเส้นทาง</p>
      <p className="zd-line">เทียบทั้งประเทศ: <b className={"lvl-" + zone.level}>{lv.label}</b> <span className="muted">({lv.nat})</span></p>

      {(!entry || entry.status === "loading") && <Loading text="กำลังดูว่าที่ผ่านมาเกิดเหตุแบบไหน…" />}
      {entry && entry.status === "error" && <ErrorBox title="โหลดสถิติที่ผ่านมาไม่สำเร็จ" text="ข้อมูลจุดนี้ยังใช้ได้" onRetry={onRetry} technical={techText(entry.failure)} />}
      {hasData && n === 0 && <p className="notice">ยังไม่มีเหตุที่ถูกบันทึกตรงนี้ในปี 2564–2568 ระดับมาจากปัจจัยอื่นของแบบจำลอง</p>}
      {hasData && n > 0 && (
        <>
          <p className="zd-h">ที่ผ่านมาส่วนใหญ่</p>
          <div className="stat-grid">
            {type && <div className="stat"><b>{fmtPct(type.share)}</b><span>{type.value}</span></div>}
            {rain !== null && rain > 0 && <div className="stat"><b>{fmtPct(rain)}</b><span>เกิดตอนฝนตก</span></div>}
            {peak && <div className="stat"><b>{peak.block.replace("-", "–")} น.</b><span>ช่วงที่เกิดบ่อย{peak.block === zone.eta.block ? " · ตรงกับที่คุณผ่าน" : ""}</span></div>}
          </div>
          {tips.length > 0 && (
            <div className="tips">
              <p className="tips-h">ก่อนถึงจุดนี้</p>
              <ul>{tips.map((t) => <li key={t}>{t}</li>)}</ul>
            </div>
          )}
          <p className="fine">จาก {n} เหตุที่บันทึกไว้ปี 2564–2568{n < 5 ? " (ยังน้อย ใช้เป็นข้อสังเกต)" : ""}</p>
        </>
      )}

      <details className="tech">
        <summary>ข้อมูลทางเทคนิค</summary>
        <dl>
          <dt>ช่วงเวลาที่ประเมิน</dt><dd>{BLOCK_LABEL[zone.eta.block]}</dd>
          <dt>ช่วงถนนในจุดนี้</dt><dd>{zone.members.length} ช่วง (ราว 2 กม./ช่วง)</dd>
          <dt>ค่าคาดสูงสุด</dt><dd>{fmtSmall(Math.max(...zone.members.map((m) => m.pred.expected_recorded_count || 0)))} เหตุที่ถูกบันทึก / 6 ชม. / ช่วงถนน</dd>
          <dt>การจับคู่</dt><dd>≥50% ของช่วงถนนอยู่ภายใน {BUFFER_M} ม. จากเส้นทาง</dd>
          {zone.members[0].pred.model_version && (<><dt>รุ่นแบบจำลอง</dt><dd className="mono">{String(zone.members[0].pred.model_version)}</dd></>)}
          <dt>รหัสช่วงถนน</dt><dd className="mono">{zone.members.map((m) => m.id).join(", ")}</dd>
        </dl>
      </details>
    </div>
  );
}

function ZoneRow({ z, on, onClick, mobile }) {
  return (
    <button type="button" className="zone-head" aria-expanded={mobile ? undefined : on} onClick={onClick}>
      <span className="zone-badge" style={{ background: LEVELS[z.level].hex, color: LEVELS[z.level].ink }}>{z.n}</span>
      <span className="zone-main">
        <span className="zone-name">{z.road}</span>
        <span className="zone-sub">{z.provinces.map(shortPlace).join("–") || " "}</span>
      </span>
      <span className="zone-time">{z.eta.clock}</span>
      <svg className="zone-chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d={mobile ? "M9 6l6 6-6 6" : on ? "M6 15l6-6 6 6" : "M6 9l6 6 6-6"} />
      </svg>
    </button>
  );
}

// ---------------------------------------------------------------- 4. more detail (folded)
function TimeCompare({ compare, when, onPickTime }) {
  if (compare.status === "idle") return null;
  const vals = DEPART_OPTIONS.map((o) => compare.results[o.time]).filter((r) => r && r.status === "ok").map((r) => r.red);
  const best = vals.length === DEPART_OPTIONS.length ? Math.min(...vals) : null;
  return (
    <div className="more-sec">
      <div className="more-head"><h4>ถ้าออกเวลาอื่น</h4><span className="block-hint">ระยะทางช่วงเสี่ยงสูงมาก</span></div>
      <div className="cmp-grid">
        {DEPART_OPTIONS.map((o) => {
          const r = compare.results[o.time];
          const on = when.time === o.time;
          const isBest = best !== null && r && r.status === "ok" && Math.round(r.red) === Math.round(best);
          return (
            <button key={o.time} type="button" className={"cmp-btn" + (on ? " is-on" : "") + (isBest ? " is-best" : "")} aria-pressed={on}
              aria-label={"ออก " + o.time + (r && r.status === "ok" ? " ช่วงเสี่ยงสูงมาก " + Math.round(r.red) + " กิโลเมตร" : "")}
              onClick={() => onPickTime(o.time)}>
              <span className="cmp-time">{o.time}</span>
              <span className="cmp-part">{o.part}</span>
              <span className="cmp-counts" aria-hidden="true">
                {!r || r.status === "loading" ? <span className="spinner spinner-sm" /> : r.status === "error" ? "—" : Math.round(r.red) + " กม."}
              </span>
              {isBest && <span className="cmp-best">น้อยสุด</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function AllRoutes({ alts, main, altFocus, onFocusAlt, onUseAlt }) {
  if (!alts || alts.length === 0) return null;
  const rows = [{ ...main, id: null, name: "เส้นที่เลือก", status: "ok", isMain: true }, ...alts.map((a, i) => ({ ...a, name: "ทางเลือก " + (i + 1) }))];
  return (
    <div className="more-sec">
      <div className="more-head"><h4>เส้นทางอื่นที่เวลาใกล้กัน</h4></div>
      <table className="route-table">
        <thead><tr><th>เส้นทาง</th><th>เวลา</th><th>ช่วงเสี่ยงสูงมาก</th><th><span className="visually-hidden">การทำงาน</span></th></tr></thead>
        <tbody>
          {rows.map((r) => {
            const v = r.isMain ? null : altVerdict(r, main);
            const na = !r.isMain && r.status === "ok" && r.coverage < CONFIG.altMinCoverage;
            const on = !r.isMain && altFocus === r.id;
            return (
              <tr key={r.id || "main"} className={(r.isMain ? "is-main" : "") + (on ? " is-on" : "")}>
                <td>{r.name}{v && v.kind === "better" && <span className="pill pill-good">น้อยกว่า</span>}</td>
                <td>{fmtDuration(r.duration)}</td>
                <td>{r.status === "loading" ? <span className="spinner spinner-sm" /> : r.status === "error" ? "—" : na ? "ข้อมูลไม่พอ" : Math.round(r.redKm) + " กม."}</td>
                <td className="rt-act">
                  {!r.isMain && r.status === "ok" && (
                    <>
                      <button type="button" className="link-btn" onClick={() => onFocusAlt(on ? null : r.id)}>{on ? "ซ่อน" : "ดู"}</button>
                      <button type="button" className="link-btn" onClick={() => onUseAlt(r.id)}>ใช้</button>
                    </>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function HowToRead() {
  return (
    <div className="more-sec">
      <div className="more-head"><h4>อ่านผลนี้ยังไง</h4></div>
      <ul className="howto-list">
        <li><b>หมายเลข</b> คือช่วงที่คาดว่าจะเกิดอุบัติเหตุมากที่สุดของทริปนี้ ในเวลาที่คุณจะผ่าน · <b>สีแดง</b> = ระดับสูงมาก (5% บนสุดของประเทศ) · <b>สีส้ม</b> = ระดับสูง</li>
        <li><b>เส้นสีน้ำเงิน</b> คือทางหลวงที่ประเมินแล้ว · <b>เส้นสีเทา</b> คือถนนที่ยังไม่มีข้อมูล (ไม่ได้แปลว่าปลอดภัย)</li>
        <li>คาดจากสถิติอุบัติเหตุปี 2564–2568 วัน เวลา เทศกาล และลักษณะถนน โดยแบ่งทางหลวงเป็นช่วงละราว 2 กม.</li>
        <li>เป็นการเปรียบเทียบระหว่างช่วงถนน ไม่ใช่โอกาสที่คุณจะเกิดอุบัติเหตุ</li>
      </ul>
    </div>
  );
}

export default function Briefing({ route, when, forecast, zones, hidden, counts, mode, onMode, ribbon, compare, alts, altFocus, onFocusAlt, onUseAlt, onDrive, selectedKey, history, mobile, onEdit, onSelectZone, onPickTime, onRetry, onRetryHistory, onAbout }) {
  const depart = bkkToEpoch(when.date, when.time);
  const arrive = epochToBkk(depart + route.duration * 1000);
  const selected = zones.find((z) => z.key === selectedKey) || null;
  const main = { duration: route.duration, distance: route.distance, redKm: counts.red || 0, points: zones.length + hidden, coverage: ribbon.coverage };
  const done = forecast.status === "done" && forecast.items.length > 0;

  // Phone: a selected point is its own screen.
  if (mobile && selected) {
    return (
      <div className="zone-screen">
        <button type="button" className="back-link" onClick={() => onSelectZone(null)}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
          กลับไปสรุปทริป
        </button>
        <div className="zs-head">
          <span className="zone-badge zone-badge-lg" style={{ background: LEVELS[selected.level].hex, color: LEVELS[selected.level].ink }}>{selected.n}</span>
          <div>
            <h2 className="zs-title">{selected.road}</h2>
            <p className="zs-sub">{selected.provinces.map(shortPlace).join("–")}</p>
          </div>
        </div>
        <ZoneDetail zone={selected} entry={history[selected.key]} onRetry={() => onRetryHistory(selected)} />
      </div>
    );
  }

  return (
    <div className="briefing">
      <section className="trip-line" aria-label="เส้นทางที่เลือก">
        <div className="tl-route">
          <span className="tl-names"><span className="pin pin-a" aria-hidden="true">A</span><span className="tl-name">{route.origin.name}</span></span>
          <span className="tl-names"><span className="pin pin-b" aria-hidden="true">B</span><span className="tl-name">{route.dest.name}</span></span>
          <span className="tl-meta">{fmtThaiDate(when.date)} · ออก {when.time} ถึงราว {arrive.clock} · {fmtKm(route.distance)}</span>
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onEdit}>แก้ไข</button>
      </section>
      {route.snapNote && <p className="fine">{route.snapNote}</p>}

      <Verdict forecast={forecast} zones={zones} coverage={ribbon.coverage} />

      {forecast.status === "done" && onDrive && (
        <button type="button" className="btn btn-primary drive-go" onClick={onDrive}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2l7 19-7-4-7 4z" /></svg>
          เริ่มเดินทาง · เตือนด้วยเสียง
        </button>
      )}

      {forecast.status === "notReady" && <ErrorBox title="ระบบประเมินยังไม่พร้อม" text="เส้นทางยังใช้ได้ตามปกติ เปิด backend แล้วลองอีกครั้ง" onRetry={onRetry} />}
      {forecast.status === "error" && <ErrorBox title="ประเมินไม่สำเร็จ" text="เส้นทางยังใช้ได้ ลองใหม่อีกครั้ง" technical={techText(forecast.failure)} onRetry={onRetry} />}
      {forecast.status === "needWhen" && <p className="notice">เลือกวันที่ตั้งแต่วันนี้ถึง 31 ธ.ค. 2570 และเวลาออก เพื่อประเมิน</p>}
      {forecast.status === "done" && forecast.outOfRange > 0 && <p className="notice">{forecast.outOfRange} ช่วงถนนจะผ่านในวันที่แบบจำลองยังไม่รองรับ</p>}

      {done && <Suggestions alts={alts} main={main} compare={compare} when={when} altFocus={altFocus} onFocusAlt={onFocusAlt} onUseAlt={onUseAlt} onPickTime={onPickTime} />}

      {zones.length > 0 && (
        <section className="block" aria-labelledby="zoneTitle">
          <div className="block-head"><h3 id="zoneTitle">จุดที่ควรระวัง</h3><span className="block-hint">เรียงตามที่จะผ่าน · แตะเพื่อดูรายละเอียด</span></div>
          <ol className="zone-list">
            {zones.map((z) => {
              const on = !mobile && z.key === selectedKey;
              return (
                <li key={z.key} id={"zone-" + z.n} className={"zone-card" + (on ? " is-open" : "")}>
                  <ZoneRow z={z} on={on} mobile={mobile} onClick={() => onSelectZone(on ? null : z.key)} />
                  {on && <ZoneDetail zone={z} entry={history[z.key]} onRetry={() => onRetryHistory(z)} />}
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {done && (
        <details className="more">
          <summary>
            <span className="more-title">ข้อมูลเพิ่มเติม</span>
            <span className="more-hint">เวลาออกอื่น{(alts || []).length ? " · เส้นทางอื่น" : ""} · วิธีอ่านผล</span>
          </summary>
          <div className="more-body">
            <TimeCompare compare={compare} when={when} onPickTime={onPickTime} />
            <AllRoutes alts={alts} main={main} altFocus={altFocus} onFocusAlt={onFocusAlt} onUseAlt={onUseAlt} />
            <HowToRead />
          </div>
        </details>
      )}

      <p className="fine panel-fine">
        เป็นการเปรียบเทียบจากสถิติ ไม่ใช่การรับประกันความปลอดภัย ·{" "}
        <button type="button" className="link-btn link-inline" onClick={onAbout}>ข้อมูลนี้มาจากไหน</button>
      </p>
    </div>
  );
}
