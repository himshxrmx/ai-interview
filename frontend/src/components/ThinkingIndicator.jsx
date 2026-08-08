"use client";

/**
 * ThinkingIndicator — Pulsing terminal cursor animation for "AI is thinking..." state.
 */
export default function ThinkingIndicator() {
  return (
    <div className="thinking-indicator">
      <div className="thinking-avatar">
        <span className="thinking-avatar-icon">AI</span>
      </div>
      <div className="thinking-bubble">
        <div className="thinking-dots">
          <span className="thinking-dot" style={{ animationDelay: "0s" }} />
          <span className="thinking-dot" style={{ animationDelay: "0.2s" }} />
          <span className="thinking-dot" style={{ animationDelay: "0.4s" }} />
        </div>
        <span className="thinking-text">Analyzing response...</span>
        <div className="thinking-cursor" />
      </div>
    </div>
  );
}
