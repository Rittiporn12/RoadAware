// The whole route A→B on one strip, with the colour key and coverage beside it (so the map itself stays clean).
// Grey hatched = no forecast coverage. Numbered buttons jump to zones.
import { LEVELS, LEVEL_ORDER } from "../config.js";
import { bkkToEpoch, epochToBkk } from "../lib/util.js";

function Key() {
  return (
    <span className="ribbon-key" aria-label="คำอธิบายสี">
      {LEVEL_ORDER.map((k) => <span key={k}><i style={{ background: LEVELS[k].hex }} />{LEVELS[k].label}</span>)}
      <span><i className="key-unknown" />ไม่มีข้อมูล</span>
    </span>
  );
}

export default function RouteRibbon({ ribbon, zones, route, when, selectedKey, onSelectZone, compact }) {
  const depart = bkkToEpoch(when.date, when.time);
  const arrive = epochToBkk(depart + route.duration * 1000).clock;
  const covered = Math.round(ribbon.coverage * 100);
  // Badges closer than ~5% of the strip go on a second row so numbers never overlap.
  const rows = {};
  let lastLeft = -100, lastRow = 0, twoRows = false;
  for (const z of zones) {
    const left = ((z.startM + z.endM) / 2 / route.distance) * 100;
    const row = left - lastLeft < 5 ? 1 - lastRow : 0;
    if (row) twoRows = true;
    rows[z.key] = row;
    lastLeft = left; lastRow = row;
  }
  return (
    <div className={"ribbon" + (compact ? " ribbon-compact" : "")}>
      {!compact && (
        <div className="ribbon-head">
          <span className="ribbon-title">เส้นทาง A → B</span>
          <Key />
        </div>
      )}
      <div className={"ribbon-track-wrap" + (zones.length ? (twoRows ? " has-2rows" : " has-zones") : "")}>
        <div className="ribbon-track" role="img" aria-label={"แถบเส้นทาง ประเมินได้ราว " + covered + "% ของระยะทาง"}>
          {ribbon.pieces.map((p, i) => (
            <span key={i} className={p.level ? "rp" : "rp rp-unknown"} style={{ flexGrow: p.n, background: p.level ? LEVELS[p.level].hex : undefined }} />
          ))}
        </div>
        {zones.map((z) => {
          const left = ((z.startM + z.endM) / 2 / route.distance) * 100;
          const lv = LEVELS[z.level];
          return (
            <button key={z.key} type="button" className={"ribbon-zone row-" + (rows[z.key] || 0) + (z.key === selectedKey ? " is-on" : "")}
              style={{ left: "calc(" + left.toFixed(2) + "% - 12px)", background: lv.hex, color: lv.ink }}
              aria-label={"โซน " + z.n + " " + lv.label} onClick={() => onSelectZone(z.key)}>{z.n}</button>
          );
        })}
      </div>
      <div className="ribbon-axis">
        <span>A · {when.time}</span>
        <span className="ribbon-cov">ประเมินได้ {covered}% ของเส้นทาง</span>
        <span>B · {arrive}</span>
      </div>
      {compact && <div className="ribbon-key-row"><Key /></div>}
    </div>
  );
}
