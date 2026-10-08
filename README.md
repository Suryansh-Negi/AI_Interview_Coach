# AI Interview Coach

A Streamlit interview practice app backed by a FastAPI service. It supports user accounts, adaptive interview sessions, answer feedback, reports, and history.

## Run it now: no `.env`, API key, MongoDB, or paid service

In PowerShell, from this project directory:

```powershell
.\run-local.ps1
```

The launcher creates `.venv` if needed, installs Python packages, starts the API and Streamlit, and opens the app at `http://localhost:8501`. This first-run path needs an internet connection to download Python packages, but it does not make paid AI API calls. Until a local AI model is installed and running, the app uses built-in questions and clearly labeled placeholder feedback. Without MongoDB, accounts and sessions are kept in memory and disappear when the API stops.

## Zero API-cost AI (optional local setup)

The app defaults to Ollama at `http://127.0.0.1:11434`. Install [Ollama](https://ollama.com/download) and download a model once:

```powershell
ollama run gemma4:e2b
```

For the extra semantic-similarity score, download the embedding model too:

```powershell
ollama pull embeddinggemma
```

The chat model runs locally, so the app needs no LLM key and sends interview text to no remote AI provider. The model download requires disk space and internet; local inference uses your computer's resources and electricity. If Ollama is not running or the model is unavailable, the app falls back to demo questions/placeholder feedback rather than failing to launch. The API calls Ollama's local [generate](https://docs.ollama.com/api/generate) and [embed](https://docs.ollama.com/api/embed) endpoints.

## MongoDB choices

- **Run immediately:** the built-in memory store requires no database setup; data is temporary and clears when the API stops.
- **Persistent local database:** install Docker Desktop, then run `docker compose up -d mongodb`. The backend detects the default local MongoDB address automatically. This stores data on your computer in a Docker volume and does not require a paid cloud database.
- **Cloud option:** MongoDB Atlas has a free cluster tier with a 512 MB data-and-index storage limit. Atlas requires a database user and IP access-list entry; configure its URI in `.env`. [Atlas cluster tiers](https://www.mongodb.com/docs/atlas/manage-clusters/)

## Optional remote AI providers

The default app mode does not use remote AI services. You may optionally configure Gemini or OpenAI, but this requires an API key. Google's Gemini API offers a free tier for selected models subject to changing quotas; check current [pricing and limits](https://ai.google.dev/gemini-api/docs/pricing). Do not treat a free tier as a permanent guarantee, and avoid sending sensitive personal information to external providers. OpenAI API usage may incur charges. Provider keys are never needed for the local Ollama path.

To use optional overrides, copy `.env.example` to `.env` and edit only the settings you need. `.env.example` is a shareable template; `.env` is your private local configuration and is excluded from Git. Neither file is required to start the demo.

## Voice

Local Whisper speech-to-text is optional. Install `requirements-voice.txt` and FFmpeg, then the first transcription downloads a Whisper model. This is local processing, with no speech API key. Text-to-speech is not implemented yet.

## Implemented

- Streamlit sign-up/sign-in, interview configuration, five-question sessions, feedback, report, and history screens.
- FastAPI auth/session endpoints. Passwords are hashed with Argon2; JWTs protect user data.
- MongoDB persistence when available, with in-memory fallback for a zero-setup demo.
- Local Ollama question generation, evaluation, adaptive follow-ups, reports, and optional embeddings; optional Gemini/OpenAI providers.
- Optional local Whisper transcription.

API documentation is available at `http://127.0.0.1:8000/docs` while running.
