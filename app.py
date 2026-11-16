#python3 -m venv .venv
import random

import streamlit as st

from logic_utils import (
    check_guess,
    get_attempt_limit,
    get_range_for_difficulty,
    parse_guess,
    update_score,
)

# Display text for each outcome check_guess can return. Hint wording lives
# here in the UI layer, not in logic_utils.
HINT_MESSAGES = {
    "Win": "🎉 Correct!",
    "Too High": "📉 Go LOWER!",
    "Too Low": "📈 Go HIGHER!",
}

st.set_page_config(page_title="Glitchy Guesser", page_icon="🎮")

st.title("🎮 Game Glitch Investigator")
st.caption("An AI-generated guessing game. Something is off.")

st.sidebar.header("Settings")

difficulty = st.sidebar.selectbox(
    "Difficulty",
    ["Easy", "Normal", "Hard"],
    index=1,
)

attempt_limit = get_attempt_limit(difficulty)

low, high = get_range_for_difficulty(difficulty)

st.sidebar.caption(f"Range: {low} to {high}")
st.sidebar.caption(f"Attempts allowed: {attempt_limit}")

def start_new_round():
    """Reset every piece of per-round state for the current difficulty."""
    st.session_state.secret = random.randint(low, high)
    st.session_state.secret_difficulty = difficulty
    st.session_state.attempts = 0 #FIX: changed the count of start attempt from 1 to 0
    st.session_state.score = 0
    st.session_state.status = "playing"
    st.session_state.history = []
    st.session_state.final_message = ""
    st.session_state.celebrated = False


if "secret" not in st.session_state:
    start_new_round()

# FIX: Changing difficulty changes the range, so the old secret may now be
# unreachable. Re-roll it and start a fresh round.
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

raw_guess = st.text_input(
    "Enter your guess:",
    key=f"guess_input_{difficulty}"
)

col1, col2, col3 = st.columns(3)
with col1:
    submit = st.button("Submit Guess 🚀")
with col2:
    new_game = st.button("New Game 🔁")
with col3:
    show_hint = st.checkbox("Show hint", value=True)

if new_game:
    start_new_round()
    st.rerun()

if st.session_state.status != "playing":
    if st.session_state.status == "won":
        st.success(st.session_state.final_message)
        # Only pop the balloons on the render right after the win, not on
        # every later rerun (toggling the hint box, reopening debug info).
        if not st.session_state.celebrated:
            st.balloons()
            st.session_state.celebrated = True
        st.caption("Start a new game to play again.")
    else:
        st.error(st.session_state.final_message)
        st.caption("Start a new game to try again.")
    st.stop()

if submit:
    ok, guess_int, err = parse_guess(raw_guess, low, high)

    if not ok:
        # Rejected input is not a guess: it costs no attempt and is not
        # recorded in history.
        st.error(err)
    else:
        st.session_state.attempts += 1
        st.session_state.history.append(guess_int)

        secret = st.session_state.secret

        outcome = check_guess(guess_int, secret)

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

st.divider()
st.caption("Built by an AI that claims this code is production-ready.")
