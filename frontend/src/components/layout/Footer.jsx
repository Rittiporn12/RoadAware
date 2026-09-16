import Icon from "../common/Icon";
export default function Footer() {
  return (
    <footer className="container site-footer">
      <p>
        <Icon name="shield" size={15} /> ต้นแบบเพื่อการศึกษา <span>•</span>{" "}
        ข้อมูลในภาพเป็นตัวอย่าง
      </p>
      <span className="footer-caption">เดินทางอย่างมั่นใจ ไปด้วยกัน</span>
      <button type="button" className="chat-launcher" aria-label="ถาม RoadAware">
        <Icon name="chat" size={22} />
        <span>ถาม RoadAware</span>
      </button>
    </footer>
  );
}
