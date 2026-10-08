"""Streamlit frontend for the AI Interview Coach."""

import os

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()


st.set_page_config(
    page_title="Interview Coach",
    page_icon="✳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "page" not in st.session_state:
    st.session_state.page = "Dashboard"
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Sign in"
if "active_session" not in st.session_state:
    st.session_state.active_session = None
if "answer_feedback" not in st.session_state:
    st.session_state.answer_feedback = None
if "answer_submitted" not in st.session_state:
    st.session_state.answer_submitted = False

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def api_request(method: str, path: str, *, json: dict | None = None, files=None):
    headers = {}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    response = requests.request(
        method,
        f"{API_BASE_URL}{path}",
        json=json,
        files=files,
        headers=headers,
        timeout=45,
    )
    if not response.ok:
        try:
            detail = response.json().get("detail", "Request failed.")
        except ValueError:
            detail = "Request failed."
        raise RuntimeError(detail)
    return response.json() if response.content else None


def go(page: str) -> None:
    st.session_state.page = page


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
        :root { --ink:#302d49; --muted:#89869d; --purple:#7664d5; --line:#eceaf3; }
        html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
        .stApp { background:#f7f8fc; color:var(--ink); }
        [data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding-top:1.2rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:#77748c; }
        h1,h2,h3 { font-family:'Manrope',sans-serif !important; color:var(--ink); letter-spacing:-.04em; }
        h1 { font-size:2rem !important; }
        .brand { font:800 1.25rem Manrope,sans-serif; color:#302d49; padding:.25rem .2rem 1.8rem; letter-spacing:-.06em; }
        .brand span { color:var(--purple); }
        .overline { text-transform:uppercase; letter-spacing:.12em; font-size:.66rem; font-weight:700; color:#918ca7; margin-bottom:.5rem; }
        .muted { color:var(--muted); font-size:.9rem; }
        .hero { border-radius:18px; padding:2rem 2.15rem; color:white; background:linear-gradient(112deg,#2c294c,#51467d); margin:.8rem 0 1.6rem; }
        .hero h2 { color:white; font-size:2rem; margin:.65rem 0 .35rem; }
        .hero p { color:#d2cee2; max-width:560px; font-size:.95rem; }
        .hero-tag { display:inline-block; background:#ffffff18; border:1px solid #ffffff20; border-radius:20px; padding:.35rem .65rem; color:#e2dcff; text-transform:uppercase; letter-spacing:.08em; font-size:.65rem; font-weight:700; }
        .surface { background:white; border:1px solid var(--line); border-radius:14px; padding:1.15rem 1.25rem; margin-bottom:.8rem; }
        .metric-label { color:#89869d; font-size:.78rem; }
        .metric-value { color:var(--ink); font:700 1.65rem Manrope,sans-serif; margin-top:.35rem; }
        .metric-note { color:#6da88a; font-size:.72rem; margin-top:.2rem; }
        .stButton > button[kind="primary"] { background:var(--purple); border:0; border-radius:9px; font-weight:700; min-height:2.7rem; }
        .stButton > button[kind="primary"]:hover { background:#6553c4; border:0; }
        .stButton > button { border-radius:8px; }
        div[data-testid="stForm"] { background:white; padding:1.2rem 1.35rem; border:1px solid var(--line); border-radius:14px; }
        .question-box { background:#fff; border:1px solid var(--line); border-radius:14px; padding:1.4rem 1.5rem; margin:.8rem 0 1rem; }
        .feedback { background:#f5f2ff; border:1px solid #e9e4ff; border-radius:12px; padding:1rem 1.1rem; margin:.8rem 0; }
        .feedback strong { color:#5e50ad; }
        .stProgress > div > div > div > div { background:var(--purple); }
        footer { visibility:hidden; }
        @media(max-width:700px) { h1 {font-size:1.6rem !important;} .hero {padding:1.4rem;} .hero h2 {font-size:1.55rem;} }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_styles()

with st.sidebar:
    st.markdown('<div class="brand">✳ interviewly<span>.</span></div>', unsafe_allow_html=True)
    st.caption("YOUR PRACTICE SPACE")
    for item, icon in [("Dashboard", "⌂"), ("New Interview", "＋"), ("Interview History", "◷")]:
        if st.button(f"{icon}  {item}", key=f"nav_{item}", use_container_width=True):
            go(item)
    st.divider()
    st.divider()
    if st.session_state.current_user:
        st.markdown(f"**{st.session_state.current_user['full_name']}**")
        st.caption(st.session_state.current_user["email"])
        if st.button("Sign out", use_container_width=True):
            st.session_state.access_token = None
            st.session_state.current_user = None
            st.session_state.active_session = None
            st.rerun()
    else:
        st.caption("Sign in to save your progress")


page = st.session_state.page

if not st.session_state.access_token:
    st.markdown('<div class="overline">YOUR PERSONAL INTERVIEW COACH</div>', unsafe_allow_html=True)
    st.title("Practice with purpose.")
    st.markdown('<p class="muted">Sign in or create an account to start preparing and keep your interview history.</p>', unsafe_allow_html=True)
    st.session_state.auth_mode = st.radio("Account", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.auth_mode == "Sign in" else 1)
    with st.form("auth_form"):
        if st.session_state.auth_mode == "Create account":
            full_name = st.text_input("Full name")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", help="Use at least 8 characters.")
        auth_submit = st.form_submit_button(st.session_state.auth_mode, type="primary", use_container_width=True)
        if auth_submit:
            try:
                if st.session_state.auth_mode == "Create account":
                    result = api_request("POST", "/api/auth/register", json={"email": email, "full_name": full_name, "password": password})
                else:
                    result = api_request("POST", "/api/auth/login", json={"email": email, "password": password})
                st.session_state.access_token = result["access_token"]
                st.session_state.current_user = result["user"]
                st.session_state.page = "Dashboard"
                st.rerun()
            except requests.ConnectionError:
                st.error(f"Could not reach the API at {API_BASE_URL}. Start the backend and try again.")
            except requests.Timeout:
                st.error("The API took too long to respond. Try again.")
            except RuntimeError as exc:
                st.error(str(exc))
    st.stop()

if page == "Dashboard":
    try:
        sessions = api_request("GET", "/api/sessions")
        health = api_request("GET", "/api/health")
    except (RuntimeError, requests.RequestException) as exc:
        sessions = []
        health = {}
        st.warning(f"Interview history is temporarily unavailable: {exc}")
    if health.get("database") == "memory_fallback":
        st.info("Free local demo mode: sessions stay available until you stop the API. Add local MongoDB later if you want them saved between runs.")
    completed = [item for item in sessions if item["status"] == "completed"]
    scores = [item["report"]["overall_score"] for item in completed if item.get("report")]
    st.markdown('<div class="overline">✳ YOUR PRACTICE SPACE</div>', unsafe_allow_html=True)
    left, right = st.columns([5, 1.3])
    with left:
        st.title(f"Good morning, {st.session_state.current_user['full_name'].split()[0]}")
        st.markdown('<p class="muted">A little practice today goes a long way. Ready when you are.</p>', unsafe_allow_html=True)
    with right:
        if st.button("＋  New interview", type="primary", use_container_width=True):
            go("New Interview")
            st.rerun()
    st.markdown('<div class="hero"><span class="hero-tag">✦ Your next big thing starts here</span><h2>Show up as your most<br>confident self.</h2><p>Practice relevant interview questions, reflect on your answers, and build confidence one session at a time.</p></div>', unsafe_allow_html=True)
    st.subheader("Your progress")
    metric_cols = st.columns(4)
    stats = [("Sessions completed", str(len(completed)), "Saved to your account"), ("Average score", f"{round(sum(scores)/len(scores))}%" if scores else "—", "Across completed sessions"), ("Sessions in progress", str(sum(item["status"] == "in_progress" for item in sessions)), "Pick up where you left off"), ("Interview history", str(len(sessions)), "All-time sessions")]
    for col, (label, value, note) in zip(metric_cols, stats):
        with col:
            st.markdown(f'<div class="surface"><div class="metric-label">{label}</div><div class="metric-value">{value}</div><div class="metric-note">{note}</div></div>', unsafe_allow_html=True)
    recent_col, focus_col = st.columns([1.1, .9])
    with recent_col:
        st.subheader("Recent sessions")
        if sessions:
            for session in sessions[:3]:
                score = f" · {session['report']['overall_score']}%" if session.get("report") else ""
                st.markdown(f'<div class="surface"><b>{session["role"]}</b><br><span class="muted">{session["interview_type"]} · {session["difficulty"]} · {session["status"].replace("_", " ")}</span><br><b>{score.strip()}</b></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="surface"><b>No practice sessions yet</b><br><span class="muted">Start your first mock interview to see your progress here.</span></div>', unsafe_allow_html=True)
        if st.button("View interview history →"):
            go("Interview History")
            st.rerun()
    with focus_col:
        st.subheader("Your focus areas")
        st.markdown('<div class="surface"><b>Answer structure</b><br><span class="muted">Lead with the key point, then add context.</span></div><div class="surface"><b>Technical depth</b><br><span class="muted">Explain the trade-offs behind your choices.</span></div><div class="surface"><b>Clear communication</b><br><span class="muted">Your explanations are getting sharper.</span></div>', unsafe_allow_html=True)

elif page == "New Interview":
    st.markdown('<div class="overline">PERSONALIZED PRACTICE</div>', unsafe_allow_html=True)
    st.title("Set up your interview")
    st.markdown('<p class="muted">Choose what you’re preparing for. You can change these settings anytime.</p>', unsafe_allow_html=True)
    with st.form("interview_setup"):
        role = st.text_input("Job role", placeholder="e.g. Frontend Developer")
        type_col, level_col = st.columns(2)
        with type_col:
            interview_type = st.selectbox("Interview type", ["Mixed", "Behavioral", "Technical"])
        with level_col:
            difficulty = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"], index=1)
        st.markdown("**Your session**  ·  5 AI-generated questions  ·  Personalized feedback")
        submitted = st.form_submit_button("Start interview →", type="primary", use_container_width=True)
        if submitted:
            if not role.strip():
                st.error("Enter the job role you’re preparing for.")
            else:
                try:
                    with st.spinner("Preparing your interview questions…"):
                        st.session_state.active_session = api_request("POST", "/api/sessions", json={"role": role, "interview_type": interview_type, "difficulty": difficulty})
                    st.session_state.current_question = 0
                    st.session_state.answer_feedback = None
                    st.session_state.answer_submitted = False
                    go("Interview")
                    st.rerun()
                except (RuntimeError, requests.RequestException) as exc:
                    st.error(f"Could not start the interview: {exc}")

elif page == "Interview":
    interview = st.session_state.active_session
    if not interview:
        st.info("Choose your interview settings to begin.")
        if st.button("Set up an interview", type="primary"):
            go("New Interview")
            st.rerun()
        st.stop()
    current = st.session_state.get("current_question", 0)
    total = len(interview["questions"])
    question = interview["questions"][current]
    answer_data = interview["answers"][current]
    st.progress((current + 1) / total, text=f"QUESTION {current + 1} OF {total}")
    st.markdown(f'<div class="overline">{interview["role"].upper()} · {interview["interview_type"].upper()} · {interview["difficulty"].upper()}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="question-box"><span class="hero-tag">{question["category"]}</span><h3>{question["prompt"]}</h3><span class="muted">{question["hint"]}</span></div>', unsafe_allow_html=True)
    answer_key = f"answer_{interview['id']}_{current}"
    if answer_key not in st.session_state:
        st.session_state[answer_key] = answer_data.get("answer", "")
    audio_upload = st.file_uploader(
        "Optional voice answer · local Whisper",
        type=["wav", "mp3", "m4a", "mp4", "webm", "ogg", "flac", "mpeg"],
        key=f"audio_{interview['id']}_{current}",
        help="Audio stays on this machine and is transcribed locally. The optional Whisper package must be installed.",
    )
    if audio_upload is not None and st.button("Transcribe voice answer", key=f"transcribe_{interview['id']}_{current}"):
        try:
            with st.spinner("Transcribing locally with Whisper…"):
                transcript = api_request(
                    "POST",
                    "/api/voice/transcribe",
                    files={"file": (audio_upload.name, audio_upload.getvalue(), audio_upload.type or "application/octet-stream")},
                )
            st.session_state[answer_key] = transcript["text"]
            st.rerun()
        except (RuntimeError, requests.RequestException) as exc:
            st.error(f"Could not transcribe audio: {exc}")
    if not st.session_state.answer_submitted:
        with st.form(f"answer_form_{interview['id']}_{current}"):
            answer = st.text_area("Your answer", key=answer_key, height=190, placeholder="Type your answer here…")
            st.caption(f"{len(answer)} characters · Saved with your interview history")
            submitted_answer = st.form_submit_button("Submit answer for feedback →", type="primary", use_container_width=True)
        if submitted_answer:
            if not answer.strip():
                st.error("Write an answer first, or skip this question.")
            else:
                try:
                    with st.spinner("Reviewing your answer…"):
                        result = api_request("POST", f"/api/sessions/{interview['id']}/answers", json={"question_index": current, "answer": answer})
                    interview["answers"][current] = {"answer": answer, "evaluation": result["evaluation"]}
                    if result.get("added_follow_up"):
                        interview["questions"].insert(current + 1, result["added_follow_up"])
                        interview["answers"].insert(current + 1, {"answer": "", "evaluation": None})
                    st.session_state.answer_feedback = result["evaluation"]
                    st.session_state.answer_submitted = True
                    st.rerun()
                except (RuntimeError, requests.RequestException) as exc:
                    st.error(f"Could not evaluate this answer: {exc}")
    else:
        feedback = st.session_state.answer_feedback or answer_data.get("evaluation") or {}
        st.markdown(f'<div class="feedback"><strong>Coach feedback</strong><br><span class="muted">{feedback.get("summary", "Your answer has been saved.")}</span></div>', unsafe_allow_html=True)
        visible_metrics = ["correctness", "relevance", "clarity", "completeness"]
        if feedback.get("semantic_similarity") is not None:
            visible_metrics.append("semantic_similarity")
        metric_cols = st.columns(len(visible_metrics))
        for col, metric in zip(metric_cols, visible_metrics):
            with col:
                st.metric(metric.replace("_", " ").title(), f"{feedback.get(metric, 0)}%")
        for strength in feedback.get("strengths", []):
            st.success(strength)
        for improvement in feedback.get("improvements", []):
            st.info(improvement)
        if feedback.get("follow_up_question"):
            st.markdown(f"**Follow-up to consider:** {feedback['follow_up_question']}")
    prev_col, next_col = st.columns(2)
    with prev_col:
        if current > 0 and st.button("← Previous question"):
            st.session_state.current_question = current - 1
            st.session_state.answer_feedback = interview["answers"][current - 1].get("evaluation")
            st.session_state.answer_submitted = bool(interview["answers"][current - 1].get("evaluation"))
            st.rerun()
    with next_col:
        if not st.session_state.answer_submitted and st.button("Skip question →", use_container_width=True):
            if current < total - 1:
                st.session_state.current_question = current + 1
                st.rerun()
            else:
                try:
                    st.session_state.active_session = api_request("POST", f"/api/sessions/{interview['id']}/complete")
                    go("Report")
                    st.rerun()
                except (RuntimeError, requests.RequestException) as exc:
                    st.error(f"Could not finish the interview: {exc}")
        if st.session_state.answer_submitted:
            label = "Finish interview →" if current == total - 1 else "Next question →"
            if st.button(label, type="primary", use_container_width=True):
                if current < total - 1:
                    st.session_state.current_question = current + 1
                    st.session_state.answer_submitted = False
                    st.session_state.answer_feedback = None
                    st.rerun()
                else:
                    try:
                        with st.spinner("Preparing your performance report…"):
                            st.session_state.active_session = api_request("POST", f"/api/sessions/{interview['id']}/complete")
                        go("Report")
                        st.rerun()
                    except (RuntimeError, requests.RequestException) as exc:
                        st.error(f"Could not finish the interview: {exc}")

elif page == "Report":
    session = st.session_state.active_session
    report = session.get("report") if session else None
    if not report:
        st.title("Your practice report")
        st.info("Complete an interview to see your report.")
    else:
        st.markdown('<div class="overline">SESSION COMPLETE</div>', unsafe_allow_html=True)
        st.title("Your practice report")
        st.markdown(f'<p class="muted">{session["role"]} · {session["interview_type"]} · {session["difficulty"]}</p>', unsafe_allow_html=True)
        score_col, feedback_col = st.columns([.75, 1.25])
        with score_col:
            st.markdown(f'<div class="surface"><div class="metric-label">OVERALL PRACTICE SCORE</div><div class="metric-value">{report["overall_score"]}%</div><div class="metric-note">Based on evaluated answers</div></div>', unsafe_allow_html=True)
            evaluations = [item.get("evaluation") for item in session["answers"] if item.get("evaluation")]
            st.markdown("**Evaluation dimensions**")
            for metric in ["correctness", "relevance", "clarity", "completeness", "semantic_similarity"]:
                values = [item[metric] for item in evaluations if item.get(metric) is not None]
                if values:
                    value = round(sum(values) / len(values))
                    st.progress(value / 100, text=f"{metric.replace('_', ' ').title()} · {value}%")
        with feedback_col:
            st.markdown(f'<div class="feedback"><strong>Strengths</strong><br><span class="muted">{"<br>".join(report.get("strengths", [])) or "Keep practicing to identify your strongest patterns."}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="feedback"><strong>Areas to improve</strong><br><span class="muted">{"<br>".join(report.get("weaknesses", [])) or "No specific weaknesses were identified."}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="feedback"><strong>Suggestions</strong><br><span class="muted">{"<br>".join(report.get("suggestions", [])) or "Continue practicing with role-specific questions."}</span></div>', unsafe_allow_html=True)
            st.caption(report.get("summary", ""))
        a, b = st.columns(2)
        with a:
            if st.button("← Dashboard", use_container_width=True):
                st.session_state.active_session = None
                go("Dashboard")
                st.rerun()
        with b:
            if st.button("Practice again →", type="primary", use_container_width=True):
                st.session_state.active_session = None
                go("New Interview")
                st.rerun()

elif page == "Interview History":
    st.markdown('<div class="overline">YOUR GROWTH, AT A GLANCE</div>', unsafe_allow_html=True)
    st.title("Interview history")
    st.markdown('<p class="muted">Review your past sessions and track your improvement.</p>', unsafe_allow_html=True)
    try:
        sessions = api_request("GET", "/api/sessions")
        if not sessions:
            st.markdown('<div class="surface"><b>Your history will show up here.</b><br><span class="muted">Complete an interview to start tracking your progress.</span></div>', unsafe_allow_html=True)
        for session in sessions:
            score = f' · {session["report"]["overall_score"]}%' if session.get("report") else " · In progress"
            st.markdown(f'<div class="surface"><b>{session["role"]}</b>{score}<br><span class="muted">{session["interview_type"]} · {session["difficulty"]} · {session["created_at"][:10]}</span></div>', unsafe_allow_html=True)
            if session["status"] == "completed" and st.button("Open report", key=f"report_{session['id']}"):
                st.session_state.active_session = session
                go("Report")
                st.rerun()
            elif session["status"] == "in_progress" and st.button("Continue interview", key=f"continue_{session['id']}"):
                st.session_state.active_session = session
                saved_index = next((i for i, item in enumerate(session["answers"]) if not item.get("evaluation")), len(session["answers"]) - 1)
                st.session_state.current_question = saved_index
                st.session_state.answer_feedback = session["answers"][saved_index].get("evaluation")
                st.session_state.answer_submitted = bool(session["answers"][saved_index].get("evaluation"))
                go("Interview")
                st.rerun()
    except (RuntimeError, requests.RequestException) as exc:
        st.error(f"Could not load interview history: {exc}")
    if st.button("＋ New interview", type="primary"):
        go("New Interview")
        st.rerun()
