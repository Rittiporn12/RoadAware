// โมเดล — what the model predicts, how it was chosen, and how it did on data it never saw.
// Every number comes from the project's own reports (public/data/model-v1.json, built by
// backend/scripts/build_model_page_data.py). Unit switch (รายวัน / ราย 6 ชม.) changes every chart.
import { useEffect, useMemo, useState } from "react";
import SiteNav from "./SiteNav.jsx";

const ENV = (import.meta.env) || {};
const DATA_URL = (ENV.BASE_URL || "./") + "data/model-v1.json";
const CHAMP = "hgb_poisson_fixed::routed_context";
const BASE = "segment_mean_k365";

// Plain-language names for every method in the benchmark
const METHOD = {
  "hgb_poisson_fixed::routed_context": { name: "HGB · เลือกใช้ส่วนเสริมเมื่อมีข้อมูล", group: "hgb", note: "โมเดลที่ใช้จริง: ใช้ข้อมูลถนนและปฏิทินเสมอ และเพิ่มสภาพอากาศกับปริมาณจราจรเฉพาะช่วงที่มีข้อมูลครบ" },
  "hgb_poisson_fixed::core": { name: "HGB · ถนน + ปฏิทินเท่านั้น", group: "hgb", note: "โมเดลเดียวกันแต่ไม่ใช้สภาพอากาศและปริมาณจราจร ใช้ได้กับทุกช่วงถนน" },
  "hgb_poisson_fixed::context": { name: "HGB · ใช้ส่วนเสริมทุกช่วง", group: "hgb", note: "ใช้ข้อมูลเสริมกับทุกช่วงถนน ทำคะแนนได้ดีแต่ใช้งานจริงไม่ได้ เพราะบางช่วงไม่มีข้อมูลเสริม", ineligible: true },
  segment_mean_k365: { name: "ค่าเฉลี่ยในอดีตของช่วงถนน (k=365)", group: "base", note: "ค่าเทียบที่แข็งแรงที่สุด: นับเหตุในอดีตของแต่ละช่วงถนน แล้วปรับให้นิ่งด้วยค่าเฉลี่ยของสายทาง" },
  segment_mean_k180: { name: "ค่าเฉลี่ยในอดีตของช่วงถนน (k=180)", group: "base", note: "แบบเดียวกัน แต่ให้น้ำหนักค่าเฉลี่ยสายทางน้อยกว่า" },
  segment_mean_k30: { name: "ค่าเฉลี่ยในอดีตของช่วงถนน (k=30)", group: "base", note: "แบบเดียวกัน แต่เชื่อข้อมูลของช่วงถนนนั้นเองมากที่สุด" },
  route_length_rate: { name: "อัตราต่อกิโลเมตรของสายทาง", group: "base", note: "ทุกช่วงในสายทางเดียวกันได้ค่าเท่ากันตามความยาว" },
  global_length_rate: { name: "อัตราต่อกิโลเมตรทั้งประเทศ", group: "base", note: "ทุกช่วงถนนในประเทศได้ค่าเท่ากันตามความยาว" },
  global_mean: { name: "ค่าเฉลี่ยทั้งประเทศ", group: "base", note: "ทุกช่วงถนนได้ค่าเท่ากันหมด" },
  segment_month_k30: { name: "ค่าเฉลี่ยของช่วงถนนแยกตามเดือน", group: "base", note: "ดูว่าเดือนนี้ของปีก่อน ๆ ช่วงถนนนี้เกิดเหตุเท่าไร" },
  segment_weekday_k10: { name: "ค่าเฉลี่ยของช่วงถนนแยกตามวันในสัปดาห์", group: "base", note: "ดูว่าวันเดียวกันของสัปดาห์ในอดีต ช่วงถนนนี้เกิดเหตุเท่าไร" },
  recent90_segment: { name: "ค่าเฉลี่ย 90 วันล่าสุดของช่วงถนน", group: "base", note: "ใช้เฉพาะเหตุการณ์ช่วงสั้น ๆ ล่าสุด" },
  zero: { name: "ทายว่าไม่เกิดเหตุเลย", group: "base", note: "ใช้เป็นจุดอ้างอิงเท่านั้น" },
};
const MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
const GROUP_TH = {
  new_year_2026: "ปีใหม่", songkran_2026: "สงกรานต์", none: "วันปกติ",
  "00-06": "00–06 น.", "06-12": "06–12 น.", "12-18": "12–18 น.", "18-24": "18–24 น.", day: "ทั้งวัน",
  cool: "หน้าหนาว", hot: "หน้าร้อน", rainy: "หน้าฝน",
  Mon: "จันทร์", Tue: "อังคาร", Wed: "พุธ", Thu: "พฤหัสฯ", Fri: "ศุกร์", Sat: "เสาร์", Sun: "อาทิตย์",
};
const WEEK_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const pct = (x, d = 1) => (x * 100).toFixed(d) + "%";
const beDate = (iso) => { const [y, m, d] = iso.split("-").map(Number); return `${d} ${MONTHS[m - 1]} ${y + 543}`; };

