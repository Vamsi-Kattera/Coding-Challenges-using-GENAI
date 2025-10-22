# app.py - Adaptive Coding & Quiz App (styled professional)
import time
import ast
import pandas as pd
import streamlit as st
from utils import evaluate_code
from gemini_api import generate_hint

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
      [data-testid="stSidebar"] .css-1d391kg {{ color: {SIDEBAR_TEXT}; }}

      .css-1d391kg, .css-10trblm, .stText, .stMarkdown {{ color: {TEXT_COLOR}; }}

      .stTextArea textarea, .stCodeBlock {{
          background-color: {CODE_BG} !important;
          color: {TEXT_COLOR} !important;
          font-family: 'Courier New', monospace;
      }}

      .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{ color: {ACCENT}; }}

      .stButton>button {{
          background-color: {BUTTON_BG}; color: white; border-radius: 8px; border: 1px solid {BUTTON_BORDER};
          padding: 8px 14px; font-weight: 600;
      }}
      .stButton>button:hover {{ background-color: {BUTTON_HOVER}; border-color: {BUTTON_BORDER}; color: #ffffff; }}

      .stRadio>div, .stSelectbox>div, .stTextInput>div, .stDropdown>div {{
          color: {TEXT_COLOR} !important;
      }}

      .score-box {{
        padding: 10px;
        border-radius: 8px;
        background-color: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.04);
        color: {TEXT_COLOR};
      }}

      .main-panel {{
        padding: 18px;
        border-radius: 12px;
        background: linear-gradient(180deg, rgba(255,255,255,0.01), rgba(255,255,255,0.00));
        border: 1px solid rgba(255,255,255,0.03);
      }}

      .main-panel, .main-panel * {{
        color: {TEXT_COLOR} !important;
      }}

      .main-panel .stRadio label,
      .main-panel .stRadio div,
      .main-panel .stRadio,
      .main-panel .css-1dq8tca label,
      .main-panel .css-1w8ux8s label,
      .main-panel .stRadio * {{
        color: {TEXT_COLOR} !important;
      }}

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

      .css-1dq8tca label, .css-1w8ux8s label {{ color: {SIDEBAR_TEXT} !important; }}
      .stCodeBlock pre {{ font-size: 14px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# Constants 
DIFFICULTY_ORDER = ["easy", "medium", "hard"]

# Utilities
def ss_init(key: str, default):
    if key not in st.session_state:
        st.session_state[key] = default

def bump_difficulty(current: str, go_up: bool) -> str:
    idx = DIFFICULTY_ORDER.index(current)
    if go_up and idx < len(DIFFICULTY_ORDER) - 1:
        return DIFFICULTY_ORDER[idx + 1]
    if not go_up and idx > 0:
        return DIFFICULTY_ORDER[idx - 1]
    return current

def parse_literal(s):
    try:
        return ast.literal_eval(str(s))
    except Exception:
        return s

def next_diff_with_unseen(cur_diff: str, seen_ids_iterable, df: pd.DataFrame):
    seen_ids = set(seen_ids_iterable or [])
    start = DIFFICULTY_ORDER.index(cur_diff)
    for i in range(start, len(DIFFICULTY_ORDER)):
        d = DIFFICULTY_ORDER[i]
        unseen = df[(df["difficulty"] == d) & (~df["id"].isin(seen_ids))]
        if not unseen.empty:
            return d
    for d in DIFFICULTY_ORDER:
        unseen = df[(df["difficulty"] == d) & (~df["id"].isin(seen_ids))]
        if not unseen.empty:
            return d
    return None

def show_hint(msg: str, compact: bool = False):
    cls = "custom-hint small" if compact else "custom-hint"
    st.markdown(f'<div class="{cls}">{msg}</div>', unsafe_allow_html=True)

def show_error(msg: str, compact: bool = False):
    cls = "custom-error small" if compact else "custom-error"
    st.markdown(f'<div class="{cls}">{msg}</div>', unsafe_allow_html=True)

# =======================================================
#               DATA LOADERS (UPDATED)
# =======================================================
@st.cache_data
def load_data():
    try:
        coding = pd.read_csv("coding_questions.csv")
        quiz = pd.read_csv("quiz_questions.csv")
    except FileNotFoundError as e:
        st.error(
            f"❌ Required CSV file not found: {e.filename}. "
            "Please make sure 'coding_questions.csv' and 'quiz_questions.csv' "
            "are in the same folder as app.py."
        )
        return pd.DataFrame(columns=["id", "title", "description", "template", "test_input", "expected_output", "difficulty"]), \
               pd.DataFrame(columns=["id", "question", "options", "correct_answer", "difficulty"])
    coding["difficulty"] = coding["difficulty"].astype(str).str.lower()
    quiz["difficulty"] = quiz["difficulty"].astype(str).str.lower()
    return coding, quiz

CODING_DF, QUIZ_DF = load_data()

# Stop app if data missing
if CODING_DF.empty or QUIZ_DF.empty:
    st.stop()

# ================== [Rest of your code remains the same] ==================
# Flash messages, session state, coding mode, quiz mode, router, etc.
# Keep all your functions and render_coding_mode() / render_quiz_mode() exactly
# as you had in your previous code, just after this data loading block.

