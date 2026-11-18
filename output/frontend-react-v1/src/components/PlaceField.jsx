import { ErrorBox } from "./common.jsx";

// One endpoint: free text + explicit search, result list for disambiguation, or pick on the map.
export default function PlaceField({ which, letter, label, placeholder, text, place, results, picking, onText, onSearch, onChoose, onPick, onCloseResults }) {
  const inputId = which + "Input";
  return (
    <div className="place">
      <label className="field-label" htmlFor={inputId}>
        <span className={"pin pin-" + letter.toLowerCase()} aria-hidden="true">{letter}</span>{label}
      </label>
      <form className="search-row" autoComplete="off" onSubmit={(e) => { e.preventDefault(); onSearch(); }}>
        <input
          id={inputId}
          type="search"
          value={text}
          placeholder={placeholder}
          enterKeyHint="search"
          onChange={(e) => onText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Escape") onCloseResults(); }}
        />
        <button type="submit" className="btn btn-icon" aria-label={"ค้นหา" + label}><span className="i-search" aria-hidden="true" /></button>
      </form>
      <button type="button" className={"link-btn" + (picking ? " is-active" : "")} onClick={onPick}>
        {picking ? "กำลังเลือกบนแผนที่… (แตะเพื่อยกเลิก)" : "เลือก" + label + "บนแผนที่"}
      </button>
      {place && <p className="chosen is-chosen" aria-live="polite">{place.sub || "เลือกแล้ว"}</p>}
      {results.status !== "idle" && (
        <ul className="results-list">
          {results.status === "loading" && <li className="results-note">กำลังค้นหา…</li>}
          {results.status === "short" && <li className="results-note">พิมพ์ชื่อสถานที่อย่างน้อย 2 ตัวอักษร</li>}
          {results.status === "error" && (
            <li><ErrorBox title="ค้นหาสถานที่ไม่สำเร็จ" text="บริการค้นหาไม่ตอบสนอง ลองอีกครั้ง หรือเลือกจุดบนแผนที่แทน" onRetry={onSearch} technical={results.tech} /></li>
          )}
          {results.status === "ok" && results.places.length === 0 && (
            <li className="results-note">ไม่พบสถานที่ในประเทศไทย ลองพิมพ์ให้เจาะจงขึ้น (เช่น ใส่ชื่ออำเภอ/จังหวัด) หรือเลือกบนแผนที่</li>
          )}
          {results.status === "ok" && results.places.length > 1 && <li className="results-note">มีหลายแห่งที่ชื่อใกล้กัน โปรดเลือกแห่งที่ถูกต้อง</li>}
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
