# 🎮 Game Glitch Investigator — Agentic AI Edition

**An interactive Streamlit number-guessing game enhanced with a self-verifying Google Gemini AI agent, runtime guardrails, structured logging, and an automated reliability test suite.**

---

## 📌 Project Overview & Origin

This system is an applied AI evolution of **Game Glitch Investigator** (originally built in Modules 1–3). In its original form, *Game Glitch Investigator* was a deterministic Streamlit number-guessing game focused on debugging broken game logic—such as inverted high/low hints, unvalidated user inputs costing attempts, and difficulty changes failing to reset the secret number. 

In this upgraded version, I embedded an **autonomous AI QA investigator and strategic coach** directly into the core game loop. Rather than acting as a disconnected chatbot, the AI agent actively plans guesses, plays through the game engine (`logic_utils.py`), and mathematically audits every returned hint to verify that logic glitches never resurface—demonstrating how agentic workflows and deterministic guardrails make LLM-powered software reliable in production.

---

## 🏗️ Architecture Overview

The system follows a strict **Input → Process → Output** pipeline with both automated testing and human-in-the-loop verification:

1. **Input & Human-in-the-Loop (`app.py`):** A player selects a difficulty (`Easy`, `Normal`, `Hard`) and chooses between **Human + AI Coach** mode or **Autonomous AI Investigator** mode. Human reviewers can expand **Developer Debug Info** or inspect the live **Plan → Act → Self-Verify Log** to audit the AI's reasoning step by step.
2. **Core Processing & Agentic Loop (`ai_agent.py` + `logic_utils.py`):**
   - **Plan:** `GlitchInvestigatorAgent` sends the valid numeric bounds and past turn history from `st.session_state` to **Google Gemini (`gemini-2.5-flash`)** to generate a structured JSON guess and explanation.
   - **Guardrails & Fallback:** A validation layer extracts JSON safely, clamps any out-of-range guesses to a valid midpoint, and falls back to a deterministic binary search midpoint if the API is unreachable or missing a key.
   - **Act & Self-Verify:** The validated guess executes inside `logic_utils.check_guess()`. The agent then checks whether the returned hint (`"Too High"` or `"Too Low"`) mathematically aligns with prior turns, raising a `GLITCH ALERT` if a contradiction occurs.
3. **Output, Observability & Automated Evaluator (`logs/ai_agent.log` + `tests/test_ai_reliability.py`):** Renders real-time hints, scores, and consistency badges in Streamlit, writes timestamped audit trails to `logs/ai_agent.log`, and runs automated `pytest` evaluations against hallucinated outputs, injected glitches, and boundary secrets.

> 📐 View the full Mermaid diagram source in [`diagrams/architecture.mmd`](diagrams/architecture.mmd).

