// The whole route A→B on one strip.
//  trip view (default): red = the numbered hotspots of THIS trip, blue = evaluated, hatched grey = no data
//  national view:       each piece coloured by its national level (where it sits among all roads in Thailand)
import { LEVELS, LEVEL_ORDER, ROUTE_HEX, HOT_HEX } from "../config.js";
import { bkkToEpoch, epochToBkk } from "../lib/util.js";

export function RouteKey({ mode }) {
  if (mode === "national") {
    return (
      <span className="ribbon-key" aria-label="คำอธิบายสีระดับประเทศ">
        {LEVEL_ORDER.map((k) => <span key={k}><i style={{ background: LEVELS[k].hex }} />{LEVELS[k].label}</span>)}
        <span><i className="key-unknown" />ถนนท้องถิ่น (ยังไม่ประเมิน)</span>
      </span>
    );
  }
  return (
    <span className="ribbon-key" aria-label="คำอธิบายแถบเส้นทาง">
      <span><b className="key-num">1</b>จุดที่ควรระวังที่สุดของทริปนี้</span>
      <span><i style={{ background: ROUTE_HEX }} />ประเมินแล้ว</span>
      <span><i className="key-unknown" />ถนนท้องถิ่น (ยังไม่ประเมิน)</span>
    </span>
  );
}

export default function RouteRibbon({ ribbon, zones, route, when, selectedKey, onSelectZone, compact, mode }) {
  const depart = bkkToEpoch(when.date, when.time);
  const arrive = epochToBkk(depart + route.duration * 1000).clock;
  const covered = Math.round(ribbon.coverage * 100);
  const colourOf = (p) => (!p.level ? undefined : mode === "national" ? LEVELS[p.level].hex : p.hot ? HOT_HEX : ROUTE_HEX);
  const badgeColour = (z) => (mode === "national" ? LEVELS[z.level] : { hex: HOT_HEX, ink: "#FFFFFF" });
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
          <span className="ribbon-title">เส้นทาง A → B {mode === "national" ? "· สีเทียบทั้งประเทศ" : "· จุดที่ควรระวังของทริปนี้"}</span>
          <span className="ribbon-hint">แตะหมายเลขเพื่อดูรายละเอียด</span>
        </div>
      )}
      <div className={"ribbon-track-wrap" + (zones.length ? (twoRows ? " has-2rows" : " has-zones") : "")}>
        <div className="ribbon-track" role="img" aria-label={"แถบเส้นทาง ประเมินได้ราว " + covered + "% ของระยะทาง"}>
          {ribbon.pieces.map((p, i) => (
            <span key={i} className={p.level ? "rp" : "rp rp-unknown"} style={{ flexGrow: p.n, background: colourOf(p) }} />
          ))}
        </div>
        {zones.map((z) => {
          const left = ((z.startM + z.endM) / 2 / route.distance) * 100;
          const c = badgeColour(z);
          return (
            <button key={z.key} type="button" className={"ribbon-zone row-" + (rows[z.key] || 0) + (z.key === selectedKey ? " is-on" : "")}
              style={{ left: "calc(" + left.toFixed(2) + "% - 12px)", background: c.hex, color: c.ink }}
              aria-label={"จุดที่ " + z.n + " ผ่านราว " + z.eta.clock} onClick={() => onSelectZone(z.key)}>{z.n}</button>
          );
        })}
      </div>
      <div className="ribbon-axis">
        <span>A · {when.time}</span>
        <span className="ribbon-cov">ประเมินได้ {covered}% ของเส้นทาง</span>
        <span>B · {arrive}</span>
      </div>
      {compact && <div className="ribbon-key-row"><RouteKey mode={mode} /></div>}
    </div>
  );
}
