// โมเดล — what the model predicts, how it was chosen, and how it did on data it never saw.
// Every number comes from the project's own reports (public/data/model-v1.json, built by
// backend/scripts/build_model_page_data.py). Unit switch (รายวัน / ราย 6 ชม.) changes every chart.
import { useEffect, useMemo, useRef, useState } from "react";
import { CountUp, PageBody, SiteFooter, SiteNav, useReveal } from "./site.jsx";

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

const SECTIONS = [
  ["mp-s1", "ทายอะไร"], ["mp-s2", "แบ่งข้อมูล"], ["mp-s3", "เทียบวิธี"], ["mp-s4", "ทดสอบ 2569"], ["mp-s5", "ข้อจำกัด"],
];

function Section({ n, title, sub, children }) {
  return (
    <section className="mp-sec rv" id={"mp-s" + n}>
      <header className="mp-sec-h">
        <span className="mp-num">{String(n).padStart(2, "0")}</span>
        <div><small>ขั้นที่ {n}</small><h2>{title}</h2>{sub && <p>{sub}</p>}</div>
      </header>
      {children}
    </section>
  );
}

// In-page menu: highlights the section being read, click to jump.
function SectionNav() {
  const [active, setActive] = useState(SECTIONS[0][0]);
  useEffect(() => {
    const root = document.querySelector(".dash");
    const els = SECTIONS.map(([id]) => document.getElementById(id)).filter(Boolean);
    if (!root || !els.length || !("IntersectionObserver" in window)) return undefined;
    const io = new IntersectionObserver((entries) => {
      const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
      if (vis[0]) setActive(vis[0].target.id);
    }, { root, rootMargin: "-130px 0px -55% 0px" });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
  const go = (id) => { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: "smooth", block: "start" }); };
  return (
    <nav className="mp-secnav" aria-label="ส่วนของหน้า">
      <div className="db-wrap mp-secnav-in">
        {SECTIONS.map(([id, label], i) => (
          <button key={id} type="button" className={active === id ? "is-on" : ""} onClick={() => go(id)}><span>{i + 1}</span>{label}</button>
        ))}
      </div>
    </nav>
  );
}


// Hero visual: how gradient boosting builds a prediction — small trees added one after another, each following
// its own decision path (amber), summed into the expected number of accidents.
function Tree({ x, i, path }) {
  const n = [[30, 14], [14, 44], [46, 44], [6, 74], [22, 74], [38, 74], [54, 74]];
  const e = [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5], [2, 6]];
  return (
    <g transform={`translate(${x} 0)`}><g className="bz-tree" style={{ "--i": i }}>
      {e.map(([a, b]) => <line key={a + "-" + b} x1={n[a][0]} y1={n[a][1]} x2={n[b][0]} y2={n[b][1]} className={path.includes(b) && path.includes(a) ? "bz-on" : ""} />)}
      {n.map(([cx, cy], k) => <circle key={k} cx={cx} cy={cy} r={k === 0 ? 6 : 5} className={path.includes(k) ? "bz-on" : ""} />)}
    </g></g>
  );
}
function BoostViz() {
  return (
    <figure className="bz" aria-label="ต้นไม้ตัดสินใจหลายต้นรวมกันเป็นค่าคาดการณ์">
      <svg viewBox="0 0 380 92">
        <Tree x={0} i={0} path={[0, 1, 4]} />
        <text x="72" y="50" className="bz-op" style={{ "--i": 0.6 }}>+</text>
        <Tree x={88} i={1} path={[0, 2, 5]} />
        <text x="160" y="50" className="bz-op" style={{ "--i": 1.6 }}>+</text>
        <Tree x={176} i={2} path={[0, 2, 6]} />
        <text x="238" y="50" className="bz-op" style={{ "--i": 2.6 }}>+ …</text>
        <text x="284" y="50" className="bz-op" style={{ "--i": 3 }}>=</text>
        <g className="bz-out" style={{ "--i": 3.2 }}><rect x="304" y="28" width="74" height="34" rx="9" /><text x="341" y="50" textAnchor="middle">0.003</text></g>
      </svg>
      <figcaption>ต้นไม้ตัดสินใจหลายร้อยต้นต่อกัน แต่ละต้นแก้ส่วนที่ต้นก่อนหน้าทายพลาด รวมเป็นจำนวนอุบัติเหตุที่คาดว่าจะเกิด</figcaption>
    </figure>
  );
}

