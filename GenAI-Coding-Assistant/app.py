# app.py - Adaptive Coding & Quiz App (styled professional)
import time
import ast
import pandas as pd
import streamlit as st
from utils import evaluate_code
from gemini_api import generate_hint

import os

@st.cache_data
def load_data():
    base_path = os.path.dirname(__file__)  # folder where app.py is
    coding_path = os.path.join(base_path, "coding_questions.csv")
    quiz_path = os.path.join(base_path, "quiz_questions.csv")
    
    if not os.path.exists(coding_path) or not os.path.exists(quiz_path):
        st.error("CSV files not found in the app folder!")
        st.stop()
    
    coding = pd.read_csv(coding_path)
    quiz = pd.read_csv(quiz_path)
    coding["difficulty"] = coding["difficulty"].astype(str).str.lower()
    quiz["difficulty"] = quiz["difficulty"].astype(str).str.lower()
    return coding, quiz
CODING_DF, QUIZ_DF = load_data()
# -----------------------
# CONFIGURABLE THEME COLORS (professional palette)
# -----------------------
APP_BG = "#0b1020"        # deep navy app background
SIDEBAR_BG = "#f4f6f8"    # elegant light sidebar
CODE_BG = "#071015"       # code/textarea background (very dark)
TEXT_COLOR = "#e6eef8"    # primary text color on dark
SIDEBAR_TEXT = "#172033"  # dark text for sidebar (for readability)
ACCENT = "#2dd4bf"        # teal accent for headings/borders
BUTTON_BG = "#12313a"     # dark teal buttons
BUTTON_HOVER = "#154b44"  # hover color
BUTTON_BORDER = "#1fb89a" # lighter border for buttons

# Hint/Error colors (adjustable)
HINT_ACCENT = "#2dd4bf"
ERROR_ACCENT = "#f97366"
HINT_TEXT = "#d7fff6"
ERROR_TEXT = "#ffe8e2"

# The first Streamlit call!
st.set_page_config(page_title="Adaptive Coding & Quiz App", layout="wide")

