# AI Interview Coach

A local-first interview practice app with a Streamlit interface, FastAPI backend, MongoDB storage, and Ollama-powered question generation and feedback. AI requests and interview answers stay on the computer running Ollama; the project does not require a paid API key.

## One-time setup on Windows

1. Install Python and [MongoDB Community Server](https://www.mongodb.com/docs/manual/administration/install-community/). Run MongoDB as a Windows service.
2. Install [Ollama for Windows](https://ollama.com/download) and open it.
3. In the VS Code terminal, download the local language model and optional embedding model:

   ```powershell
   ollama pull qwen3.5:4b
   ollama pull embeddinggemma
   ```

   The embedding model only adds the semantic-similarity metric. Interview generation, evaluation, and reports use `qwen3.5:4b`.

4. Confirm the project `.env` uses your local MongoDB and Ollama settings. It is private and excluded from Git. `.env.example` is only a shareable settings template.
5. Start the app from the project directory:

   ```powershell
   .\run-local.ps1
   ```

The launcher creates the Python virtual environment if needed, starts the FastAPI backend, and then opens Streamlit. Visit `http://localhost:8501`. MongoDB must be running before the launcher starts.

## Check local services

Open `http://127.0.0.1:8000/api/health`. A healthy response reports `"database":"mongodb"` and `"ai":"ready"`. If Ollama is not running, open the Ollama app. If the configured model is missing, run the `ollama pull` command shown by the health response or dashboard.

The dashboard also displays Ollama readiness. If the model is unavailable, creating an interview or requesting feedback returns a clear setup error; the app does not silently replace AI feedback with placeholder scores.

## Local settings

- `MONGODB_URI=mongodb://127.0.0.1:27017`
- `MONGODB_DATABASE=interview_coach`
- `MONGODB_REQUIRED=true` to require persistent local MongoDB
- `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `OLLAMA_MODEL=qwen3.5:4b`
- `OLLAMA_EMBEDDING_MODEL=embeddinggemma` (optional)
- `OLLAMA_NUM_CTX=8192` to keep the local model's context and memory use bounded
- `OLLAMA_KEEP_ALIVE=5m` to keep the model loaded during a practice session

If MongoDB is stopped or unreachable while `MONGODB_REQUIRED=true`, the API will not start. To try the app without persistent storage, set `MONGODB_REQUIRED=false`; accounts and sessions will then be lost when the backend stops.

## Voice answers

Local voice transcription is optional. Install `requirements-voice.txt` and FFmpeg, then use the audio upload in an interview. Text-to-speech is not implemented.

## Hosting from this PC

Ollama runs on the machine that serves inference. To share a demo, this PC must remain powered on, connected to the internet, and running Ollama, FastAPI, and Streamlit. A tunnel can provide temporary access for a demo; it does not make the app independent of this PC or give it unlimited compute capacity. Keep Ollama's port private and expose only the authenticated app/API.

FastAPI documentation is available at `http://127.0.0.1:8000/docs` while the app is running.
