// Trip briefing — answer first (verdict + how to read it), the numbered hotspots of this trip, the whole route
// against the national scale, then the departure-time comparison.
// Desktop: a zone expands in place. Phone: a zone opens as its own screen inside the sheet.
import { CONFIG, LEVELS, LEVEL_ORDER, BLOCK_LABEL, DEPART_OPTIONS, HOT_HEX } from "../config.js";
import { fmtKm, fmtDuration, fmtThaiDate, fmtPct, fmtSmall, epochToBkk, bkkToEpoch, techText } from "../lib/util.js";
import { topValues, rainShare, peakBlock, tipsFor } from "../lib/zones.js";
const pctTop = (rank) => Math.max(1, Math.round((1 - rank) * 100));
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
        <h2 className="verdict-title">ไม่มีช่วงที่สูงกว่าค่ากลางของประเทศเด่นเป็นพิเศษ</h2>
        <p className="verdict-sub">ในส่วนที่ประเมินได้ ({covered}% ของระยะทาง) ไม่มีช่วงระดับ “สูง” ขึ้นไป ขับขี่ด้วยความระมัดระวังตามปกติ — ไม่ได้แปลว่าปลอดภัย</p>
      </div>
    );
  }
  const worst = zones.reduce((a, b) => (b.maxDensity > a.maxDensity ? b : a));
  return (
    <div className="verdict">
      <p className="verdict-kicker">สรุปทริป · ประเมินได้ {covered}% ของระยะทาง</p>
      <h2 className="verdict-title">จุดที่ควรระวังที่สุด {zones.length} จุด</h2>
      <p className="verdict-sub">
        หมายเลข <span className="num-inline">1</span>–<span className="num-inline">{zones.length}</span> บนแผนที่ คือช่วงที่คาดว่าจะเกิดเหตุมากที่สุดของเส้นทางนี้ ในเวลาที่คุณจะผ่าน
        เรียงตามลำดับที่จะผ่าน{hidden > 0 ? " (ยังมีอีก " + hidden + " ช่วงที่ค่าใกล้เคียงกัน)" : ""} · หนักสุดคือ <strong>จุดที่ {worst.n}</strong> ผ่านราว {worst.eta.clock}
      </p>
      {covered < 98 && <p className="fine">อีก {100 - covered}% ของระยะทางเป็นถนนในเมือง/ถนนท้องถิ่น (เส้นสีเทาอ่อน) ที่ระบบยังไม่ประเมิน</p>}
    </div>
  );
}

function HowToRead() {
  return (
    <details className="howto">
      <summary>อ่านผลนี้ยังไง</summary>
      <ol>
        <li><b>ระบบแบ่งทางหลวงเป็นช่วงละราว 2 กม.</b> แล้วคาดว่าแต่ละช่วงจะมีอุบัติเหตุที่ถูกบันทึกมากแค่ไหน <b>ในช่วง 6 ชั่วโมงที่คุณจะผ่าน</b> จากสถิติปี 2564–2568 วันในสัปดาห์ เทศกาล และปริมาณรถ</li>
        <li><b>หมายเลขสีแดง</b> = ช่วงที่ค่าคาดสูงที่สุดของทริปนี้ (อยู่ใน 20% บนสุดของเส้นทาง และสูงกว่าค่ากลางของประเทศ) · เส้นสีน้ำเงิน = ทางหลวงที่ประเมินแล้ว ยิ่งเข้มยิ่งสูงเมื่อเทียบกับช่วงอื่นในทริปนี้ · เส้นสีเทาอ่อน = ถนนในเมือง/ถนนท้องถิ่นที่ยังไม่ประเมิน</li>
        <li><b>ระดับประเทศ</b> (สูงมาก / สูง / ปานกลาง / ต่ำกว่าครึ่งประเทศ) บอกว่าช่วงนั้นอยู่ตรงไหนเมื่อเทียบกับช่วงถนนทั้งประเทศ ทางหลวงสายหลักมักอยู่ระดับ “สูง” เกือบทั้งเส้นเพราะรถเยอะ จึงใช้หมายเลขเพื่อชี้จุดที่เด่นที่สุดในทริป</li>
        <li>เป็นการจัดอันดับเปรียบเทียบ ไม่ใช่โอกาสที่คุณจะเกิดอุบัติเหตุ และช่วงที่ไม่ถูกเลือกไม่ได้แปลว่าปลอดภัย</li>
      </ol>
    </details>
  );
}

