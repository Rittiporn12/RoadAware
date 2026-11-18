import { ErrorBox } from "./common.jsx";

// One endpoint: free text + explicit search (Enter / button). Results are listed for the user to choose —
// never auto-picked (e.g. Sripatum has several campuses; "เขาใหญ่" names several places).
export default function PlaceField({ which, letter, label, placeholder, text, place, results, onText, onSearch, onChoose, onCloseResults }) {
  const inputId = which + "Input";
  return (
    <div className="pf">
      <div className="pf-row">
        <span className={"pin pin-" + letter.toLowerCase()} aria-hidden="true">{letter}</span>
        <form className="pf-form" autoComplete="off" onSubmit={(e) => { e.preventDefault(); onSearch(); }}>
          <label className="pf-label" htmlFor={inputId}>{label}</label>
          <input
            id={inputId}
            type="search"
            value={text}
            placeholder={placeholder}
            enterKeyHint="search"
            onChange={(e) => onText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Escape") onCloseResults(); }}
          />
        </form>
        {text.trim() && !place && (
          <button type="button" className="search-btn" onClick={onSearch}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
            ค้นหา
          </button>
        )}
      </div>
      {place && <p className="pf-chosen">✓ {place.sub || "เลือกแล้ว"}</p>}
      {results.status !== "idle" && (
        <ul className="results" aria-label={"ผลค้นหา" + label}>
          {results.status === "loading" && <li className="results-note">กำลังค้นหา…</li>}
          {results.status === "short" && <li className="results-note">พิมพ์ชื่อสถานที่อย่างน้อย 2 ตัวอักษร</li>}
          {results.status === "error" && (
            <li><ErrorBox title="ค้นหาสถานที่ไม่สำเร็จ" text="บริการค้นหาไม่ตอบสนอง ลองอีกครั้ง หรือเลือกจุดบนแผนที่แทน" onRetry={onSearch} technical={results.tech} /></li>
          )}
          {results.status === "ok" && results.places.length === 0 && (
            <li className="results-note">ไม่พบสถานที่ในประเทศไทย ลองพิมพ์ให้เจาะจงขึ้น เช่น ใส่ชื่ออำเภอหรือจังหวัด</li>
          )}
          {results.status === "ok" && results.places.length > 1 && <li className="results-note">มีหลายแห่งที่ชื่อใกล้กัน เลือกแห่งที่ถูกต้อง</li>}
          {results.status === "ok" && results.places.map((p) => (
            <li key={p.id}>
              <button type="button" className="result-btn" onClick={() => onChoose(p)}>
                <span className="result-name">{p.name}</span>
                <span className="result-sub">{p.sub || "ประเทศไทย"}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
