import Brand from "../common/Brand";
import Button from "../common/Button";
import "./layout.css";
export default function Header() {
  return (
    <header className="site-header">
      <div className="container header-inner">
        <Brand />
        <nav className="main-nav" aria-label="เมนูหลัก">
          <button
            type="button"
            className="nav-item is-active"
            aria-current="page"
          >
            หน้าแรก
          </button>
          <button type="button" className="nav-item">
            แผนที่ความเสี่ยง
          </button>
          <button type="button" className="nav-item">
            เกี่ยวกับโครงการ
          </button>
        </nav>
        <div className="header-actions">
          <Button variant="outline">เข้าสู่ระบบ</Button>
          <Button icon="map">เปิดแผนที่</Button>
        </div>
      </div>
    </header>
  );
}
