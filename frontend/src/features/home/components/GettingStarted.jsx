import Icon from "../../../components/common/Icon";
import { steps } from "../data/homeContent";
export default function GettingStarted() {
  return (
    <section className="container getting-started">
      <div className="section-heading">
        <div>
          <span className="section-kicker">ออกเดินทางอย่างมั่นใจ</span>
          <h2>เริ่มต้นใช้งาน RoadAware</h2>
        </div>
        <p>
          เพียงไม่กี่ขั้นตอน ก็ร่วมเป็นส่วนหนึ่งของชุมชน
          <br className="desktop-break" />
          ที่ช่วยกันสร้างถนนที่ปลอดภัยกว่าเดิม
        </p>
      </div>
      <div className="steps">
        {steps.map((step, index) => (
          <div className="step" key={step.title}>
            <span className="step-number">0{index + 1}</span>
            <span className="step-icon">
              <Icon name={step.icon} size={25} />
            </span>
            <div className="step-copy">
              <h3>{step.title}</h3>
              <p>{step.description}</p>
            </div>
            {index < steps.length - 1 && (
              <Icon name="arrow" className="step-arrow" size={28} />
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
