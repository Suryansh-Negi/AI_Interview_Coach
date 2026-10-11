import os
from math import sqrt

import httpx
from pydantic import BaseModel, Field, ValidationError


class AIServiceError(RuntimeError):
    """An actionable error returned when the local Ollama service cannot help."""


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
    follow_up_question: str | None = None


class InterviewReport(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    summary: str


def ollama_base_url() -> str:
    return os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")


def ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "qwen3.5:4b").strip()


def ollama_embedding_model() -> str:
    return os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma").strip()


def _model_is_installed(configured: str, installed: set[str]) -> bool:
    if configured in installed:
        return True
    if ":" not in configured and f"{configured}:latest" in installed:
        return True
    return False


async def health_status() -> dict[str, str | None]:
    model = ollama_model()
    embedding_model = ollama_embedding_model()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(3.0, connect=1.0)) as client:
            response = await client.get(f"{ollama_base_url()}/api/tags")
            response.raise_for_status()
        installed = {
            name
            for item in response.json().get("models", [])
            for name in (item.get("name"), item.get("model"))
            if name
        }
    except (httpx.ConnectError, httpx.TimeoutException):
        return {
            "ai": "not_running",
            "ai_model": model,
            "ai_detail": f"Ollama is not responding at {ollama_base_url()}. Open Ollama, then refresh this page.",
            "embedding": "unavailable",
            "embedding_model": embedding_model,
        }
    except (httpx.HTTPError, ValueError, AttributeError, TypeError):
        return {
            "ai": "unavailable",
            "ai_model": model,
            "ai_detail": "Ollama responded, but its local model list could not be read. Restart Ollama and try again.",
            "embedding": "unavailable",
            "embedding_model": embedding_model,
        }

    if not _model_is_installed(model, installed):
        return {
            "ai": "model_missing",
            "ai_model": model,
            "ai_detail": f"The Ollama model '{model}' is not installed. In a terminal, run: ollama pull {model}",
            "embedding": "ready" if _model_is_installed(embedding_model, installed) else "model_missing",
            "embedding_model": embedding_model,
        }

    return {
        "ai": "ready",
        "ai_model": model,
        "ai_detail": "Local Ollama is ready.",
        "embedding": "ready" if _model_is_installed(embedding_model, installed) else "model_missing",
        "embedding_model": embedding_model,
    }


def _request_timeout() -> float:
    try:
        return max(30.0, float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300")))
    except ValueError:
        return 300.0


async def _ollama_post(path: str, payload: dict, timeout: float | None = None) -> dict:
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout or _request_timeout(), connect=5.0)
        ) as client:
            response = await client.post(f"{ollama_base_url()}/{path.lstrip('/')}", json=payload)
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        if isinstance(exc, httpx.ConnectError):
            raise AIServiceError(
                f"Ollama is not responding at {ollama_base_url()}. Open Ollama and retry."
            ) from None
        raise AIServiceError(
            "The local model took too long to respond. Keep Ollama running and retry; "
            "the first request can take longer while the model loads."
        ) from None
    except httpx.HTTPError:
        raise AIServiceError("Could not communicate with the local Ollama service. Restart Ollama and retry.") from None

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError:
        try:
            detail = str(response.json().get("error", ""))
        except (ValueError, AttributeError):
            detail = ""
        requested_model = str(payload.get("model", ""))
        if "not found" in detail.lower() and requested_model:
            raise AIServiceError(
                f"The Ollama model '{requested_model}' is not installed. Run: ollama pull {requested_model}"
            ) from None
        message = f"Ollama returned an error (HTTP {response.status_code})."
        if detail:
            message = f"{message} {detail}"
        raise AIServiceError(message) from None

    try:
        return response.json()
    except ValueError:
        raise AIServiceError("Ollama returned an unreadable response. Restart Ollama and retry.") from None


