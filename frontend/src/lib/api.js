/**
 * API client for the AI Interview Agent backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "YOUR_AWS_API_GATEWAY_URL";

/**
 * Upload candidate data (curriculum, profile, specialization) either as text or files.
 * @param {FormData} formData - The FormData containing text fields or files.
 * @returns {Promise<{candidate_id: string}>}
 */
export async function uploadCandidateData(formData) {
  const response = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData, // fetch automatically sets Content-Type to multipart/form-data with boundary
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to upload data: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Start a new interview session.
 * @param {string} candidateId - The ID returned from the upload step
 * @returns {Promise<{session_id: string, first_message: string, profile_summary: object}>}
 */
export async function startInterview(candidateId) {
  const response = await fetch(`${API_BASE}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_id: candidateId })
  });

  if (!response.ok) {
    throw new Error(`Failed to start interview: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send a chat message and get the AI's response.
 * @param {string} sessionId - The current session ID
 * @param {string} userMessage - The user's message
 * @returns {Promise<{session_id: string, ai_message: string, question_count: number, is_complete: boolean, grader_payload: object|null}>}
 */
export async function sendMessage(sessionId, userMessage) {
  const response = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: sessionId,
      user_message: userMessage,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send message: ${response.statusText}`);
  }

  return response.json();
}