function Section({ n, title, sub, children }) {
  return (
    <section className="mp-sec">
      <header className="mp-sec-h">
        <span className="mp-num">{n}</span>
        <div><h2>{title}</h2>{sub && <p>{sub}</p>}</div>
      </header>
      {children}
    </section>
  );
}

// ---------------------------------------------------------------- 1. what it predicts
function Pipeline() {
  return (
    <div className="mp-flow">
      <div className="mp-flow-in">
        <h4>ข้อมูลที่ป้อน</h4>
        <ul>
          <li><b>ถนน</b><span>ตำแหน่ง ความยาว รูปทรงถนน สายทาง จังหวัด</span></li>
          <li><b>ปฏิทิน</b><span>วันในสัปดาห์ เดือน ช่วง 6 ชม. วันหยุด สงกรานต์ ปีใหม่</span></li>
          <li><b>ส่วนเสริม</b><span>ฝนและอากาศย้อนหลัง 2 วัน ปริมาณจราจรเฉลี่ย (AADT)</span></li>
        </ul>
      </div>
      <span className="mp-arrow" aria-hidden="true" />
      <div className="mp-flow-model">
        <small>โมเดล</small>
        <b>HistGradientBoosting</b>
        <span>Poisson regression · 2 โมเดล: รายวัน และราย 6 ชม.</span>
      </div>
      <span className="mp-arrow" aria-hidden="true" />
      <div className="mp-flow-out">
        <h4>ผลลัพธ์</h4>
        <p><b>ค่าคาดจำนวนอุบัติเหตุ</b> ของแต่ละช่วงถนน (ยาว ~2 กม.) ในวันหรือช่วง 6 ชม. ที่เลือก</p>
        <p className="mp-flow-then">→ เทียบกับทุกช่วงถนนทั้งประเทศ แล้วให้สี <i className="mp-dot mp-dot-r" />สูงมาก (5% บนสุด) <i className="mp-dot mp-dot-o" />สูง (5–20%)</p>
      </div>
    </div>
  );
}

