# GrooveMatch — Final Presentation Script
**5–7 minute walkthrough · Loom recording guide**

---

## 0. Before you hit Record (30 seconds, off-camera setup)

Open two terminal panes side by side:
- **Left pane** — ready to run `python -m src.agent_main "..."` commands
- **Right pane** — ready to run `pytest` and `python scripts/eval.py`

Make sure `GOOGLE_API_KEY` is exported and `data/embeddings.npy` exists.
Zoom terminal font to at least 16pt so output is readable in the recording.

---

## 1. Opening — What is GrooveMatch? (45 seconds)

> "Hi, I'm Yuhi. This is GrooveMatch — a music recommendation system that takes
> a plain English description of what you want to hear and gives you ranked song
> suggestions, with explanations for each one.
>
> The original version was a rule-based scorer I built in Modules 1–3.
> This version adds two AI layers on top: a RAG retrieval step and a
> three-turn Gemini agent. I'll show you both in action, then walk through
> the reliability layer, and close with what I learned."

*[Keep terminal visible in background. Don't show file structure or setup.]*

---

## 2. Demo — Run 1: Happy path (1 minute 15 seconds)

**Type and run:**
```
python -m src.agent_main "something calm to study to, acoustic and not too slow"
```

**Narrate as output appears:**

> "Turn 0 is the new planning step — Gemini reads the raw request and reasons
> about it before doing anything structured. You can see it identified low energy,
> an acoustic genre family, and a focused mood. It also flags what's ambiguous —
> in this case, 'not too slow' is subjective.
>
> Turn 1 uses Gemini's function calling API — not a prompt, but a forced function call —
> to produce a guaranteed-structured UserProfile. Genre, mood, energy, acousticness,
> all eight fields, no JSON parsing risk.
>
> The RAG step then embeds that profile as a sentence and runs cosine similarity
> against 150 pre-embedded songs, narrowing to the 30 closest candidates before
> the rule-based scorer ranks them.
>
> Turn 2 is the reflection step — Gemini looks at the top-5 results and decides
> whether they match what the user actually asked for. Here it says 'pass' with
> a one-sentence verdict. Confidence scores are visible next to each result —
> these three hit 99–100% because genre, mood, and energy all matched."

*[Pause on the final ranked list for 3 seconds so it's readable in the recording.]*

---

## 3. Demo — Run 2: Vague request, agent refines (1 minute 30 seconds)

**Type and run:**
```
python -m src.agent_main "late night vibes, kind of sad but nice"
```

**Narrate as output appears:**

> "This input is deliberately vague — 'late night vibes, kind of sad but nice'
> isn't a genre or a mood. Watch Turn 0: Gemini infers moderate energy, jazz
> family, melancholic mood. That reasoning goes into Turn 1 as context, which
> is why the extracted profile lands on jazz + melancholic rather than something
> generic.
>
> Now watch Turn 2. Gemini looks at the top-5 results — all jazz, but mostly
> 'melancholic' tagged songs — and decides the original request actually reads
> more as 'nostalgic' than purely melancholic. Verdict: refine. It changes one
> field, favorite_mood → nostalgic, and the system re-runs retrieval and scoring
> automatically.
>
> The final list shifts. 'Two AM Standard' comes out on top — jazz, nostalgic,
> score 3.96 — and Gemini's closing line explains exactly why it made the change.
> One refinement, one re-run, hard stop."

*[Pause on the final list for 3 seconds.]*

---

## 4. Demo — Run 3: Edge case the guardrails catch (1 minute)

**Type and run:**
```
python -m src.agent_main "I need high energy music for the gym, something intense and electronic"
```

**Narrate as output appears:**

> "This is the clean happy path for the agentic layer — clear genre, clear mood,
> clear energy. Notice the confidence scores: 99% on the top two. That's what
> a full genre + mood + energy match looks like numerically.
>
> Now I'll show the guardrail that protects against bad inputs. Switch to the
> eval harness."

**Switch to right pane and run:**
```
python scripts/eval.py
```

> "This eval harness runs eight predefined profiles — no API key needed — and
> checks named assertions with pass/fail output. The three at the top are happy
> paths. The bottom five are adversarial edge cases:
>
> Ghost Genre — the user asks for 'ska', which isn't in the catalog. The system
> still returns results, but confidence is capped at 50% because no genre bonus
> can fire. The system doesn't crash; it surfaces its own uncertainty.
>
> Out-of-Range Energy — the original codebase accepted energy 1.5, which made
> the energy similarity score negative. The _validate_prefs guardrail now clamps
> that to 1.0 before it ever reaches the scorer. Zero negative scores.
>
> Genre Dominance — this one is a documented limitation. The +2.0 genre weight
> can override a very mismatched energy. The eval confirms it, flags it, and
> the model card documents it honestly. 8 out of 8 pass."

*[Pause on the final line for 2 seconds.]*

---

## 5. Unit tests (30 seconds)

**Run:**
```
pytest
```

> "18 unit tests, all mocked — no API key needed. The agent tests verify the
> full control flow: extraction, Turn 0 planning, reflection pass, reflection
> refine, and the JSON parse fallback. The recommender tests cover the scoring
> formula and the five confidence-score scenarios. Everything green."

*[Pause on the green output for 2 seconds.]*

---

## 6. What I learned (1 minute)

> "Three things stuck with me from this project.
>
> First: structured extraction is not the same as understanding. Gemini reliably
> converts 'late night vibes, kind of sad but nice' into a JSON dict — but that
> translation is lossy. The reflection turn exists because the only way to catch
> that loss is to look at the output and ask whether it matches.
>
> Second: layering works better than replacing. RAG didn't replace the rule-based
> scorer — it made the scorer's inputs better. The scorer still only uses genre,
> mood, and energy. But the retrieval step pre-filters to candidates that are
> already close in acousticness and tempo, so the scorer's blind spots matter less.
>
> Third: every design choice is a policy. The +2.0 genre weight, the 30 RAG
> candidates, the one-refinement cap — none of those are objectively correct.
> They're tradeoffs that need real user data to validate. Building the eval
> harness made that explicit: the genre dominance case is a known failure mode,
> documented and measured, not hidden."

---

## 7. Portfolio close (30 seconds)

> "GitHub link is in the README. The repo has all the source, the eval harness,
> and this walkthrough. If you want to run it yourself, you need a Gemini
> API key and one command to build the embeddings — everything else is standard
> pip.
>
> Thanks for watching."

---

## Portfolio Artifact

**GitHub:** https://github.com/7uhi/applied-ai-system-project

**Reflection paragraph:**

This project shows that I approach AI engineering as a systems problem, not a
prompting problem. My instinct when something breaks is to add a test that
reproduces it and a guardrail that prevents it — the energy-clamping fix, the
ghost-genre confidence cap, and the JSON-fallback path in reflect_and_refine
all came from this. I also care about observability: every Gemini call is
logged as a JSON line, the planning step surfaces its own reasoning, and
confidence scores make the system's uncertainty visible to the user rather
than hiding it. What this project says about me as an AI engineer is that I
want the system to fail gracefully and loudly, not silently and confidently.

---

## Loom Recording Checklist

Before uploading, confirm the video clearly shows:

- [ ] **End-to-end system run** — at least two inputs, full terminal output visible
- [ ] **AI feature behavior** — Turn 0 plan output, Turn 1 extracted profile, RAG candidate count, Turn 2 reflection verdict
- [ ] **Reliability / guardrail behavior** — `scripts/eval.py` output with edge case results labeled, OR the ghost-genre/out-of-range-energy cases called out verbally while the eval runs
- [ ] **Clear outputs for each case** — ranked list with score + confidence visible on screen before moving to the next input

*Paste your Loom URL into README.md under a new "## Walkthrough" section once recorded.*
