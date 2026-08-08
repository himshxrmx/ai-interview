"use client";

import { useRef, useEffect } from "react";
import ThinkingIndicator from "./ThinkingIndicator";

/**
 * ChatInterface — Sleek chat terminal for the interview conversation.
 */
export default function ChatInterface({
  messages,
  isLoading,
  inputValue,
  onInputChange,
  onSubmit,
  isComplete,
}) {
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Focus input when not loading
  useEffect(() => {
    if (!isLoading && !isComplete) {
      inputRef.current?.focus();
    }
  }, [isLoading, isComplete]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim() && !isLoading) {
      onSubmit(inputValue.trim());
    }
  };

  return (
    <div className="chat-interface">
      {/* Terminal Header */}
      <div className="terminal-header">
        <div className="terminal-dots">
          <span className="dot dot-red" />
          <span className="dot dot-yellow" />
          <span className="dot dot-green" />
        </div>
        <span className="terminal-title">AI Interview Terminal</span>
        <div className="terminal-status">
          <span
            className={`status-indicator ${
              isComplete ? "status-complete" : "status-live"
            }`}
          />
          <span className="status-text">
            {isComplete ? "Complete" : "Live Session"}
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="messages-area">
        {messages.length === 0 && !isLoading && (
          <div className="chat-empty">
            <div className="empty-icon">⚡</div>
            <p className="empty-text">Initializing interview session...</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${
              msg.role === "assistant" ? "message-ai" : "message-user"
            }`}
          >
            {/* Avatar */}
            <div className="message-avatar">
              {msg.role === "assistant" ? (
                <span className="avatar-ai">AI</span>
              ) : (
                <span className="avatar-user">You</span>
              )}
            </div>

            {/* Content */}
            <div className="message-content">
              <div className="message-bubble">
                <p className="message-text">{msg.content}</p>
              </div>
            </div>
          </div>
        ))}

        {isLoading && <ThinkingIndicator />}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      {!isComplete && (
        <form className="input-area" onSubmit={handleSubmit}>
          <div className="input-wrapper">
            <span className="input-prompt">❯</span>
            <textarea
              ref={inputRef}
              className="chat-input"
              placeholder={
                isLoading
                  ? "Waiting for AI response..."
                  : "Type your answer here..."
              }
              value={inputValue}
              onChange={(e) => onInputChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              disabled={isLoading}
              rows={1}
            />
            <button
              type="submit"
              className="send-button"
              disabled={isLoading || !inputValue.trim()}
            >
              <span className="send-icon">↵</span>
              <span className="send-text">Send</span>
            </button>
          </div>
          <p className="input-hint">
            Press <kbd>Enter</kbd> to send, <kbd>Shift+Enter</kbd> for new line
          </p>
        </form>
      )}
    </div>
  );
}