---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com
cd applied-ai-system-project
```

### 2. Create & Activate a Virtual Environment
**Windows (Command Prompt):**
```bash
python -m venv .venv
.venv\Scripts\activate
```
**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and add a free API key from [Google AI Studio](https://google.com):
```bash
copy .env.example .env
```
Update `.env` with your credentials:
```env
GEMINI_API_KEY=your_google_ai_studio_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
*(Note: If no API key is configured, the system's fallback guardrail engages automatically so the application and `pytest` suite still run without errors.)*

### 5. Launch the Application
```bash
python -m streamlit run app.py
```

---

## 💬 Sample Interactions

### Example 1: Autonomous AI Investigator Solving a Round (Normal: 1–100, Secret = `73`)
- **Input:** User selects `Autonomous AI Investigator` and clicks **Auto-Solve Round ⚡**.
- **AI Output (Turn 1):**
  - **Plan:** *"Start at the midpoint of 1 to 100 to eliminate half the search space."* → Guesses `50`
  - **Game Outcome:** `📈 Go HIGHER!`
  - **Verify:** ✅ *"Verified 'Too Low' is consistent. Remaining search space: [51, 100]."*
- **AI Output (Turn 2):**
  - **Plan:** *"Pick the midpoint of the updated valid range 51 to 100."* → Guesses `75`
  - **Game Outcome:** `📉 Go LOWER!`
  - **Verify:** ✅ *"Verified 'Too High' is consistent. Remaining search space: [51, 74]."*
- **Final Result:** Solves `73` in 6 attempts (`Final score: 15`) with every step logged to `logs/ai_agent.log`.

### Example 2: Human + AI Coach Mode
- **Input:** Player is on `Hard` (1–200), has guessed `100` (`Too High`) and `50` (`Too Low`), and clicks **Ask Gemini Coach 🤖**.
- **AI Output:**
  - `Gemini Coach (gemini): Try 75 — Based on previous hints, the target must lie between 51 and 99; 75 splits the remaining range evenly.`

### Example 3: Guardrail Interception on Out-of-Bounds LLM Output
- **Input:** Simulated LLM returns `{"reasoning": "Guessing way outside range", "guess": 9999}` when valid bounds are `1` to `100`.
- **System Output:**
  - Guardrail intercepts `9999`, clamps the guess to `50`, logs a `WARNING` to `logs/ai_agent.log`, and prevents the AI from wasting a player attempt.

---

## 🧠 Design Decisions & Trade-Offs

- **OpenAI-Compatible SDK with Google Gemini (`gemini-2.5-flash`):** Using the `openai` Python client pointed at Google's OpenAI-compatible endpoint allows easy model swapping via `.env` without rewriting application code, while taking advantage of Gemini's fast, free-tier JSON responses.
- **Deterministic Guardrails Over Pure LLM Autonomy:** LLMs occasionally violate numeric constraints or experience network timeouts. Pairing Gemini with strict Python boundary checks (`cur_low <= proposed_guess <= cur_high`) and a deterministic midpoint fallback trades a tiny bit of open-ended LLM creativity for **100% uptime and zero invalid guesses**.
- **Pure Logic Separation (`logic_utils.py` vs. `ai_agent.py`):** Keeping `logic_utils.py` completely free of Streamlit and LLM dependencies ensures the core game rules remain fast, deterministic, and independently unit-testable.

---

## 🧪 Testing Summary

Run the full automated reliability and unit test suite with:
```bash
pytest
```

- **What Worked:** All parameterized tests in `tests/test_ai_reliability.py` passed, verifying 100% solve reliability on boundary edge cases (`min`, `mid`, `max`) across Easy, Normal, and Hard difficulties, accurate `GLITCH ALERT` detection when contradictory hints are injected, and clean guardrail clamping on out-of-bounds LLM responses.
- **What Didn't & How It Was Fixed:** During initial integration, missing `python-dotenv` dependencies caused test collection errors, and mixing old UI code into `app.py` rendered raw docstrings on screen. Pinning all dependencies in `requirements.txt` and isolating UI rendering from `logic_utils.py` resolved both issues reproducibly.
- **What I Learned:** Integrating AI into an existing codebase works best when the LLM handles high-level planning and explanation while deterministic Python guardrails enforce hard business rules.

---

## 💡 Reflection

Building this project taught me that the hardest part of applied AI engineering isn't getting an LLM to generate an answer—it is designing the **guardrails, state tracking, and evaluation tests** around the model so the overall application remains predictable when the LLM fails or hallucinates.

*(For a detailed responsible-AI reflection—covering AI collaboration, accepted vs. revised suggestions, and system limitations—please see [`model_card.md`](model_card.md).)*


## 🧪 Reliability and Evaluation

To prove the AI agent works reliably rather than just appearing to work in a single demo, the system combines **automated `pytest` evaluations**, **runtime guardrails with structured logging (`logs/ai_agent.log`)**, and **structured scenario testing**.

**Summary:** **11 out of 11 automated tests passed (100% pass rate)** across boundary edge cases, hallucinated out-of-bounds outputs, and injected logic glitches. Before adding deterministic bounds validation, raw LLM outputs occasionally drifted outside the active search range on narrow intervals; after adding the clamping guardrail and midpoint fallback, solve accuracy reached **100% (9/9 boundary rounds solved within attempt limits)** and invalid guess rate dropped to **0%**.

### Structured Evaluation Matrix

| Test Scenario / Input | Evaluation Criteria | Method | Result |
| :--- | :--- | :--- | :--- |
| **Hallucinated Out-of-Bounds Guess** (`{"guess": 9999}` on range `1–100`) | Guardrail intercepts `9999`, clamps to valid midpoint `50`, sets `guardrail_triggered=True`, and logs `WARNING` | Automated (`pytest`) | **Pass** — Clamped to `50` and logged |
| **Injected Logic Glitch** (Prior: `50 -> Too Low`; Next: `40 -> Too High`) | Self-verifier detects mathematical contradiction and flags `consistent=False` with `GLITCH ALERT` | Automated (`pytest`) | **Pass** — Caught contradiction immediately |
| **Easy Mode Boundaries** (`secret = 1, 10, 20`; max 6 attempts) | Solves 100% of boundary secrets within attempt budget with zero invalid guesses | Automated (`pytest`) | **Pass** — 3/3 solved (avg 3.3 turns) |
| **Normal Mode Boundaries** (`secret = 1, 50, 100`; max 8 attempts) | Solves 100% of boundary secrets within attempt budget with zero invalid guesses | Automated (`pytest`) | **Pass** — 3/3 solved (avg 5.0 turns) |
| **Hard Mode Boundaries** (`secret = 1, 100, 200`; max 8 attempts) | Solves 100% of boundary secrets within attempt budget with zero invalid guesses | Automated (`pytest`) | **Pass** — 3/3 solved (avg 6.0 turns) |
| **Missing / Invalid API Key** (`GEMINI_API_KEY` unset or API timeout) | Logs error to `logs/ai_agent.log` and engages deterministic midpoint fallback without crashing UI | Manual + Automated | **Pass** — Graceful fallback; 0 crashes |
| **Human Coach Request** (Mid-game on `Normal`, history: `50 -> Too Low`, `75 -> Too High`) | Recommends valid integer inside `[51, 74]` with accurate 1-sentence reasoning | Human Review | **Pass** — Suggested `62` with clear logic |

### Reproducing the Evaluation
Run the automated test suite locally to verify all metrics:
```bash
pytest -v
```
All guardrail interventions, API errors, and self-verification checks are recorded in `logs/ai_agent.log` with ISO timestamps and severity levels (`INFO`, `WARNING`, `ERROR`).
