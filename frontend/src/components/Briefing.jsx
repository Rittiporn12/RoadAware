// Trip briefing — answer first (verdict), then departure-time comparison, then numbered zones.
// Desktop: a zone expands in place. Phone: a zone opens as its own screen inside the sheet.
import { LEVELS, BLOCK_LABEL, DEPART_OPTIONS } from "../config.js";
import { fmtKm, fmtDuration, fmtThaiDate, fmtPct, fmtSmall, epochToBkk, bkkToEpoch, techText } from "../lib/util.js";
import { topValues, rainShare, peakBlock, tipsFor } from "../lib/zones.js";
import { BUFFER_M } from "../lib/routeMatch.js";
import { ErrorBox, Loading, Progress } from "./common.jsx";
import RouteRibbon from "./RouteRibbon.jsx";

const kmRange = (z) => {
  const a = Math.round(z.startM / 1000);
  return a + "–" + Math.max(Math.round(z.endM / 1000), a + 1);
};
export const zoneTitle = (z) => z.road + (z.provinces.length ? " · " + z.provinces.join("–") : "");

function Verdict({ forecast, zones, hidden, coverage }) {
  if (forecast.status === "loading") return <div className="verdict-loading"><Progress text={forecast.text} frac={forecast.frac} /></div>;
  if (forecast.status !== "done") return null;
  const covered = Math.round(coverage * 100);
  if (forecast.items.length === 0) {
    return (
      <div className="verdict">
        <p className="verdict-kicker">สรุปทริป</p>
        <h2 className="verdict-title">ยังไม่มีข้อมูลประเมินบนเส้นทางนี้</h2>
        <p className="verdict-sub">ตอนนี้ครอบคลุมทางหลวงกรมทางหลวงทั่วประเทศ ยังไม่รวมถนนชนบท ทางพิเศษ และถนนในเมือง ส่วนที่ไม่มีข้อมูลไม่ได้แปลว่าปลอดภัย</p>
      </div>
    );
  }
  if (zones.length === 0) {
    return (
      <div className="verdict">
        <p className="verdict-kicker">สรุปทริป</p>
        <h2 className="verdict-title">ไม่พบโซนที่ต้องระวังเป็นพิเศษ</h2>
        <p className="verdict-sub">ในส่วนที่ประเมินได้ ({covered}% ของระยะทาง) ขับขี่ด้วยความระมัดระวังตามปกติ</p>
      </div>
    );
  }
  const reds = zones.filter((z) => z.level === "red");
  const worst = (reds.length ? reds : zones).reduce((a, b) => (b.maxDensity > a.maxDensity ? b : a));
  return (
    <div className="verdict">
      <p className="verdict-kicker">สรุปทริป · ประเมินได้ {covered}% ของระยะทาง</p>
      <h2 className="verdict-title">มี {zones.length + hidden} โซนที่ควรระวัง</h2>
      <p className="verdict-sub">หนักที่สุด: <strong>โซน {worst.n}</strong> {zoneTitle(worst)} · ผ่านราว {worst.eta.clock}</p>
    </div>
  );
}

