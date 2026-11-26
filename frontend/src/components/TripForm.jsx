import PlaceField from "./PlaceField.jsx";
import { Loading, ErrorBox } from "./common.jsx";
import { DATE_MIN, DATE_MAX } from "../config.js";
import { epochToBkk, fmtThaiDate } from "../lib/util.js";
import { REVIEW_PERIODS, REVIEW_MIN, REVIEW_MAX, REVIEW_MAX_DAYS, periodProblem } from "../lib/review.js";

function dayChoices() {
  const today = epochToBkk(Date.now()).date;
  const tomorrow = epochToBkk(Date.now() + 24 * 3600 * 1000).date;
  return { today, tomorrow };
}

export default function TripForm({ appMode = "plan", onAppMode, reviewPeriod, onReviewPeriod, texts, places, results, pick, when, canRoute, trip, onText, onSearch, onChoose, onCloseResults, onPick, onMyLocation, locating, onSwap, onWhen, onSubmit, onExample }) {
  const { today, tomorrow } = dayChoices();
  const other = when.date !== today && when.date !== tomorrow;
  const review = appMode === "review";
  const custom = review && reviewPeriod && !REVIEW_PERIODS.some((p) => p.id === reviewPeriod.id);
  const problem = review ? periodProblem(reviewPeriod) : null;
  return (
    <section className="trip-form" aria-labelledby="planTitle">
      {/* โหมด "ย้อนดูผล" ปิดไว้ก่อน: ปุ่มสลับโหมดถูกซ่อน ระบบใช้โหมดวางแผนเดินทางอย่างเดียว (โค้ดของโหมดยังอยู่ใน App.jsx / lib/review.js) */}
      {review ? (
        <>
          <h1 id="planTitle" className="plan-title">โมเดลชี้ถูกไหม?</h1>
          <p className="plan-lead">เลือกเส้นทางและช่วงเวลาในอดีต แล้วดูว่าจุดที่โมเดลชี้ ตรงกับที่เกิดเหตุจริงแค่ไหน</p>
        </>
      ) : (
        <>
          <h1 id="planTitle" className="plan-title">จะเดินทางไปไหน?</h1>
          <p className="plan-lead">บอกเส้นทางและเวลาออก แล้วเราจะสรุปว่าต้องระวังช่วงไหน</p>
        </>
      )}

      <div className="pf-card">
        <PlaceField which="origin" letter="A" label="ต้นทาง" placeholder="เช่น มหาวิทยาลัยศรีปทุม"
          text={texts.origin} place={places.origin} results={results.origin}
          onText={(v) => onText("origin", v)} onSearch={() => onSearch("origin")}
          onChoose={(p) => onChoose("origin", p)} onCloseResults={() => onCloseResults("origin")} />
        <div className="pf-divider">
          <button type="button" className="swap-btn" aria-label="สลับต้นทางและปลายทาง" title="สลับต้นทาง/ปลายทาง" onClick={onSwap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M7 4v16" /><path d="M3 8l4-4 4 4" /><path d="M17 20V4" /><path d="M13 16l4 4 4-4" /></svg>
          </button>
        </div>
        <PlaceField which="dest" letter="B" label="ปลายทาง" placeholder="เช่น อุทยานแห่งชาติเขาใหญ่"
          text={texts.dest} place={places.dest} results={results.dest}
          onText={(v) => onText("dest", v)} onSearch={() => onSearch("dest")}
          onChoose={(p) => onChoose("dest", p)} onCloseResults={() => onCloseResults("dest")} />
      </div>

      <div className="quick-row" role="group" aria-label="เลือกจุดแบบเร็ว">
        <button type="button" className="quick-btn" onClick={onMyLocation} disabled={locating}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></svg>
          <span>{locating ? "กำลังหา…" : "ตำแหน่งของฉัน"}</span>
        </button>
        {["origin", "dest"].map((w) => (
          <button key={w} type="button" className={"quick-btn" + (pick === w ? " is-active" : "")} aria-pressed={pick === w} onClick={() => onPick(w)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M12 21s-7-6.5-7-12a7 7 0 0 1 14 0c0 5.5-7 12-7 12z" /><circle cx="12" cy="9" r="2.5" /></svg>
            <span>{pick === w ? "แตะบนแผนที่…" : (w === "origin" ? "A" : "B") + " บนแผนที่"}</span>
          </button>
        ))}
      </div>

      {review ? (
        <fieldset className="when">
          <legend className="when-title">ช่วงเวลาในอดีต</legend>
          <div className="period-grid">
            {REVIEW_PERIODS.map((p) => (
              <button key={p.id} type="button" className={"period-btn" + (reviewPeriod && reviewPeriod.id === p.id ? " is-on" : "")}
                aria-pressed={!!reviewPeriod && reviewPeriod.id === p.id} onClick={() => onReviewPeriod(p)}>
                <b>{p.label}</b><span>{fmtThaiDate(p.start)} – {fmtThaiDate(p.end)}</span>
              </button>
            ))}
          </div>
          <div className="period-custom">
            <label>ตั้งแต่ (กำหนดเอง)
              <input type="date" min={REVIEW_MIN} max={REVIEW_MAX} value={custom ? reviewPeriod.start : ""}
                onChange={(e) => onReviewPeriod({ id: "custom", label: "ช่วงที่เลือกเอง", start: e.target.value, end: custom && reviewPeriod.end >= e.target.value ? reviewPeriod.end : e.target.value })} />
            </label>
            <label>ถึง
              <input type="date" min={REVIEW_MIN} max={REVIEW_MAX} value={custom ? reviewPeriod.end : ""}
                onChange={(e) => onReviewPeriod({ id: "custom", label: "ช่วงที่เลือกเอง", start: custom ? reviewPeriod.start : e.target.value, end: e.target.value })} />
            </label>
          </div>
          <p className="fine">ได้ตั้งแต่ 1 ม.ค. 2567 – 30 ก.ย. 2569 ครั้งละไม่เกิน {REVIEW_MAX_DAYS} วัน · ปี 2569 คือข้อมูลที่โมเดลไม่เคยเห็น</p>
          {problem && custom && <p className="notice">{problem}</p>}
        </fieldset>
      ) : (
      <fieldset className="when">
        <legend className="when-title">ออกเดินทางเมื่อไร</legend>
        <div className="day-row">
          <button type="button" className={"day-btn" + (when.date === today ? " is-on" : "")} aria-pressed={when.date === today} onClick={() => onWhen({ date: today })}>วันนี้</button>
          <button type="button" className={"day-btn" + (when.date === tomorrow ? " is-on" : "")} aria-pressed={when.date === tomorrow} onClick={() => onWhen({ date: tomorrow })}>พรุ่งนี้</button>
          <label className={"day-btn day-pick" + (other ? " is-on" : "")}>
            <span>{other && when.date ? fmtThaiDate(when.date) : "เลือกวัน"}</span>
            <input type="date" min={DATE_MIN} max={DATE_MAX} value={when.date} aria-label="เลือกวันที่ออกเดินทาง"
              onChange={(e) => onWhen({ date: e.target.value })} />
          </label>
        </div>
        <label className="time-row">
          <span>เวลาออก</span>
          <input type="time" step={300} required value={when.time} onChange={(e) => onWhen({ time: e.target.value })} />
        </label>
      </fieldset>
      )}

      <div className="cta-wrap">
        <button type="button" className="btn btn-primary btn-block btn-lg" disabled={!canRoute} onClick={onSubmit}>
          {review ? "ย้อนดูผลเส้นทางนี้" : "ตรวจเส้นทางนี้"}
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h14" /><path d="M13 6l6 6-6 6" /></svg>
        </button>
      </div>
      <div className="trip-status" aria-live="polite">
        {trip.status === "loading" && <Loading text="กำลังหาเส้นทาง…" />}
        {trip.status === "error" && <ErrorBox title={trip.title} text={trip.text} technical={trip.tech} onRetry={onSubmit} />}
        {trip.status === "hint" && <p className="notice notice-info">เลือกผลค้นหาที่ถูกต้องทั้งสองช่อง — ม.ศรีปทุมมีหลายวิทยาเขต และ “เขาใหญ่” มีหลายแห่ง</p>}
      </div>
      <button type="button" className="link-btn example-link" onClick={onExample}>ลองตัวอย่าง: ม.ศรีปทุม → อช.เขาใหญ่</button>
    </section>
  );
}