# Theme / Styling (editable via the constants above)
st.markdown(
    f"""
    <style>
      /* App & sidebar */
      .stApp {{ background-color: {APP_BG}; color: {TEXT_COLOR}; }}
      [data-testid="stSidebar"] {{ background-color: {SIDEBAR_BG}; color: {SIDEBAR_TEXT}; }}
      [data-testid="stSidebar"] .css-1d391kg {{ color: {SIDEBAR_TEXT}; }} /* header/text fallback */

      /* Generic text color overrides (for some streamlit widgets) */
      .css-1d391kg, .css-10trblm, .stText, .stMarkdown {{ color: {TEXT_COLOR}; }}

      /* Code & textareas */
      .stTextArea textarea, .stCodeBlock {{
          background-color: {CODE_BG} !important;
          color: {TEXT_COLOR} !important;
          font-family: 'Courier New', monospace;
      }}

      /* Headings and accent */
      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: {ACCENT}; }}

      /* Buttons */
      .stButton>button {{
          background-color: {BUTTON_BG}; color: white; border-radius: 8px; border: 1px solid {BUTTON_BORDER};
          padding: 8px 14px; font-weight: 600;
      }}
      .stButton>button:hover {{ background-color: {BUTTON_HOVER}; border-color: {BUTTON_BORDER}; color: #ffffff; }}

      /* Inputs / radios / selects (ensure readable text) */
      .stRadio>div, .stSelectbox>div, .stTextInput>div, .stDropdown>div {{
          color: {TEXT_COLOR} !important;
      }}

      /* Score box */
      .score-box {{
        padding: 10px;
        border-radius: 8px;
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.04);
        color: {TEXT_COLOR};
      }}

      /* Card-like container for main panels (subtle) */
      .main-panel {{
        padding: 18px;
        border-radius: 12px;
        background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00));
        border: 1px solid rgba(255,255,255,0.03);
      }}

      /* Force everything inside main-panel to use TEXT_COLOR for readability */
      .main-panel, .main-panel * {{
        color: {TEXT_COLOR} !important;
      }}

      /* Ensure radio labels and options inside main-panel use TEXT_COLOR */
      .main-panel .stRadio label,
      .main-panel .stRadio div,
      .main-panel .stRadio,
      .main-panel .css-1dq8tca label,
      .main-panel .css-1w8ux8s label,
      .main-panel .stRadio * {{
        color: {TEXT_COLOR} !important;
      }}

      /* Custom hint & error boxes */
      .custom-hint {{
        background: linear-gradient(180deg, rgba(45,212,191,0.06), rgba(45,212,191,0.02));
        border-radius: 10px;
        padding: 14px;
        margin-top: 16px;
        border: 1px solid rgba(45,212,191,0.18);
        color: {HINT_TEXT};
        line-height: 1.45;
        box-shadow: 0 8px 24px rgba(0,0,0,0.45);
      }}
      .custom-error {{
        background: linear-gradient(180deg, rgba(249,115,102,0.06), rgba(249,115,102,0.02));
        border-radius: 10px;
        padding: 14px;
        margin-top: 16px;
        border: 1px solid rgba(249,115,102,0.18);
        color: {ERROR_TEXT};
        line-height: 1.45;
        box-shadow: 0 8px 24px rgba(0,0,0,0.5);
      }}
      .custom-hint.small {{ padding: 10px; font-size: 0.95rem; }}
      .custom-error.small {{ padding: 10px; font-size: 0.95rem; }}
      .custom-hint a, .custom-hint strong {{ color: #bff6ea; }}
      .custom-error a, .custom-error strong {{ color: #ffd0c7; }}

      /* Make radio labels in sidebar use sidebar text color */
      .css-1dq8tca label, .css-1w8ux8s label {{ color: {SIDEBAR_TEXT} !important; }}

      /* Tweak code block font size for readability */
      .stCodeBlock pre {{ font-size: 14px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Constants 
DIFFICULTY_ORDER = ["easy", "medium", "hard"]


# Utilities
def ss_init(key: str, default):
    """Safe init for session state keys."""
    if key not in st.session_state:
        st.session_state[key] = default


def bump_difficulty(current: str, go_up: bool) -> str:
    """Increase/decrease difficulty by exactly one step (no skipping)."""
    idx = DIFFICULTY_ORDER.index(current)
    if go_up and idx < len(DIFFICULTY_ORDER) - 1:
        return DIFFICULTY_ORDER[idx + 1]
    if not go_up and idx > 0:
        return DIFFICULTY_ORDER[idx - 1]
    return current


def parse_literal(s):
    """Try to parse a Python literal from text (list/dict/bool/int/etc.). Fallback to raw string."""
    try:
        return ast.literal_eval(str(s))
    except Exception:
        return s


def next_diff_with_unseen(cur_diff: str, seen_ids_iterable, df: pd.DataFrame):
    """
    Return the next difficulty (>= current) that still has unseen questions.
    If none at or above, wrap and try all. If none at all, return None.
    seen_ids_iterable can be a list or set.
    """
    seen_ids = set(seen_ids_iterable or [])
    start = DIFFICULTY_ORDER.index(cur_diff)

    # Prefer current or higher difficulty that has unseen questions
    for i in range(start, len(DIFFICULTY_ORDER)):
        d = DIFFICULTY_ORDER[i]
        unseen = df[(df["difficulty"] == d) & (~df["id"].isin(seen_ids))]
        if not unseen.empty:
            return d

    # Wrap around (in case datasets changed mid-run)
    for d in DIFFICULTY_ORDER:
        unseen = df[(df["difficulty"] == d) & (~df["id"].isin(seen_ids))]
        if not unseen.empty:
            return d

    return None


# Custom display helpers (styled hint/error)
def show_hint(msg: str, compact: bool = False):
    """Render a nicely styled hint box using custom CSS (avoids default st.info)."""
    cls = "custom-hint small" if compact else "custom-hint"
    html = f'<div class="{cls}">{msg}</div>'
    st.markdown(html, unsafe_allow_html=True)


def show_error(msg: str, compact: bool = False):
    """Render a nicely styled error box using custom CSS (avoids default st.error)."""
    cls = "custom-error small" if compact else "custom-error"
    html = f'<div class="{cls}">{msg}</div>'
    st.markdown(html, unsafe_allow_html=True)


# Data Loaders (must be after set_page_config)




# App Title (wrapped in nice markup)
st.markdown(f"<h1 style='color:{ACCENT}; margin-bottom:6px;'>Adaptive Coding Challenges & Quizzes</h1>", unsafe_allow_html=True)
st.markdown(f"<div style='color:{TEXT_COLOR}; margin-bottom:18px;'>Interactive coding challenges with intelligent hints (Gemini AI)</div>", unsafe_allow_html=True)

#  Sidebar 
with st.sidebar:
    st.header("Select Mode")
    ss_init("mode", "coding")
    st.session_state.mode = st.radio("Choose Mode:", ["coding", "quiz"], index=0)
    st.markdown("---")
    st.markdown('<div class="score-box">', unsafe_allow_html=True)
    st.markdown(f"### Score: **{st.session_state.get('score', 0)}**")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
    st.markdown("<small style='color:#6b7280;'>Tip: Select 'coding' to solve functions, or 'quiz' for multiple-choice practice.</small>", unsafe_allow_html=True)

#  Session State (safe init) 
ss_init("score", 0)

# Coding state (use lists for session_state serializability)
ss_init("coding_difficulty", "easy")
ss_init("coding_idx", 0)
ss_init("coding_seen_ids", [])     # store as list in session_state
ss_init("user_code", "")
ss_init("code_submitted", False)
ss_init("coding_start_time", time.time())
ss_init("hint", "")

# Quiz state
ss_init("quiz_difficulty", "easy")
ss_init("quiz_idx", 0)
ss_init("quiz_seen_ids", [])       # store as list in session_state
ss_init("quiz_answered", False)
ss_init("quiz_feedback", "")
ss_init("quiz_selected", None)
ss_init("quiz_hint", "")
ss_init("quiz_start_time", time.time())

# Flash messages
ss_init("flash_type", "")   # "success" | "error" | ""
ss_init("flash_msg", "")

# Flash banner (shows once)
if st.session_state.flash_msg:
    if st.session_state.flash_type == "success":
        st.success(st.session_state.flash_msg)
    elif st.session_state.flash_type == "error":
        st.error(st.session_state.flash_msg)
    else:
        st.info(st.session_state.flash_msg)
    st.session_state.flash_msg = ""
    st.session_state.flash_type = ""


# =======================================================
#                   CODING MODE
# =======================================================
def render_coding_mode():
    # Pick a difficulty that still has unseen questions
    target_diff = next_diff_with_unseen(
        st.session_state.coding_difficulty,
        st.session_state.coding_seen_ids,
        CODING_DF,
    )

    if target_diff is None:
        st.success("You've completed all coding questions!")
        return

    # If we had to move to another difficulty (because current one is exhausted), reset index
    if target_diff != st.session_state.coding_difficulty:
        st.session_state.coding_difficulty = target_diff
        st.session_state.coding_idx = 0

    # Slice unseen questions for this difficulty
    subset = CODING_DF[
        (CODING_DF["difficulty"] == st.session_state.coding_difficulty)
        & (~CODING_DF["id"].isin(set(st.session_state.coding_seen_ids)))
    ].reset_index(drop=True)

    # Safety check
    if subset.empty:
        st.session_state.coding_idx = 0
        return

    # Clamp index
    if st.session_state.coding_idx >= len(subset):
        st.session_state.coding_idx = 0

    row = subset.iloc[st.session_state.coding_idx]

    # Main panel wrapper (visual container)
    st.markdown('<div class="main-panel">', unsafe_allow_html=True)

    # Header (no difficulty label in UI)
    st.subheader(f'Coding Challenge: {row.get("title", "")}')
    # Description forced to TEXT_COLOR for visibility
    st.markdown(f"<div style='color:{TEXT_COLOR}; font-size:14px; margin-bottom:8px;'>{row.get('description', '')}</div>", unsafe_allow_html=True)
    st.code(row.get("template", ""), language="python")

    # Start/Reset timer for this question
    if not st.session_state.code_submitted:
        st.session_state.coding_start_time = time.time()

    # Code editor
    new_code = st.text_area(
        "Write your code below:",
        value=st.session_state.user_code or row.get("template", ""),
        height=220,
        key="code_area",
    )
    if new_code != st.session_state.user_code:
        st.session_state.user_code = new_code
        st.session_state.hint = ""

    # Actions
    col1, col2 = st.columns([2, 1])
    submit_pressed = col1.button("Submit Code")
    skip_pressed = col2.button("Skip Question")

    # Submit handler
    if submit_pressed:
        st.session_state.code_submitted = True

        # Extract function name safely
        try:
            func_name = row.get("template", "").split("def ")[1].split("(")[0].strip()
        except Exception:
            func_name = None

        # Parse input/expected
        test_input = parse_literal(row.get("test_input", ""))
        expected_output = parse_literal(row.get("expected_output", ""))

        if func_name:
            # ensure we pass a list of inputs if necessary
            test_args = test_input if isinstance(test_input, list) else [test_input]
            correct, _ = evaluate_code(
                st.session_state.user_code,
                func_name,
                test_args,
                expected_output,
            )
        else:
            correct = False

      if correct:
    if int(row["id"]) not in set(st.session_state.coding_seen_ids):
        st.session_state.coding_seen_ids.append(int(row["id"]))

    # Show success message immediately
    st.success("Correct!")
    st.session_state.score += 10

    # Adapt difficulty based on elapsed time
    elapsed = time.time() - st.session_state.coding_start_time
    if elapsed < 40:
        st.session_state.coding_difficulty = bump_difficulty(
            st.session_state.coding_difficulty, go_up=True
        )
        st.session_state.coding_idx = 0
    else:
        st.session_state.coding_idx += 1

    # Reset code and hint **after feedback is displayed**
    st.session_state.user_code = ""
    st.session_state.code_submitted = False
    st.session_state.hint = ""
    st.markdown("</div>", unsafe_allow_html=True)
    return


        else:
            # Use custom error/hint displays for clarity
            show_error("Incorrect or Error")
            st.session_state.score -= 5

            if not st.session_state.hint:
                with st.spinner("Generating Hint..."):
                    try:
                        st.session_state.hint = generate_hint(
                            row.get("description", ""), st.session_state.user_code
                        )
                    except Exception as e:
                        st.session_state.hint = f"(hint generation failed: {e})"
            if st.session_state.hint:
                show_hint(st.session_state.hint)

    # Skip handler
    if skip_pressed:
        if int(row["id"]) not in set(st.session_state.coding_seen_ids):
            st.session_state.coding_seen_ids.append(int(row["id"]))  # skip still marks as seen
        st.session_state.coding_idx += 1
        st.session_state.user_code = ""
        st.session_state.code_submitted = False
        st.session_state.hint = ""
        st.session_state.coding_start_time = time.time()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown("</div>", unsafe_allow_html=True)


# =======================================================
#                     QUIZ MODE
# =======================================================
def render_quiz_mode():
    target_diff = next_diff_with_unseen(
        st.session_state.quiz_difficulty,
        st.session_state.quiz_seen_ids,
        QUIZ_DF,
    )

    if target_diff is None:
        st.success("You've completed all quiz questions!")
        return

    if target_diff != st.session_state.quiz_difficulty:
        st.session_state.quiz_difficulty = target_diff
        st.session_state.quiz_idx = 0

    subset = QUIZ_DF[
        (QUIZ_DF["difficulty"] == st.session_state.quiz_difficulty)
        & (~QUIZ_DF["id"].isin(set(st.session_state.quiz_seen_ids)))
    ].reset_index(drop=True)

    if subset.empty:
        st.session_state.quiz_idx = 0
        return

    if st.session_state.quiz_idx >= len(subset):
        st.session_state.quiz_idx = 0

    qrow = subset.iloc[st.session_state.quiz_idx]

    st.markdown('<div class="main-panel">', unsafe_allow_html=True)

    # Header (no difficulty label in UI)
    st.subheader("Multiple Choice Quiz")
    # Question forced to TEXT_COLOR for visibility
    st.markdown(f"<div style='color:{TEXT_COLOR}; font-size:16px; font-weight:600; margin-bottom:8px;'>{qrow.get('question', '')}</div>", unsafe_allow_html=True)

    # Parse options
    options = parse_literal(qrow.get("options", ""))
    if not isinstance(options, list):
        options = [str(qrow.get("options", ""))]

    # Start/Reset timer for this question
    if not st.session_state.quiz_answered:
        st.session_state.quiz_start_time = time.time()

    selected = st.radio(
        "Choose your answer:", options, index=0, key=f"quiz_{qrow['id']}"
    )
    st.session_state.quiz_selected = selected

    col1, col2 = st.columns([2, 1])
    submit_q = col1.button("Submit Answer")
    next_q = col2.button("Next Question")  # acts as skip

    # Submit handler
    if submit_q and not st.session_state.quiz_answered:
        st.session_state.quiz_answered = True
        correct_answer = qrow.get("correct_answer", "")

        if selected == correct_answer:
            # Mark seen, score, flash
            if int(qrow["id"]) not in set(st.session_state.quiz_seen_ids):
                st.session_state.quiz_seen_ids.append(int(qrow["id"]))
            st.session_state.flash_type = "success"
            st.session_state.flash_msg = "Correct!"
            st.session_state.score += 10

            # Quick & correct -> raise difficulty by a single step
            elapsed = time.time() - st.session_state.quiz_start_time
            if elapsed < 30:
                st.session_state.quiz_difficulty = bump_difficulty(
                    st.session_state.quiz_difficulty, go_up=True
                )
                st.session_state.quiz_idx = 0
            else:
                st.session_state.quiz_idx += 1

            # Reset question state
            st.session_state.quiz_answered = False
            st.session_state.quiz_hint = ""
            st.session_state.quiz_selected = None
            st.markdown("</div>", unsafe_allow_html=True)
            return
        else:
            # Use custom error/hint displays for clarity
            show_error(f"Incorrect. Correct Answer: **{correct_answer}**")
            st.session_state.score -= 5

            if not st.session_state.quiz_hint:
                with st.spinner("Generating hint..."):
                    try:
                        st.session_state.quiz_hint = generate_hint(qrow.get("question", ""), selected)
                    except Exception as e:
                        st.session_state.quiz_hint = f"(hint generation failed: {e})"
            if st.session_state.quiz_hint:
                show_hint(st.session_state.quiz_hint)

    # Next/Skip handler
    if next_q:
        if int(qrow["id"]) not in set(st.session_state.quiz_seen_ids):
            st.session_state.quiz_seen_ids.append(int(qrow["id"]))  # mark as seen when skipping
        st.session_state.quiz_idx += 1
        st.session_state.quiz_answered = False
        st.session_state.quiz_hint = ""
        st.session_state.quiz_selected = None
        st.session_state.quiz_start_time = time.time()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown("</div>", unsafe_allow_html=True)


#  Router 
if st.session_state.mode == "coding":
    render_coding_mode()
else:
    render_quiz_mode()












