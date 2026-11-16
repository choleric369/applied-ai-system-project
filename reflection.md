# 💭 Reflection: Game Glitch Investigator

Answer each question in 3 to 5 sentences. Be specific and honest about what actually happened while you worked. This is about your process, not trying to sound perfect.

## 1. What was broken when you started?

- What did the game look like the first time you ran it?
- List at least two concrete bugs you noticed at the start  
  (for example: "the hints were backwards").

The game UI part, rendering everything is good, seems like nothing wrong but when I started guessing
the number noticed couple of bugs:

1st bug I noticed was instead of giving GO HIGHER it gives GO LOW and vice-versa
2nd bug I noticed is once I finish the game there's not restart option, I can't start a new game the
button doesn't seem to be working 


Bug Reproduction Log

Document at least 3 bugs you found. Add rows as needed.

| Input | Expected Behavior | Actual Behavior | Console Output / Error |
|-------|-------------------|-----------------|------------------------|
| Secret is 50, guess `60` | Hint says to go lower | Outcome `"Too High"` displayed the message " Go HIGHER!" | No error — silently wrong |
| Click New Game after winning | A fresh round starts | Nothing happens; the button is dead | No error — `status` stayed `"won"` and the guard called `st.stop()` right after the rerun |
| Guess `abc` or submit an empty box | Error message, no attempt consumed | Error message and an attempt consumed, with `"abc"` appended to history | No error |
| Guess `3.9` | Rejected, or an explicit rounding rule | Silently truncated to `3` and scored as a real guess | No error |
| Difficulty set to Hard | A harder round than Normal | Range *narrowed* to 1–50 (Normal is 1–100), and 5 attempts could not cover it | No error |

---

## 2. How did you use AI as a teammate?

- Which AI tools did you use on this project (for example: ChatGPT, Gemini, Copilot)?
- Give one example of an AI suggestion that was correct (including what the AI suggested and how you verified the result).
- Give one example of an AI suggestion you did not accept as written (including what the AI suggested, why you rejected or changed it, and how you verified your version). It does not have to be a suggestion that was wrong: over-engineered, out of scope, harder to read, or a poor fit for this codebase all count.

I used Claude Code as an agent in the VS code terminal, working through the bugs
in stages rather than asking for one big fix: first "list the bugs, don't fix
them", then fixing the most critical ones, then the refactor, then tests.
Asking for the list *before* any fixes was the most useful decision, because
it let me see the whole picture and choose an order instead of accepting
whatever it changed first.

A suggestion that was correct: it identified that `check_guess` fell into a
`try/except TypeError` branch doing a lexicographic string comparison, and
traced it back to the real cause in the caller — `app.py` was casting the
secret to `str` on even attempts. I verified it by checking the specific case
the explanation predicted: guess `9` against secret `80` returned "Too High"
before the fix and "Too Low" after. 

A suggestion I did not accept as written:

1) Raising Hard's attempt limit from 5 to 13. It widened Hard's range to 1-200 to fix the backwards difficulty ladder, which forced the attempt budget up. Initially it suggested me 13 but upon additional prompt and reasoning we agreed on 8 becuase of the binary search logic the mininmum buget should be 8 and coz it's a hard mode fixing it to minimum i.e, 8 made more sense.


2) The agent told me twice that pytest was missing from requirements.txt and should be added. It was already there on line 3 - the file had never been opened. A confident claim about a file nobody checked.


---

## 3. Debugging and testing your fixes

- How did you decide whether a bug was really fixed?
- Describe at least one test you ran (manual or using pytest)  
  and what it showed you about your code.
- Did AI help you design or understand any tests? How?

"It works now" was not good enough, because almost every bug here failed
silently — the app looked fine while being wrong. The check I trusted most was
a differential test: the old buggy versions of the four logic functions
were reconstructed in a scratch file, and the new test suite was run against
them. 23 of the 64 tests failed against the old code and all 64 passed against
the fixed code. That is the thing that proves a test is actually a regression
test rather than a test that would pass either way.

The single most useful test is `test_binary_search_beats_every_possible_secret`. It plays a complete game against every secret in every difficulty range, driven by real `check_guess` calls, and asserts both that the game is won inside the attempt limit and that the search range never collapses. One test catches inverted hints, lexicographic comparison, and an unwinnable difficulty all at once, because all three break the same invariant.

AI helped most in pointing out what the tests did not cover: bugs 6, 7 and 14 live in Streamlit's session-state flow, so no amount of `logic_utils` testing touches them, and covering them properly needs `streamlit.testing.v1.AppTest`. Knowing where the coverage stops is worth as much as the coverage itself.

---

## 4. What did you learn about Streamlit and state?

- How would you explain Streamlit "reruns" and session state to a friend who has never used Streamlit?

Streamlit re-runs your entire script from the top every time anyone touches a
widget. There is no "on click" handler that fires in isolation — clicking a
button just re-executes the whole file with that button reporting `True` once.
So any plain variable is rebuilt from scratch on every interaction, which is
why `random.randint()` at the top level would hand you a brand new secret
every single click. `st.session_state` is the one dictionary that survives
between reruns, which is why the secret, score, and attempt count all have to
live there.

The subtler lesson was that order matters within the rerun. The "New Game"
button looked correct in isolation, but it failed because it ran before the
`status != "playing"` guard that calls `st.stop()` — and because it never reset
`status`, the guard killed the fresh round immediately. Reading the file
top-to-bottom as a script that executes every time, rather than as a set of
independent event handlers, is what makes that bug visible.

---

## 5. Looking ahead: your developer habits

- What is one habit or strategy from this project that you want to reuse in future labs or projects?
  - This could be a testing habit, a prompting strategy, or a way you used Git.
- What is one thing you would do differently next time you work with AI on a coding task?
- In one or two sentences, describe how this project changed the way you think about AI generated code.

The habit I want to keep is asking for the diagnosis before the fix.
Prompting "list the bugs, don't fix them" produced a numbered list I could work from, argue with, and prioritise — and because the list stayed stable, I could point at "fix the top 4" and know exactly what that meant. Handing over the whole problem at once would have produced a large diff I had no framework for reviewing.

The second habit is proving a test can fail. A regression test that has never been run against the broken code is just a test.

What I would do differently: commit between stages. Everything in this project sat as uncommitted working-tree changes through several rounds of edits, which means there was no checkpoint to fall back to if a refactor went wrong. One commit per fix or couple of fixes stage would have made each change reviewable on its own.


This project changed how I read AI-generated code in one specific way: the code that broke this game was not sloppy-looking. It was well-formatted, had sensible function names, used a `try/except`, and ran without errors — and it was wrong in six different places. Plausible structure is not evidence of
correct behaviour, and the only thing that told the difference was a test that had been proven to fail.
