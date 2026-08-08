"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { startInterview, sendMessage } from "@/lib/api";
import CandidateProfile from "@/components/CandidateProfile";
import ProgressTracker from "@/components/ProgressTracker";
import TopicsList from "@/components/TopicsList";
import ChatInterface from "@/components/ChatInterface";
import InterviewReport from "@/components/InterviewReport";

function InterviewContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const candidateId = searchParams.get("candidate_id");

  // ─── State ─────────────────────────────────────────────────────────────
  const [sessionId, setSessionId] = useState(null);
  const [profileSummary, setProfileSummary] = useState(null);
  const [messages, setMessages] = useState([]);
  const [questionCount, setQuestionCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [graderPayload, setGraderPayload] = useState(null);
  const [inputValue, setInputValue] = useState("");
  const [error, setError] = useState(null);
  const [isInitializing, setIsInitializing] = useState(true);

  // ─── Initialize Session ────────────────────────────────────────────────
  useEffect(() => {
    if (!candidateId) {
      router.push("/setup");
      return;
    }

    async function init() {
      try {
        setIsInitializing(true);
        const data = await startInterview(candidateId);
        setSessionId(data.session_id);
        setProfileSummary(data.profile_summary);
        setQuestionCount(1);
        setMessages([
          {
            role: "assistant",
            content: data.first_message,
          },
        ]);
      } catch (err) {
        setError(`Failed to start interview: ${err.message}`);
      } finally {
        setIsInitializing(false);
      }
    }

    init();
  }, [candidateId, router]);

  // ─── Send Message Handler ─────────────────────────────────────────────
  const handleSubmit = useCallback(
    async (message) => {
      if (!sessionId || isLoading) return;

      // Add user message optimistically
      setMessages((prev) => [...prev, { role: "user", content: message }]);
      setInputValue("");
      setIsLoading(true);
      setError(null);

      try {
        const data = await sendMessage(sessionId, message);

        // Add AI response
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.ai_message },
        ]);

        setQuestionCount(data.question_count);

        if (data.is_complete) {
          setIsComplete(true);
          setGraderPayload(data.grader_payload);
        }
      } catch (err) {
        setError(`Failed to send message: ${err.message}`);
        // Remove the optimistic user message on error
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, isLoading]
  );

  // ─── Render ────────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      {/* Background effects */}
      <div className="bg-grid" />
      <div className="bg-glow bg-glow-1" />
      <div className="bg-glow bg-glow-2" />

      {/* Main Layout */}
      <div className="split-layout">
        {/* ── Left Pane: Context Dashboard (30%) ─────────────────────── */}
        <aside className="left-pane">
          <div className="pane-inner">
            {/* Logo */}
            <div className="brand">
              <div className="brand-icon">⚡</div>
              <div className="brand-text">
                <h1 className="brand-name">AB Talks</h1>
                <p className="brand-tagline">AI Interview Agent</p>
              </div>
            </div>

            {/* Candidate Profile */}
            {isInitializing ? (
              <div className="skeleton-card">
                <div className="skeleton-line skeleton-lg" />
                <div className="skeleton-line skeleton-md" />
                <div className="skeleton-line skeleton-sm" />
              </div>
            ) : (
              <CandidateProfile profile={profileSummary} />
            )}

            {/* Progress Tracker */}
            <ProgressTracker current={questionCount} total={8} />

            {/* Topics List */}
            <TopicsList
              topics={profileSummary?.target_topics || []}
              currentQuestion={questionCount}
            />

            {/* Session Info */}
            {sessionId && (
              <div className="session-info">
                <span className="session-label">Session</span>
                <span className="session-id">
                  {sessionId.slice(0, 8)}...
                </span>
              </div>
            )}
          </div>
        </aside>

        {/* ── Right Pane: Interview Terminal (70%) ───────────────────── */}
        <main className="right-pane">
          {/* Error Banner */}
          {error && (
            <div className="error-banner">
              <span className="error-icon">⚠</span>
              <span className="error-text">{error}</span>
              <button
                className="error-dismiss"
                onClick={() => setError(null)}
              >
                ✕
              </button>
            </div>
          )}

          {/* Show report when complete, otherwise show chat */}
          {isComplete && graderPayload ? (
            <InterviewReport payload={graderPayload} />
          ) : (
            <ChatInterface
              messages={messages}
              isLoading={isLoading || isInitializing}
              inputValue={inputValue}
              onInputChange={setInputValue}
              onSubmit={handleSubmit}
              isComplete={isComplete}
            />
          )}
        </main>
      </div>
    </div>
  );
}

export default function Home() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-[#0a0e17] text-gray-400">Loading...</div>}>
      <InterviewContent />
    </Suspense>
  );
}
