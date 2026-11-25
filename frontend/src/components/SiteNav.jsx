// The home page's navigation bar, in its dark state, for the other pages (แดชบอร์ด, โมเดล).
// Section links go back to the home page and scroll to that section.
const goHomeSection = (id) => {
  try { window.sessionStorage.setItem("roadaware.scrollTo", id); } catch (_) { /* ignore */ }
  window.location.hash = "#/";
};
const toTop = () => {
  const el = document.querySelector(".dash");
  if (el) el.scrollTo({ top: 0, behavior: "smooth" });
};

export default function SiteNav({ active }) {
  const page = (key, label) => (
    active === key
      ? <button type="button" aria-current="page" onClick={toTop}>{label}</button>
      : <button type="button" onClick={() => { window.location.hash = "#/" + key; }}>{label}</button>
  );
  return (
    <header className="ld-nav ld-nav-solid">
      <div className="ld-wrap ld-nav-in">
        <a className="ld-brand" href="#/">
          <svg width="30" height="30" viewBox="0 0 26 26" aria-hidden="true"><circle cx="13" cy="13" r="12" fill="#FFFFFF" /><path d="M7 18 C10 12, 13 15, 19 7" stroke="#E8821E" strokeWidth="2.6" fill="none" strokeLinecap="round" /></svg>
          <span>RoadAware</span>
        </a>
        <nav className="ld-links" aria-label="เมนู">
          <button type="button" onClick={() => goHomeSection("ld-features")}>ความสามารถ</button>
          <button type="button" onClick={() => goHomeSection("ld-how")}>วิธีใช้</button>
          <button type="button" onClick={() => goHomeSection("ld-tech")}>เบื้องหลัง</button>
          {page("dashboard", "แดชบอร์ด")}
          {page("model", "โมเดล")}
        </nav>
        <span className="ld-nav-mini">
          <a href="#/dashboard" aria-current={active === "dashboard" ? "page" : undefined}>แดชบอร์ด</a>
          <a href="#/model" aria-current={active === "model" ? "page" : undefined}>โมเดล</a>
        </span>
        <a className="ld-btn ld-btn-sm" href="#/app">เริ่มใช้งาน</a>
      </div>
    </header>
  );
}
