import { LEVELS, LEVEL_ORDER } from "../config.js";
import { Dot } from "./common.jsx";

export default function Legend({ spots, hidden, onToggle }) {
  const counts = {};
  for (const g of spots) counts[g.primary.level] = (counts[g.primary.level] || 0) + 1;
  return (
    <div className="legend">
      <p className="legend-title">ระดับเฝ้าระวัง <span className="legend-sub">(แตะเพื่อซ่อน/แสดง)</span></p>
      <div className="legend-items">
        {LEVEL_ORDER.map((lv) => (
          <button key={lv} type="button" className="legend-item" aria-pressed={!hidden.has(lv)} onClick={() => onToggle(lv)}>
            <Dot hex={LEVELS[lv].hex} />
            <span>{LEVELS[lv].title}</span>
            <span className="count">{counts[lv] || 0}</span>
          </button>
        ))}
        <div className="legend-item"><span className="legend-line" aria-hidden="true" /><span>ยังไม่มีข้อมูลประเมิน</span></div>
      </div>
    </div>
  );
}
