# Model Card & Responsible AI Reflection — Game Glitch Investigator

## 1. System Overview & Intended Use
- **Model & Stack:** Google Gemini (`gemini-2.5-flash` via OpenAI-compatible SDK), Python, Streamlit, and deterministic Python guardrails (`ai_agent.py` + `logic_utils.py`).
- **Intended Purpose:** Educational software engineering and QA demonstration showing how an agentic workflow (`Plan → Act → Self-Verify`) can play, coach, and audit a number-guessing game for logic glitches.
- **Out-of-Scope Uses:** This agent is specialized strictly for bounded integer search and hint-consistency auditing; it is not designed for general-purpose software QA, security penetration testing, or high-stakes decision-making.

---

## 2. Limitations and Biases in the System
- **Domain & Rule Rigidity:** The agent's self-verification module (`_compute_valid_bounds`) assumes standard stationary binary-search rules (where `"Too High"` and `"Too Low"` strictly shrink an inclusive integer interval). If the game rules intentionally changed mid-round (e.g., a moving target or probabilistic hints), the verifier would flag intentional game mechanics as false-positive `GLITCH ALERT` errors.
- **LLM Arithmetic & Interval Drift:** General-purpose language models tokenize digits as text rather than performing native symbolic math. Without deterministic guardrails, `gemini-2.5-flash` occasionally proposes numbers outside narrowed intervals or repeats boundary guesses when intervals become very small (e.g., `51` to `52`).
- **API & Latency Dependency:** Live reasoning depends on external network availability and free-tier rate limits from Google AI Studio. High request volume in **Auto-Solve Round ⚡** mode can trigger API throttling, requiring the deterministic midpoint fallback to take over—which sacrifices natural-language explanation quality in exchange for uptime.
- **Prompt & Framing Bias:** Because the system prompt explicitly instructs the model to *"use binary search to win within the attempt limit,"* the AI always plays with optimal mathematical efficiency rather than mimicking realistic human guessing patterns (which limits its usefulness if someone wanted to simulate casual player behavior).

---

## 3. Potential Misuse and Mitigation Strategies
- **API Key Exposure & Quota Abuse:** If a developer commits their `.env` file or exposes the Streamlit app publicly without authentication, malicious users could drain the owner's API quota or abuse the endpoint to proxy free LLM completions.
  - **Prevention:** `.env` is excluded via `.gitignore`, only a placeholder `.env.example` is committed, and prompts are constructed strictly from server-side game state (`low`, `high`, `turn_records`) rather than passing arbitrary free-form user text to the LLM.
- **Prompt Injection via Game State:** If future versions allowed custom text labels or user-submitted notes inside `turn_records`, crafted text could attempt to hijack the model's JSON output or force out-of-bounds guesses.
  - **Prevention:** All user inputs first pass through `logic_utils.parse_guess()` (enforcing strict integer types), and the LLM's output passes through a regex JSON extractor plus a hard numeric range check (`cur_low <= proposed_guess <= cur_high`) before touching `st.session_state`.
- **Over-Reliance on AI Verification:** Treating the AI's `"Verified consistent"` badge as proof that an entire application is bug-free could lead developers to skip traditional unit testing.
  - **Prevention:** The system pairs live agent verification with a deterministic `pytest` suite (`tests/test_ai_reliability.py` and core `logic_utils.py` unit tests) so critical logic does not rely solely on LLM judgment.

---

## 4. Surprises During Reliability Testing
- **How Smoothly Deterministic Guardrails Masked Model & Network Failures:** While testing `tests/test_ai_reliability.py` with a mock hallucinating LLM (`{"guess": 9999}`) and running the app before configuring an API key, I expected the agent loop to break or waste turns. Instead, the combination of `_compute_valid_bounds` clamping and the midpoint fallback achieved a **100% solve rate across all 9 boundary edge cases (`min`, `mid`, `max` in Easy, Normal, and Hard)** with zero crashes.
- **Dependency & Environment Fragility Over Logic Bugs:** The biggest reliability issues during testing weren't caused by the LLM's math—they came from environment setup gaps (such as missing `python-dotenv` during `pytest` collection) and UI state rendering issues when merging old and new Streamlit code. Recording exact dependency versions in `requirements.txt` and logging every fallback event to `logs/ai_agent.log` proved just as important as prompt engineering.

---

## 5. Collaboration with AI: Accepted vs. Revised Suggestions
Throughout this project, I collaborated with an AI coding assistant to design the agentic architecture, debug environment errors, and build the evaluation harness.

- **One Suggestion I Accepted:**
  - **What it was:** Separating the pure game rules (`logic_utils.py`) from the agentic workflow (`ai_agent.py`) and structuring the agent around a three-step **Plan → Act → Self-Verify** loop with a `pytest` suite (`tests/test_ai_reliability.py`) that simulates hallucinated out-of-bounds guesses and injected logic glitches.
  - **Why I accepted it:** Keeping `logic_utils.py` untouched preserved all my existing Module 1–3 fixes and unit tests, while the self-verification step directly connected the new AI feature to the original theme of *Game Glitch Investigator* instead of adding a generic chatbot.

- **One Suggestion I Rejected / Revised:**
  - **What it was:** The AI assistant initially recommended integrating **Anthropic Claude (`anthropic` SDK)** and later **OpenAI (`gpt-4o-mini` via paid OpenAI API billing)**, along with generating a separate `eval_hints.py` script for riddle-style hints.
  - **Why I rejected/changed it:** I rejected using Anthropic and paid OpenAI billing because I did not have free API credits for Anthropic and my ChatGPT subscription did not cover separate OpenAI API billing. Instead, I revised the architecture to use **Google Gemini (`gemini-2.5-flash`)** on Google AI Studio's free tier via the OpenAI-compatible endpoint, and scoped the AI's role strictly to structured JSON binary-search coaching and glitch verification rather than riddle generation—making the project completely free to reproduce for any reviewer while keeping responses deterministic and testable.
