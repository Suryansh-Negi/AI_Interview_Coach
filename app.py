"""Streamlit frontend for the AI Interview Coach."""

import html
import os
import re
import time

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
if "sidebar_page" not in st.session_state:
    st.session_state.sidebar_page = st.session_state.page
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

SIDEBAR_PAGES = ("Dashboard", "New Interview", "Interview History")
PAGE_SIDEBAR_TARGET = {
    "Dashboard": "Dashboard",
    "New Interview": "New Interview",
    "Interview History": "Interview History",
    "Interview": "New Interview",
    "Report": "Interview History",
}
JOB_ROLE_OPTIONS = (
    "Frontend Engineer",
    "Frontend Developer",
    "Full-Stack Engineer",
    "Full-Stack Developer",
    "Backend Engineer",
    "Backend Developer",
    "Software Engineer",
    "Software Developer",
    "Web Developer",
    "Mobile App Developer",
    "iOS Developer",
    "Android Developer",
    "Data Analyst",
    "Data Scientist",
    "Data Engineer",
    "Machine Learning Engineer",
    "AI Engineer",
    "NLP Engineer",
    "Cloud Engineer",
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Cybersecurity Analyst",
    "Security Engineer",
    "QA Engineer",
    "Automation Test Engineer",
    "Product Manager",
    "Project Manager",
    "Business Analyst",
    "UX Designer",
    "UI Designer",
    "UX/UI Designer",
    "Product Designer",
    "Technical Support Engineer",
    "Sales Engineer",
    "Marketing Manager",
    "Financial Analyst",
    "HR Manager",
    "Operations Manager",
    "Research Scientist",
)

# Apply navigation requested by a page button before the keyed radio widget is
# instantiated. Streamlit forbids changing a widget's state after rendering it.
pending_sidebar_page = st.session_state.pop("pending_sidebar_page", None)
if pending_sidebar_page in SIDEBAR_PAGES:
    st.session_state.sidebar_page = pending_sidebar_page
elif st.session_state.sidebar_page not in SIDEBAR_PAGES:
    st.session_state.sidebar_page = PAGE_SIDEBAR_TARGET.get(st.session_state.page, "Dashboard")

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


def api_request(method: str, path: str, *, json: dict | None = None, files=None, timeout: float = 45):
    headers = {}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    response = requests.request(
        method,
        f"{API_BASE_URL}{path}",
        json=json,
        files=files,
        headers=headers,
        timeout=timeout,
    )
    if not response.ok:
        try:
            detail = response.json().get("detail", "Request failed.")
        except ValueError:
            detail = "Request failed."
        if isinstance(detail, list):
            messages = []
            for item in detail:
                location = item.get("loc", []) if isinstance(item, dict) else []
                field = location[-1] if location else ""
                if field == "email":
                    messages.append("Enter a valid email address.")
                elif field == "full_name":
                    messages.append("Enter your full name (at least 2 characters).")
                elif field == "password":
                    messages.append("Enter a password with at least 8 characters.")
                elif isinstance(item, dict):
                    messages.append(str(item.get("msg", "Check the information you entered.")))
            detail = " ".join(dict.fromkeys(messages)) or "Check the information you entered."
        raise RuntimeError(detail)
    if method.upper() != "GET" and path.startswith("/api/sessions"):
        clear_dashboard_cache()
    return response.json() if response.content else None


def go(page: str) -> None:
    st.session_state.page = page
    st.session_state.pending_sidebar_page = PAGE_SIDEBAR_TARGET.get(page, "Dashboard")


def navigate_from_sidebar() -> None:
    st.session_state.page = st.session_state.sidebar_page


def clear_dashboard_cache() -> None:
    st.session_state.pop("dashboard_snapshot", None)


def load_dashboard_snapshot() -> tuple[list, dict, str | None]:
    user_id = st.session_state.current_user["id"]
    cached = st.session_state.get("dashboard_snapshot")
    if cached and cached["user_id"] == user_id and time.monotonic() - cached["loaded_at"] < 20:
        return cached["sessions"], cached["health"], cached["error"]
    try:
        sessions = api_request("GET", "/api/sessions", timeout=5)
        health = api_request("GET", "/api/health", timeout=5)
        error = None
    except (RuntimeError, requests.RequestException) as exc:
        sessions = cached["sessions"] if cached and cached["user_id"] == user_id else []
        health = cached["health"] if cached and cached["user_id"] == user_id else {}
        error = str(exc)
    st.session_state.dashboard_snapshot = {
        "user_id": user_id,
        "loaded_at": time.monotonic(),
        "sessions": sessions,
        "health": health,
        "error": error,
    }
    return sessions, health, error