// Whole evaluated route against the national scale (shares of LENGTH only — never a route probability).
function Overview({ counts }) {
  const total = LEVEL_ORDER.reduce((a, k) => a + (counts[k] || 0), 0);
  if (total <= 0) return null;
  const high = ((counts.red || 0) + (counts.orange || 0)) / total;
  return (
    <section className="block" aria-labelledby="ovTitle">
      <div className="block-head"><h3 id="ovTitle">ทั้งเส้นทาง เทียบทั้งประเทศ</h3><span className="block-hint">สัดส่วนระยะทางที่ประเมินได้</span></div>
      <div className="ov-bar" role="img" aria-label={LEVEL_ORDER.map((k) => LEVELS[k].label + " " + Math.round(((counts[k] || 0) / total) * 100) + "%").join(", ")}>
        {LEVEL_ORDER.map((k) => (counts[k] > 0 ? <span key={k} style={{ flexGrow: counts[k], background: LEVELS[k].hex }} /> : null))}
      </div>
      <ul className="ov-legend">
        {LEVEL_ORDER.map((k) => (
          <li key={k} title={LEVELS[k].nat}><i style={{ background: LEVELS[k].hex }} /><span className="ov-l">{LEVELS[k].label}</span><b>{Math.round(((counts[k] || 0) / total) * 100)}%</b></li>
        ))}
      </ul>
      {high >= 0.6 && <p className="fine">เส้นทางนี้ส่วนใหญ่เป็นทางหลวงสายหลักที่สูงกว่าค่ากลางของประเทศ ไม่ได้แปลว่าทุกช่วงหนักเท่ากัน ให้ดูหมายเลขเป็นหลัก</p>}
    </section>
  );
}

function Compare({ compare, when, onPickTime }) {
  if (compare.status === "idle") return null;
  const vals = DEPART_OPTIONS.map((o) => compare.results[o.time]).filter((r) => r && r.status === "ok").map((r) => r.red);
  const best = vals.length === DEPART_OPTIONS.length ? Math.min(...vals) : null;
  return (
    <section className="block" aria-labelledby="cmpTitle">
      <div className="block-head">
        <h3 id="cmpTitle">ถ้าออกเวลาอื่นล่ะ?</h3>
        <span className="block-hint"><i className="dot" style={{ background: LEVELS.red.hex }} />ระยะทางที่ระดับประเทศ “สูงมาก”</span>
      </div>
      <div className="cmp-grid">
        {DEPART_OPTIONS.map((o) => {
          const r = compare.results[o.time];
          const on = when.time === o.time;
          const isBest = best !== null && r && r.status === "ok" && Math.round(r.red) === Math.round(best);
          return (
            <button key={o.time} type="button" className={"cmp-btn" + (on ? " is-on" : "") + (isBest ? " is-best" : "")} aria-pressed={on}
              aria-label={"ออก " + o.time + (r && r.status === "ok" ? " ระดับสูงมาก " + Math.round(r.red) + " กิโลเมตร" : "")}
              onClick={() => onPickTime(o.time)}>
              <span className="cmp-time">{o.time}</span>
              <span className="cmp-part">{o.part}</span>
              <span className="cmp-counts" aria-hidden="true">
                {!r || r.status === "loading" ? <span className="spinner spinner-sm" /> : r.status === "error" ? "—" : (
                  <span><i className="dot" style={{ background: LEVELS.red.hex }} />{Math.round(r.red)} กม.</span>
                )}
              </span>
              {isBest && <span className="cmp-best">น้อยสุด</span>}
            </button>
          );
        })}
      </div>
      <p className="fine">นับเฉพาะระยะทางที่ประเมินได้ ไม่ได้รวมเป็นความเสี่ยงของทั้งเส้นทาง</p>
    </section>
  );
}

