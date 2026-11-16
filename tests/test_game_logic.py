import math
import sys
from pathlib import Path

import pytest

# Put the project root on sys.path before importing logic_utils. conftest.py
# does this too, but only pytest loads conftest -- running this file directly
# (`python test_game_logic.py`, or an IDE's Run button) would otherwise fail
# at this import.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from logic_utils import (  # noqa: E402  (import follows the sys.path setup above)
    check_guess,
    get_attempt_limit,
    get_range_for_difficulty,
    parse_guess,
    update_score,
)

DIFFICULTIES = ["Easy", "Normal", "Hard"]


# ---------------------------------------------------------------------------
# Original starter tests
# ---------------------------------------------------------------------------

def test_winning_guess():
    # If the secret is 50 and guess is 50, it should be a win
    result = check_guess(50, 50)
    assert result == "Win"

def test_guess_too_high():
    # If secret is 50 and guess is 60, hint should be "Too High"
    result = check_guess(60, 50)
    assert result == "Too High"

def test_guess_too_low():
    # If secret is 50 and guess is 40, hint should be "Too Low"
    result = check_guess(40, 50)
    assert result == "Too Low"


# ---------------------------------------------------------------------------
# Bug #2: the secret was cast to str on every other attempt, forcing a
# lexicographic comparison ("9" > "80" is True). Single-digit guesses against
# multi-digit secrets are where that shows up.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "guess, secret, expected",
    [
        (9, 80, "Too Low"),    # lexicographic compare wrongly said "Too High"
        (9, 10, "Too Low"),
        (5, 100, "Too Low"),
        (80, 9, "Too High"),
        (100, 5, "Too High"),
        (20, 3, "Too High"),
    ],
)
def test_check_guess_compares_numerically_not_as_text(guess, secret, expected):
    assert check_guess(guess, secret) == expected


def test_check_guess_refuses_to_compare_a_string_secret():
    # app.py used to cast the secret to str on every other attempt. The old
    # check_guess caught the resulting TypeError and fell back to comparing
    # text, silently returning the wrong direction. Raising is correct: a
    # type mix-up here should be loud, not quietly wrong.
    with pytest.raises(TypeError):
        check_guess(9, "80")


def test_check_guess_returns_a_plain_outcome_string():
    # Display text belongs to the UI layer, so the logic module must return
    # a bare outcome -- not an (outcome, message) tuple.
    result = check_guess(60, 50)
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Bug #8: the win bonus read `100 - 10 * (attempt_number + 1)`, double-counting
# the attempt that had already been incremented. A first-guess win paid 80.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "attempt_number, expected_points",
    [(1, 90), (2, 80), (3, 70), (4, 60), (8, 20), (9, 10)],
)
def test_win_awards_points_for_the_attempt_actually_used(attempt_number, expected_points):
    assert update_score(0, "Win", attempt_number) == expected_points


def test_win_points_never_fall_below_the_floor():
    for attempt_number in range(10, 40):
        assert update_score(0, "Win", attempt_number) == 10


def test_winning_sooner_always_scores_at_least_as_well():
    scores = [update_score(0, "Win", n) for n in range(1, 15)]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Bug #9: "Too High" paid +5 on even attempts and -5 otherwise, while
# "Too Low" always paid -5. A wrong guess must cost the same either way.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("attempt_number", [1, 2, 3, 4, 5, 6])
def test_wrong_guess_costs_the_same_in_both_directions(attempt_number):
    too_high = update_score(50, "Too High", attempt_number)
    too_low = update_score(50, "Too Low", attempt_number)
    assert too_high == too_low == 45


@pytest.mark.parametrize("outcome", ["Too High", "Too Low"])
@pytest.mark.parametrize("attempt_number", [2, 4, 6])
def test_wrong_guess_never_increases_the_score(outcome, attempt_number):
    assert update_score(50, outcome, attempt_number) < 50


def test_unknown_outcome_leaves_the_score_untouched():
    assert update_score(50, "Something Else", 3) == 50


