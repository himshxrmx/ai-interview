"use client";

/**
 * ProgressTracker — Visual progress bar showing question X of 8.
 */
export default function ProgressTracker({ current, total = 8 }) {
  const percentage = Math.min((current / total) * 100, 100);

  return (
    <div className="progress-tracker">
      <div className="progress-header">
        <h3 className="progress-title">Interview Progress</h3>
        <span className="progress-count">
          <span className="progress-current">{Math.min(current, total)}</span>
          <span className="progress-divider">/</span>
          <span className="progress-total">{total}</span>
        </span>
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${percentage}%` }}
        />
        <div className="progress-bar-glow" style={{ width: `${percentage}%` }} />
      </div>

      {/* Segment Indicators */}
      <div className="progress-segments">
        {Array.from({ length: total }, (_, i) => (
          <div
            key={i}
            className={`progress-segment ${
              i < current ? "segment-complete" : ""
            } ${i === current - 1 ? "segment-active" : ""}`}
          >
            <div className="segment-dot" />
            <span className="segment-label">Q{i + 1}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
