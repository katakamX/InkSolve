import base64
import json
import re
import sqlite3
from datetime import datetime

import requests
import streamlit as st
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

# ----------------------------- Configuration -----------------------------
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5vl:3b"
DB_PATH = "inksolve_history.db"

st.set_page_config(
    page_title="InkSolve | Handwritten Math Solver",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ----------------------------- Styling -----------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&display=swap');
    :root { color-scheme: dark; }
    .stApp {
        background:
            radial-gradient(circle at 12% 0%, rgba(25, 118, 122, .19), transparent 32%),
            radial-gradient(circle at 95% 12%, rgba(51, 91, 163, .16), transparent 30%),
            #080d18;
        color: #eef4ff;
        font-family: 'DM Sans', sans-serif;
    }
    h1, h2, h3, [data-testid="stMetricValue"] {
        font-family: 'Space Grotesk', sans-serif !important;
    }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem; }
    .hero {
        padding: 1.6rem 1.8rem; border: 1px solid rgba(120, 160, 190, .2);
        border-radius: 24px; background: linear-gradient(135deg, rgba(18, 37, 54, .94), rgba(13, 20, 37, .94));
        margin-bottom: 1.2rem;
    }
    .eyebrow { color: #61e5d0; font-size: .78rem; font-weight: 700; letter-spacing: .17em; text-transform: uppercase; }
    .hero h1 { font-size: clamp(2.3rem, 5vw, 3.5rem); margin: .25rem 0 .4rem; letter-spacing: -.055em; }
    .hero p { color: #aab9ce; max-width: 720px; margin: 0; font-size: 1.02rem; }
    .panel {
        border: 1px solid rgba(120, 160, 190, .19); border-radius: 20px;
        padding: 1.15rem 1.25rem; background: rgba(15, 24, 40, .76);
    }
    .small-muted { color: #9aabc2; font-size: .9rem; }
    .answer-card {
        border: 1px solid rgba(67, 220, 192, .35); border-radius: 18px;
        padding: 1.2rem 1.35rem; background: linear-gradient(135deg, rgba(16, 62, 65, .45), rgba(13, 28, 43, .8));
    }
    .answer-label { color: #69ead3; font-size: .75rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; }
    .answer-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; margin-top: .4rem; overflow-wrap: anywhere; }
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 12px; border: 1px solid rgba(96, 230, 211, .42);
        background: linear-gradient(135deg, #4fe0c6, #38bdb7); color: #07131d;
        font-weight: 700; min-height: 2.8rem;
    }
    div.stButton > button:hover { border-color: #8df7e6; color: #06131b; }
    [data-testid="stFileUploader"], [data-testid="stCameraInput"] {
        border: 1px dashed rgba(105, 180, 192, .45); border-radius: 16px; padding: .5rem;
        background: rgba(10, 20, 34, .45);
    }
    [data-baseweb="tab-list"] { gap: .5rem; }
    button[data-baseweb="tab"] { border-radius: 10px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------- History -----------------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                equation TEXT NOT NULL,
                result TEXT NOT NULL
            )"""
        )

def save_history(equation, result):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO history (created_at, equation, result) VALUES (?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), equation, result),
        )

def get_history():
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(
            "SELECT created_at, equation, result FROM history ORDER BY id DESC LIMIT 100"
        ).fetchall()

init_db()

# ----------------------------- Local AI ----------------------------------
def ask_ollama(image_bytes, model):
    """Ask the local Ollama vision model to transcribe the equation, not solve it."""
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    prompt = """
You are a mathematical handwriting OCR system. Read the equation or expression in the image.
Do not solve it. Return ONLY valid JSON in exactly this shape:
{"equation":"...","notes":"..."}
Rules:
- Put the transcription in equation using plain text.
- Use ^ for powers (write x^2, not x²), * for multiplication when needed, / for division.
- Use ordinary variable letters such as x, y, and z.
- Preserve signs, brackets, fractions and all numbers exactly as written.
- Do not invent missing symbols. If unreadable, put [?] in the equation and explain briefly in notes.
- Ignore unrelated marks and background.
"""
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": model,
            "messages": [
                {"role": "user", "content": prompt, "images": [encoded]}
            ],
            "stream": False,
            "options": {"temperature": 0},
        },
        timeout=180,
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "").strip()
    # Strip common markdown fences if the model accidentally includes them.
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE)
    try:
        parsed = json.loads(content)
        return str(parsed.get("equation", "")).strip(), str(parsed.get("notes", "")).strip()
    except json.JSONDecodeError:
        # Fallback: show the raw model transcription so the user can correct it.
        return content, "The model did not return clean JSON. Please check the transcription."

# ----------------------------- Math engine -------------------------------
TRANSFORMATIONS = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

SAFE_LOCALS = {
    "sqrt": sp.sqrt, "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "log": sp.log, "ln": sp.log, "pi": sp.pi, "E": sp.E,
    "exp": sp.exp, "abs": sp.Abs,
}

def clean_equation(text):
    text = text.strip()
    text = text.replace("−", "-").replace("–", "-").replace("×", "*").replace("÷", "/")
    text = text.replace("²", "^2").replace("³", "^3").replace("⁴", "^4")
    text = text.replace("＝", "=").replace("π", "pi")
    text = text.replace("√", "sqrt")
    text = text.replace("≤", "<=").replace("≥", ">=")
    text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    return text

def parse_math_side(side):
    return parse_expr(
        side,
        local_dict=SAFE_LOCALS,
        transformations=TRANSFORMATIONS,
        evaluate=True,
    )

def solve_equation(raw_text):
    text = clean_equation(raw_text)
    if not text:
        raise ValueError("Enter or recognize an equation first.")
    if "[?]" in text or "?" in text:
        raise ValueError("The equation contains an unreadable symbol. Correct it in the equation box first.")
    if text.count("=") > 1:
        raise ValueError("Please use one equals sign in an equation.")

    if "=" in text:
        left_text, right_text = [part.strip() for part in text.split("=", 1)]
        if not left_text or not right_text:
            raise ValueError("Both sides of the equation need an expression.")
        left = parse_math_side(left_text)
        right = parse_math_side(right_text)
        symbols = sorted(left.free_symbols | right.free_symbols, key=lambda symbol: symbol.name)
        if not symbols:
            is_true = sp.simplify(left - right) == 0
            return "True — both sides are equal." if is_true else f"False — left side is {sp.sstr(left)}, right side is {sp.sstr(right)}."
        solution = sp.solve(sp.Eq(left, right), symbols)
        if not solution:
            return "No solution found (or the equation may be outside the supported solver range)."
        if len(symbols) == 1:
            symbol = symbols[0]
            values = solution if isinstance(solution, list) else [solution]
            return ", ".join(f"{symbol} = {sp.sstr(value)}" for value in values)
        if isinstance(solution, dict):
            return ", ".join(f"{key} = {sp.sstr(value)}" for key, value in solution.items())
        return sp.sstr(solution)

    expression = parse_math_side(text)
    simplified = sp.simplify(expression)
    if not simplified.free_symbols:
        return f"{sp.sstr(simplified)}  (≈ {sp.N(simplified, 8)})"
    return f"Simplified: {sp.sstr(simplified)}"

# ----------------------------- UI ----------------------------------------
if "recognized_equation" not in st.session_state:
    st.session_state.recognized_equation = ""
if "recognition_notes" not in st.session_state:
    st.session_state.recognition_notes = ""

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">LOCAL AI · PRIVATE BY DESIGN</div>
      <h1>InkSolve <span style="color:#60e5d0">✦</span></h1>
      <p>Capture handwritten maths, let a local vision model read it, and solve it with symbolic mathematics.
      Your equation image stays on your computer.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Local AI settings")
    model_name = st.text_input("Ollama vision model", value=DEFAULT_MODEL)
    st.caption("The model must already be downloaded in Ollama.")
    st.caption("Ollama runs locally at 127.0.0.1:11434.")

scan_tab, history_tab, help_tab = st.tabs(["✦  Scan & Solve", "◷  History", "ⓘ  How it works"])

with scan_tab:
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown("### 01 / Capture")
        st.markdown('<p class="small-muted">Write one clear equation on plain paper. Keep it centered and well lit.</p>', unsafe_allow_html=True)
        camera_image = st.camera_input("Take a picture of your equation", key="inksolve_camera")
        uploaded_image = st.file_uploader("Or upload an image", type=["png", "jpg", "jpeg", "webp"], key="inksolve_upload")
        image_file = uploaded_image if uploaded_image is not None else camera_image

        if image_file is not None:
            st.image(image_file, caption="Image to recognize", use_container_width=True)
            if st.button("Read equation with local AI", use_container_width=True):
                with st.spinner("Local vision model is reading the handwriting…"):
                    try:
                        equation, notes = ask_ollama(image_file.getvalue(), model_name.strip() or DEFAULT_MODEL)
                        st.session_state.recognized_equation = equation
                        st.session_state.recognition_notes = notes
                        st.rerun()
                    except requests.exceptions.ConnectionError:
                        st.error("Could not connect to Ollama. Open Ollama and make sure it is running.")
                    except requests.exceptions.Timeout:
                        st.error("The model took too long. Try a smaller model or a clearer image.")
                    except requests.exceptions.HTTPError as exc:
                        detail = ""
                        try:
                            detail = exc.response.text[:500]
                        except Exception:
                            pass
                        st.error(f"Ollama returned an error: {detail or exc}")
                    except Exception as exc:
                        st.error(f"Recognition failed: {exc}")

    with right:
        st.markdown("### 02 / Check & solve")
        st.markdown('<p class="small-muted">Always check the recognized symbols before solving.</p>', unsafe_allow_html=True)
        equation_text = st.text_input(
            "Recognized equation (editable)",
            key="recognized_equation",
            placeholder="Example: x^2 + 3 = 7",
        )
        if st.session_state.recognition_notes:
            st.caption(st.session_state.recognition_notes)
        st.caption("Tip: type powers with ^, for example x^2. You can edit any misread symbol.")
        if st.button("Solve equation", use_container_width=True):
            try:
                result = solve_equation(equation_text)
                st.markdown(
                    f'<div class="answer-card"><div class="answer-label">Result</div><div class="answer-value">{result}</div></div>',
                    unsafe_allow_html=True,
                )
                save_history(equation_text, result)
                st.session_state.last_equation = equation_text
                st.session_state.last_result = result
            except Exception as exc:
                st.error(f"Could not solve this yet: {exc}")

        if "last_result" in st.session_state:
            st.markdown("#### Latest result")
            st.latex(sp.latex(sp.Symbol("x")) if False else r"\text{Solved successfully}")
            st.write(f"**Equation:** `{st.session_state.last_equation}`")
            st.write(f"**Answer:** {st.session_state.last_result}")

with history_tab:
    st.markdown("### Your recent equations")
    history = get_history()
    if not history:
        st.info("Solved equations will appear here.")
    else:
        for created_at, equation, result in history:
            with st.expander(f"{equation}  ·  {created_at}"):
                st.write(f"**Result:** {result}")
                if st.button("Use this equation", key=f"use_{created_at}_{equation}"):
                    st.session_state.recognized_equation = equation
                    st.info("Equation loaded. Return to Scan & Solve to edit or solve it again.")

with help_tab:
    st.markdown("### How it works")
    st.markdown(
        """
        1. **Capture:** use your webcam or upload a picture.
        2. **Recognize:** Ollama sends the image to a vision model running on your own computer.
        3. **Review:** check and correct the transcription.
        4. **Solve:** SymPy handles the symbolic mathematics.
        5. **History:** previous equations are stored in a local SQLite file.

        **Privacy:** this app sends the image only to your local Ollama service at `localhost`. The app does not call a cloud OCR API.
        """
    )
    st.warning("This is a learning project, not a guaranteed math tutor. Verify the transcription and results, especially for complex notation.")
