import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from logic_utils import check_guess

load_dotenv()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("GlitchAgent")
logger.setLevel(logging.INFO)
if not logger.handlers:
    fh = logging.FileHandler(LOG_DIR / "ai_agent.log", encoding="utf-8")
    fh.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(fh)

GEMINI_BASE_URL = "https://googleapis.com"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


class GlitchInvestigatorAgent:
    """Agentic workflow that plans guesses, acts on game state, and self-verifies outcomes."""

    def __init__(self, model: str = DEFAULT_MODEL, client: Any = None):
        self.model = model
        api_key = os.getenv("GEMINI_API_KEY")
        if client is not None:
            self.client = client
        elif OpenAI is not None and api_key:
            self.client = OpenAI(api_key=api_key, base_url=GEMINI_BASE_URL)
        else:
            self.client = None
            logger.warning("Gemini client unavailable; running in deterministic fallback mode.")

    def _compute_valid_bounds(
        self, low: int, high: int, turn_records: list[dict[str, Any]]
    ) -> tuple[int, int, bool]:
        """Derive tight mathematical bounds from past turns and detect impossible contradictions."""
        cur_low, cur_high = low, high
        contradiction = False
        for turn in turn_records:
            g = turn["guess"]
            out = turn["outcome"]
            if out == "Too Low":
                if g >= cur_high:
                    contradiction = True
                cur_low = max(cur_low, g + 1)
            elif out == "Too High":
                if g <= cur_low:
                    contradiction = True
                cur_high = min(cur_high, g - 1)
        if cur_low > cur_high:
            contradiction = True
        return cur_low, cur_high, contradiction

    def _extract_json(self, raw_text: str) -> dict[str, Any]:
        """Guardrail parser that safely extracts JSON even if wrapped in markdown fences."""
        cleaned = raw_text.strip()
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model output.")
        return json.loads(match.group(0))

    def plan_next_move(
        self,
        low: int,
        high: int,
        attempts_left: int,
        turn_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """STEP 1 (PLAN): Ask Gemini for the optimal next guess and reasoning, with guardrails."""
        cur_low, cur_high, contradiction = self._compute_valid_bounds(
            low, high, turn_records
        )
        safe_midpoint = (cur_low + cur_high) // 2 if cur_low <= cur_high else (low + high) // 2

        if contradiction:
            logger.error(f"GLITCH DETECTED in history bounds: {turn_records}")

        if self.client is None:
            return {
                "guess": safe_midpoint,
                "reasoning": f"Fallback binary search midpoint between {cur_low} and {cur_high}.",
                "guardrail_triggered": True,
                "source": "fallback",
            }

        prompt = (
            "You are an AI Game Glitch Investigator playing a number guessing game.\n"
            f"Original Range: {low} to {high}\n"
            f"Mathematically Valid Remaining Range: {cur_low} to {cur_high}\n"
            f"Attempts Left: {attempts_left}\n"
            f"Past Turns: {json.dumps(turn_records)}\n\n"
            "Plan your next optimal integer guess using binary search to win within the attempt limit. "
            "Respond ONLY with valid JSON in this exact format:\n"
            '{"reasoning": "short 1-sentence explanation", "guess": <integer>}'
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=150,
                temperature=0.0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            raw_content = response.choices[0].message.content
            logger.info(f"PLAN raw response: {raw_content}")
            parsed = self._extract_json(raw_content)

            proposed_guess = int(parsed["guess"])
            reasoning = str(parsed.get("reasoning", "Strategic midpoint guess.")).strip()

            # Guardrail: enforce strict valid range so the LLM cannot waste an attempt out-of-bounds
            if not (cur_low <= proposed_guess <= cur_high):
                logger.warning(
                    f"Guardrail clamped out-of-bounds AI guess {proposed_guess} to {safe_midpoint} "
                    f"(valid: {cur_low}..{cur_high})"
                )
                return {
                    "guess": safe_midpoint,
                    "reasoning": f"{reasoning} [Guardrail adjusted {proposed_guess} -> {safe_midpoint}]",
                    "guardrail_triggered": True,
                    "source": "gemini+guardrail",
                }

            return {
                "guess": proposed_guess,
                "reasoning": reasoning,
                "guardrail_triggered": False,
                "source": "gemini",
            }

        except Exception as exc:
            logger.error(f"Gemini API/parsing error during PLAN: {exc}")
            return {
                "guess": safe_midpoint,
                "reasoning": f"API fallback used due to error: {exc}",
                "guardrail_triggered": True,
                "source": "fallback",
            }

    def verify_outcome(
        self,
        low: int,
        high: int,
        prior_turns: list[dict[str, Any]],
        guess: int,
        outcome: str,
    ) -> dict[str, Any]:
        """STEP 3 (CHECK OWN WORK): Verify that the game's returned hint is logically consistent."""
        updated_turns = prior_turns + [{"guess": guess, "outcome": outcome}]
        new_low, new_high, glitch_detected = self._compute_valid_bounds(
            low, high, updated_turns
        )

        if glitch_detected:
            verdict = (
                f"GLITCH ALERT: Outcome '{outcome}' for guess {guess} contradicts prior hints!"
            )
            logger.error(verdict)
            return {"consistent": False, "verification_note": verdict}

        if outcome == "Win":
            note = f"Verified WIN on {guess}. Target confirmed."
        else:
            note = f"Verified '{outcome}' is consistent. Remaining search space: [{new_low}, {new_high}]."

        logger.info(f"VERIFY: {note}")
        return {"consistent": True, "verification_note": note}

    def execute_agent_turn(
        self,
        low: int,
        high: int,
        secret: int,
        attempts_left: int,
        turn_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Full Plan -> Act -> Self-Verify step using logic_utils.check_guess."""
        plan = self.plan_next_move(low, high, attempts_left, turn_records)
        guess = plan["guess"]

        # STEP 2 (ACT): Execute against core game logic
        outcome = check_guess(guess, secret)
        logger.info(f"ACT: Guessed {guess} -> Outcome: {outcome}")

        # STEP 3 (SELF-VERIFY): Check consistency of result
        verification = self.verify_outcome(low, high, turn_records, guess, outcome)

        return {
            "guess": guess,
            "outcome": outcome,
            "reasoning": plan["reasoning"],
            "guardrail_triggered": plan["guardrail_triggered"],
            "source": plan["source"],
            "consistent": verification["consistent"],
            "verification_note": verification["verification_note"],
        }
