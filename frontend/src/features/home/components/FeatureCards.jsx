import Icon from "../../../components/common/Icon";
import { features } from "../data/homeContent";
import "../styles/getting-started.css";
export default function FeatureCards() {
  return (
    <section
      className="container feature-grid"
      aria-label="บริการของ RoadAware"
    >
      {features.map((feature) => (
        <button type="button" className="feature-card" key={feature.title}>
          <span className={`feature-icon feature-icon--${feature.color}`}>
            <Icon name={feature.icon} size={36} />
          </span>
          <span className="feature-content">
            <span className="feature-title">{feature.title}</span>
            <span className="feature-description">
              {feature.description}
              <br />
              {feature.detail}
            </span>
          </span>
          <Icon name="chevron" className="feature-chevron" size={19} />
        </button>
      ))}
    </section>
  );
}
