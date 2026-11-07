export default function Progress({ value, label = true, total, done }) {
  return (
    <div>
      {label && (
        <div className="progress-row">
          <span>Progress</span>
          <span>
            {done ?? ""}{total != null ? `/${total} tasks` : ""} · {value}%
          </span>
        </div>
      )}
      <div className="progress">
        <div style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}