function WhyPoisson({ board }) {
  const hgb = board.find((m) => m.method === CHAMP);
  return (
    <div className="mp-why">
      <div className="mp-why-card">
        <span className="mp-ico">?</span>
        <div>
          <h4>ทำไมใช้ Poisson</h4>
          <p>สิ่งที่ทายคือ “จำนวนครั้ง” ซึ่งเป็นจำนวนเต็มไม่ติดลบ และเกือบทุกช่วงถนนในแต่ละวันมีค่าเป็น 0 การวัดแบบ Poisson จึงเหมาะกว่าการทายว่า “เกิด / ไม่เกิด”</p>
        </div>
      </div>
      <div className="mp-why-card">
        <span className="mp-ico">%</span>
        <div>
          <h4>วัดผลด้วย Poisson deviance</h4>
          <p>บอกว่าค่าที่ทายห่างจากจำนวนเหตุจริงแค่ไหน <b>ยิ่งต่ำยิ่งดี</b> เราไม่ใช้ Accuracy เพราะถ้าทายว่า “ไม่เกิด” ทุกช่องจะได้ Accuracy เกือบ 100% ทั้งที่ไม่มีประโยชน์</p>
        </div>
      </div>
      {hgb && (
        <div className="mp-why-card mp-why-stat">
          <b>เพียง ~0.2%</b>
          <p>ของช่อง “ช่วงถนน × วัน” ที่มีอุบัติเหตุจริง (ทดสอบย้อนหลัง 2565–2566 มีราว 19.5 ล้านช่อง)</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- 2. time split
const T0 = Date.UTC(2021, 0, 1), T1 = Date.UTC(2026, 9, 1);
const pos = (iso) => ((Date.parse(iso + "T00:00:00Z") - T0) / (T1 - T0)) * 100;
function Timeline({ folds, unitData, sel, setSel }) {
  const rows = [
    ...folds.map((f, i) => ({ key: f.fold, label: `รอบที่ ${i + 1}`, train: ["2021-01-01", f.train_cutoff], eval: [f.eval_start, f.eval_end], fold: f })),
    { key: "final", label: "โมเดลที่ใช้จริง", train: ["2021-01-01", "2023-12-01"], check: ["2024-01-01", "2025-12-31"], test: ["2026-01-01", "2026-09-30"] },
  ];
  const seg = (a, b, cls, title) => <span className={"mp-tl-bar " + cls} style={{ left: pos(a) + "%", width: pos(b) - pos(a) + "%" }} title={title} />;
  const f = sel && folds.find((x) => x.fold === sel);
  return (
    <div className="mp-tl">
      <div className="mp-tl-axis"><span />{[2564, 2565, 2566, 2567, 2568, 2569].map((y, i) => <i key={y} style={{ left: pos(`${2021 + i}-01-01`) + "%" }}>{y}</i>)}</div>
      {rows.map((r) => (
        <button key={r.key} type="button" className={"mp-tl-row" + (sel === r.key ? " is-sel" : "")} onClick={() => setSel(sel === r.key || r.key === "final" ? null : r.key)} disabled={r.key === "final"}>
          <span className="mp-tl-lab">{r.label}</span>
          <span className="mp-tl-track">
            {seg(r.train[0], r.train[1], "is-train", "ช่วงที่ใช้ฝึก")}
            {r.eval && seg(r.eval[0], r.eval[1], "is-eval", "ช่วงที่ใช้วัดผล")}
            {r.check && seg(r.check[0], r.check[1], "is-check", "ช่วงตรวจ (ไม่ใช้ฝึก)")}
            {r.test && seg(r.test[0], r.test[1], "is-test", "ทดสอบ (ไม่เคยเห็น)")}
          </span>
        </button>
      ))}
      <div className="mp-legend">
        <span><i className="is-train" />ข้อมูลฝึก</span><span><i className="is-eval" />วัดผลในการคัดเลือก</span>
        <span><i className="is-check" />ตรวจ (2567–2568)</span><span><i className="is-test" />ทดสอบที่ไม่เคยเห็น (2569)</span>
      </div>
      <div className="mp-tl-note">
        {f ? (
          <p><b>{rows.find((r) => r.key === sel).label}:</b> ฝึกด้วยข้อมูลถึง {beDate(f.train_cutoff)} แล้ววัดผลช่วง {beDate(f.eval_start)} – {beDate(f.eval_end)} ·
            HGB deviance <b>{f[CHAMP].toFixed(5)}</b> เทียบค่าเฉลี่ยในอดีต {f[BASE].toFixed(5)} →{" "}
            <b className={f[CHAMP] < f[BASE] ? "mp-good" : "mp-bad"}>{f[CHAMP] < f[BASE] ? `ดีกว่า ${pct(1 - f[CHAMP] / f[BASE])}` : `แย่กว่า ${pct(f[CHAMP] / f[BASE] - 1)}`}</b></p>
        ) : (
          <p>แต่ละรอบ โมเดลเรียนจากข้อมูล <b>ก่อน</b> ช่วงที่ถูกวัดผลเท่านั้น เหมือนการใช้งานจริงที่ไม่มีทางรู้อนาคต · <b>คลิกที่รอบ</b> เพื่อดูผลของรอบนั้น ·
            ผลรวม {unitData.selection.n_folds} รอบ: HGB ชนะ <b>{unitData.selection.fold_wins}/{unitData.selection.n_folds}</b> รอบ</p>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- 3. benchmark
function Leaderboard({ board, showZero, pick, setPick }) {
  const rows = board.filter((m) => showZero || m.method !== "zero").slice().sort((a, b) => a.deviance - b.deviance);
  const champ = board.find((m) => m.method === CHAMP);
  const CAP = 0.5; // bars show "% worse than the chosen model", capped at +50% (longer bars get an arrow)
  return (
    <ul className="mp-board">
      {rows.map((m) => {
        const info = METHOD[m.method] || { name: m.method, group: "base" };
        const diff = m.deviance / champ.deviance - 1;
        return (
          <li key={m.method}>
            <button type="button" className={[info.group === "hgb" ? "is-hgb" : "is-base", m.method === CHAMP ? "is-champ" : "", pick === m.method ? "is-pick" : ""].join(" ")} onClick={() => setPick(m.method)}>
              <span className="mp-board-name">{info.name}{m.method === CHAMP && <em>ที่เลือกใช้</em>}{info.ineligible && <em className="mp-tag-muted">ใช้จริงไม่ได้</em>}</span>
              <span className={"mp-board-track" + (diff > CAP ? " is-over" : "")}><i style={{ width: (Math.min(Math.max(diff, 0), CAP) / CAP) * 100 + "%" }} /></span>
              <span className="mp-board-v">{m.deviance.toFixed(5)}</span>
              <span className={"mp-board-d" + (diff > 0.0005 ? " is-worse" : diff < -0.0005 ? " is-better" : "")}>{m.method === CHAMP ? "—" : (diff > 0 ? "+" : "") + pct(diff)}</span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function FoldBars({ folds }) {
  const max = Math.max(...folds.flatMap((f) => [f[CHAMP], f[BASE]]));
  return (
    <div className="mp-folds">
      {folds.map((f, i) => {
        const win = f[CHAMP] < f[BASE];
        return (
          <div key={f.fold} className="mp-fold">
            <div className="mp-fold-h"><b>รอบที่ {i + 1}</b><span className={win ? "mp-good" : "mp-bad"}>{win ? "HGB ชนะ" : "ค่าเทียบชนะ"}</span></div>
            <div className="mp-fold-bar"><span>HGB</span><i className="is-hgb" style={{ width: (f[CHAMP] / max) * 100 + "%" }} /><b>{f[CHAMP].toFixed(4)}</b></div>
            <div className="mp-fold-bar"><span>ค่าเทียบ</span><i className="is-base" style={{ width: (f[BASE] / max) * 100 + "%" }} /><b>{f[BASE].toFixed(4)}</b></div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------- 4. unseen 2026
function ImproveBars({ items, label }) {
  const max = Math.max(0.05, ...items.map((d) => Math.abs(d.improvement || 0)));
  return (
    <ul className="mp-imp" aria-label={label}>
      {items.map((d) => (
        <li key={d.key} title={`HGB ${d.selected} · ค่าเทียบ ${d.baseline} · ${d.records.toLocaleString("en-US")} เหตุ`}>
          <span className="mp-imp-l">{d.label}</span>
          <span className="mp-imp-t"><i className={d.improvement >= 0 ? "" : "is-neg"} style={{ width: (Math.abs(d.improvement) / max) * 100 + "%" }} /></span>
          <span className="mp-imp-v">{d.improvement >= 0 ? "ดีกว่า " : "แย่กว่า "}{pct(Math.abs(d.improvement))}</span>
        </li>
      ))}
    </ul>
  );
}

export default function ModelPage() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [unit, setUnit] = useState("6h");
  const [fold, setFold] = useState(null);
  const [showZero, setShowZero] = useState(false);
  const [pick, setPick] = useState(CHAMP);
  const [view, setView] = useState("month");

  useEffect(() => { document.title = "โมเดล — RoadAware"; }, []);
  useEffect(() => {
    let alive = true;
    fetch(DATA_URL).then((r) => (r.ok ? r.json() : Promise.reject(new Error("HTTP " + r.status))))
      .then((j) => { if (alive) setData(j); }).catch((e) => { if (alive) setErr(String(e.message || e)); });
    return () => { alive = false; };
  }, []);

  const U = data && data.units[unit];
  const groups = useMemo(() => {
    if (!U) return [];
    const t = U.test2026;
    const lab = (g) => GROUP_TH[g.group] || g.group;
    if (view === "month") return t.month.map((g) => ({ ...g, key: g.group, label: MONTHS[+g.group.slice(5) - 1] + " 69" }));
    if (view === "festival") return ["songkran_2026", "new_year_2026", "none"].map((k) => t.festival.find((g) => g.group === k)).filter(Boolean).map((g) => ({ ...g, key: g.group, label: lab(g) }));
    if (view === "time") return t.time_block.map((g) => ({ ...g, key: g.group, label: lab(g) }));
    if (view === "season") return ["hot", "rainy", "cool"].map((k) => t.season.find((g) => g.group === k)).filter(Boolean).map((g) => ({ ...g, key: g.group, label: lab(g) }));
    return WEEK_ORDER.map((k) => t.weekday.find((g) => g.group === k)).filter(Boolean).map((g) => ({ ...g, key: g.group, label: lab(g) }));
  }, [U, view]);

  if (err) return <div className="dash"><SiteNav active="model" /><main className="db-wrap db-main"><div className="db-empty">โหลดข้อมูลไม่สำเร็จ ({err})</div></main></div>;
  if (!U) return <div className="dash"><SiteNav active="model" /><main className="db-wrap db-main"><div className="db-empty"><span className="boot-dot" /> กำลังโหลด…</div></main></div>;

  const t = U.test2026;
  const monthsBetter = t.month.filter((m) => m.improvement > 0).length;
  const fest = Math.min(...t.festival.filter((g) => g.group !== "none").map((g) => g.improvement));
  const festMax = Math.max(...t.festival.filter((g) => g.group !== "none").map((g) => g.improvement));
  const pickInfo = METHOD[pick] || {};
  const pickRow = U.leaderboard.find((m) => m.method === pick);
  const champRow = U.leaderboard.find((m) => m.method === CHAMP);

  return (
    <div className="dash">
      <SiteNav active="model" />
      <main className="db-wrap db-main mp">
        <div className="db-head">
          <div>
            <h1>โมเดลของ RoadAware</h1>
            <p className="mp-lead">โมเดลทายอะไร ถูกเลือกมาอย่างไร และทำได้ดีแค่ไหนกับข้อมูลที่ไม่เคยเห็น</p>
          </div>
          <div className="db-metric" role="radiogroup" aria-label="หน่วยเวลา">
            {[["6h", "ราย 6 ชั่วโมง"], ["daily", "รายวัน"]].map(([k, l]) => (
              <button key={k} type="button" role="radio" aria-checked={unit === k} className={unit === k ? "is-on" : ""} onClick={() => { setUnit(k); setFold(null); if (k === "daily" && view === "time") setView("month"); }}>{l}</button>
            ))}
          </div>
        </div>

        <div className="mp-kpis">
          <div className="mp-kpi mp-kpi-champ"><span>โมเดลที่เลือก</span><b>HistGradientBoosting</b><small>Poisson · ใช้ทั้งประเทศ</small></div>
          <div className="mp-kpi"><span>ทดสอบย้อนหลัง 2565–2566</span><b>ดีกว่า {pct(U.selection.relative_deviance_reduction)}</b><small>ชนะ {U.selection.fold_wins}/{U.selection.n_folds} รอบ เทียบค่าเทียบที่ดีที่สุด</small></div>
          <div className="mp-kpi"><span>ปี 2569 ที่ไม่เคยเห็น</span><b>ดีกว่า {pct(t.overall.improvement)}</b><small>ดีกว่าทุกเดือน ({monthsBetter}/{t.month.length}) · {t.overall.records.toLocaleString("en-US")} เหตุ</small></div>
          <div className="mp-kpi"><span>ช่วงเทศกาล 2569</span><b>ดีกว่า {Math.round(fest * 100)}–{pct(festMax, 0)}</b><small>สงกรานต์และปีใหม่</small></div>
        </div>

        <Section n={1} title="โมเดลทายอะไร" sub="จากข้อมูลถนนและเวลา ไปเป็นจุดที่ควรระวังบนแผนที่">
          <Pipeline />
          <WhyPoisson board={U.leaderboard} />
        </Section>

        <Section n={2} title="แบ่งข้อมูลตามเวลา" sub="ทดสอบแบบที่โมเดลไม่เคยเห็นอนาคต (rolling-origin backtest)">
          <Timeline folds={U.folds} unitData={U} sel={fold} setSel={setFold} />
        </Section>

        <Section n={3} title="เทียบกับวิธีอื่น (Model Benchmarking)" sub={`ค่าเฉลี่ย Poisson deviance จากการทดสอบย้อนหลัง 4 รอบ (${unit === "6h" ? "ราย 6 ชม." : "รายวัน"}) · ยิ่งต่ำยิ่งดี`}>
          <div className="mp-bench">
            <div className="db-card">
              <div className="db-card-h">
                <div><h3>อันดับของ {U.leaderboard.filter((m) => showZero || m.method !== "zero").length} วิธี</h3><p>แท่ง = ทำได้แย่กว่าโมเดลที่เลือกกี่ % (ยิ่งสั้นยิ่งดี) · คลิกที่แถวเพื่อดูคำอธิบาย</p></div>
                <label className="mp-check"><input type="checkbox" checked={showZero} onChange={(e) => setShowZero(e.target.checked)} />แสดง “ทายว่าไม่เกิดเลย”</label>
              </div>
              <Leaderboard board={U.leaderboard} showZero={showZero} pick={pick} setPick={setPick} />
              <div className="mp-legend"><span><i className="is-hgb" />HGB (Machine Learning)</span><span><i className="is-base" />ค่าเทียบแบบสถิติ</span></div>
            </div>
            <div className="mp-bench-side">
              <div className={"mp-explain" + (pick === CHAMP ? " is-champ" : "")}>
                <small>{METHOD[pick]?.group === "hgb" ? "Machine Learning" : "ค่าเทียบ (baseline)"}</small>
                <h4>{pickInfo.name}</h4>
                <p>{pickInfo.note}</p>
                {pickRow && pick !== CHAMP && <p className="mp-explain-cmp">deviance {pickRow.deviance.toFixed(5)} · {pickRow.deviance > champRow.deviance ? `สูงกว่าโมเดลที่เลือก ${pct(pickRow.deviance / champRow.deviance - 1)}` : `ต่ำกว่าโมเดลที่เลือก ${pct(1 - pickRow.deviance / champRow.deviance)}`}</p>}
              </div>
              <div className="db-card">
                <div className="db-card-h"><div><h3>ผลรายรอบ</h3><p>HGB ที่เลือก เทียบค่าเฉลี่ยในอดีต (k=365)</p></div></div>
                <FoldBars folds={U.folds} />
              </div>
              <div className="mp-verdict">
                <b>บทสรุปการคัดเลือก</b>
                <p>HGB ทำ deviance ได้ต่ำกว่าค่าเทียบที่ดีที่สุด {pct(U.selection.relative_deviance_reduction)} และชนะ {U.selection.fold_wins} จาก {U.selection.n_folds} รอบ ผ่านทุกเกณฑ์ที่กำหนดไว้ <b>ก่อน</b> ดูผล จึงถูกเลือกใช้</p>
              </div>
            </div>
          </div>
        </Section>

        <Section n={4} title="ทดสอบกับปี 2569 ที่โมเดลไม่เคยเห็น" sub="ม.ค.–ก.ย. 2569 · ตัวเลข = HGB ทำความคลาดเคลื่อนน้อยกว่าค่าเทียบกี่เปอร์เซ็นต์">
          <div className="mp-test">
            <div className="db-card">
              <div className="mp-tabs" role="tablist">
                {[["month", "รายเดือน"], ["festival", "เทศกาล"], ...(unit === "6h" ? [["time", "ช่วงเวลา"]] : []), ["season", "ฤดู"], ["weekday", "วันในสัปดาห์"]].map(([k, l]) => (
                  <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? "is-on" : ""} onClick={() => setView(k)}>{l}</button>
                ))}
              </div>
              <ImproveBars items={groups} label="ผลแยกกลุ่ม" />
            </div>
            <div className="mp-test-side">
              <div className="mp-big"><b>{monthsBetter}/{t.month.length}</b><span>เดือนที่ดีกว่าค่าเทียบ</span></div>
              <div className="mp-big"><b>{t.weeks_better}/{t.weeks}</b><span>สัปดาห์ที่ดีกว่า</span></div>
              <div className="mp-big"><b>{t.province_wins}/{t.province_count}</b><span>จังหวัดที่ดีกว่า</span></div>
            </div>
          </div>
        </Section>

        <Section n={5} title="ข้อจำกัดที่ควรรู้">
          <ul className="about-limits mp-limits">
            <li>ทายจำนวนอุบัติเหตุ “ที่ถูกบันทึก” บนทางหลวงกรมทางหลวง ไม่ใช่ทุกอุบัติเหตุที่เกิดจริง</li>
            <li>ผลปี 2569 วัดเฉพาะช่วงถนน × วันที่มีเหตุจริง และใช้แค่ส่วนหลัก (ถนน + ปฏิทิน) เพราะยังไม่มีข้อมูลอากาศและจราจรของปีนั้น</li>
            <li>ค่าที่ได้คือการเปรียบเทียบระหว่างช่วงถนน ไม่ใช่โอกาสเกิดเหตุของผู้ขับขี่แต่ละคน</li>
          </ul>
        </Section>
      </main>
    </div>
  );
}
