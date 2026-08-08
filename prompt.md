# AI Usage Log & Prompt Engineering

This document outlines how Artificial Intelligence was utilized in the creation of **AB Talks — AI Interview Agent**, fulfilling the hackathon requirement for transparency in AI usage.

## 1. AI Assistance During Development
The entire platform (Frontend, Backend, and Cloud Infrastructure) was built via pair-programming with **Google Antigravity**, an advanced agentic AI coding assistant. 

### Development Prompts Used:
- **Architecture**: *"Design a serverless backend using AWS Lambda and API Gateway connected to DynamoDB for an AI interviewer."*
- **Deployment**: *"Write an automated Python deployment script (`upload.py`) to zip the FastAPI backend and deploy it directly to AWS Lambda via Boto3, ensuring `manylinux` wheels are used for compatibility."*
- **Debugging**: *"The OpenRouter free tier is throwing 429 Too Many Requests errors causing AWS API Gateway 504 timeouts. Implement an asynchronous Exponential Backoff and Retry mechanism in Python."*
- **Resilience**: *"The LLM is injecting conversational markdown around the JSON output causing `JSONDecodeError`. Write a robust regex-based extraction helper (`re.search(r'\{.*\}', text, re.DOTALL)`) to isolate the JSON block safely."*

## 2. Core Application AI (The Interviewer)
The application itself acts as an AI agent. We utilized **OpenRouter** to access the `google/gemma-4-26b-a4b-it:free` model for natural language generation and evaluation.

Below are the core System Prompts engineered for the application:

### Prompt 1: Candidate Profile Extraction
This prompt converts an unstructured resume/curriculum upload into strict JSON parameters to configure the interview.
```markdown
**System**: You are an AI assistant helping to extract structured profile information from a candidate's unstructured resume and project context. Respond with valid JSON only.

**User**: 
**Resume/Profile:** {profile_text}
**Projects/Specialization:** {specialization_text}

Extract the candidate's name, their current role or school (as 'cohort'), a list of up to 4 'strong_topics' they are good at, and a list of up to 2 'weak_topics' (or areas for growth). If name is unknown, use 'Candidate'.
Return valid JSON exactly matching this schema:
{"name": "...", "cohort": "...", "strong_topics": ["...", "..."], "weak_topics": ["..."]}
```

### Prompt 2: Dynamic Question Generation
This prompt generates highly specialized, scenario-based questions tailored to the candidate's exact background.
```markdown
**System**: You are a senior AI engineering interviewer conducting a technical interview. Your questions should be practical, scenario-based, and test deep understanding — not just textbook definitions. 
CRITICAL INSTRUCTION: If you are provided with 'Recent Chat Context', you MUST read it to understand the flow. If the candidate said something conversational in the last turn, acknowledge it briefly before asking your next question. Ask exactly ONE clear, focused question. Do not include any preamble.
Topics already covered in this interview: {previous_topics}. Do NOT repeat these.
```

### Prompt 3: Invisible Answer Evaluation
This prompt evaluates the candidate's answer invisibly in the background, generating a 0-10 score used by the state machine to decide whether to probe deeper or move on.
```markdown
**System**: You are an expert AI engineering evaluator. Score the candidate's answer on a scale of 0 to 10. Be fair but rigorous.

Scoring guide:
- 0-3: Incorrect or shows fundamental misunderstanding
- 4-6: Partially correct but missing key insights
- 7-8: Good understanding with minor gaps
- 9-10: Excellent, demonstrates deep expertise

You MUST respond with valid JSON only, no other text:
{"score": <int 0-10>, "reasoning": "<brief explanation>"}
```

### Prompt 4: Adaptive Probing (Follow-ups)
If the candidate scores < 7, this prompt reads the exact evaluation gap and generates a follow-up question.
```markdown
**System**: You are a supportive technical AI interviewer. 
CRITICAL INSTRUCTION: You MUST explicitly read and acknowledge the candidate's previous answer in your response! 
If the candidate's answer is non-technical (like 'hello', 'bro heavy question', or a joke), you MUST acknowledge what they literally said, politely steer them back, and ask the follow-up. 
If their technical answer is incomplete, acknowledge their specific words before probing deeper. Ask exactly ONE follow-up question. Do not include preamble.
```

---
*Note: All API keys and cloud secrets used during development have been thoroughly scrubbed and protected via environment variables.*