// Other routes with a similar driving time. Compared only on lengths/counts (never a route probability) and
// only when most of the alternative is evaluated — an unevaluated road must never look "better".
function Alternatives({ alts, main, altFocus, onFocusAlt, onUseAlt }) {
  if (!alts || alts.length === 0) return null;
  const mins = (s) => Math.round(s / 60);
  const verdict = (a) => {
    if (a.status !== "ok") return null;
    if (a.coverage < CONFIG.altMinCoverage) return { kind: "na", text: "ส่วนใหญ่เป็นถนนที่ยังไม่ประเมิน — เทียบไม่ได้" };
    const diff = main.redKm - a.redKm;
    if (diff >= Math.max(5, main.redKm * 0.2)) return { kind: "better", text: "ผ่านช่วงระดับ “สูงมาก” น้อยกว่า " + Math.round(diff) + " กม." };
    if (-diff >= Math.max(5, main.redKm * 0.2)) return { kind: "worse", text: "ผ่านช่วงระดับ “สูงมาก” มากกว่า " + Math.round(-diff) + " กม." };
    return { kind: "same", text: "ใกล้เคียงกับเส้นที่เลือก" };
  };
  return (
    <section className="block" aria-labelledby="altTitle">
      <div className="block-head"><h3 id="altTitle">เส้นทางอื่นที่เวลาใกล้กัน</h3><span className="block-hint">ออกเวลาเดียวกัน · เส้นประบนแผนที่</span></div>
      <div className="alt-list">
        <div className="alt-card is-main">
          <div className="alt-top"><b>เส้นที่เลือกอยู่</b><span>{fmtDuration(main.duration)} · {fmtKm(main.distance)}</span></div>
          <div className="alt-stats">
            <span><i className="dot" style={{ background: LEVELS.red.hex }} />สูงมาก {Math.round(main.redKm)} กม.</span>
            <span><b className="key-num">{main.points}</b> จุดควรระวัง</span>
            <span>ประเมินได้ {Math.round(main.coverage * 100)}%</span>
          </div>
        </div>
        {alts.map((a, i) => {
          const v = verdict(a);
          const dt = mins(a.duration - main.duration);
          const on = altFocus === a.id;
          return (
            <div key={a.id} className={"alt-card" + (on ? " is-on" : "") + (v ? " alt-" + v.kind : "")}>
              <button type="button" className="alt-pick" aria-pressed={on} onClick={() => onFocusAlt(on ? null : a.id)}>
                <div className="alt-top"><b>ทางเลือก {i + 1}</b><span>{fmtDuration(a.duration)} ({dt === 0 ? "เวลาเท่ากัน" : (dt > 0 ? "+" : "−") + Math.abs(dt) + " นาที"}) · {fmtKm(a.distance)}</span></div>
                {a.status === "loading" && <div className="alt-stats"><span className="spinner spinner-sm" /> กำลังประเมิน…</div>}
                {a.status === "error" && <div className="alt-stats">ประเมินเส้นนี้ไม่สำเร็จ</div>}
                {a.status === "ok" && (
                  <div className="alt-stats">
                    <span><i className="dot" style={{ background: LEVELS.red.hex }} />สูงมาก {Math.round(a.redKm)} กม.</span>
                    <span><b className="key-num">{a.points}</b> จุดควรระวัง</span>
                    <span>ประเมินได้ {Math.round(a.coverage * 100)}%</span>
                  </div>
                )}
                {v && <p className={"alt-verdict alt-v-" + v.kind}>{v.text}</p>}
              </button>
              {a.status === "ok" && <button type="button" className="btn btn-ghost btn-sm alt-use" onClick={() => onUseAlt(a.id)}>ใช้เส้นนี้</button>}
            </div>
          );
        })}
      </div>
      <p className="fine">เทียบเฉพาะระยะทางระดับ “สูงมาก” และจำนวนจุดควรระวัง ไม่ได้บอกว่าเส้นไหนปลอดภัยกว่า · เส้นที่ประเมินได้ไม่ถึง {Math.round(CONFIG.altMinCoverage * 100)}% จะไม่ถูกนับว่าดีกว่า</p>
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
        <span><strong>คุณจะผ่านราว {zone.eta.clock}</strong> <span className="muted">· ประเมินสำหรับช่วง {BLOCK_LABEL[zone.eta.block]}</span></span>
      </div>
      <div className="zd-why">
        <span>ค่าคาดสูงกว่า <b>{100 - pctTop(zone.routeRank)}%</b> ของช่วงอื่นในทริปนี้</span>
        <span>ระดับประเทศ: <b className={"lvl-" + zone.level}>{LEVELS[zone.level].label}</b> <span className="muted">({LEVELS[zone.level].nat})</span></span>
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
      <span className="zone-badge" style={{ background: HOT_HEX, color: "#fff" }}>{z.n}</span>
      <span className="zone-main">
        <span className="zone-name">{zoneTitle(z)}</span>
        <span className="zone-sub">กม. {kmRange(z)} ของเส้นทาง · ผ่านราว {z.eta.clock}</span>
        <span className="zone-sub">ระดับประเทศ <b className={"lvl-" + z.level}>{lv.label}</b></span>
      </span>
      <svg className="zone-chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={on ? "M6 15l6-6 6 6" : "M6 9l6 6 6-6"} /></svg>
    </button>
  );
}