def validate_auth(mode: str, full_name: str, email: str, password: str) -> str | None:
    if mode == "Create account" and not full_name.strip():
        return "Enter your full name."
    if mode == "Create account" and len(full_name.strip()) < 2:
        return "Your name must be at least 2 characters."
    if not email.strip():
        return "Enter your email address."
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
        return "Enter a valid email address, such as name@example.com."
    if not password:
        return "Enter your password."
    if mode == "Create account" and len(password) < 8:
        return "Choose a password with at least 8 characters."
    return None


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#172622; --muted:#71807b; --green:#1e5146; --green-dark:#173c35; --lime:#d8ed91; --line:#e6ebe7; --canvas:#f7f9f6; }
        html, body, [class*="css"] { font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
        .stApp { background:var(--canvas); color:var(--ink); }
        [data-testid="stHeader"] { background:transparent; }
        [data-testid="stToolbar"], #MainMenu { visibility:hidden; height:0; }
        [data-testid="stDecoration"] { display:none; }
        [data-testid="stMainBlockContainer"] { max-width:1220px; padding-top:2rem; padding-bottom:3rem; }
        [data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] > div:first-child { padding:1.1rem .9rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color:var(--muted); }
        h1,h2,h3 { font-family:Inter,ui-sans-serif,system-ui,sans-serif !important; color:var(--ink); letter-spacing:-.045em; }
        h1 { font-size:2.35rem !important; line-height:1.13 !important; }
        h2 { letter-spacing:-.035em; }
        .brand { font:800 1.18rem Inter,ui-sans-serif,system-ui,sans-serif; color:var(--ink); padding:.25rem .45rem 1.8rem; letter-spacing:-.055em; }
        .brand-mark { display:inline-grid; place-items:center; width:1.8rem; height:1.8rem; margin-right:.5rem; border-radius:9px; background:var(--green); color:var(--lime); font-size:.95rem; }
        .side-label { padding:.35rem .6rem; color:#9aa6a0; font-size:.65rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase; }
        .overline { text-transform:uppercase; letter-spacing:.14em; font-size:.66rem; font-weight:700; color:#84938c; margin-bottom:.6rem; }
        .muted { color:var(--muted); font-size:.92rem; line-height:1.65; }
        .hero { position:relative; overflow:hidden; border-radius:22px; padding:2.6rem 2.8rem; color:white; background:radial-gradient(ellipse at 88% 15%,#3d7868 0,transparent 34%),linear-gradient(118deg,#193d35,#245648 60%,#2f6858); margin:.9rem 0 1.7rem; min-height:240px; }
        .hero:after { content:''; position:absolute; right:7%; top:22%; width:195px; height:195px; border-radius:50%; border:1px solid #ffffff24; box-shadow:0 0 0 22px #ffffff08,0 0 0 46px #ffffff06; }
        .hero-content { position:relative; z-index:1; max-width:620px; }
        .hero h2 { color:white; font-size:2.2rem; line-height:1.15; margin:.7rem 0 .55rem; }
        .hero p { color:#d2e0d8; max-width:540px; font-size:.96rem; }
        .hero-tag { display:inline-block; background:#ffffff16; border:1px solid #ffffff28; border-radius:20px; padding:.36rem .72rem; color:#e4efbd; text-transform:uppercase; letter-spacing:.1em; font-size:.64rem; font-weight:700; }
        .surface { background:white; border:1px solid var(--line); border-radius:16px; padding:1.2rem 1.3rem; margin-bottom:.8rem; box-shadow:0 4px 16px #233f2e06; }
        .surface-title { font:700 1rem Inter,ui-sans-serif,system-ui,sans-serif; color:var(--ink); margin-bottom:.3rem; }
        .metric-label { color:#829089; font-size:.73rem; font-weight:600; letter-spacing:.02em; }
        .metric-value { color:var(--ink); font:700 1.8rem Inter,ui-sans-serif,system-ui,sans-serif; margin-top:.42rem; }
        .metric-note { color:#7e8c85; font-size:.72rem; margin-top:.2rem; }
        .section-heading { font:700 1.12rem Inter,ui-sans-serif,system-ui,sans-serif; color:var(--ink); letter-spacing:-.03em; margin:.3rem 0 .8rem; }
        .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button { background:var(--green); color:#fff; border:1px solid var(--green); border-radius:10px; font-weight:700; min-height:2.75rem; transition:all .18s ease; }
        .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button:hover { background:var(--green-dark); border-color:var(--green-dark); color:#fff; }
        .stButton > button { border-radius:10px; border-color:#dce4de; min-height:2.55rem; font-weight:600; }
        [data-testid="stSidebar"] .stButton > button { text-align:left; border:0; background:transparent; color:#63716a; padding:.65rem .75rem; }
        [data-testid="stSidebar"] .stButton > button:hover { background:#f1f5f1; color:var(--green); }
        div[data-testid="stForm"] { background:white; padding:1.45rem 1.55rem; border:1px solid var(--line); border-radius:17px; box-shadow:0 8px 28px #1b3b2d08; }
        [data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stSelectbox"] div[data-baseweb="select"] > div { border-radius:10px; }
        [data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus { border-color:#4c8877; box-shadow:0 0 0 1px #4c8877; }
        .auth-panel { min-height:410px; padding:2.4rem 2.2rem; border-radius:22px; background:linear-gradient(145deg,#edf3e9,#e4eee4); display:flex; flex-direction:column; justify-content:space-between; }
        .auth-panel h2 { font-size:2.2rem; line-height:1.15; max-width:490px; margin:.65rem 0; }
        .auth-pill { display:inline-block; border:1px solid #d4e1d7; color:#49685b; background:#ffffff90; border-radius:99px; padding:.45rem .7rem; margin:.28rem .22rem .15rem 0; font-size:.75rem; font-weight:600; }
        .auth-note { margin-top:1.4rem; padding:1rem; border-left:3px solid #a1c36e; background:#ffffffa8; border-radius:0 10px 10px 0; color:#4b6257; font-size:.84rem; }
        .question-box { background:#fff; border:1px solid var(--line); border-radius:18px; padding:1.7rem 1.8rem; margin:.85rem 0 1.1rem; box-shadow:0 8px 24px #203c2d08; }
        .question-box h3 { font-size:1.55rem; line-height:1.4; margin:1rem 0 .65rem; }
        .feedback { background:#eff5ee; border:1px solid #dce9dc; border-radius:14px; padding:1.05rem 1.2rem; margin:.8rem 0; }
        .feedback strong { color:var(--green); font:700 .95rem Inter,ui-sans-serif,system-ui,sans-serif; }
        .coach-list { color:#5e7066; font-size:.86rem; line-height:1.65; padding-left:1.15rem; margin:.55rem 0 0; }
        .coach-list li { padding:.15rem 0; }
        .score-card { background:linear-gradient(145deg,#193d35,#28604f); color:#fff; padding:1.45rem; border-radius:17px; margin-bottom:1rem; }
        .score-card .metric-label { color:#c8dacf; }
        .score-card .metric-value { color:#fff; font-size:2.65rem; }
        .score-card .metric-note { color:#d6e5dc; }
        .dashboard-hero { position:relative; overflow:hidden; display:flex; align-items:center; min-height:220px; margin:1.1rem 0 1.6rem; padding:2.1rem 2.4rem; border-radius:22px; color:#fff; background:radial-gradient(ellipse at 90% 0%,#497c69 0,transparent 34%),linear-gradient(120deg,#183c34,#24584a 68%,#316a58); }
        .dashboard-hero:after { content:""; position:absolute; right:8%; top:18%; width:170px; height:170px; border:1px solid #ffffff25; border-radius:50%; box-shadow:0 0 0 22px #ffffff09,0 0 0 44px #ffffff06; }
        .dashboard-hero-content { position:relative; z-index:1; max-width:640px; }
        .dashboard-hero h2 { margin:.55rem 0; color:#fff; font-size:2rem; line-height:1.16; }
        .dashboard-hero p { max-width:550px; margin:0; color:#d6e5dd; font-size:.94rem; line-height:1.65; }
        .dashboard-kicker { color:#d8ed91; font-size:.67rem; font-weight:800; letter-spacing:.14em; text-transform:uppercase; }
        .dashboard-stat { height:100%; min-height:125px; padding:1.1rem 1.2rem; border:1px solid var(--line); border-radius:15px; background:#fff; box-shadow:0 4px 14px #203c2d05; }
        .dashboard-stat-label { color:#79877f; font-size:.76rem; font-weight:650; }
        .dashboard-stat-value { margin:.43rem 0 .16rem; color:var(--ink); font-size:1.85rem; font-weight:750; letter-spacing:-.05em; line-height:1.1; }
        .dashboard-stat-note { color:#8a968f; font-size:.72rem; }
        .dashboard-session { display:flex; justify-content:space-between; gap:1rem; align-items:center; margin:.65rem 0; padding:1rem 1.1rem; border:1px solid var(--line); border-radius:14px; background:#fff; }
        .dashboard-session-title { color:var(--ink); font-size:.93rem; font-weight:700; }
        .dashboard-session-detail { margin-top:.28rem; color:var(--muted); font-size:.76rem; }
        .dashboard-session-score { flex:0 0 auto; padding:.36rem .65rem; border-radius:99px; color:#285d4c; background:#edf5ec; font-size:.75rem; font-weight:750; }
        .dashboard-next { height:100%; padding:1.35rem; border:1px solid #dce8d9; border-radius:16px; background:linear-gradient(145deg,#f1f6ed,#eaf2e8); }
        .dashboard-next-label { color:#648071; font-size:.66rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
        .dashboard-next-title { margin:.5rem 0; color:var(--ink); font-size:1.08rem; font-weight:750; letter-spacing:-.025em; }
        .dashboard-next-copy { color:#687970; font-size:.84rem; line-height:1.6; }
        .stButton > button, [data-testid="stFormSubmitButton"] button { transition:background-color .15s ease,border-color .15s ease; }
        .stProgress > div > div > div > div { background:var(--green); }
        [data-testid="stMetric"] { background:white; padding:1rem 1.1rem; border:1px solid var(--line); border-radius:14px; }
        [data-testid="stMetricLabel"] { color:#77867e; }
        [data-testid="stMetricValue"] { color:var(--ink); font-family:Inter,ui-sans-serif,system-ui,sans-serif; }
        [data-testid="stRadio"] label { font-weight:600; }
        footer { visibility:hidden; }
        @media(max-width:800px) { h1 {font-size:1.8rem !important;} .hero {padding:1.6rem; min-height:0;} .hero h2,.auth-panel h2,.dashboard-hero h2 {font-size:1.7rem;} .hero:after,.dashboard-hero:after {right:-80px;} .auth-panel {min-height:300px; padding:1.5rem;} .dashboard-hero {min-height:180px;padding:1.5rem;} .dashboard-stat {min-height:110px;padding:.9rem;} }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_styles()

with st.sidebar:
    st.markdown('<div class="brand"><span class="brand-mark">✳</span>Interview Coach</div>', unsafe_allow_html=True)
    if st.session_state.current_user:
        st.markdown('<div class="side-label">Your workspace</div>', unsafe_allow_html=True)
        st.radio(
            "Workspace navigation",
            SIDEBAR_PAGES,
            key="sidebar_page",
            on_change=navigate_from_sidebar,
            label_visibility="collapsed",
        )
        st.divider()
        user_name = html.escape(st.session_state.current_user["full_name"])
        user_email = html.escape(st.session_state.current_user["email"])
        st.markdown(f'<div class="surface"><div class="surface-title">{user_name}</div><div class="muted" style="font-size:.76rem">{user_email}</div></div>', unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            st.session_state.access_token = None
            st.session_state.current_user = None
            st.session_state.active_session = None
            clear_dashboard_cache()
            go("Dashboard")
            st.rerun()
    else:
        st.markdown('<div class="auth-note">A quieter space to practice, get thoughtful feedback, and build confidence one answer at a time.</div>', unsafe_allow_html=True)


page = st.session_state.page

if not st.session_state.access_token:
    auth_left, auth_right = st.columns([1.1, .9], gap="large", vertical_alignment="center")
    with auth_left:
        st.markdown('''<div class="auth-panel"><div><div class="overline">PREPARE WITH PURPOSE</div><h2>Walk into your next interview with a clearer story.</h2><p class="muted">Practice realistic questions, get thoughtful feedback, and make each answer stronger than the last.</p><div><span class="auth-pill">Role-specific practice</span><span class="auth-pill">Actionable feedback</span><span class="auth-pill">Progress over time</span></div></div><div class="auth-note"><b>One question at a time.</b><br>Build confidence through practice that fits your goals.</div></div>''', unsafe_allow_html=True)
    with auth_right:
        st.markdown('<div class="overline">YOUR PERSONAL PRACTICE SPACE</div>', unsafe_allow_html=True)
        st.markdown('<h2 style="margin:.25rem 0 .4rem">Welcome</h2><p class="muted">Sign in or create an account to continue.</p>', unsafe_allow_html=True)
        st.session_state.auth_mode = st.radio("Account", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.auth_mode == "Sign in" else 1)
        with st.form("auth_form"):
            if st.session_state.auth_mode == "Create account":
                full_name = st.text_input("Full name", placeholder="Alex Morgan")
            else:
                full_name = ""
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="At least 8 characters", help="Use at least 8 characters.")
            auth_submit = st.form_submit_button("Continue →", type="primary", use_container_width=True)
            if auth_submit:
                validation_error = validate_auth(st.session_state.auth_mode, full_name, email, password)
                if validation_error:
                    st.error(validation_error)
                else:
                    try:
                        action = "Creating your account…" if st.session_state.auth_mode == "Create account" else "Signing you in…"
                        with st.spinner(action):
                            if st.session_state.auth_mode == "Create account":
                                result = api_request("POST", "/api/auth/register", json={"email": email.strip(), "full_name": full_name.strip(), "password": password}, timeout=15)
                            else:
                                result = api_request("POST", "/api/auth/login", json={"email": email.strip(), "password": password}, timeout=15)
                        st.session_state.access_token = result["access_token"]
                        st.session_state.current_user = result["user"]
                        clear_dashboard_cache()
                        go("Dashboard")
                        st.rerun()
                    except requests.ConnectionError:
                        st.error(f"Could not reach the API at {API_BASE_URL}. Start the backend and try again.")
                    except requests.Timeout:
                        st.error("Signing in took too long. Check that the backend and MongoDB are running, then try again.")
                    except requests.RequestException:
                        st.error("A network error interrupted sign-in. Check that the backend is running and try again.")
                    except RuntimeError as exc:
                        st.error(str(exc))
        st.caption("Your practice history is private to your account.")
    st.stop()

if page == "Dashboard":
    sessions, health, dashboard_error = load_dashboard_snapshot()
    if dashboard_error:
        st.warning(f"Interview history is temporarily unavailable: {dashboard_error}")
    if health.get("database") == "memory_fallback":
        st.info("Temporary storage is active. Start MongoDB to keep accounts and interview history after restarting the app.")
    if health.get("ai") == "ready":
        st.success(f"Local AI is ready · {health.get('ai_model', 'Ollama')}")
        if health.get("embedding") == "model_missing":
            st.caption(
                f"Optional semantic similarity is off. Install the embedding model with: "
                f"ollama pull {health.get('embedding_model', 'embeddinggemma')}"
            )
    else:
        st.warning(health.get("ai_detail") or "Local Ollama is not ready. Start Ollama before beginning an interview.")
        st.caption("Interview questions and feedback require Ollama. The app will not substitute placeholder scores.")
    completed = [item for item in sessions if item["status"] == "completed"]
    scores = [item["report"]["overall_score"] for item in completed if item.get("report")]
    first_name = html.escape(st.session_state.current_user["full_name"].split()[0])
    st.markdown('<div class="overline">YOUR PRACTICE SPACE</div>', unsafe_allow_html=True)
    left, right = st.columns([4.2, 1.3], vertical_alignment="center")
    with left:
        st.title(f"Welcome back, {first_name}")
        st.markdown('<p class="muted">Build confidence one focused practice session at a time.</p>', unsafe_allow_html=True)
    with right:
        if st.button("＋  New interview", type="primary", use_container_width=True):
            go("New Interview")
            st.rerun()
    st.markdown('<div class="dashboard-hero"><div class="dashboard-hero-content"><div class="dashboard-kicker">A LITTLE PRACTICE GOES A LONG WAY</div><h2>Make your next answer<br>your best one yet.</h2><p>Choose a role, work through realistic questions, and leave with feedback you can use in your next interview.</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">Your progress</div>', unsafe_allow_html=True)
    average_score = f"{round(sum(scores) / len(scores))}%" if scores else "—"
    best_score = f"{max(scores)}%" if scores else "—"
    stats = [
        ("Completed", str(len(completed)), "Sessions finished"),
        ("Average score", average_score, "Across completed sessions"),
        ("Best score", best_score, "Your personal best"),
        ("In progress", str(sum(item["status"] == "in_progress" for item in sessions)), "Ready to continue"),
    ]
    metric_cols = st.columns(4)
    for col, (label, value, note) in zip(metric_cols, stats):
        with col:
            st.markdown(f'<div class="dashboard-stat"><div class="dashboard-stat-label">{label}</div><div class="dashboard-stat-value">{value}</div><div class="dashboard-stat-note">{note}</div></div>', unsafe_allow_html=True)
    recent_col, focus_col = st.columns([1.12, .88], gap="large")
    with recent_col:
        st.markdown('<div class="section-heading">Recent sessions</div>', unsafe_allow_html=True)
        if sessions:
            for session in sessions[:4]:
                role_label = html.escape(session["role"])
                outcome = f'Score · {session["report"]["overall_score"]}%' if session.get("report") else "In progress"
                details = f'{html.escape(session["interview_type"])} · {html.escape(session["difficulty"])}'
                st.markdown(f'<div class="dashboard-session"><div><div class="dashboard-session-title">{role_label}</div><div class="dashboard-session-detail">{details}</div></div><div class="dashboard-session-score">{html.escape(outcome)}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="surface"><div class="surface-title">Your history starts here</div><span class="muted">Complete your first mock interview and your sessions and scores will appear here.</span></div>', unsafe_allow_html=True)
        if st.button("View interview history →"):
            go("Interview History")
            st.rerun()
    with focus_col:
        in_progress = next((item for item in sessions if item["status"] == "in_progress"), None)
        latest_suggestions = next((item.get("report", {}).get("suggestions", []) for item in completed if item.get("report", {}).get("suggestions")), [])
        st.markdown('<div class="section-heading">Your next step</div>', unsafe_allow_html=True)
        if in_progress:
            role_name = html.escape(in_progress["role"])
            st.markdown(f'<div class="dashboard-next"><div class="dashboard-next-label">PICK UP WHERE YOU LEFT OFF</div><div class="dashboard-next-title">Continue your {role_name} interview</div><div class="dashboard-next-copy">Your answers and progress are saved. Return to your next question whenever you’re ready.</div></div>', unsafe_allow_html=True)
            if st.button("Continue interview →", type="primary", use_container_width=True):
                st.session_state.active_session = in_progress
                saved_index = next((i for i, answer in enumerate(in_progress["answers"]) if not answer.get("evaluation")), len(in_progress["answers"]) - 1)
                st.session_state.current_question = saved_index
                st.session_state.answer_feedback = in_progress["answers"][saved_index].get("evaluation")
                st.session_state.answer_submitted = bool(in_progress["answers"][saved_index].get("evaluation"))
                go("Interview")
                st.rerun()
        elif latest_suggestions:
            suggestion = html.escape(str(latest_suggestions[0]))
            st.markdown(f'<div class="dashboard-next"><div class="dashboard-next-label">BASED ON YOUR LAST REPORT</div><div class="dashboard-next-title">One thing to work on</div><div class="dashboard-next-copy">{suggestion}</div></div>', unsafe_allow_html=True)
            if st.button("Practice again →", type="primary", use_container_width=True):
                go("New Interview")
                st.rerun()
        else:
            st.markdown('<div class="dashboard-next"><div class="dashboard-next-label">A SIMPLE PRACTICE RHYTHM</div><div class="dashboard-next-title">Start with one clear example</div><div class="dashboard-next-copy">Answer the question directly, describe a specific situation, then explain the result or what you learned.</div></div>', unsafe_allow_html=True)
            if st.button("Start your first interview →", type="primary", use_container_width=True):
                go("New Interview")
                st.rerun()

elif page == "New Interview":
    if st.button("← Dashboard", key="new_interview_back"):
        go("Dashboard")
        st.rerun()
    st.markdown('<div class="overline">PERSONALIZED PRACTICE</div>', unsafe_allow_html=True)
    st.title("Set up your practice")
    st.markdown('<p class="muted">A few details help shape questions around the interview you have in mind.</p>', unsafe_allow_html=True)
    setup_intro, setup_form = st.columns([.9, 1.1], gap="large", vertical_alignment="top")
    with setup_intro:
        st.markdown('<div class="surface"><div class="surface-title">Your session, your focus</div><p class="muted">Choose the role and style of interview you want to rehearse. You can take your time, move through questions at your own pace, and review feedback as you go.</p><hr><div class="surface-title">What to expect</div><span class="muted">A tailored set of questions<br>Clear feedback after each answer<br>A summary with next steps</span></div>', unsafe_allow_html=True)
    with setup_form:
        with st.form("interview_setup"):
            role = st.selectbox(
                "Job role",
                JOB_ROLE_OPTIONS,
                index=None,
                placeholder="Type to search roles or enter your own",
                accept_new_options=True,
                filter_mode="prefix",
                help="Type a few letters to filter suggestions, or enter a custom job title.",
            )
            interview_type = st.selectbox("Interview focus", ["Mixed", "Behavioral", "Technical"])
            difficulty = st.selectbox("Experience level", ["Beginner", "Intermediate", "Advanced"], index=1)
            st.caption("You’ll receive five starting questions. Follow-ups may be added based on your answers.")
            submitted = st.form_submit_button("Build my interview →", type="primary", use_container_width=True)
            if submitted:
                if not role or not role.strip():
                    st.error("Enter the job role you’re preparing for.")
                else:
                    try:
                        with st.spinner("Preparing your interview questions…"):
                            st.session_state.active_session = api_request("POST", "/api/sessions", json={"role": role.strip(), "interview_type": interview_type, "difficulty": difficulty}, timeout=300)
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
    back_col, history_col, spacer = st.columns([1.25, 1.55, 5.2])
    with back_col:
        if st.button("← Dashboard", key="interview_dashboard"):
            go("Dashboard")
            st.rerun()
    with history_col:
        if st.button("Interview history", key="interview_history"):
            go("Interview History")
            st.rerun()
    current = st.session_state.get("current_question", 0)
    total = len(interview["questions"])
    question = interview["questions"][current]
    answer_data = interview["answers"][current]
    st.markdown(f'<div class="overline">MOCK INTERVIEW &nbsp; / &nbsp; {html.escape(interview["role"].upper())}</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;margin:.35rem 0 .25rem"><span class="surface-title">Question {current + 1} <span class="muted" style="font-weight:400">of {total}</span></span><span class="auth-pill">{html.escape(interview["interview_type"])} · {html.escape(interview["difficulty"])}</span></div>', unsafe_allow_html=True)
    st.progress((current + 1) / total)
    st.markdown(f'<div class="question-box"><span class="auth-pill">{html.escape(question["category"])}</span><h3>{html.escape(question["prompt"])}</h3><span class="muted">{html.escape(question["hint"])}</span></div>', unsafe_allow_html=True)
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
                        result = api_request("POST", f"/api/sessions/{interview['id']}/answers", json={"question_index": current, "answer": answer}, timeout=300)
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
        st.markdown(f'<div class="feedback"><strong>Coach feedback</strong><br><span class="muted">{html.escape(feedback.get("summary", "Your answer has been saved."))}</span></div>', unsafe_allow_html=True)
        visible_metrics = ["correctness", "relevance", "clarity", "completeness"]
        if feedback.get("semantic_similarity") is not None:
            visible_metrics.append("semantic_similarity")
        metric_cols = st.columns(len(visible_metrics))
        for col, metric in zip(metric_cols, visible_metrics):
            with col:
                st.metric(metric.replace("_", " ").title(), f"{feedback.get(metric, 0)}%")
        strength_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in feedback.get("strengths", []))
        improvement_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in feedback.get("improvements", []))
        if strength_html or improvement_html:
            strengths_col, improvements_col = st.columns(2)
            with strengths_col:
                st.markdown(f'<div class="surface"><div class="surface-title">What worked</div><ul class="coach-list">{strength_html or "<li>Keep building on your answer.</li>"}</ul></div>', unsafe_allow_html=True)
            with improvements_col:
                st.markdown(f'<div class="surface"><div class="surface-title">Try next time</div><ul class="coach-list">{improvement_html or "<li>Keep practicing with specific examples.</li>"}</ul></div>', unsafe_allow_html=True)
        if feedback.get("follow_up_question"):
            st.markdown(f'<div class="surface"><div class="surface-title">A follow-up to consider</div><span class="muted">{html.escape(feedback["follow_up_question"])}</span></div>', unsafe_allow_html=True)
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
                    st.session_state.active_session = api_request("POST", f"/api/sessions/{interview['id']}/complete", timeout=300)
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
                            st.session_state.active_session = api_request("POST", f"/api/sessions/{interview['id']}/complete", timeout=300)
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
        st.markdown(f'<p class="muted">{html.escape(session["role"])} · {html.escape(session["interview_type"])} · {html.escape(session["difficulty"])}</p>', unsafe_allow_html=True)
        score_col, feedback_col = st.columns([.75, 1.25])
        with score_col:
            st.markdown(f'<div class="score-card"><div class="metric-label">OVERALL PRACTICE SCORE</div><div class="metric-value">{report["overall_score"]}<span style="font-size:1.2rem">%</span></div><div class="metric-note">A snapshot of this practice session</div></div>', unsafe_allow_html=True)
            evaluations = [item.get("evaluation") for item in session["answers"] if item.get("evaluation")]
            st.markdown('<div class="section-heading">Feedback dimensions</div>', unsafe_allow_html=True)
            for metric in ["correctness", "relevance", "clarity", "completeness", "semantic_similarity"]:
                values = [item[metric] for item in evaluations if item.get(metric) is not None]
                if values:
                    value = round(sum(values) / len(values))
                    st.progress(value / 100, text=f"{metric.replace('_', ' ').title()} · {value}%")
        with feedback_col:
            for title, field, empty in [
                ("What you did well", "strengths", "Keep practicing to identify your strongest patterns."),
                ("Areas to develop", "weaknesses", "No specific weaknesses were identified."),
                ("Your next steps", "suggestions", "Continue practicing with role-specific questions."),
            ]:
                items = "".join(f"<li>{html.escape(str(text))}</li>" for text in report.get(field, []))
                st.markdown(f'<div class="surface"><div class="surface-title">{title}</div><ul class="coach-list">{items or f"<li>{empty}</li>"}</ul></div>', unsafe_allow_html=True)
            if report.get("summary"):
                st.caption(html.escape(report["summary"]))
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
    if st.button("← Dashboard", key="history_dashboard"):
        go("Dashboard")
        st.rerun()
    st.markdown('<div class="overline">YOUR GROWTH, AT A GLANCE</div>', unsafe_allow_html=True)
    st.title("Interview history")
    st.markdown('<p class="muted">Review your past sessions and track your improvement.</p>', unsafe_allow_html=True)
    try:
        sessions = api_request("GET", "/api/sessions")
        if not sessions:
            st.markdown('<div class="surface"><div class="surface-title">Your history starts with your first session</div><span class="muted">Complete an interview and you’ll find your practice reports here.</span></div>', unsafe_allow_html=True)
        for session in sessions:
            card_col, action_col = st.columns([4, 1.2], vertical_alignment="center")
            with card_col:
                role_name = html.escape(session["role"])
                outcome = f'Score · {session["report"]["overall_score"]}%' if session.get("report") else "In progress"
                details = f'{html.escape(session["interview_type"])} · {html.escape(session["difficulty"])} · {html.escape(session["created_at"][:10])}'
                st.markdown(f'<div class="surface"><div class="surface-title">{role_name}</div><span class="muted">{details}</span><br><span class="metric-note">{html.escape(outcome)}</span></div>', unsafe_allow_html=True)
            with action_col:
                if session["status"] == "completed" and st.button("View report", key=f"report_{session['id']}", use_container_width=True):
                    st.session_state.active_session = session
                    go("Report")
                    st.rerun()
                elif session["status"] == "in_progress" and st.button("Continue", key=f"continue_{session['id']}", use_container_width=True):
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
