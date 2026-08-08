"use client";

/**
 * TopicsList — Displays the 4 target topics with active/completed indicators.
 */
export default function TopicsList({ topics, currentQuestion, totalQuestions = 8 }) {
  if (!topics || topics.length === 0) return null;

  // Each topic gets ~2 questions: topic index = floor((questionNum - 1) / 2)
  const activeTopicIndex = Math.min(
    Math.floor((currentQuestion - 1) / 2),
    topics.length - 1
  );

  return (
    <div className="topics-list">
      <h3 className="topics-title">
        <span className="topics-icon">◆</span>
        Assessment Topics
      </h3>

      <div className="topics-container">
        {topics.map((topic, index) => {
          const isActive = index === activeTopicIndex;
          const isComplete = index < activeTopicIndex;
          const isPending = index > activeTopicIndex;

          return (
            <div
              key={index}
              className={`topic-item ${
                isActive ? "topic-active" : ""
              } ${isComplete ? "topic-complete" : ""} ${
                isPending ? "topic-pending" : ""
              }`}
            >
              {/* Status indicator */}
              <div className="topic-status">
                {isComplete ? (
                  <span className="topic-check">✓</span>
                ) : isActive ? (
                  <span className="topic-pulse" />
                ) : (
                  <span className="topic-dot" />
                )}
              </div>

              {/* Topic info */}
              <div className="topic-info">
                <span className="topic-day">Day {topic.day}</span>
                <span className="topic-name">{topic.topic}</span>
              </div>

              {/* Active indicator line */}
              {isActive && <div className="topic-active-line" />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