// HGB vs baseline, month by month: two lines, lower = better, gap shaded. Hover shows both values.
function CompareLine({ items }) {
  const [hi, setHi] = useState(null);
  const box = useRef(null);
  const [W, setW] = useState(640);
  useEffect(() => {
    const el = box.current;
    if (!el || !("ResizeObserver" in window)) return undefined;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const H = W < 500 ? 230 : 270, pad = { l: 40, r: 16, t: 16, b: 30 };
  const vals = items.flatMap((d) => [d.selected, d.baseline]);
  const lo = Math.floor(Math.min(...vals) - 0.5), up = Math.ceil(Math.max(...vals) + 0.5);
  const X = (i) => pad.l + (i / (items.length - 1)) * (W - pad.l - pad.r);
  const Y = (v) => pad.t + (1 - (v - lo) / (up - lo)) * (H - pad.t - pad.b);
  const path = (k) => items.map((d, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(d[k]).toFixed(1)).join(" ");
  const gap = items.map((d, i) => (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(d.baseline).toFixed(1)).join(" ")
    + " " + items.slice().reverse().map((d, j) => "L" + X(items.length - 1 - j).toFixed(1) + " " + Y(d.selected).toFixed(1)).join(" ") + " Z";
  const ticks = [lo, (lo + up) / 2, up];
  const last = items.length - 1;
  return (
    <div className="mp-line" ref={box}>
      <svg width={W} height={H} role="img" aria-label="ความคลาดเคลื่อนรายเดือน HGB เทียบค่าเทียบ" onMouseLeave={() => setHi(null)}>
        {ticks.map((t) => <g key={t}><line x1={pad.l} x2={W - pad.r} y1={Y(t)} y2={Y(t)} className="db-grid" /><text x={pad.l - 8} y={Y(t) + 4} textAnchor="end" className="db-axis">{t.toFixed(1)}</text></g>)}
        <path d={gap} className="mp-gap" />
        <path d={path("baseline")} className="mp-ln mp-ln-base" />
        <path d={path("selected")} className="mp-ln mp-ln-hgb" />
        {items.map((d, i) => (
          <g key={d.key}>
            <circle cx={X(i)} cy={Y(d.baseline)} r={hi === i ? 5.5 : 4} className="mp-pt-base" />
            <circle cx={X(i)} cy={Y(d.selected)} r={hi === i ? 5.5 : 4} className="mp-pt-hgb" />
            <text x={X(i)} y={H - 8} textAnchor={i === 0 ? "start" : i === items.length - 1 ? "end" : "middle"} className="db-axis">{d.label.split(" ")[0]}</text>
            <rect x={X(i) - (W - pad.l - pad.r) / (items.length - 1) / 2} y={pad.t} width={(W - pad.l - pad.r) / (items.length - 1)} height={H - pad.t - pad.b} fill="transparent" onMouseEnter={() => setHi(i)} />
          </g>
        ))}
        <text x={X(last) + 2} y={Y(items[last].baseline) - 10} textAnchor="end" className="mp-lab mp-lab-base">ค่าเทียบ</text>
        <text x={X(last) + 2} y={Y(items[last].selected) + 20} textAnchor="end" className="mp-lab mp-lab-hgb">HGB</text>
        {hi != null && <line x1={X(hi)} x2={X(hi)} y1={pad.t} y2={H - pad.b} className="db-cross" />}
      </svg>
      {hi != null && (
        <div className="mp-tip" style={{ left: `${(X(hi) / W) * 100}%` }}>
          <b>{items[hi].label}</b>
          <span><i className="is-hgb" />HGB {items[hi].selected.toFixed(2)}</span>
          <span><i className="is-base" />ค่าเทียบ {items[hi].baseline.toFixed(2)}</span>
          <em>คลาดเคลื่อนน้อยกว่า {pct(items[hi].improvement)}</em>
        </div>
      )}
    </div>
  );
}

// HGB vs baseline for groups (festival, time of day…): paired bars from zero, lower = better.
function CompareBars({ items }) {
  const max = Math.max(...items.flatMap((d) => [d.selected, d.baseline]));
  return (
    <ul className="mp-pairs">
      {items.map((d) => (
        <li key={d.key}>
          <div className="mp-pair-h"><b>{d.label}</b><span>คลาดเคลื่อนน้อยกว่า <em>{pct(d.improvement)}</em></span></div>
          <div className="mp-pair-bar"><small>HGB</small><span><i className="is-hgb" style={{ width: (d.selected / max) * 100 + "%" }} /></span><b>{d.selected.toFixed(2)}</b></div>
          <div className="mp-pair-bar"><small>ค่าเทียบ</small><span><i className="is-base" style={{ width: (d.baseline / max) * 100 + "%" }} /></span><b>{d.baseline.toFixed(2)}</b></div>
        </li>
      ))}
    </ul>
  );
}

// Monthly results as columns (one per month, height = improvement)
function MonthColumns({ items }) {
  const max = Math.max(0.05, ...items.map((d) => d.improvement || 0));
  const avg = items.reduce((a, d) => a + d.improvement, 0) / items.length;
  return (
    <div className="mp-cols" role="img" aria-label="ผลรายเดือน">
      <div className="mp-cols-avg" style={{ bottom: `calc(${(avg / max) * 100}% * .82 + 26px)` }}><span>เฉลี่ย {pct(avg)}</span></div>
      {items.map((d) => (
        <div key={d.key} className="mp-col" title={`${d.label}: ดีกว่า ${pct(d.improvement)} · ${d.records.toLocaleString("en-US")} เหตุ`}>
          <b>{pct(d.improvement, 0)}</b>
          <span className="mp-col-bar"><i style={{ height: (Math.max(d.improvement, 0) / max) * 100 + "%" }} className={d.key.endsWith("-04") || d.key.endsWith("-01") ? "is-fest" : ""} /></span>
          <small>{d.label.split(" ")[0]}</small>
        </div>
      ))}
    </div>
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
        <span>ทายจำนวนอุบัติเหตุด้วย Poisson loss · 2 โมเดล: รายวัน และราย 6 ชม.</span>
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

  useReveal([!!U]);

  if (err) return <div className="dash"><SiteNav active="model" /><main className="db-wrap db-main"><div className="db-empty">โหลดข้อมูลไม่สำเร็จ ({err})</div></main></div>;
  if (!U) return <div className="dash" aria-busy="true"><SiteNav active="model" /><PageBody kind="model" /></div>;

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
      <header className="page-hero">
        <div className="db-wrap">
          <div className="page-hero-top">
            <div>
              <small className="eyebrow hero-in" style={{ "--d": "0ms" }}>เบื้องหลังการคาดการณ์</small>
              <h1 className="hero-mask"><span style={{ "--d": "60ms" }}>โมเดลของ RoadAware</span></h1>
              <p className="hero-in" style={{ "--d": "160ms" }}>โมเดลทายอะไร ถูกเลือกมาอย่างไร และทำได้ดีแค่ไหนกับข้อมูลที่ไม่เคยเห็น</p>
            </div>
            <div className="mp-hero-side hero-in" style={{ "--d": "220ms" }}>
              <BoostViz />
              <div className="seg-dark" data-seg role="radiogroup" aria-label="หน่วยเวลา">
                {[["6h", "ราย 6 ชั่วโมง"], ["daily", "รายวัน"]].map(([k, l]) => (
                  <button key={k} type="button" role="radio" aria-checked={unit === k} className={unit === k ? "is-on" : ""} onClick={() => { setUnit(k); setFold(null); if (k === "daily" && view === "time") setView("month"); }}>{l}</button>
                ))}
              </div>
            </div>
          </div>
          <div className="mp-kpis">
            <div className="mp-kpi mp-kpi-champ hero-in" style={{ "--d": "260ms" }}><span>โมเดลที่เลือกใช้</span><b>HistGradientBoosting</b><small>ทายจำนวนอุบัติเหตุ · Poisson loss · ทั้งประเทศ</small></div>
            <div className="mp-kpi hero-in" style={{ "--d": "330ms" }}><span>ทดสอบย้อนหลัง 2565–2566</span><b><CountUp value={U.selection.relative_deviance_reduction} format={(v) => pct(v)} /></b><small>คลาดเคลื่อนน้อยกว่าค่าเทียบ · ชนะ {U.selection.fold_wins}/{U.selection.n_folds} รอบ</small></div>
            <div className="mp-kpi hero-in" style={{ "--d": "400ms" }}><span>ปี 2569 ที่ไม่เคยเห็น</span><b><CountUp value={t.overall.improvement} format={(v) => pct(v)} /></b><small>ดีกว่าทุกเดือน ({monthsBetter}/{t.month.length}) · {t.overall.records.toLocaleString("en-US")} เหตุ</small></div>
            <div className="mp-kpi hero-in" style={{ "--d": "470ms" }}><span>สงกรานต์ · ปีใหม่ 2569</span><b><CountUp value={fest * 100} format={(v) => Math.round(v)} />–<CountUp value={festMax} format={(v) => pct(v, 0)} /></b><small>คลาดเคลื่อนน้อยกว่าค่าเทียบ</small></div>
          </div>
        </div>
        <div className="ld-lane" aria-hidden="true" />
      </header>
      <SectionNav />
      <main className="db-wrap db-main mp">
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

        <Section n={4} title="ทดสอบกับปี 2569 ที่โมเดลไม่เคยเห็น" sub="ม.ค.–ก.ย. 2569 — ข้อมูลที่ไม่ได้ใช้ทั้งตอนฝึกและตอนเลือกโมเดล">
          <div className="mp-test">
            <div className="db-card">
              <div className="mp-tabs" data-seg role="tablist">
                {[["month", "รายเดือน"], ["festival", "เทศกาล"], ...(unit === "6h" ? [["time", "ช่วงเวลา"]] : []), ["season", "ฤดู"], ["weekday", "วันในสัปดาห์"]].map(([k, l]) => (
                  <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? "is-on" : ""} onClick={() => setView(k)}>{l}</button>
                ))}
              </div>
              <div className="mp-legend mp-legend-top"><span><i className="is-hgb" />HGB (โมเดลที่เลือก)</span><span><i className="is-base" />ค่าเทียบ: ค่าเฉลี่ยในอดีตของช่วงถนน</span><span className="mp-legend-hint">ค่าความคลาดเคลื่อน (Poisson deviance) · <b>ยิ่งต่ำยิ่งดี</b></span></div>
              {view === "month" ? <CompareLine items={groups} /> : <CompareBars items={groups} />}
              <p className="mp-note">{view === "month" ? "เส้น HGB อยู่ต่ำกว่าเส้นค่าเทียบทุกเดือน = ทายใกล้ความจริงกว่าทุกเดือน · ช่องว่างระหว่างเส้นกว้างสุดในเดือนที่มีเทศกาล (ม.ค. ปีใหม่, เม.ย. สงกรานต์) · ชี้ที่กราฟเพื่อดูตัวเลข" : "แท่ง HGB สั้นกว่าแท่งค่าเทียบ = ทายใกล้ความจริงกว่า"}</p>
            </div>
            <div className="mp-test-side">
              {[[monthsBetter, t.month.length, "เดือนที่ดีกว่าค่าเทียบ"], [t.weeks_better, t.weeks, "สัปดาห์ที่ดีกว่า"], [t.province_wins, t.province_count, "จังหวัดที่ดีกว่า"]].map(([a, b, l]) => (
                <div key={l} className="mp-big">
                  <div><b>{a}</b><small>/{b}</small></div>
                  <span>{l}</span>
                  <i className="mp-prog"><em style={{ width: (a / b) * 100 + "%" }} /></i>
                </div>
              ))}
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
      <SiteFooter />
    </div>
  );
}
