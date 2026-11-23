import random

import streamlit as st

from ai_agent import GlitchInvestigatorAgent
from logic_utils import (
    check_guess,
    get_attempt_limit,
    get_range_for_difficulty,
    parse_guess,
    update_score,
)

HINT_MESSAGES = {
    "Win": "🎉 Correct!",
    "Too High": "📉 Go LOWER!",
    "Too Low": "📈 Go HIGHER!",
}

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

st.title("🎮 Game Glitch Investigator")
st.caption("An AI-powered guessing game with an autonomous Gemini Glitch Investigator.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

ai_mode = st.sidebar.radio(
    "Player Mode",
    ["Human + AI Coach", "Autonomous AI Investigator"],
    index=0,
)

attempt_limit = get_attempt_limit(difficulty)
low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

if "agent" not in st.session_state:
    st.session_state.agent = GlitchInvestigatorAgent()


def start_new_round():
    """Reset every piece of per-round state for the current difficulty."""
    st.session_state.secret = random.randint(low, high)
    st.session_state.secret_difficulty = difficulty
    st.session_state.attempts = 0
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.turn_records = []
    st.session_state.agent_logs = []
    st.session_state.coach_advice = None
    st.session_state.final_message = ""
    st.session_state.celebrated = False


def process_validated_guess(guess_int: int, show_hint: bool, agent_step: dict | None = None):
    """Apply a validated guess (from human or AI) to the core game loop."""
    st.session_state.attempts += 1
    st.session_state.history.append(guess_int)

    secret = st.session_state.secret
    outcome = check_guess(guess_int, secret)

    st.session_state.turn_records.append({"guess": guess_int, "outcome": outcome})

    if agent_step is not None:
        st.session_state.agent_logs.append(agent_step)

    if show_hint:
        st.warning(HINT_MESSAGES[outcome])

    st.session_state.score = update_score(
        current_score=st.session_state.score,
        outcome=outcome,
        attempt_number=st.session_state.attempts,
    )

    if outcome == "Win":
        st.session_state.status = "won"
        st.session_state.final_message = (
            f"You won in {st.session_state.attempts} "
            f"attempt{'s' if st.session_state.attempts != 1 else ''}! "
            f"The secret was {secret}. "
            f"Final score: {st.session_state.score}"
        )
        st.rerun()
    elif st.session_state.attempts >= attempt_limit:
        st.session_state.status = "lost"
        st.session_state.final_message = (
            f"Out of attempts! "
            f"The secret was {secret}. "
            f"Score: {st.session_state.score}"
        )
        st.rerun()


if "secret" not in st.session_state:
    start_new_round()

if st.session_state.secret_difficulty != difficulty:
    start_new_round()
    st.info(f"Difficulty changed to {difficulty}. New round started.")

st.subheader("Make a guess")

st.info(
    f"Guess a number between {low} and {high}. "
    f"Attempts left: {attempt_limit - st.session_state.attempts}"
)

with st.expander("Developer Debug Info"):
    st.write("Secret:", st.session_state.secret)
    st.write("Attempts:", st.session_state.attempts)
    st.write("Score:", st.session_state.score)
    st.write("Difficulty:", difficulty)
    st.write("History:", st.session_state.history)
    st.write(
        "Agent Status:",
        "Gemini API Connected" if st.session_state.agent.client else "Fallback Mode (No API Key)",
    )

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success(st.session_state.final_message)
        if not st.session_state.celebrated:
            st.balloons()
            st.session_state.celebrated = True
        st.caption("Start a new game to play again.")
    else:
        st.error(st.session_state.final_message)
        st.caption("Start a new game to try again.")

    if st.button("New Game 🔁"):
        start_new_round()
        st.rerun()
    st.stop()

# --- GAMEPLAY CONTROLS ---
if ai_mode == "Human + AI Coach":
    raw_guess = st.text_input("Enter your guess:", key=f"guess_input_{difficulty}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        submit = st.button("Submit Guess 🚀")
    with col2:
        ask_coach = st.button("Ask Gemini Coach 🤖")
    with col3:
        new_game = st.button("New Game 🔁")
    with col4:
        show_hint = st.checkbox("Show hint", value=True)

    if new_game:
        start_new_round()
        st.rerun()

    if ask_coach:
        with st.spinner("Gemini is analyzing game state..."):
            plan = st.session_state.agent.plan_next_move(
                low=low,
                high=high,
                attempts_left=attempt_limit - st.session_state.attempts,
                turn_records=st.session_state.turn_records,
            )
            st.session_state.coach_advice = plan

    if st.session_state.coach_advice:
        advice = st.session_state.coach_advice
        st.info(
            f"**Gemini Coach ({advice['source']}):** Try **{advice['guess']}** — {advice['reasoning']}"
        )

    if submit:
        ok, guess_int, err = parse_guess(raw_guess, low, high)
        if not ok:
            st.error(err)
        else:
            st.session_state.coach_advice = None
            verification = st.session_state.agent.verify_outcome(
                low=low,
                high=high,
                prior_turns=st.session_state.turn_records,
                guess=guess_int,
                outcome=check_guess(guess_int, st.session_state.secret),
            )
            step_log = {
                "guess": guess_int,
                "reasoning": "Human player move audited by Gemini.",
                "verification_note": verification["verification_note"],
                "consistent": verification["consistent"],
            }
            process_validated_guess(guess_int, show_hint, agent_step=step_log)

else:
    # Autonomous AI Investigator Mode (Plan -> Act -> Self-Verify)
    col1, col2, col3 = st.columns(3)
    with col1:
        ai_step_btn = st.button("Run 1 AI Turn 🤖")
    with col2:
        ai_solve_btn = st.button("Auto-Solve Round ⚡")
    with col3:
        new_game = st.button("New Game 🔁")

    if new_game:
        start_new_round()
        st.rerun()

    if ai_step_btn:
        with st.spinner("Agent planning, acting, and verifying..."):
            step = st.session_state.agent.execute_agent_turn(
                low=low,
                high=high,
                secret=st.session_state.secret,
                attempts_left=attempt_limit - st.session_state.attempts,
                turn_records=st.session_state.turn_records,
            )
            process_validated_guess(step["guess"], show_hint=True, agent_step=step)

    if ai_solve_btn:
        with st.spinner("Gemini Investigator solving full round..."):
            while (
                st.session_state.status == "playing"
                and st.session_state.attempts < attempt_limit
            ):
                step = st.session_state.agent.execute_agent_turn(
                    low=low,
                    high=high,
                    secret=st.session_state.secret,
                    attempts_left=attempt_limit - st.session_state.attempts,
                    turn_records=st.session_state.turn_records,
                )
                st.session_state.attempts += 1
                st.session_state.history.append(step["guess"])
                st.session_state.turn_records.append(
                    {"guess": step["guess"], "outcome": step["outcome"]}
                )
                st.session_state.agent_logs.append(step)
                st.session_state.score = update_score(
                    current_score=st.session_state.score,
                    outcome=step["outcome"],
                    attempt_number=st.session_state.attempts,
                )
                if step["outcome"] == "Win":
                    st.session_state.status = "won"
                    st.session_state.final_message = (
                        f"AI Investigator won in {st.session_state.attempts} attempts! "
                        f"Secret: {st.session_state.secret}. Final score: {st.session_state.score}"
                    )
                    break
            if st.session_state.status == "playing":
                st.session_state.status = "lost"
                st.session_state.final_message = (
                    f"AI ran out of attempts! Secret was {st.session_state.secret}."
                )
            st.rerun()

# --- AGENTIC REASONING & SELF-VERIFICATION LOG ---
if st.session_state.agent_logs:
    st.divider()
    st.subheader("🔍 Agent Plan → Act → Self-Verify Log")
    for idx, entry in enumerate(st.session_state.agent_logs, start=1):
        badge = "✅" if entry["consistent"] else "🚨"
        st.markdown(
            f"**Turn {idx} (Guess: `{entry['guess']}`)** {badge}\n"
            f"- **Plan:** {entry['reasoning']}\n"
            f"- **Verify:** {entry['verification_note']}"
        )

st.divider()
st.caption("Built with Streamlit + Google Gemini Agentic Workflow & Guardrails.")
