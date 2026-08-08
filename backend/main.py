"""
FastAPI main application — AI Technical Interview Agent.

Endpoints:
    POST /start  — Initialize a new interview session
    POST /chat   — Handle a chat turn with evaluation and branching
"""

import json
import uuid
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from database import create_session, get_session, update_session, save_candidate_data, get_candidate_data
from models import (
    SessionState,
    StartRequest,
    StartResponse,
    UploadResponse,
    ChatRequest,
    ChatResponse,
    GraderPayload,
)
from llm_service import (
    generate_question,
    evaluate_answer,
    generate_followup,
    generate_final_report,
    extract_candidate_summary,
)

# ─── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AB Talks — AI Interview Agent",
    description="An AI-powered technical interview agent for AI engineering candidates.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-interview-ab.netlify.app",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Lambda Adapter
handler = Mangum(app)

# ─── Data Loading ───────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"


def load_curriculum() -> dict:
    """Load the curriculum JSON file."""
    with open(DATA_DIR / "curriculum.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_candidate_profile() -> dict:
    """Load the candidate profiles JSON file."""
    with open(DATA_DIR / "candidate_profiles.json", "r", encoding="utf-8") as f:
        return json.load(f)


def get_day_info(curriculum: dict, day_number: int) -> dict:
    """Look up a specific day from the curriculum."""
    for day in curriculum["days"]:
        if day["day"] == day_number:
            return day
    raise ValueError(f"Day {day_number} not found in curriculum")


def build_candidate_context(profile: dict) -> str:
    """Build a text summary of the candidate for LLM context."""
    candidate = profile["candidate"]
    signals = candidate["learning_signals"]

    strong = ", ".join(
        [s["topic"] for s in signals.get("strong_topics", [])]
    )
    weak = ", ".join(
        [w["topic"] for w in signals.get("weak_topics", [])]
    )

    return (
        f"Candidate: {candidate['name']}\n"
        f"Cohort: {candidate['cohort']}\n"
        f"Completion Rate: {candidate['completion_rate'] * 100:.0f}%\n"
        f"Completed {len(candidate['completed_days'])} of {candidate['total_days']} days\n"
        f"Strong Topics: {strong}\n"
        f"Weak Topics: {weak}\n"
        f"Avg Lab Score: {signals['engagement_metrics']['avg_lab_score']}\n"
        f"Peer Review Rating: {signals['engagement_metrics']['peer_review_rating']}/5"
    )


def build_profile_summary(profile: dict, target_days: list[int], curriculum: dict) -> dict:
    """Build a profile summary dict for the frontend dashboard."""
    candidate = profile["candidate"]
    signals = candidate["learning_signals"]

    target_topics = []
    for day_num in target_days:
        day_info = get_day_info(curriculum, day_num)
        target_topics.append({
            "day": day_num,
            "topic": day_info["topic"],
        })

    return {
        "name": candidate["name"],
        "cohort": candidate["cohort"],
        "completion_rate": candidate["completion_rate"],
        "completed_days": len(candidate["completed_days"]),
        "total_days": candidate["total_days"],
        "strong_topics": [s["topic"] for s in signals.get("strong_topics", [])],
        "weak_topics": [w["topic"] for w in signals.get("weak_topics", [])],
        "target_topics": target_topics,
        "engagement": signals["engagement_metrics"],
    }


# ─── Endpoints ──────────────────────────────────────────────────────────────────


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "running", "service": "AB Talks Interview Agent"}


async def extract_text(file: UploadFile) -> str:
    """Helper to extract text from an uploaded file (PDF or TXT)."""
    import io
    import PyPDF2
    
    if not file:
        return ""
    content = await file.read()
    if file.filename.lower().endswith(".pdf"):
        try:
            pdf = PyPDF2.PdfReader(io.BytesIO(content))
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing PDF: {str(e)}")
    else:
        return content.decode("utf-8", errors="ignore")


@app.post("/upload", response_model=UploadResponse)
async def upload_candidate_data(
    curriculum_file: UploadFile = File(None),
    curriculum_text: str = Form(""),
    profile_file: UploadFile = File(None),
    profile_text: str = Form(""),
    specialization_file: UploadFile = File(None),
    specialization_text: str = Form(""),
):
    """
    Accepts candidate data via file uploads or direct text input.
    Stores the extracted text in DynamoDB and returns a candidate_id.
    """
    curriculum = await extract_text(curriculum_file) + "\n" + curriculum_text
    profile = await extract_text(profile_file) + "\n" + profile_text
    specialization = await extract_text(specialization_file) + "\n" + specialization_text

    if not curriculum.strip() and not profile.strip() and not specialization.strip():
        raise HTTPException(status_code=400, detail="No data provided")

    candidate_id = str(uuid.uuid4())
    data = {
        "curriculum": curriculum.strip(),
        "profile": profile.strip(),
        "specialization": specialization.strip(),
    }
    
    save_candidate_data(candidate_id, data)
    return {"candidate_id": candidate_id}


