// Drive mode — the panel while travelling. Voice-first: big type, few controls, nothing to read while driving.
// Turn-by-turn directions are NOT provided here (use your usual navigation app); this only warns about the
// numbered points of this trip as you approach them.
import { fmtDist, nextZone } from "../lib/drive.js";
import { topValues, tipsFor } from "../lib/zones.js";
import { fmtKm } from "../lib/util.js";
import { HOT_HEX, LEVELS } from "../config.js";

export function DriveStart({ hasVoice, onStart, onCancel }) {
  return (
    <div className="drive-start">
      <h2 className="verdict-title">เริ่มเดินทาง</h2>
      <p className="verdict-sub">ระบบจะติดตามตำแหน่งและ<b>พูดเตือน</b>ก่อนถึงจุดที่ควรระวังแต่ละจุด (2 กม. และ 500 ม.) ใช้คู่กับแอปนำทางที่คุณใช้อยู่ได้ เพราะส่วนนี้ไม่บอกทางเลี้ยว</p>
      <p className="notice">ให้<b>ผู้โดยสาร</b>เป็นคนใช้งาน ห้ามแตะหรืออ่านจอขณะขับ · เสียงเตือนเป็นข้อมูลเปรียบเทียบ ไม่ใช่การรับประกันความปลอดภัย</p>
      {!hasVoice && <p className="fine">เบราว์เซอร์นี้ไม่มีเสียงภาษาไทย จะแสดงเป็นข้อความเตือนบนจอแทน</p>}
      <div className="drive-start-btns">
        <button type="button" className="btn btn-primary" onClick={() => onStart("gps")}>เริ่มด้วยตำแหน่งจริง (GPS)</button>
        <button type="button" className="btn btn-ghost" onClick={() => onStart("sim")}>จำลองการขับ (สาธิต)</button>
        <button type="button" className="link-btn" onClick={onCancel}>ยกเลิก</button>
      </div>
    </div>
  );
}

export function DriveBanner({ drive, zones, route }) {
  if (!drive || drive.alongM == null) return null;
  if (drive.arrived) return <div className="drive-banner drive-done" role="status">ถึงปลายทางแล้ว</div>;
  if (drive.off) return <div className="drive-banner drive-off" role="status">ไม่พบตำแหน่งบนเส้นทาง — กลับเข้าเส้นทาง หรือตรวจเส้นทางใหม่</div>;
  const nz = nextZone(zones, drive.alongM);
  if (!nz) return <div className="drive-banner" role="status">ไม่มีจุดที่ควรระวังข้างหน้าแล้ว · อีก {fmtDist(route.distance - drive.alongM)} ถึงปลายทาง</div>;
  return (
    <div className={"drive-banner" + (nz.inside ? " drive-inside" : nz.distM <= 2000 ? " drive-near" : "")} role="status" aria-live="polite">
      <span className="drive-num">{nz.zone.n}</span>
      <span className="drive-main">
        <b>{nz.inside ? "อยู่ในจุดที่ควรระวัง" : "จุดที่ควรระวัง อีก " + fmtDist(nz.distM)}</b>
        <span>{nz.zone.road}{nz.zone.provinces.length ? " · " + nz.zone.provinces[0] : ""}</span>
      </span>
    </div>
  );
}

