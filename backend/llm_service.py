"""
LLM Service — OpenRouter API client for the AI Interview Agent.

Handles all LLM interactions: question generation, answer evaluation,
follow-up generation, and final grading.
"""

import os
import re
import json
import httpx
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-4-26b-a4b-it:free"
FALLBACK_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter/free"
]

# Groq safety net: used only when every OpenRouter model above is exhausted.
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# Groq's free tier caps tokens-per-minute (6k) well before requests-per-day
# (14.4k), so the limit we actually hit is TPM — and it resets in seconds.
# Retrying is therefore almost always worth it, unlike OpenRouter's daily cap.
GROQ_MAX_ATTEMPTS = 3

# Shown to the candidate when no provider could answer. Phrased as an
# interviewer asking for a better answer rather than as a stack trace — the
# candidate can act on this, and it keeps the interview in character.
DEFAULT_FALLBACK_MESSAGE = (
    "I didn't quite catch that — could you rephrase your answer? "
    "Try framing it as you would in a formal interview: state your approach "
    "first, then walk me through your reasoning and any trade-offs."
)


def _get_api_key() -> str:
    """Retrieve the OpenRouter API key from environment."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key or key == "your_key_here":
        raise ValueError(
            "OPENROUTER_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
    return key


def _parse_duration(value: str) -> float | None:
    """
    Parse a Groq duration header such as '410ms', '6s', or '1m30s' into seconds.
    Returns None if the value isn't a duration we understand.
    """
    if not value:
        return None

    value = value.strip()

    # A bare number means seconds (this is what `retry-after` uses).
    try:
        return float(value)
    except ValueError:
        pass

    total = 0.0
    matched = False
    for amount, unit in re.findall(r"([\d.]+)\s*(ms|s|m|h)", value):
        try:
            number = float(amount)
        except ValueError:
            continue
        total += number * {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}[unit]
        matched = True

    return total if matched else None


def _retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    """
    Decide how long to wait before retrying a rate-limited Groq call.

    Prefers the server's own timing headers over guesswork, since Groq reports
    exactly when the token bucket refills. Falls back to exponential backoff.
    """
    for header in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
        seconds = _parse_duration(response.headers.get(header, ""))
        if seconds is not None:
            # Pad slightly so we don't land exactly on the boundary, and cap so
            # a bad header can't stall the request past the Lambda timeout.
            return min(seconds + 0.5, 20.0)

    return min(2.0 * (2 ** attempt), 20.0)


async def call_llm(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: dict | None = None,
    model_override: str | None = None,
    fallback_message: str | None = None,
) -> str:
    """
    Make an async call to the OpenRouter API.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        temperature: Sampling temperature (0.0–1.0).
        max_tokens: Maximum tokens in the response.
        response_format: Optional JSON schema for structured output.
        model_override: Model to try first. The normal fallback chain still
            applies if it fails.
        fallback_message: Returned when no provider could answer. Defaults to
            an in-character prompt asking the candidate to rephrase.

    Returns:
        The assistant's response content as a string.
    """
    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://abtalks.interview-agent.local",
        "X-Title": "AB Talks Interview Agent",
    }

    # An override is a preference, not a restriction — a call that names a
    # preferred model still falls through the chain rather than giving up.
    models_to_try = [MODEL] + FALLBACK_MODELS
    if model_override:
        models_to_try = [model_override] + [m for m in models_to_try if m != model_override]

    async with httpx.AsyncClient(timeout=45.0) as client:
        for model in models_to_try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if response_format:
                payload["response_format"] = response_format

            for attempt in range(2): # Reduce to 2 attempts to fail over faster
                try:
                    response = await client.post(
                        OPENROUTER_API_URL,
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content")
                    return content if content is not None else ""
                except httpx.HTTPStatusError as e:
                    logger.warning(
                        "OpenRouter model %s failed: HTTP %s — %s",
                        model, e.response.status_code, e.response.text[:200],
                    )
                    # A burst 429 is worth one retry; a daily-quota 429 is not,
                    # and neither is it worth retrying on the remaining models.
                    if e.response.status_code == 429:
                        if "per-day" in e.response.text:
                            break
                        if attempt < 1:
                            await asyncio.sleep(2)
                            continue
                    break  # try next model
                except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                    logger.warning("OpenRouter model %s timed out: %s", model, type(e).__name__)
                    break  # try next model

    logger.warning("All %d OpenRouter models failed; falling back to Groq.", len(models_to_try))

    # Fallback to Groq if all OpenRouter models fail
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        # Silence here is what makes this look like "Groq was removed" — say it.
        logger.error(
            "GROQ_API_KEY is not set, so the Groq safety net cannot run. "
            "Set it in .env and redeploy to arm the fallback."
        )
        return fallback_message or DEFAULT_FALLBACK_MESSAGE

    groq_headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json",
    }
    groq_payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        groq_payload["response_format"] = response_format

    async with httpx.AsyncClient(timeout=45.0) as client:
        for attempt in range(GROQ_MAX_ATTEMPTS):
            try:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=groq_headers,
                    json=groq_payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                logger.info(
                    "Groq fallback succeeded using %s (attempt %d).", GROQ_MODEL, attempt + 1
                )
                return content if content is not None else ""
            except httpx.HTTPStatusError as e:
                # A swallowed error here is indistinguishable from "no key at all",
                # which is exactly the confusion this logging exists to prevent.
                # A retired model id shows up as a 404/400 naming GROQ_MODEL.
                logger.error(
                    "Groq fallback failed: HTTP %s using model %s (attempt %d/%d) — %s",
                    e.response.status_code, GROQ_MODEL, attempt + 1,
                    GROQ_MAX_ATTEMPTS, e.response.text[:300],
                )
                # The cap that actually bites is tokens-per-minute, and it
                # resets in seconds — so wait it out rather than giving up.
                if e.response.status_code == 429 and attempt < GROQ_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(_retry_after_seconds(e.response, attempt))
                    continue
                break
            except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                logger.error(
                    "Groq fallback timed out: %s (attempt %d/%d)",
                    type(e).__name__, attempt + 1, GROQ_MAX_ATTEMPTS,
                )
                if attempt < GROQ_MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2)
                    continue
                break
            except Exception as e:
                logger.error("Groq fallback failed: %s: %s", type(e).__name__, e)
                break

    return fallback_message or DEFAULT_FALLBACK_MESSAGE


# ─── Domain-Specific LLM Functions ─────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """
    Extract the first complete JSON object from a string that may be wrapped in
    markdown fences or followed by commentary.

    Scans for a balanced closing brace rather than matching to the last one in
    the string, so trailing prose containing braces doesn't get swallowed.
    """
    start = text.find("{")
    if start == -1:
        return text

    depth = 0
    in_string = False
    escaped = False

    for i in range(start, len(text)):
        char = text[i]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]

    return text[start:]

async def extract_candidate_summary(profile_text: str, specialization_text: str) -> dict:
    """Extract structured profile data from unstructured text."""
    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI assistant helping to extract structured profile information "
                "from a candidate's unstructured resume and project context. "
                "Respond with valid JSON only."
            ),
        },
        {
            "role": "user",
            "content": (
                f"**Resume/Profile:**\n{profile_text}\n\n"
                f"**Projects/Specialization:**\n{specialization_text}\n\n"
                "Extract the candidate's name, their current role or school (as 'cohort'), "
                "a list of up to 4 'strong_topics' they are good at, and a list of up to 2 'weak_topics' "
                "(or areas for growth). If name is unknown, use 'Candidate'.\n"
                "Return valid JSON exactly matching this schema:\n"
                '{"name": "...", "cohort": "...", "strong_topics": ["...", "..."], "weak_topics": ["..."]}'
            )
        }
    ]
    response = await call_llm(
        messages, 
        temperature=0.1, 
        max_tokens=300,
        response_format={"type": "json_object"}
    )
    cleaned = _extract_json(response.strip())

    try:
        result = json.loads(cleaned)
        return {
            "name": result.get("name", "Candidate"),
            "cohort": result.get("cohort", "Custom Upload"),
            "strong_topics": result.get("strong_topics", ["Technical Skills"]),
            "weak_topics": result.get("weak_topics", ["To be assessed"])
        }
    except json.JSONDecodeError:
        return {
            "name": "Candidate",
            "cohort": "Custom Upload",
            "strong_topics": ["Technical Skills"],
            "weak_topics": ["To be assessed"]
        }

async def generate_question(
    curriculum_text: str,
    profile_text: str,
    specialization_text: str,
    question_number: int,
    previous_topics: list[str] | None = None,
    recent_history: str = "",
) -> str:
    """
    Generate a technical interview question for a specific curriculum day.
    """
    previous = ""
    if previous_topics:
        previous = f"\n\nTopics already covered in this interview: {', '.join(previous_topics)}. Do NOT repeat these."

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior AI engineering interviewer conducting a technical interview. "
                "Your questions should be practical, scenario-based, and test deep understanding — "
                "not just textbook definitions. "
                "CRITICAL INSTRUCTION: If you are provided with 'Recent Chat Context', you MUST read it to understand the flow. "
                "If the candidate said something conversational in the last turn, acknowledge it briefly before asking your next question. "
                "Ask exactly ONE clear, focused question. Do not include any preamble."
                f"{previous}"
            ),
        },
        {
            "role": "user",
            "content": (
                f"Generate question #{question_number} for this interview.\n\n"
                f"**Curriculum Details:**\n{curriculum_text}\n\n"
                f"**Candidate Profile:**\n{profile_text}\n\n"
                f"**Candidate Technical Specialization:**\n{specialization_text}\n\n"
                f"**Recent Chat Context:**\n{recent_history}\n\n"
                "Based on the provided curriculum and the candidate's background/specialization, "
                "select a highly relevant technical topic and ask a thoughtful, scenario-based question."
            ),
        },
    ]

    return await call_llm(messages, temperature=0.8)


async def evaluate_answer(
    question: str,
    answer: str,
    topic: str,
) -> dict:
    """
    Invisibly evaluate a candidate's answer and return a score + reasoning.

    Args:
        question: The question that was asked.
        answer: The candidate's response.
        topic: The topic being evaluated.

    Returns:
        A dict with 'score' (int 0-10) and 'reasoning' (str).
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert AI engineering evaluator. Score the candidate's answer "
                "on a scale of 0 to 10. Be fair but rigorous.\n\n"
                "Scoring guide:\n"
                "- 0-3: Incorrect or shows fundamental misunderstanding\n"
                "- 4-6: Partially correct but missing key insights\n"
                "- 7-8: Good understanding with minor gaps\n"
                "- 9-10: Excellent, demonstrates deep expertise\n\n"
                "You MUST respond with valid JSON only, no other text:\n"
                '{"score": <int 0-10>, "reasoning": "<brief explanation>"}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"**Topic:** {topic}\n\n"
                f"**Question:** {question}\n\n"
                f"**Candidate's Answer:** {answer}\n\n"
                "Evaluate this answer. Return JSON only."
            ),
        },
    ]

    response = await call_llm(
        messages, 
        temperature=0.2, 
        max_tokens=300,
        response_format={"type": "json_object"}
    )
    cleaned = _extract_json(response.strip())

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: extract score with a simple heuristic
        result = {"score": 5, "reasoning": "Evaluation parsing error. Default score applied."}

    return result


