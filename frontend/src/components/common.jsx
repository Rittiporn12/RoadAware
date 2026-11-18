export function Loading({ text }) {
  return (
    <div className="loading">
      <span className="spinner" aria-hidden="true" />
      <span>{text}</span>
    </div>
  );
}

export function Progress({ text, frac }) {
  return (
    <div>
      <Loading text={text} />
      {typeof frac === "number" && (
        <div className="progress"><span style={{ width: Math.round(Math.max(0, Math.min(1, frac)) * 100) + "%" }} /></div>
      )}
    </div>
  );
}

export function ErrorBox({ title, text, onRetry, technical }) {
  return (
    <div className="error-box" role="alert">
      <strong>{title}</strong>
      <span>{text}</span>
      {technical && (
        <details>
          <summary>รายละเอียดทางเทคนิค</summary>
          <div className="mono">{technical}</div>
        </details>
      )}
      {onRetry && <button type="button" className="btn btn-ghost btn-small" onClick={onRetry}>ลองอีกครั้ง</button>}
    </div>
  );
}

export function Dot({ hex }) {
  return <span className="dot" style={{ background: hex }} aria-hidden="true" />;
}

export function Bars({ title, rows, note }) {
  return (
    <div className="cause-block">
      <h3>{title}</h3>
      {rows.map((r) => (
        <div className="bar-row" key={r.label}>
          <span className="bar-label">{r.label}</span>
          <span className="bar-pct">{r.right}</span>
          <div className="bar-track"><span style={{ width: Math.round(Math.max(0, Math.min(1, r.frac)) * 100) + "%" }} /></div>
        </div>
      ))}
      {note && <p className="help">{note}</p>}
    </div>
  );
}