async def _ollama_parse(schema: type[BaseModel], system: str, prompt: str) -> BaseModel:
    model = ollama_model()
    result = await _ollama_post(
        "/api/generate",
        {
            "model": model,
            "system": system,
            "prompt": prompt,
            "format": schema.model_json_schema(),
            "stream": False,
            "keep_alive": os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
            "options": {"num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")), "temperature": 0.2},
        },
    )
    output = result.get("response")
    if not isinstance(output, str) or not output.strip():
        raise AIServiceError("Ollama returned an empty answer. Try again.")
    try:
        return schema.model_validate_json(output)
    except (ValidationError, ValueError):
        raise AIServiceError(
            f"The local model '{model}' returned feedback in an unexpected format. Retry the request."
        ) from None


async def generate_questions(role: str, interview_type: str, difficulty: str) -> list[dict]:
    system = (
        "You are an experienced interview coach. Create exactly five realistic, distinct interview questions. "
        "Match the job role, interview type, and difficulty. Include a brief useful answer hint. Do not include answers."
    )
    prompt = f"Role: {role}\nInterview type: {interview_type}\nDifficulty: {difficulty}"
    parsed = await _ollama_parse(GeneratedQuestionSet, system, prompt)
    if len(parsed.questions) != 5:
        raise AIServiceError("The local model did not return five questions. Retry with a simpler role description.")
    return [question.model_dump() for question in parsed.questions]


async def evaluate_answer(role: str, difficulty: str, question: str, answer: str) -> dict:
    system = (
        "Evaluate an interview answer fairly and constructively. Score correctness, relevance, clarity, and completeness "
        "from 0 to 100. Do not penalize a candidate for not knowing niche facts outside the prompt. Give concise, "
        "specific strengths and improvements. Suggest one natural follow-up question only when it would deepen the "
        "answer; otherwise use null."
    )
    prompt = f"Job role: {role}\nDifficulty: {difficulty}\nQuestion: {question}\nCandidate answer: {answer}"
    result = (await _ollama_parse(AnswerEvaluation, system, prompt)).model_dump()
    result["semantic_similarity"] = await _ollama_similarity(question, answer)
    return result


async def _ollama_similarity(question: str, answer: str) -> int | None:
    model = ollama_embedding_model()
    try:
        result = await _ollama_post(
            "/api/embed",
            {"model": model, "input": [question, answer]},
            timeout=60.0,
        )
        first, second = result["embeddings"][:2]
        denominator = sqrt(sum(value * value for value in first) * sum(value * value for value in second))
        if denominator:
            return round(max(0.0, sum(a * b for a, b in zip(first, second)) / denominator) * 100)
    except (AIServiceError, KeyError, IndexError, TypeError, ValueError):
        return None
    return None


async def create_report(role: str, answers: list[dict]) -> dict:
    evaluated = [item for item in answers if item.get("evaluation")]
    if not evaluated:
        return InterviewReport(
            overall_score=0,
            strengths=[],
            weaknesses=["No answers were submitted."],
            suggestions=["Complete a practice session and answer at least one question."],
            summary="No answer data is available for a report.",
        ).model_dump()

    score_values = [
        (
            item["evaluation"]["correctness"]
            + item["evaluation"]["relevance"]
            + item["evaluation"]["clarity"]
            + item["evaluation"]["completeness"]
        )
        / 4
        for item in evaluated
    ]
    average = round(sum(score_values) / len(score_values))
    report_inputs = [
        {
            "scores": {
                key: item["evaluation"].get(key)
                for key in ("correctness", "relevance", "clarity", "completeness")
            },
            "feedback": item["evaluation"].get("summary", ""),
            "strengths": item["evaluation"].get("strengths", []),
            "improvements": item["evaluation"].get("improvements", []),
        }
        for item in evaluated
    ]
    system = (
        "Summarize an interview practice session. Be constructive, specific, and concise. Identify recurring strengths, "
        "weaknesses, and actionable suggestions. Set overall_score to the provided arithmetic mean, rounded to an integer."
    )
    prompt = f"Role: {role}\nComputed overall score: {average}\nQuestion feedback: {report_inputs}"
    report = (await _ollama_parse(InterviewReport, system, prompt)).model_dump()
    report["overall_score"] = average
    return report
