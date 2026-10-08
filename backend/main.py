import logging
import os
import secrets
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated

import jwt
from bson import ObjectId
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pymongo import AsyncMongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError
from pwdlib import PasswordHash
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv

from backend import ai
from backend.models import (
    AnswerRequest,
    AuthResponse,
    HealthResponse,
    InterviewSessionPublic,
    LoginRequest,
    RegisterRequest,
    SessionCreate,
    UserPublic,
)
from backend.memory_store import MemoryDatabase

load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("interview_coach")
password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)
JWT_SECRET = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(48)
JWT_ALGORITHM = "HS256"
JWT_EXPIRES_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "60"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mongo_client = None
    app.state.db = None
    app.state.database_mode = "memory_fallback"
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
    if mongo_uri:
        client = AsyncMongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        try:
            await client.admin.command("ping")
            database_name = os.getenv("MONGODB_DATABASE", "interview_coach")
            db = client[database_name]
            await db.users.create_index([("email", ASCENDING)], unique=True)
            await db.sessions.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
            app.state.mongo_client = client
            app.state.db = db
            app.state.database_mode = "mongodb"
            logger.info("Connected to MongoDB database %s", database_name)
        except PyMongoError:
            await client.close()
            logger.warning("MongoDB is unavailable; using temporary in-memory storage for this run")
    else:
        logger.info("MONGODB_URI is blank; using temporary in-memory storage for this run")
    if app.state.db is None:
        app.state.db = MemoryDatabase()
    if not os.getenv("JWT_SECRET_KEY"):
        logger.warning("JWT_SECRET_KEY is unset; tokens will be invalidated whenever the API restarts")
    yield
    await ai.close_client()
    if app.state.mongo_client is not None:
        await app.state.mongo_client.close()


app = FastAPI(
    title="AI Interview Coach API",
    description="Authentication, interview sessions, evaluation, and history for the AI Interview Coach.",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def get_db():
    db = getattr(app.state, "db", None)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Storage is unavailable.",
        )
    return db


def public_user(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "email": document["email"],
        "full_name": document["full_name"],
        "created_at": document["created_at"],
    }


def session_document(document: dict) -> dict:
    return {
        "id": str(document["_id"]),
        "role": document["role"],
        "interview_type": document["interview_type"],
        "difficulty": document["difficulty"],
        "status": document["status"],
        "questions": document["questions"],
        "answers": document["answers"],
        "created_at": document["created_at"],
        "completed_at": document.get("completed_at"),
        "report": document.get("report"),
    }


def create_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "email": email, "iat": now, "exp": now + timedelta(minutes=JWT_EXPIRES_MINUTES)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db=Depends(get_db),
) -> dict:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sign in to continue.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id or not ObjectId.is_valid(user_id):
            raise unauthorized
    except InvalidTokenError:
        raise unauthorized from None
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[dict, Depends(current_user)]
Database = Annotated[object, Depends(get_db)]


@app.get("/api/health", response_model=HealthResponse)
async def health():
    database = app.state.database_mode
    provider = ai.ai_provider()
    ai_status = "local_ollama_or_fallback" if provider == "ollama" else ("configured" if ai.ai_is_configured() else "fallback_mode")
    return {"status": "ok", "database": database, "ai": ai_status}


@app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: Database):
    email = str(payload.email).lower()
    document = {
        "email": email,
        "full_name": payload.full_name.strip(),
        "password_hash": password_hash.hash(payload.password),
        "created_at": datetime.now(timezone.utc),
    }
    try:
        result = await db.users.insert_one(document)
    except DuplicateKeyError:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from None
    document["_id"] = result.inserted_id
    return {"access_token": create_token(str(result.inserted_id), email), "user": public_user(document)}


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: Database):
    user = await db.users.find_one({"email": str(payload.email).lower()})
    if user is None or not password_hash.verify(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_token(str(user["_id"]), user["email"]), "user": public_user(user)}


@app.get("/api/auth/me", response_model=UserPublic)
async def me(user: CurrentUser):
    return public_user(user)


@lru_cache(maxsize=1)
def _whisper_model():
    try:
        import whisper
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="Local Whisper is optional. Install requirements-voice.txt to enable audio transcription.") from exc
    return whisper.load_model(os.getenv("WHISPER_MODEL", "base"))


def _transcribe(path: str) -> str:
    result = _whisper_model().transcribe(path, fp16=False)
    return result["text"].strip()


