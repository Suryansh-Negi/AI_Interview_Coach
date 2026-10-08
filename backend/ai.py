import os
from math import sqrt

from openai import AsyncOpenAI
from pydantic import BaseModel, Field


class GeneratedQuestion(BaseModel):
    category: str
    prompt: str
    hint: str


class GeneratedQuestionSet(BaseModel):
    questions: list[GeneratedQuestion]


class AnswerEvaluation(BaseModel):
    correctness: int = Field(ge=0, le=100)
    relevance: int = Field(ge=0, le=100)
    clarity: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    semantic_similarity: int | None = Field(default=None, ge=0, le=100)
    strengths: list[str]
    improvements: list[str]
    summary: str
    follow_up_question: str | None


class InterviewReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    summary: str


DEFAULT_QUESTIONS = {
    "Behavioral": [
        ("Behavioral", "Tell me about a time you solved a difficult problem with limited information.", "Use Situation, Task, Action, and Result to structure your example."),
        ("Behavioral", "Describe a time you received feedback that was difficult to hear.", "Explain how you listened, responded, and applied what you learned."),
        ("Teamwork", "Tell me about a time you worked with someone whose approach differed from yours.", "Focus on how you found common ground and moved forward."),
        ("Ownership", "Describe a project or task where you took initiative beyond your assigned work.", "Share the impact and what motivated you to step in."),
        ("Prioritization", "How do you handle competing deadlines when everything feels important?", "Walk through your decision process and how you communicate trade-offs."),
    ],
    "Technical": [
        ("Technical", "How would you design a service that needs to handle a large number of concurrent users?", "Cover the main components, bottlenecks, and trade-offs."),
        ("Problem solving", "Tell me about a technical decision you made and the trade-offs you considered.", "Explain the context, alternatives, and why you chose your approach."),
        ("Debugging", "How do you investigate a bug that you cannot reproduce consistently?", "Describe how you gather evidence and narrow down possible causes."),
        ("Technical", "What is the difference between a process and a thread?", "Explain the distinction and include an example of when it matters."),
        ("Quality", "How do you ensure the quality and maintainability of your code?", "Mention practical habits, tools, and how you balance speed with quality."),
    ],
    "Mixed": [
        ("Behavioral", "Tell me about a time you solved a difficult problem with limited information.", "Use Situation, Task, Action, and Result to structure your example."),
        ("Problem solving", "How would you approach designing a URL shortener for millions of requests?", "Consider identifiers, storage, traffic, and likely bottlenecks."),
        ("Technical", "What is the difference between a process and a thread?", "Explain the distinction and include an example of when it matters."),
        ("Communication", "How do you handle feedback when you disagree with it?", "Show how you listen, evaluate the feedback, and respond constructively."),
        ("Teamwork", "Tell me about a time you worked with someone whose approach differed from yours.", "Focus on how you found common ground and moved forward."),
    ],
}

_openai_client: AsyncOpenAI | None = None
_gemini_client = None


def ai_provider() -> str:
    return os.getenv("AI_PROVIDER", "ollama").strip().lower()


def ai_is_configured() -> bool:
    if ai_provider() == "ollama":
        return True
    if ai_provider() == "gemini":
        return bool(os.getenv("GEMINI_API_KEY"))
    if ai_provider() == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    return False


async def _ollama_parse(schema: type[BaseModel], system: str, prompt: str) -> BaseModel:
    import httpx

    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=2.0)) as client:
        response = await client.post(
            f"{base_url}/api/generate",
            json={
                "model": os.getenv("OLLAMA_MODEL", "gemma4:e2b"),
                "system": system,
                "prompt": prompt,
                "format": schema.model_json_schema(),
                "stream": False,
            },
        )
        response.raise_for_status()
        return schema.model_validate_json(response.json()["response"])


def _client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai_client


def _gemini() :
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        _gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _gemini_client


