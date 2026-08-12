"""
Pydantic models for the AI Technical Interview Agent.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ─── Session State ──────────────────────────────────────────────────────────────

class SessionState(BaseModel):
    """Represents the full state of an interview session stored in DynamoDB."""

    session_id: str = Field(..., description="Unique identifier for the session")
    candidate_id: str = Field(..., description="Unique identifier for the candidate data")
    transcript: list[dict] = Field(
        default_factory=list,
        description="Ordered list of transcript entries: {role, content, metadata}"
    )
    question_count: int = Field(
        default=0,
        description="Number of distinct questions asked so far (max 8)"
    )
    is_followup: bool = Field(
        default=False,
        description="Whether the last question was a follow-up probe"
    )
    is_complete: bool = Field(
        default=False,
        description="Whether the interview has concluded"
    )
    profile_summary: dict = Field(
        default_factory=dict,
        description="Snapshot of candidate profile info for this session"
    )


# ─── API Request / Response Models ──────────────────────────────────────────────

class StartRequest(BaseModel):
    candidate_id: str

class StartResponse(BaseModel):
    """Response returned when a new interview session starts."""

    session_id: str
    first_message: str = Field(..., description="The first interview question from the AI")
    profile_summary: dict = Field(..., description="Candidate profile context for the dashboard")

class UploadResponse(BaseModel):
    candidate_id: str


class ChatRequest(BaseModel):
    """Payload sent by the client for each chat turn."""

    session_id: str
    user_message: str


class ChatResponse(BaseModel):
    """Standard response for a chat turn (non-final)."""

    session_id: str
    ai_message: str
    question_count: int
    is_complete: bool = False
    grader_payload: Optional["GraderPayload"] = None


# ─── Grader Payload ─────────────────────────────────────────────────────────────

class GraderPayload(BaseModel):
    """Structured evaluation returned at the end of the interview."""

    strengths: list[str] = Field(
        ..., description="List of candidate strengths identified during the interview"
    )
    areas_for_improvement: list[str] = Field(
        ..., description="List of areas where the candidate can improve"
    )
    final_rating: str = Field(
        ..., description="Overall rating (e.g., 'Strong Hire', 'Hire', 'Lean No Hire', 'No Hire')"
    )
    topic_scores: dict[str, int] = Field(
        default_factory=dict,
        description="Per-topic score mapping, e.g. {'RAG': 8, 'Vector DBs': 7}"
    )
    summary: str = Field(
        default="",
        description="Brief narrative summary of the candidate's performance"
    )


# Rebuild ChatResponse to resolve the forward reference to GraderPayload
ChatResponse.model_rebuild()