function Compare({ compare, when, onPickTime }) {
  if (compare.status === "idle") return null;
  return (
    <section className="block" aria-labelledby="cmpTitle">
      <div className="block-head">
        <h3 id="cmpTitle">ถ้าออกเวลาอื่นล่ะ?</h3>
        <span className="block-hint"><i className="dot" style={{ background: LEVELS.red.hex }} />ระวังมาก <i className="dot" style={{ background: LEVELS.orange.hex }} />ระวัง</span>
      </div>
      <div className="cmp-grid">
        {DEPART_OPTIONS.map((o) => {
          const r = compare.results[o.time];
          const on = when.time === o.time;
          return (
            <button key={o.time} type="button" className={"cmp-btn" + (on ? " is-on" : "")} aria-pressed={on}
              aria-label={"ออก " + o.time + (r && r.status === "ok" ? " ระวังมาก " + r.red + " ระวัง " + r.orange + " โซน" : "")}
              onClick={() => onPickTime(o.time)}>
              <span className="cmp-time">{o.time}</span>
              <span className="cmp-part">{o.part}</span>
              <span className="cmp-counts" aria-hidden="true">
                {!r || r.status === "loading" ? <span className="spinner spinner-sm" /> : r.status === "error" ? "—" : (
                  <>
                    <span><i className="dot" style={{ background: LEVELS.red.hex }} />{r.red}</span>
                    <span><i className="dot" style={{ background: LEVELS.orange.hex }} />{r.orange}</span>
                  </>
                )}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

function ZoneDetail({ zone, entry, onRetry }) {
  const hasData = entry && entry.status === "ok";
  const agg = hasData ? entry.agg : null;
  const n = agg ? agg.n : 0;
  const rain = agg ? rainShare(agg) : null;
  const types = agg ? topValues(agg, "accident_type", 3) : [];
  const cause = agg ? topValues(agg, "presumed_cause", 1)[0] : null;
  const weatherTop = agg ? topValues(agg, "weather", 1)[0] : null;
  const peak = agg ? peakBlock(agg) : null;
  const tips = agg ? tipsFor(agg) : [];
  return (
    <div className="zone-detail">
      <div className="zd-time">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
        <span><strong>คุณจะผ่านราว {zone.eta.clock}</strong> <span className="muted">· ระดับนี้สำหรับช่วง {BLOCK_LABEL[zone.eta.block]}</span></span>
      </div>

      {(!entry || entry.status === "loading") && <Loading text="กำลังดูว่าที่ผ่านมาเกิดเหตุแบบไหน…" />}
      {entry && entry.status === "error" && <ErrorBox title="โหลดสถิติที่ผ่านมาไม่สำเร็จ" text="ระดับของโซนยังใช้ได้" onRetry={onRetry} technical={techText(entry.failure)} />}
      {hasData && n === 0 && <p className="notice">ยังไม่มีเหตุที่ถูกบันทึกบนโซนนี้ (ปี 2564–2568) — ระดับมาจากปัจจัยอื่นของแบบจำลอง และไม่ได้แปลว่าปลอดภัย</p>}
      {hasData && n > 0 && (
        <>
          <h4 className="zd-h">ที่ผ่านมา ส่วนใหญ่เกิดเหตุแบบนี้</h4>
          <div className="stat-grid">
            {types[0] && <div className="stat"><b>{fmtPct(types[0].share)}</b><span>{types[0].value}</span></div>}
            {rain !== null && rain > 0
              ? <div className="stat"><b>{fmtPct(rain)}</b><span>เกิดตอนฝนตก</span></div>
              : weatherTop && <div className="stat"><b>{fmtPct(weatherTop.share)}</b><span>อากาศ{weatherTop.value}</span></div>}
            {peak && <div className="stat"><b>{peak.block.replace("-", "–")} น.</b><span>เกิดบ่อยที่สุด{peak.block === zone.eta.block ? " · ตรงกับช่วงที่คุณผ่าน" : ""}</span></div>}
          </div>
          {types.length > 1 && (
            <div className="bars" aria-label="ลักษณะเหตุที่บันทึก">
              {types.map((t) => (
                <div className="bar" key={t.value}>
                  <div className="bar-top"><span>{t.value}</span><span>{fmtPct(t.share)}</span></div>
                  <div className="bar-track"><span style={{ width: Math.round(t.share * 100) + "%" }} /></div>
                </div>
              ))}
            </div>
          )}
          {tips.length > 0 && (
            <div className="tips">
              <p className="tips-h">ก่อนถึงโซนนี้</p>
              <ol>{tips.map((t) => <li key={t}>{t}</li>)}</ol>
            </div>
          )}
          <p className="fine">
            จาก {n} เหตุที่บันทึกปี 2564–2568{cause ? " · สาเหตุที่บันทึกบ่อยสุด: " + cause.value : ""}{n < 5 ? " · จำนวนยังน้อย ใช้เป็นข้อสังเกต" : ""} · เป็นข้อมูลที่บันทึกไว้ ไม่ใช่การพิสูจน์สาเหตุ
          </p>
        </>
      )}

      <details className="tech">
        <summary>ข้อมูลทางเทคนิค</summary>
        <dl>
          <dt>ช่วงถนนในโซน</dt><dd>{zone.members.length} ช่วง (ราว 2 กม./ช่วง)</dd>
          <dt>ค่าคาดสูงสุด</dt><dd>{fmtSmall(Math.max(...zone.members.map((m) => m.pred.expected_recorded_count || 0)))} เหตุที่ถูกบันทึก / 6 ชม. / ช่วงถนน</dd>
          <dt>การจับคู่</dt><dd>≥50% ของช่วงถนนอยู่ภายใน {BUFFER_M} ม. จากเส้นทาง</dd>
          {zone.members[0].pred.model_version && (<><dt>รุ่นแบบจำลอง</dt><dd className="mono">{String(zone.members[0].pred.model_version)}</dd></>)}
          <dt>รหัสช่วงถนน</dt><dd className="mono">{zone.members.map((m) => m.id).join(", ")}</dd>
        </dl>
      </details>
    </div>
  );
}

function ZoneHead({ z, on, onClick }) {
  const lv = LEVELS[z.level];
  return (
    <button type="button" className="zone-head" aria-expanded={on} onClick={onClick}>
      <span className="zone-badge" style={{ background: lv.hex, color: lv.ink }}>{z.n}</span>
      <span className="zone-main">
        <span className="zone-name">{zoneTitle(z)}</span>
        <span className="zone-sub">กม. {kmRange(z)} · ผ่านราว {z.eta.clock}</span>
      </span>
      <span className={"zone-pill zone-pill-" + z.level}>{lv.label}</span>
    </button>
  );
}

export default function Briefing({ route, when, forecast, zones, hidden, ribbon, compare, selectedKey, history, mobile, onEdit, onSelectZone, onPickTime, onRetry, onRetryHistory, onAbout }) {
  const depart = bkkToEpoch(when.date, when.time);
  const arrive = epochToBkk(depart + route.duration * 1000);
  const selected = zones.find((z) => z.key === selectedKey) || null;

  // Phone: a selected zone is its own screen.
  if (mobile && selected) {
    const lv = LEVELS[selected.level];
    return (
      <div className="zone-screen">
        <button type="button" className="back-link" onClick={() => onSelectZone(null)}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
          กลับไปสรุปทริป
        </button>
        <span className={"zone-tag zone-tag-" + selected.level}><span>{selected.n}</span>{lv.label}</span>
        <h2 className="zs-title">{zoneTitle(selected)}</h2>
        <p className="zs-sub">กม. {kmRange(selected)} ของเส้นทาง · ยาวราว {fmtKm(selected.lengthM)}</p>
        <ZoneDetail zone={selected} entry={history[selected.key]} onRetry={() => onRetryHistory(selected)} />
      </div>
    );
  }

  return (
    <div className="briefing">
      <section className="trip-card" aria-label="เส้นทางที่เลือก">
        <div className="tc-ends">
          <div><span className="pin pin-a" aria-hidden="true">A</span><span className="tc-name">{route.origin.name}</span></div>
          <div><span className="pin pin-b" aria-hidden="true">B</span><span className="tc-name">{route.dest.name}</span></div>
        </div>
        <div className="tc-meta">
          <span>{fmtThaiDate(when.date)} · ออก {when.time} · ถึงราว {arrive.clock}<br />{fmtKm(route.distance)} · {fmtDuration(route.duration)}</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onEdit}>แก้ไข</button>
        </div>
        {route.snapNote && <p className="fine">{route.snapNote}</p>}
      </section>

      <Verdict forecast={forecast} zones={zones} hidden={hidden} coverage={ribbon.coverage} />
      {forecast.status === "notReady" && (
        <ErrorBox title="ระบบประเมินยังไม่พร้อม" text="เส้นทางยังใช้ได้ตามปกติ เปิด backend แล้วลองอีกครั้ง" onRetry={onRetry} />
      )}
      {forecast.status === "error" && (
        <ErrorBox title="ประเมินความเสี่ยงไม่สำเร็จ" text="ไม่แสดงผลบางส่วนเพื่อไม่ให้เข้าใจผิด เส้นทางยังใช้ได้" technical={techText(forecast.failure)} onRetry={onRetry} />
      )}
      {forecast.status === "needWhen" && <p className="notice">เลือกวันที่ (1 ม.ค. 2567 – 31 ธ.ค. 2570) และเวลาออก เพื่อประเมินโซน</p>}
      {forecast.status === "done" && forecast.outOfRange > 0 && <p className="notice">{forecast.outOfRange} ช่วงถนนจะผ่านในวันที่แบบจำลองยังไม่รองรับ</p>}

      {mobile && forecast.status === "done" && forecast.items.length > 0 && (
        <RouteRibbon ribbon={ribbon} zones={zones} route={route} when={when} selectedKey={selectedKey} onSelectZone={onSelectZone} compact />
      )}

      {zones.length > 0 && (
        <section className="block" aria-labelledby="zoneTitle">
          <div className="block-head"><h3 id="zoneTitle">โซนที่ควรระวัง</h3><span className="block-hint">ตามลำดับที่จะผ่าน</span></div>
          <ol className="zone-list">
            {zones.map((z) => {
              const on = !mobile && z.key === selectedKey;
              return (
                <li key={z.key} id={"zone-" + z.n} className={"zone-card" + (on ? " is-open zone-open-" + z.level : "")}>
                  <ZoneHead z={z} on={on} onClick={() => onSelectZone(on ? null : z.key)} />
                  {on && <ZoneDetail zone={z} entry={history[z.key]} onRetry={() => onRetryHistory(z)} />}
                </li>
              );
            })}
          </ol>
        </section>
      )}

      {forecast.status === "done" && forecast.items.length > 0 && <Compare compare={compare} when={when} onPickTime={onPickTime} />}

      <p className="fine panel-fine">
        ระดับเทียบกับช่วงถนนอื่น ไม่ใช่โอกาสเกิดเหตุของคุณ ·{" "}
        <button type="button" className="link-btn link-inline" onClick={onAbout}>ข้อมูลนี้มาจากไหน</button>
      </p>
    </div>
  );
}
