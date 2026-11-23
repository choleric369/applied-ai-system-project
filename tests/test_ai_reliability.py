import pytest

from ai_agent import GlitchInvestigatorAgent
from logic_utils import get_attempt_limit, get_range_for_difficulty

class MockBadLLMClient:
    """Simulates a hallucinating LLM returning out-of-bounds numbers."""

    class Chat:
        class Completions:
            def create(self, **kwargs):
                class Message:
                    content = '{"reasoning": "Guessing way outside range", "guess": 9999}'

                class Choice:
                    message = Message()

                class Resp:
                    choices = [Choice()]

                return Resp()

        def __init__(self):
            self.completions = self.Completions()

    def __init__(self):
        self.chat = self.Chat()



def test_guardrail_clamps_out_of_bounds_guess():
    """Verify guardrail intercepts out-of-range guesses from the LLM."""
    agent = GlitchInvestigatorAgent(client=MockBadLLMClient())
    plan = agent.plan_next_move(low=1, high=100, attempts_left=8, turn_records=[])
    assert 1 <= plan["guess"] <= 100
    assert plan["guardrail_triggered"] is True
    assert plan["guess"] == 50


def test_self_verification_detects_logic_glitch():
    """Verify the agent detects contradictory game hints (the original Game Glitch bug)."""
    agent = GlitchInvestigatorAgent(client=None)
    prior_turns = [{"guess": 50, "outcome": "Too Low"}]  # Secret must be > 50
    # Simulate a broken game claiming 40 is "Too High" (impossible if secret > 50)
    verification = agent.verify_outcome(
        low=1, high=100, prior_turns=prior_turns, guess=40, outcome="Too High"
    )
    assert verification["consistent"] is False
    assert "GLITCH ALERT" in verification["verification_note"]


@pytest.mark.parametrize("difficulty", ["Easy", "Normal", "Hard"])
@pytest.mark.parametrize("edge_case", ["min", "mid", "max"])
def test_agent_reliability_across_difficulties(difficulty, edge_case):
    """Benchmark 100% solve reliability on boundary secrets across all difficulty modes."""
    low, high = get_range_for_difficulty(difficulty)
    limit = get_attempt_limit(difficulty)
    secret = low if edge_case == "min" else (high if edge_case == "max" else (low + high) // 2)

    agent = GlitchInvestigatorAgent(client=None)
    turns = []
    won = False

    for _ in range(limit):
        step = agent.execute_agent_turn(
            low=low,
            high=high,
            secret=secret,
            attempts_left=limit - len(turns),
            turn_records=turns,
        )
        assert low <= step["guess"] <= high
        assert step["consistent"] is True
        turns.append({"guess": step["guess"], "outcome": step["outcome"]})
        if step["outcome"] == "Win":
            won = True
            break

    assert won is True, f"Agent failed to solve {difficulty} ({edge_case}={secret}) within {limit} attempts"