async def _gemini_parse(schema: type[BaseModel], system: str, prompt: str) -> BaseModel:
    from google.genai import types

    response = await _gemini().aio.models.generate_content(
        model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    if getattr(response, "parsed", None) is not None:
        return schema.model_validate(response.parsed)
    if response.text:
        return schema.model_validate_json(response.text)
    raise RuntimeError("Gemini did not return structured output.")


async def close_client() -> None:
    global _openai_client, _gemini_client
    if _openai_client is not None:
        await _openai_client.close()
        _openai_client = None
    if _gemini_client is not None:
        await _gemini_client.aio.aclose()
        _gemini_client.close()
        _gemini_client = None


async def generate_questions(role: str, interview_type: str, difficulty: str) -> list[dict]:
    system = "You are an experienced interview coach. Create exactly five realistic, distinct interview questions. Match the job role, interview type, and difficulty. Include a brief useful answer hint. Do not include answers."
    prompt = f"Role: {role}\nInterview type: {interview_type}\nDifficulty: {difficulty}"
    if ai_provider() == "ollama":
        try:
            parsed = await _ollama_parse(GeneratedQuestionSet, system, prompt)
            if len(parsed.questions) != 5:
                raise RuntimeError("The local model did not return five valid interview questions.")
            return [question.model_dump() for question in parsed.questions]
        except Exception:
            return [GeneratedQuestion(category=c, prompt=p, hint=h).model_dump() for c, p, h in DEFAULT_QUESTIONS[interview_type]]
    if not ai_is_configured():
        return [GeneratedQuestion(category=c, prompt=p, hint=h).model_dump() for c, p, h in DEFAULT_QUESTIONS[interview_type]]
    if ai_provider() == "gemini":
        parsed = await _gemini_parse(GeneratedQuestionSet, system, prompt)
        if len(parsed.questions) != 5:
            raise RuntimeError("The AI did not return five valid interview questions.")
        return [question.model_dump() for question in parsed.questions]

    response = await _client().responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        text_format=GeneratedQuestionSet,
        store=False,
    )
    parsed = response.output_parsed
    if not parsed or len(parsed.questions) != 5:
        raise RuntimeError("The AI did not return five valid interview questions.")
    return [question.model_dump() for question in parsed.questions]


async def evaluate_answer(role: str, difficulty: str, question: str, answer: str) -> dict:
    if ai_provider() == "ollama":
        system = "Evaluate an interview answer fairly and constructively. Score correctness, relevance, clarity, and completeness from 0 to 100. Give concise, specific strengths and improvements. Suggest one natural follow-up question only when it would deepen the answer; otherwise use null. Return only the requested structured data."
        prompt = f"Job role: {role}\nDifficulty: {difficulty}\nQuestion: {question}\nCandidate answer: {answer}"
        try:
            result = (await _ollama_parse(AnswerEvaluation, system, prompt)).model_dump()
            result["semantic_similarity"] = await _ollama_similarity(question, answer)
            return result
        except Exception:
            return _fallback_evaluation(answer)
    if not ai_is_configured():
        return _fallback_evaluation(answer)

    system = "Evaluate an interview answer fairly and constructively. Score correctness, relevance, clarity, and completeness from 0 to 100. Do not penalize a candidate for not knowing niche facts outside the prompt. Give concise, specific strengths and improvements. Suggest one natural follow-up question only when it would deepen the answer; otherwise use null."
    prompt = f"Job role: {role}\nDifficulty: {difficulty}\nQuestion: {question}\nCandidate answer: {answer}"
    if ai_provider() == "gemini":
        parsed = await _gemini_parse(AnswerEvaluation, system, prompt)
        result = parsed.model_dump()
        result["semantic_similarity"] = await _gemini_similarity(question, answer)
        return result

    response = await _client().responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        text_format=AnswerEvaluation,
        store=False,
    )
    if not response.output_parsed:
        raise RuntimeError("The AI could not evaluate this answer.")
    result = response.output_parsed.model_dump()
    result["semantic_similarity"] = await _openai_similarity(question, answer)
    return result


