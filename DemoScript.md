# GrooveMatch — The Engineer's Pitch
**3-minute presentation script**

---

## The Problem: What did you solve?

> "Most recommendation systems make you fill out a form — pick a genre, pick a mood,
> set a slider. The problem is that's not how people actually think about music.
> People say things like 'something calm to study to, acoustic and not too slow,'
> or 'late night vibes, kind of sad but nice.'
>
> GrooveMatch solves the translation problem: it takes a plain English description
> and turns it into ranked song recommendations with confidence scores and
> explanations — no form, no sliders. I built the original rule-based scorer in
> Modules 1–3. This version adds two AI layers on top to make the natural language
> input actually work."

---

## The Logic: How does the AI think?

> "There are two AI systems running in sequence.
>
> First, RAG — Retrieval-Augmented Generation. The 150-song catalog is
> pre-embedded using a local sentence transformer. When a user makes a request,
> their extracted preferences get embedded the same way, and cosine similarity
> narrows the catalog down to 30 semantic candidates before any scoring happens.
> This means the rule-based scorer never has to look at songs that are obviously
> wrong.
>
> Second, a three-turn Gemini agent. Turn 0 is a planning step — Gemini reads
> the raw request and reasons about intent before anything structured happens.
> Turn 1 uses function calling with mode ANY — not a prompt asking for JSON,
> but a forced function call — so the output is guaranteed structured every time.
> Turn 2 is reflection: Gemini reads the top-5 results, compares them to the
> original request, and either approves or proposes one single-field refinement.
> If it refines, the retrieval and scoring run once more. Hard stop at one retry."

---

## The Reliability: How do you know it works?

> "Three layers. First, an input guardrail — `_validate_prefs` clamps all float
> fields to valid ranges and fills missing keys with defaults before anything
> reaches the scorer. The original code could produce negative energy-similarity
> scores from an out-of-range input. That bug is now a passing test.
>
> Second, 18 unit tests — all mocked, no API key needed. They cover the full
> control flow including the reflection retry signal and the JSON parse fallback.
>
> Third, an eval harness with 8 predefined profiles and named assertions. It
> includes adversarial cases: a ghost genre not in the catalog, an out-of-range
> energy, and the genre dominance limitation — where the +2.0 genre weight
> overrides a bad energy match. That last one is a known failure mode.
> It's documented in the model card rather than hidden. 8 out of 8 pass."

---

## The Reflection: What surprised you?

> "Two things.
>
> The first was how lossy the extraction step actually is. Gemini reliably converts
> 'late night vibes, kind of sad but nice' into a structured dict — but that
> translation throws away information. 'Kind of sad but nice' is a feeling, not
> a feature. The reflection turn exists because the only way to catch that loss
> is to look at the output and ask whether it actually matches. I didn't expect
> the second pass to matter as much as it does.
>
> The second was that layering worked better than replacing. RAG didn't replace
> the rule-based scorer — it made the scorer's inputs better. The scorer still
> only uses genre, mood, and energy. But retrieval pre-filters to candidates
> that are already close in acousticness and tempo, so the scorer's blind spots
> matter less in practice. I expected to need a smarter scorer. What I actually
> needed was better candidates going in."