# ---------------------------------------------------------------------------
# Bug #11: Hard used a 1-50 range, narrower than Normal's 1-100, and its
# 5-attempt budget could not cover the range at all. Range and attempt limit
# have to be tuned together, so both are asserted here.
# ---------------------------------------------------------------------------

def test_ranges_widen_as_difficulty_rises():
    spans = []
    for difficulty in DIFFICULTIES:
        low, high = get_range_for_difficulty(difficulty)
        spans.append(high - low + 1)
    assert spans == sorted(spans), f"difficulty ladder is out of order: {spans}"
    assert len(set(spans)) == len(spans), "difficulties must differ in range"


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_every_difficulty_is_winnable_within_its_attempt_limit(difficulty):
    low, high = get_range_for_difficulty(difficulty)
    needed = math.ceil(math.log2(high - low + 1))
    limit = get_attempt_limit(difficulty)
    assert needed <= limit, (
        f"{difficulty} spans {low}-{high} and needs {needed} guesses "
        f"but allows only {limit}"
    )


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_binary_search_beats_every_possible_secret(difficulty):
    """Play out a real game against each secret, driven by check_guess."""
    low, high = get_range_for_difficulty(difficulty)
    limit = get_attempt_limit(difficulty)

    for secret in range(low, high + 1):
        lo, hi, attempts = low, high, 0

        while True:
            guess = (lo + hi) // 2
            attempts += 1
            assert attempts <= limit, (
                f"{difficulty}: secret {secret} not found within {limit} attempts"
            )

            outcome = check_guess(guess, secret)
            if outcome == "Win":
                break
            if outcome == "Too High":
                hi = guess - 1
            else:
                lo = guess + 1

            assert lo <= hi, (
                f"{difficulty}: hints for secret {secret} contradicted "
                f"each other and emptied the search range"
            )


def test_unknown_difficulty_falls_back_to_a_usable_round():
    low, high = get_range_for_difficulty("Nightmare")
    assert low < high
    assert get_attempt_limit("Nightmare") >= math.ceil(math.log2(high - low + 1))


# ---------------------------------------------------------------------------
# Bug #12: parse_guess silently truncated floats ("3.9" became 3) and did no
# bounds checking, so out-of-range numbers were accepted as valid guesses.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw", ["3.9", "0.5", "-2.7", "99.999"])
def test_fractional_input_is_rejected_not_truncated(raw):
    ok, value, error = parse_guess(raw)
    assert ok is False
    assert value is None
    assert error


@pytest.mark.parametrize("raw, expected", [("42", 42), ("42.0", 42), ("  42  ", 42), ("-7", -7)])
def test_whole_numbers_are_accepted(raw, expected):
    ok, value, error = parse_guess(raw)
    assert ok is True
    assert value == expected
    assert error is None


@pytest.mark.parametrize("raw", ["0", "101", "500", "-7"])
def test_out_of_range_guesses_are_rejected(raw):
    ok, value, error = parse_guess(raw, 1, 100)
    assert ok is False
    assert value is None
    assert "1" in error and "100" in error


@pytest.mark.parametrize("raw", ["1", "50", "100"])
def test_in_range_guesses_including_the_boundaries_are_accepted(raw):
    ok, value, error = parse_guess(raw, 1, 100)
    assert ok is True
    assert value == int(raw)
    assert error is None


@pytest.mark.parametrize("raw", ["abc", "ten", "4 2", "", "   ", None])
def test_non_numeric_input_is_rejected_with_a_message(raw):
    ok, value, error = parse_guess(raw)
    assert ok is False
    assert value is None
    assert isinstance(error, str) and error


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_parse_guess_accepts_the_whole_range_it_is_given(difficulty):
    low, high = get_range_for_difficulty(difficulty)
    for raw in [str(low), str((low + high) // 2), str(high)]:
        ok, value, error = parse_guess(raw, low, high)
        assert ok is True, f"{raw} rejected on {difficulty}: {error}"
        assert low <= value <= high


if __name__ == "__main__":
    # Running this file directly executes the suite instead of merely
    # importing it, so an IDE's Run button behaves like `pytest`.
    sys.exit(pytest.main([__file__, "-v"]))