def _fallback_evaluation(answer: str) -> dict:
    words = len(answer.split())
    baseline = min(78, max(38, 38 + words // 4))
    return AnswerEvaluation(
        correctness=baseline,
        relevance=min(82, baseline + 3),
        clarity=min(80, baseline + 5),
        completeness=min(78, baseline),
        strengths=["You submitted a response and addressed the prompt."],
        improvements=["Add a specific example and explain the result or impact."],
        summary="Placeholder feedback: install and start Ollama for local AI evaluation, or configure a remote provider.",
        follow_up_question=None,
    ).model_dump()


async def _ollama_similarity(question: str, answer: str) -> int | None:
    import httpx

    try:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=2.0)) as client:
            response = await client.post(
                f"{base_url}/api/embed",
                json={"model": os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma"), "input": [question, answer]},
            )
            response.raise_for_status()
        first, second = response.json()["embeddings"][:2]
        denominator = sqrt(sum(value * value for value in first) * sum(value * value for value in second))
        if denominator:
            return round(max(0.0, sum(a * b for a, b in zip(first, second)) / denominator) * 100)
    except Exception:
        return None
    return None


async def _gemini_similarity(question: str, answer: str) -> int | None:
    try:
        from google.genai import types

        embeddings = await _gemini().aio.models.embed_content(
            model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2"),
            contents=[
                types.Content(parts=[types.Part.from_text(text=f"task: semantic similarity | text: {question}")]),
                types.Content(parts=[types.Part.from_text(text=f"task: semantic similarity | text: {answer}")]),
            ],
        )
        first, second = (item.values for item in embeddings.embeddings[:2])
        denominator = sqrt(sum(value * value for value in first) * sum(value * value for value in second))
        if denominator:
            return round(max(0.0, sum(a * b for a, b in zip(first, second)) / denominator) * 100)
    except Exception:
        return None
    return None


async def _openai_similarity(question: str, answer: str) -> int | None:
    try:
        vectors = await _client().embeddings.create(
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            input=[question, answer],
        )
        first, second = (item.embedding for item in vectors.data[:2])
        denominator = sqrt(sum(value * value for value in first) * sum(value * value for value in second))
        if denominator:
            return round(max(0.0, sum(a * b for a, b in zip(first, second)) / denominator) * 100)
    except Exception:
        return None
    return None


async def create_report(role: str, answers: list[dict]) -> dict:
    evaluated = [item for item in answers if item.get("evaluation")]
    if not evaluated:
        return InterviewReport(overall_score=0, strengths=[], weaknesses=["No answers were submitted."], suggestions=["Complete a practice session and answer each question."], summary="No answer data is available for a report.").model_dump()

    score_values = [
        (item["evaluation"]["correctness"] + item["evaluation"]["relevance"] + item["evaluation"]["clarity"] + item["evaluation"]["completeness"]) / 4
        for item in evaluated
    ]
    average = round(sum(score_values) / len(score_values))
    strengths = list(dict.fromkeys(s for item in evaluated for s in item["evaluation"].get("strengths", [])))[:3]
    improvements = list(dict.fromkeys(s for item in evaluated for s in item["evaluation"].get("improvements", [])))[:3]
    if not ai_is_configured():
        return _fallback_report(average, strengths, improvements)

    system = "Summarize an interview practice session. Be constructive, specific, and concise. Identify recurring strengths, weaknesses, and actionable suggestions. Set overall_score to the arithmetic mean of the provided question scores, rounded to an integer."
    prompt = f"Role: {role}\nComputed overall score: {average}\nEvaluated answers: {evaluated}"
    if ai_provider() == "ollama":
        try:
            report = (await _ollama_parse(InterviewReport, system, prompt)).model_dump()
            report["overall_score"] = average
            return report
        except Exception:
            return _fallback_report(average, strengths, improvements)
    if ai_provider() == "gemini":
        parsed = await _gemini_parse(InterviewReport, system, prompt)
        report = parsed.model_dump()
        report["overall_score"] = average
        return report

    response = await _client().responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        text_format=InterviewReport,
        store=False,
    )
    if not response.output_parsed:
        raise RuntimeError("The AI could not generate a session report.")
    report = response.output_parsed.model_dump()
    report["overall_score"] = average
    return report


def _fallback_report(average: int, strengths: list[str], improvements: list[str]) -> dict:
    return InterviewReport(
        overall_score=average,
        strengths=strengths,
        weaknesses=improvements,
        suggestions=improvements,
        summary="Placeholder report based on basic response-length scoring. Start Ollama for local AI feedback, or configure a remote provider.",
    ).model_dump()
