"""Pure game logic for the number guessing game.

This module holds no UI code and imports no Streamlit, so every function
here is directly unit-testable.
"""

#FIX: Refactored logic into logic_utils.py using agent mode
def get_range_for_difficulty(difficulty: str):
    """Return (low, high) inclusive range for a given difficulty.

    Ranges widen as difficulty rises. See ATTEMPT_LIMITS for the matching
    attempt budgets -- every range stays winnable by binary search.
    """
    if difficulty == "Easy":
        return 1, 20
    if difficulty == "Normal":
        return 1, 100
    if difficulty == "Hard":
        return 1, 200 #FIX: The index range is fixed for hard from 50 to 200
    return 1, 100


# FIX: Attempts allowed per difficulty. A binary search needs ceil(log2(span))
# guesses: Easy 5, Normal 7, Hard 8. Easy and Normal get one spare guess;
# Hard gets none, which is what makes it hard.
ATTEMPT_LIMITS = {
    "Easy": 6,
    "Normal": 8,
    "Hard": 8,
}

#FIX: Refactored logic into logic_utils.py using agent mode
def get_attempt_limit(difficulty: str):
    """Return the number of guesses allowed for a given difficulty."""
    return ATTEMPT_LIMITS.get(difficulty, 8)

#FIX: Refactored logic into logic_utils.py using agent mode
def parse_guess(raw: str, low: int = None, high: int = None):
    """
    Parse user input into an int guess.

    If low and high are supplied, the guess must fall inside that
    inclusive range to be accepted.

    Returns: (ok: bool, guess_int: int | None, error_message: str | None)
    """
    if raw is None:
        return False, None, "Enter a guess."

    text = raw.strip()

    if text == "":
        return False, None, "Enter a guess."

    try:
        value = int(text)
    except ValueError:
        # Accept "42.0" as 42, but reject genuinely fractional input
        # rather than silently truncating it.
        try:
            as_float = float(text)
        except ValueError:
            return False, None, "That is not a number."

        if not as_float.is_integer():
            return False, None, "Enter a whole number."

        value = int(as_float)

    if low is not None and high is not None and not low <= value <= high:
        return False, None, f"Enter a number between {low} and {high}."

    return True, value, None

#FIX: Refactored logic into logic_utils.py using agent mode
def check_guess(guess, secret):
    """
    Compare guess to secret and return the outcome.

    Returns one of: "Win", "Too High", "Too Low"

    The caller is responsible for turning the outcome into a user-facing
    hint, so this module stays free of display strings.
    """
    if guess == secret:
        return "Win"

    if guess > secret:
        return "Too High"
    return "Too Low"

#FIX: Refactored logic into logic_utils.py using agent mode
def update_score(current_score: int, outcome: str, attempt_number: int):
    """Update score based on outcome and attempt number.

    attempt_number is 1-based: the first guess is attempt 1, worth the
    full 90 points. Each later attempt is worth 10 less, floored at 10.
    A wrong guess costs 5 points regardless of direction.
    """
    if outcome == "Win":
        points = 100 - 10 * attempt_number
        if points < 10:
            points = 10
        return current_score + points

    if outcome in ("Too High", "Too Low"):
        return current_score - 5

    return current_score
