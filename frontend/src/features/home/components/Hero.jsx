import Button from "../../../components/common/Button";
import Icon from "../../../components/common/Icon";
import MapPreview from "./MapPreview";
import "../styles/hero.css";
export default function Hero() {
  return (
    <section className="hero">
      <div className="hero-scenery" aria-hidden="true">
        <div className="skyline" />
        <div className="road" />
      </div>
      <div className="container hero-inner">
        <div className="hero-copy">
          <div className="eyebrow">
            <span />
            รู้จุดเสี่ยง เข้าใจเส้นทาง
          </div>
          <h1>
            มองเห็นความเสี่ยง
            <br />
            <span>ก่อนออกเดินทาง</span>
          </h1>
          <p className="hero-description">
            วิเคราะห์ข้อมูลอุบัติเหตุในอดีต
            และเปิดโอกาสให้ทุกคนร่วมรายงานจุดเสี่ยงบนท้องถนน
            เพื่อเส้นทางที่ปลอดภัยยิ่งขึ้นสำหรับทุกคน
          </p>
          <div className="hero-actions">
            <Button icon="map" trailingIcon="arrow">
              สำรวจแผนที่
            </Button>
            <Button variant="outline" icon="pin">
              รายงานจุดเสี่ยง
            </Button>
          </div>
          <div className="hero-note">
            <Icon name="shield" size={17} />
            <span>เส้นทางที่ดีกว่า เริ่มจากข้อมูลของทุกคน</span>
          </div>
        </div>
        <MapPreview />
      </div>
    </section>
  );
}
