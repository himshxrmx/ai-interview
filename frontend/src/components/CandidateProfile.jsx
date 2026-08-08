"use client";

/**
 * CandidateProfile — Displays the candidate's profile card in the left pane.
 */
export default function CandidateProfile({ profile }) {
  if (!profile) return null;

  return (
    <div className="profile-card">
      {/* Avatar & Name */}
      <div className="profile-header">
        <div className="avatar">
          <span className="avatar-initials">
            {profile.name
              ?.split(" ")
              .map((n) => n[0])
              .join("")}
          </span>
          <div className="avatar-ring" />
        </div>
        <div className="profile-name-block">
          <h2 className="profile-name">{profile.name}</h2>
          <p className="profile-cohort">{profile.cohort}</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-item">
          <span className="stat-value">
            {Math.round((profile.completion_rate || 0) * 100)}%
          </span>
          <span className="stat-label">Completion</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">
            {profile.completed_days}/{profile.total_days}
          </span>
          <span className="stat-label">Days Done</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">
            {profile.engagement?.avg_lab_score || "—"}
          </span>
          <span className="stat-label">Avg Score</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">
            {profile.engagement?.peer_review_rating || "—"}
            <span className="stat-unit">/5</span>
          </span>
          <span className="stat-label">Peer Rating</span>
        </div>
      </div>

      {/* Strengths */}
      {profile.strong_topics?.length > 0 && (
        <div className="profile-section">
          <h3 className="section-title">
            <span className="section-icon strength-icon">▲</span>
            Strengths
          </h3>
          <div className="tag-list">
            {profile.strong_topics.map((topic, i) => (
              <span key={i} className="tag tag-strength">
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Weak Areas */}
      {profile.weak_topics?.length > 0 && (
        <div className="profile-section">
          <h3 className="section-title">
            <span className="section-icon weakness-icon">▼</span>
            Growth Areas
          </h3>
          <div className="tag-list">
            {profile.weak_topics.map((topic, i) => (
              <span key={i} className="tag tag-weakness">
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
