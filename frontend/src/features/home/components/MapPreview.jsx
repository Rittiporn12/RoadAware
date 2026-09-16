import Icon from "../../../components/common/Icon";
import Button from "../../../components/common/Button";
import MapArtwork from "./MapArtwork";
import { markers } from "../data/homeContent";
import "../styles/map-preview.css";
const legend = [
  { icon: "map", text: "ทั้งหมด", color: "blue" },
  { icon: "warning", text: "อุบัติเหตุ", color: "red" },
  { icon: "pin", text: "จุดเสี่ยง", color: "amber" },
  { icon: "warning", text: "สิ่งกีดขวาง", color: "amber" },
  { icon: "document", text: "รายงานจากประชาชน", color: "green" },
];
export default function MapPreview() {
  return (
    <div
      className="map-preview"
      aria-label="แผนที่จำลองจุดเสี่ยงในกรุงเทพมหานคร"
    >
      <MapArtwork />
      <div className="map-tools">
        <div className="map-search">
          <Icon name="search" size={19} />
          <span>ค้นหาสถานที่ ถนน หรือพื้นที่</span>
        </div>
        <div className="map-legend">
          {legend.map((item, index) => (
            <div
              key={item.text}
              className={`legend-item ${index === 0 ? "selected" : ""}`}
            >
              <Icon
                name={item.icon}
                className={`color-${item.color}`}
                size={19}
              />
              <span>{item.text}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="map-pins" aria-hidden="true">
        {markers.map((marker, i) => (
          <span
            key={i}
            className={`map-pin map-pin--${marker.type}`}
            style={{ left: `${marker.x}%`, top: `${marker.y}%` }}
          >
            <span>{marker.label || "!"}</span>
          </span>
        ))}
      </div>
      <aside className="risk-card">
        <div className="risk-card-top">
          <span>
            <span className="status-dot" /> ข้อมูลตัวอย่าง
          </span>
          <Icon name="shield" size={17} />
        </div>
        <div className="risk-title">
          <span className="warning-badge">
            <Icon name="warning" size={27} />
          </span>
          <h3>พื้นที่เฝ้าระวัง</h3>
        </div>
        <h4>แยกรัชดา - ลาดพร้าว</h4>
        <p className="risk-location">เขตห้วยขวาง กรุงเทพมหานคร</p>
        <div className="risk-tags">
          <span>อุบัติเหตุบ่อย</span>
          <span>การจราจรหนาแน่น</span>
          <span>เสี่ยงในช่วงกลางคืน</span>
        </div>
        <div className="risk-description">
          <h4>
            <Icon name="warning" size={20} /> ลักษณะความเสี่ยง
          </h4>
          <p>
            เกิดอุบัติเหตุจากการเปลี่ยนเลนกะทันหัน
            <br />
            และการฝ่าฝืนสัญญาณไฟ
          </p>
        </div>
        <Button icon="pin">ดูรายละเอียดบนแผนที่</Button>
      </aside>
      <div className="map-controls" aria-hidden="true">
        <span>
          <Icon name="target" size={20} />
        </span>
        <span>
          <Icon name="plus" size={20} />
        </span>
        <span>
          <Icon name="minus" size={20} />
        </span>
      </div>
      <div className="map-scale" aria-hidden="true">
        <span>0</span>
        <span>2</span>
        <span>5 กม.</span>
      </div>
      <span className="map-caption">
        แผนที่จำลอง · ข้อมูลเพื่อการแสดงผลเท่านั้น
      </span>
    </div>
  );
}
