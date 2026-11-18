import { useState } from "react";
import { LEVELS } from "../config.js";
import { Dot } from "./common.jsx";

export default function SpotList({ spots, selectedKey, titleOf, onSelect }) {
  const [showLow, setShowLow] = useState(false);
  const sorted = [...spots].sort((a, b) => LEVELS[b.primary.level].rank - LEVELS[a.primary.level].rank ||
    (b.primary.pred.density_per_km || 0) - (a.primary.pred.density_per_km || 0));
  const high = sorted.filter((g) => LEVELS[g.primary.level].rank >= 2);
  const low = sorted.length - high.length;
  const shown = high.length === 0 || showLow ? sorted : high;
  return (
    <>
      <ol className="spot-list">
        {shown.map((g) => (
          <li key={g.key}>
            <button type="button" className={"spot-btn" + (g.key === selectedKey ? " is-selected" : "")} onClick={() => onSelect(g.key)}>
              <Dot hex={g.primary.hex} />
              <span className="spot-main">
                <span className="spot-title">{LEVELS[g.primary.level].title}</span>
                <span className="spot-sub">{titleOf(g)} · ผ่านราว {g.primary.eta.clock}</span>
              </span>
              <span className="spot-km">กม. {Math.round(g.primary.alongM / 1000)}</span>
            </button>
          </li>
        ))}
      </ol>
      {high.length > 0 && low > 0 && (
        <button type="button" className="btn btn-ghost btn-block" style={{ marginTop: 8 }} onClick={() => setShowLow((v) => !v)}>
          {showLow ? "ซ่อนจุดระดับต่ำกว่าค่ากลาง" : "แสดงจุดระดับต่ำกว่าค่ากลางอีก " + low + " จุด"}
        </button>
      )}
    </>
  );
}