@app.post("/api/voice/transcribe")
async def transcribe_audio(user: CurrentUser, file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=415, detail="Upload an audio file.")
    suffix = Path(file.filename or "recording.wav").suffix.lower()
    if suffix not in {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac", ".mpeg"}:
        raise HTTPException(status_code=415, detail="Supported formats: WAV, MP3, M4A, WebM, OGG, or FLAC.")
    audio = await file.read(15 * 1024 * 1024 + 1)
    if len(audio) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio uploads are limited to 15 MB.")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio)
            temp_path = temp_file.name
        text = await run_in_threadpool(_transcribe, temp_path)
        return {"text": text, "provider": "local-whisper"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Local Whisper transcription failed")
        raise HTTPException(status_code=502, detail="Audio transcription failed. Check the audio format and local Whisper setup.") from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/api/sessions", response_model=InterviewSessionPublic, status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, user: CurrentUser, db: Database):
    questions = await ai.generate_questions(payload.role.strip(), payload.interview_type, payload.difficulty)
    now = datetime.now(timezone.utc)
    document = {
        "user_id": user["_id"],
        "role": payload.role.strip(),
        "interview_type": payload.interview_type,
        "difficulty": payload.difficulty,
        "status": "in_progress",
        "questions": questions,
        "answers": [{"answer": "", "evaluation": None} for _ in questions],
        "created_at": now,
        "completed_at": None,
        "report": None,
    }
    inserted = await db.sessions.insert_one(document)
    document["_id"] = inserted.inserted_id
    return session_document(document)


@app.get("/api/sessions", response_model=list[InterviewSessionPublic])
async def list_sessions(user: CurrentUser, db: Database, limit: int = 50):
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=422, detail="limit must be between 1 and 100")
    cursor = db.sessions.find({"user_id": user["_id"]}).sort("created_at", DESCENDING).limit(limit)
    return [session_document(document) async for document in cursor]


@app.get("/api/sessions/{session_id}", response_model=InterviewSessionPublic)
async def get_session(session_id: str, user: CurrentUser, db: Database):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=404, detail="Interview session not found.")
    document = await db.sessions.find_one({"_id": ObjectId(session_id), "user_id": user["_id"]})
    if document is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return session_document(document)


@app.post("/api/sessions/{session_id}/answers")
async def submit_answer(session_id: str, payload: AnswerRequest, user: CurrentUser, db: Database):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=404, detail="Interview session not found.")
    query = {"_id": ObjectId(session_id), "user_id": user["_id"], "status": "in_progress"}
    document = await db.sessions.find_one(query)
    if document is None:
        raise HTTPException(status_code=404, detail="Active interview session not found.")
    if payload.question_index >= len(document["questions"]):
        raise HTTPException(status_code=422, detail="Question index is outside this interview.")
    question = document["questions"][payload.question_index]
    try:
        evaluation = await ai.evaluate_answer(document["role"], document["difficulty"], question["prompt"], payload.answer.strip())
    except Exception as exc:
        logger.exception("Answer evaluation failed")
        raise HTTPException(status_code=502, detail="Answer evaluation is temporarily unavailable.") from exc
    answers = document["answers"].copy()
    answers[payload.question_index] = {"answer": payload.answer.strip(), "evaluation": evaluation}
    questions = document["questions"].copy()
    follow_up = evaluation.get("follow_up_question")
    added_follow_up = None
    if follow_up and len(questions) < 10:
        added_follow_up = {"category": "Follow-up", "prompt": follow_up, "hint": "Build on your previous answer with a specific detail or example."}
        questions.insert(payload.question_index + 1, added_follow_up)
        answers.insert(payload.question_index + 1, {"answer": "", "evaluation": None})
    await db.sessions.update_one(query, {"$set": {"questions": questions, "answers": answers}})
    return {"question_index": payload.question_index, "evaluation": evaluation, "added_follow_up": added_follow_up}


@app.post("/api/sessions/{session_id}/complete", response_model=InterviewSessionPublic)
async def complete_session(session_id: str, user: CurrentUser, db: Database):
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=404, detail="Interview session not found.")
    query = {"_id": ObjectId(session_id), "user_id": user["_id"]}
    document = await db.sessions.find_one(query)
    if document is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    if document["status"] == "completed":
        return session_document(document)
    report = await ai.create_report(document["role"], document["answers"])
    await db.sessions.update_one(query, {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc), "report": report}})
    document["status"] = "completed"
    document["completed_at"] = datetime.now(timezone.utc)
    document["report"] = report
    return session_document(document)