@app.post("/start", response_model=StartResponse)
async def start_interview(request: StartRequest):
    """
    Initialize a new interview session using the uploaded candidate data.
    """
    candidate_id = request.candidate_id
    candidate_data = get_candidate_data(candidate_id)
    if not candidate_data:
        raise HTTPException(status_code=404, detail="Candidate not found. Please upload data first.")
    
    # Generate session ID
    session_id = str(uuid.uuid4())

    # Create a summary object for the frontend dashboard
    summary_data = await extract_candidate_summary(
        profile_text=candidate_data.get("profile", ""),
        specialization_text=candidate_data.get("specialization", "")
    )

    profile_summary = {
        "name": summary_data["name"],
        "cohort": summary_data["cohort"],
        "completion_rate": 1.0,
        "completed_days": 1,
        "total_days": 1,
        "strong_topics": summary_data["strong_topics"],
        "weak_topics": summary_data["weak_topics"],
        "target_topics": [{"day": 1, "topic": "Dynamic Interview"}],
        "engagement": {"avg_lab_score": 100}
    }

    # Generate first question
    first_question = await generate_question(
        curriculum_text=candidate_data.get("curriculum", ""),
        profile_text=candidate_data.get("profile", ""),
        specialization_text=candidate_data.get("specialization", ""),
        question_number=1,
    )

    # Build initial transcript
    initial_transcript = [
        {
            "role": "assistant",
            "content": first_question,
            "metadata": {
                "question_number": 1,
                "topic": "Dynamic Interview",
                "day": 1,
                "type": "question",
            },
        }
    ]

    # Create session state
    session = SessionState(
        session_id=session_id,
        candidate_id=candidate_id,
        transcript=initial_transcript,
        question_count=1,
        target_days=[1, 2, 3, 4],
        current_day_index=0,
        is_followup=False,
        is_complete=False,
        profile_summary=profile_summary,
    )

    # Save to DynamoDB
    create_session(session)

    return StartResponse(
        session_id=session_id,
        first_message=first_question,
        profile_summary=profile_summary,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Handle a chat turn in the interview.

    Flow:
    1. Fetch session state from DynamoDB.
    2. Invisibly evaluate the candidate's answer (score 0-10).
    3. Branch based on score:
       - Score < 7 AND not a follow-up: generate probing follow-up (no increment).
       - Score >= 7 OR already a follow-up: increment question count, advance topic.
    4. If question_count reaches 8: generate final grader report.
    5. Update DynamoDB and return response.
    """
    # Fetch session
    session = get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if session.is_complete:
        raise HTTPException(status_code=400, detail="Interview is already complete.")

    # Fetch candidate data
    candidate_data = get_candidate_data(session.candidate_id)
    if not candidate_data:
        raise HTTPException(status_code=404, detail="Candidate data not found.")

    # Append user message to transcript
    session.transcript.append({
        "role": "user",
        "content": request.user_message,
        "metadata": {"type": "answer"},
    })

    # ── The Invisible Evaluator ─────────────────────────────────────────────
    # Find the last question in the transcript
    last_question = ""
    current_topic = "General Technical Assessment"
    for entry in reversed(session.transcript):
        if entry.get("metadata", {}).get("type") in ("question", "followup"):
            last_question = entry["content"]
            current_topic = entry.get("metadata", {}).get("topic", current_topic)
            break

    evaluation = await evaluate_answer(
        question=last_question,
        answer=request.user_message,
        topic=current_topic,
    )

    score = evaluation.get("score", 5)

    # ── Branching Logic ─────────────────────────────────────────────────────

    if score < 7 and not session.is_followup:
        # ── Probe deeper — do NOT increment question count ──────────────
        followup = await generate_followup(
            original_question=last_question,
            candidate_answer=request.user_message,
            evaluation=evaluation,
            topic=current_topic,
        )

        session.transcript.append({
            "role": "assistant",
            "content": followup,
            "metadata": {
                "question_number": session.question_count,
                "topic": current_topic,
                "day": 1,
                "type": "followup",
                "evaluation_score": score,
            },
        })

        # Update session
        update_session(session.session_id, {
            "transcript": session.transcript,
            "is_followup": True,
        })

        return ChatResponse(
            session_id=session.session_id,
            ai_message=followup,
            question_count=session.question_count,
            is_complete=False,
        )

    else:
        # ── Good answer or already a follow-up — advance ────────────────
        new_question_count = session.question_count + 1

        # ── Check if interview is complete (8 questions answered) ───────
        if new_question_count > 8:
            # Generate final report
            report = await generate_final_report(
                transcript=session.transcript,
                target_topics=["Dynamic Assessment"],
            )

            grader = GraderPayload(**report)

            # Mark session complete
            update_session(session.session_id, {
                "transcript": session.transcript,
                "question_count": session.question_count,
                "is_complete": True,
            })

            return ChatResponse(
                session_id=session.session_id,
                ai_message="Thank you for completing the interview. Your evaluation report is ready.",
                question_count=session.question_count,
                is_complete=True,
                grader_report=grader,
            )

        # ── Generate Next Question ──────────────────────────────────────────
        
        next_question = await generate_question(
            curriculum_text=candidate_data.get("curriculum", ""),
            profile_text=candidate_data.get("profile", ""),
            specialization_text=candidate_data.get("specialization", ""),
            question_number=new_question_count,
            recent_history=request.user_message,
        )

        session.transcript.append({
            "role": "assistant",
            "content": next_question,
            "metadata": {
                "question_number": new_question_count,
                "topic": "Dynamic Assessment",
                "day": 1,
                "type": "question",
            },
        })

        # Update session
        update_session(session.session_id, {
            "transcript": session.transcript,
            "question_count": new_question_count,
            "is_followup": False,
        })

        return ChatResponse(
            session_id=session.session_id,
            ai_message=next_question,
            question_count=new_question_count,
            is_complete=False,
        )