async def generate_followup(
    original_question: str,
    candidate_answer: str,
    evaluation: dict,
    topic: str,
) -> str:
    """
    Generate a probing follow-up question when the candidate's answer was weak.

    Args:
        original_question: The question that was asked.
        candidate_answer: The candidate's response.
        evaluation: The evaluation result (score + reasoning).
        topic: The topic being discussed.

    Returns:
        A follow-up question probing deeper into the weak area.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You are a supportive technical AI interviewer. "
                "CRITICAL INSTRUCTION: You MUST explicitly read and acknowledge the candidate's previous answer in your response! "
                "If the candidate's answer is non-technical (like 'hello', 'bro heavy question', or a joke), you MUST acknowledge what they literally said, politely steer them back, and ask the follow-up. "
                "If their technical answer is incomplete, acknowledge their specific words before probing deeper. "
                "Ask exactly ONE follow-up question. Do not include preamble."
            ),
        },
        {
            "role": "user",
            "content": (
                f"**Topic:** {topic}\n\n"
                f"**Original Question:** {original_question}\n\n"
                f"**Candidate's Answer:** {candidate_answer}\n\n"
                f"**Evaluation Gap:** {evaluation.get('reasoning', 'Answer was incomplete.')}\n\n"
                "Generate a follow-up question that probes the specific gap in their understanding."
            ),
        },
    ]

    return await call_llm(messages, temperature=0.7)


# A full 8-question interview plus follow-ups can run to thousands of tokens.
# Sent whole, it is the single biggest request the app makes and the one most
# likely to trip Groq's 6k tokens-per-minute cap — which is why the report was
# the piece that kept failing. Trim it to a budget instead.
MAX_TRANSCRIPT_CHARS = 10000
MAX_ENTRY_CHARS = 700


def _format_transcript_for_report(transcript: list[dict]) -> str:
    """
    Render the transcript for grading, bounded to a token budget.

    Long individual answers are truncated, and if the whole thing still
    overflows, the oldest exchanges are dropped — the later answers are what
    the rating hinges on, and the summary says when anything was omitted.
    """
    entries = []
    for entry in transcript:
        role = entry.get("role", "unknown").upper()
        content = (entry.get("content") or "").strip()
        if len(content) > MAX_ENTRY_CHARS:
            content = content[:MAX_ENTRY_CHARS] + " …[truncated]"
        entries.append(f"**{role}:** {content}")

    kept = []
    total = 0
    for text in reversed(entries):
        if kept and total + len(text) > MAX_TRANSCRIPT_CHARS:
            kept.append("**[earlier exchanges omitted for length]**")
            break
        kept.append(text)
        total += len(text)

    return "\n\n".join(reversed(kept))


async def generate_final_report(transcript: list[dict], target_topics: list[str]) -> dict:
    """
    Generate the final structured grading report from the full interview transcript.

    Args:
        transcript: The complete interview transcript.
        target_topics: The list of topic names assessed.

    Returns:
        A dict matching the GraderPayload schema.
    """
    formatted_transcript = _format_transcript_for_report(transcript)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior technical hiring manager reviewing an AI engineering interview transcript. "
                "Analyze the entire conversation and produce a structured evaluation.\n\n"
                "You MUST respond with valid JSON matching this exact schema:\n"
                "{\n"
                '  "strengths": ["<strength 1>", "<strength 2>", ...],\n'
                '  "areas_for_improvement": ["<area 1>", "<area 2>", ...],\n'
                '  "final_rating": "<one of: Strong Hire, Hire, Lean No Hire, No Hire>",\n'
                '  "topic_scores": {"<topic>": <score 1-10>, ...},\n'
                '  "summary": "<2-3 sentence narrative summary>"\n'
                "}\n\n"
                "Be specific in strengths and improvements. Reference actual answers from the transcript."
            ),
        },
        {
            "role": "user",
            "content": (
                f"**Topics Assessed:** {', '.join(target_topics)}\n\n"
                f"**Full Interview Transcript:**\n\n{formatted_transcript}\n\n"
                "Generate the final evaluation report. Return JSON only."
            ),
        },
    ]

    response = await call_llm(
        messages,
        temperature=0.3,
        # 600 was tight enough that a report listing several strengths, several
        # improvements and per-topic scores could be cut off mid-JSON, which
        # then failed to parse and surfaced as "no report".
        max_tokens=1200,
        model_override="nvidia/nemotron-nano-9b-v2:free",
        response_format={"type": "json_object"},
        fallback_message="",
    )
    cleaned = _extract_json(response.strip())

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.error("Final report JSON did not parse. Raw response: %r", response[:500])
        result = {}

    # Grading is the last thing that happens in an interview, so a hard failure
    # here loses the whole session. Fill any missing or wrong-typed field rather
    # than letting GraderPayload raise and return a 500 with no report at all.
    return _coerce_report(result)


def _coerce_report(result: dict) -> dict:
    """
    Force an LLM report into the shape GraderPayload requires.

    Models drop fields, return scores as strings or floats, and occasionally
    hand back a single string where a list belongs. Any of those would raise a
    ValidationError in main.py and cost the candidate their report.
    """
    def as_list(value, default):
        if isinstance(value, list) and value:
            return [str(v) for v in value]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return default

    scores = {}
    raw_scores = result.get("topic_scores")
    if isinstance(raw_scores, dict):
        for topic, score in raw_scores.items():
            try:
                scores[str(topic)] = max(0, min(10, int(round(float(score)))))
            except (TypeError, ValueError):
                continue

    rating = result.get("final_rating")
    if not isinstance(rating, str) or not rating.strip():
        rating = "Inconclusive"

    summary = result.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = "The evaluation could not be fully generated for this session."

    return {
        "strengths": as_list(
            result.get("strengths"), ["No specific strengths were recorded."]
        ),
        "areas_for_improvement": as_list(
            result.get("areas_for_improvement"),
            ["The evaluation could not be completed — please retry the interview."],
        ),
        "final_rating": rating.strip(),
        "topic_scores": scores,
        "summary": summary.strip(),
    }