export default function Briefing({ route, when, forecast, zones, hidden, counts, mode, ribbon, compare, alts, altFocus, onFocusAlt, onUseAlt, selectedKey, history, mobile, onEdit, onSelectZone, onPickTime, onRetry, onRetryHistory, onAbout }) {
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
        <span className="zone-tag zone-tag-hot"><span>{selected.n}</span>จุดที่ควรระวัง · ประเทศ: {lv.label}</span>
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
      {forecast.status === "done" && forecast.items.length > 0 && <HowToRead />}
      {forecast.status === "done" && (alts || []).length > 0 && (
        <Alternatives alts={alts} altFocus={altFocus} onFocusAlt={onFocusAlt} onUseAlt={onUseAlt}
          main={{ duration: route.duration, distance: route.distance, redKm: counts.red || 0, points: zones.length + hidden, coverage: ribbon.coverage }} />
      )}
      {forecast.status === "notReady" && (
        <ErrorBox title="ระบบประเมินยังไม่พร้อม" text="เส้นทางยังใช้ได้ตามปกติ เปิด backend แล้วลองอีกครั้ง" onRetry={onRetry} />
      )}
      {forecast.status === "error" && (
        <ErrorBox title="ประเมินความเสี่ยงไม่สำเร็จ" text="ไม่แสดงผลบางส่วนเพื่อไม่ให้เข้าใจผิด เส้นทางยังใช้ได้" technical={techText(forecast.failure)} onRetry={onRetry} />
      )}
      {forecast.status === "needWhen" && <p className="notice">เลือกวันที่ (1 ม.ค. 2567 – 31 ธ.ค. 2570) และเวลาออก เพื่อประเมินโซน</p>}
      {forecast.status === "done" && forecast.outOfRange > 0 && <p className="notice">{forecast.outOfRange} ช่วงถนนจะผ่านในวันที่แบบจำลองยังไม่รองรับ</p>}

      {mobile && forecast.status === "done" && forecast.items.length > 0 && (
        <RouteRibbon ribbon={ribbon} zones={zones} route={route} when={when} selectedKey={selectedKey} onSelectZone={onSelectZone} compact mode={mode} />
      )}

      {zones.length > 0 && (
        <section className="block" aria-labelledby="zoneTitle">
          <div className="block-head"><h3 id="zoneTitle">จุดที่ควรระวัง</h3><span className="block-hint">ตามลำดับที่จะผ่าน · แตะเพื่อดูว่าที่ผ่านมาเกิดเหตุแบบไหน</span></div>
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

      {forecast.status === "done" && forecast.items.length > 0 && <Overview counts={counts} />}
      {forecast.status === "done" && forecast.items.length > 0 && <Compare compare={compare} when={when} onPickTime={onPickTime} />}

      <p className="fine panel-fine">
        ระดับเทียบกับช่วงถนนอื่น ไม่ใช่โอกาสเกิดเหตุของคุณ ·{" "}
        <button type="button" className="link-btn link-inline" onClick={onAbout}>ข้อมูลนี้มาจากไหน</button>
      </p>
    </div>
  );
}