export default function DriveMode({ drive, zones, route, history, onStop, onMute, onSpeed, onTestVoice }) {
  const along = drive.alongM || 0;
  const nz = nextZone(zones, along);
  const left = Math.max(0, route.distance - along);
  const avg = route.distance / Math.max(route.duration, 1);
  const minsLeft = Math.round(left / avg / 60);
  const entry = nz ? history[nz.zone.key] : null;
  const agg = entry && entry.status === "ok" ? entry.agg : null;
  const type = agg ? topValues(agg, "accident_type", 1)[0] : null;
  const tips = agg ? tipsFor(agg).slice(0, 2) : [];
  const upcoming = zones.filter((z) => z.endM >= along);
  return (
    <div className="drive">
      <div className="drive-head">
        <span className="drive-mode">{drive.source === "sim" ? "จำลองการขับ ×" + drive.speedX : "ติดตามตำแหน่งจริง"}</span>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onStop}>หยุด</button>
      </div>

      {drive.arrived ? (
        <div className="drive-card"><h2 className="verdict-title">ถึงปลายทางแล้ว</h2><p className="verdict-sub">ผ่านจุดที่ควรระวังครบ {zones.length} จุด</p></div>
      ) : drive.off ? (
        <div className="drive-card drive-card-off"><h2 className="verdict-title">ไม่พบตำแหน่งบนเส้นทาง</h2><p className="verdict-sub">ถ้าเปลี่ยนเส้นทาง ให้หยุดแล้วตรวจเส้นทางใหม่จากตำแหน่งปัจจุบัน</p></div>
      ) : nz ? (
        <div className={"drive-card" + (nz.inside ? " drive-card-in" : "")}>
          <p className="drive-k">{nz.inside ? "กำลังผ่าน" : "ถัดไป"} · จุดที่ {nz.zone.n} จาก {zones.length}</p>
          <p className="drive-big">{nz.inside ? "อยู่ในจุดที่ควรระวัง" : "อีก " + fmtDist(nz.distM)}</p>
          <p className="drive-road">{nz.zone.road}{nz.zone.provinces.length ? " · " + nz.zone.provinces.join("–") : ""} · ยาว {fmtKm(nz.zone.lengthM)}</p>
          <p className="drive-meta">ระดับประเทศ <b className={"lvl-" + nz.zone.level}>{LEVELS[nz.zone.level].label}</b>{type ? " · ที่ผ่านมาส่วนใหญ่: " + type.value : ""}</p>
          {tips.length > 0 && <ul className="drive-tips">{tips.map((t) => <li key={t}>{t}</li>)}</ul>}
        </div>
      ) : (
        <div className="drive-card"><p className="drive-big">ไม่มีจุดที่ควรระวังข้างหน้าแล้ว</p><p className="verdict-sub">ขับขี่ด้วยความระมัดระวังตามปกติ</p></div>
      )}

      <div className="drive-progress">
        <div className="drive-bar"><span style={{ width: Math.min(100, (along / route.distance) * 100) + "%" }} />
          {zones.map((z) => <i key={z.key} style={{ left: (z.startM / route.distance) * 100 + "%", background: HOT_HEX }} title={"จุดที่ " + z.n} />)}
        </div>
        <p className="fine">ไปแล้ว {fmtKm(along)} จาก {fmtKm(route.distance)} · เหลือราว {minsLeft >= 60 ? Math.floor(minsLeft / 60) + " ชม. " : ""}{minsLeft % 60} นาที · ข้างหน้าอีก {upcoming.length} จุด</p>
      </div>

      <div className="drive-ctrls">
        <button type="button" className={"btn btn-sm" + (drive.muted ? " btn-ghost" : " btn-primary")} aria-pressed={!drive.muted} onClick={onMute}>{drive.muted ? "เสียงเตือน: ปิด" : "เสียงเตือน: เปิด"}</button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onTestVoice}>ทดสอบเสียง</button>
        {drive.source === "sim" && [1, 5, 10, 30, 60].map((x) => (
          <button key={x} type="button" className={"btn btn-sm" + (drive.speedX === x ? " btn-primary" : " btn-ghost")} onClick={() => onSpeed(x)}>×{x}</button>
        ))}
      </div>
      {drive.lastSaid && <p className="drive-said">🔊 “{drive.lastSaid}”</p>}
      <p className="fine">ให้ผู้โดยสารเป็นคนใช้งาน · ไม่ใช่ระบบนำทาง ไม่บอกทางเลี้ยว · ระดับเป็นการเทียบ ไม่ใช่โอกาสเกิดเหตุของคุณ</p>
    </div>
  );
}
