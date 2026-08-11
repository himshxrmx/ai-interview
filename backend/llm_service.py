"""
LLM Service — OpenRouter API client for the AI Interview Agent.

Handles all LLM interactions: question generation, answer evaluation,
follow-up generation, and final grading.
"""

import os
import json
import httpx
import asyncio
import re
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "google/gemma-4-26b-a4b-it:free"
FALLBACK_MODELS = [
    "google/gemma-4-31b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "openrouter/free"
]


def _get_api_key() -> str:
    """Retrieve the OpenRouter API key from environment."""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key or key == "your_key_here":
        raise ValueError(
            "OPENROUTER_API_KEY is not set. "
            "Copy .env.example to .env and add your key."
        )
    return key


async def call_llm(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    response_format: dict | None = None,
    model_override: str | None = None,
) -> str:
    """
    Make an async call to the OpenRouter API.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        temperature: Sampling temperature (0.0–1.0).
        max_tokens: Maximum tokens in the response.
        response_format: Optional JSON schema for structured output.
        model_override: Specific model to use, ignoring fallbacks.

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

    models_to_try = [model_override] if model_override else [MODEL] + FALLBACK_MODELS

    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        async with httpx.AsyncClient(timeout=45.0) as client:
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
                    if e.response.status_code == 429 and attempt < 1:
                        await asyncio.sleep(2)
                        continue
                    break  # try next model
                except (httpx.ReadTimeout, httpx.ConnectTimeout):
                    break  # try next model

    # Fallback to Groq if all OpenRouter models fail
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        groq_headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json",
        }
        groq_payload = {
            "model": "llama-3.1-8b-instant",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            groq_payload["response_format"] = response_format
            
        async with httpx.AsyncClient(timeout=45.0) as client:
            try:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=groq_headers,
                    json=groq_payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                return content if content is not None else ""
            except Exception:
                pass

    return "I'm sorry, but my AI provider (OpenRouter) has reached its daily free-tier rate limit (or the models are unavailable). Please add credits to your OpenRouter account or try again tomorrow."


# ─── Domain-Specific LLM Functions ─────────────────────────────────────────────

def _extract_json(text: str) -> str:
    """Extracts JSON object from a string that might contain markdown or extra text."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return match.group(0) if match else text

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
    print("EXTRACTED SUMMARY LLM OUTPUT:", repr(response))
    print("EXTRACTED SUMMARY CLEANED:", repr(cleaned))

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


async def generate_final_report(transcript: list[dict], target_topics: list[str]) -> dict:
    """
    Generate the final structured grading report from the full interview transcript.

    Args:
        transcript: The complete interview transcript.
        target_topics: The list of topic names assessed.

    Returns:
        A dict matching the GraderPayload schema.
    """
    # Format transcript for the LLM
    formatted_transcript = ""
    for entry in transcript:
        role = entry.get("role", "unknown").upper()
        content = entry.get("content", "")
        formatted_transcript += f"**{role}:** {content}\n\n"

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
        max_tokens=600,
        model_override="nvidia/nemotron-nano-9b-v2:free",
        response_format={"type": "json_object"}
    )
    cleaned = _extract_json(response.strip())

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        result = {
            "strengths": ["Unable to parse evaluation"],
            "areas_for_improvement": ["Evaluation generation encountered an error"],
            "final_rating": "Inconclusive",
            "topic_scores": {},
            "summary": "The evaluation could not be generated due to a parsing error.",
        }

    return result
