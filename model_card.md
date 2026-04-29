# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**GrooveMatch 1.0**  

---

## 2. Intended Use  

GrooveMatch 1.0 suggests songs from a small catalog based on what genre, mood, and energy level a user prefers. It assumes the user can express their taste as a set of simple numbers (like an energy target from 0 to 1). This is a classroom project, not a production app. It is meant to show how a basic recommender system works and where that kind of system can go wrong.  

---

## 3. How the Model Works  

Every song in the catalog gets a score. The score is built from three things:

1. **Genre match** — if the song's genre matches what the user asked for, it gets +2 points. This is a big bonus.
2. **Mood match** — if the song's mood matches (like "intense" or "chill"), it gets +1 point.
3. **Energy similarity** — the system compares the song's energy (a number from 0 to 1) to the user's target. The closer they are, the closer to +1 point the song gets.

The song with the highest total score is recommended first. The maximum possible score is 4.0. No other song features (like tempo, danceability, or acousticness) are used in the score.

---

## 4. Data  

The catalog has 18 songs. Each song has a title, artist, genre, mood, energy, tempo, valence, danceability, and acousticness.

The genres are: pop, lofi, rock, electronic, ambient, synthwave, jazz, indie pop, country, folk, metal, bossa nova, darkwave, bluegrass, and meditation. Many genres appear only once. There is no classical, R&B, hip-hop, or Latin music.

The moods are: happy, chill, intense, focused, relaxed, moody, nostalgic, angry, romantic, joyful, peaceful, and melancholic.

The dataset is too small to represent real listener diversity. Genres with only one song (like rock or metal) give very limited options when that genre is requested.

---

## 5. Strengths  

The system works best when the user's favorite genre is well-represented in the catalog and their energy target matches the typical energy of songs in that genre.

For example, the Chill Lofi profile got a near-perfect result. There is one lofi song tagged "focused," and it matched the user's mood and energy target almost exactly. When the catalog and the user align, the scorer finds the right song.

The High-Energy Pop and Deep Intense Rock profiles also got reasonable top results. Both target genres exist in the catalog and have songs with matching moods and high energy, so the scoring logic rewarded the right songs.

---

## 6. Limitations and Bias 

The most significant weakness discovered during testing is that the fixed +2.0 genre bonus can completely overwhelm the continuous audio-feature signals. For example, when a user requests pop music but targets a very low energy of 0.10, high-energy pop songs (energy ~0.85) still outscore acoustically perfect non-pop tracks because their total (~2.0 + 0.2 = 2.2) beats a perfectly matched non-pop song (~1.0). This means the system will confidently recommend songs that are a poor fit on every measurable dimension except genre label. The bias favors users whose preferred genre happens to dominate the catalog: a pop fan always gets a strong boost, while a user who prefers a niche or absent genre (like classical) receives recommendations that are effectively random, chosen only by whichever song happens to be closest in energy. Until the genre weight is normalized relative to the other scoring components, the recommender cannot be trusted to surface the best song—only the best genre match.

---

## 7. Evaluation  

Eight user profiles were tested: three realistic listeners (High-Energy Pop, Chill Lofi, Deep Intense Rock) and five edge cases designed to expose specific blind spots in the scoring logic.

**What I looked for:** whether the top recommendation made intuitive sense for each profile, whether scores reflected genuine preference alignment, and whether any profile exposed unexpected behavior in how genre, mood, and energy interact.

**Results summary:**

- *High-Energy Pop* correctly surfaced **Gym Hero** (#1, score 3.97) — a pop track with intense mood and energy 0.93, nearly identical to the target of 0.90. This is the ideal outcome.
- *Chill Lofi* correctly surfaced **Focus Flow** (#1, score 3.98) — the one lofi track with a "focused" mood, matching on all three scoring axes at once.
- *Deep Intense Rock* correctly surfaced **Storm Runner** (#1, score 3.97) — the only rock song, with intense mood and very close energy. Reasonable, but slots 2–3 were Gym Hero and Eclipse Drop (pop and electronic), which a real rock listener would likely reject.

**What surprised me:**

The most striking result came from the *Genre Dominance* edge case. This profile asks for pop music but targets a very low energy (0.10) — imagine someone who loves pop artists but just wants something quiet and chill. The system returned **Sunrise City** (#1, score 3.28) with energy 0.82, and **Gym Hero** (#2, score 2.17) with energy 0.93. The two songs whose energy was furthest from the request won anyway, purely because they carry the +2.0 pop genre bonus. The actual best energy match — Sacred Geometry at energy 0.15 — scored only 0.95 and landed at #4. The user asked for quiet; the system gave them a gym playlist.

The *Contradictory Energy+Mood* case was similarly revealing. The profile requests a "peaceful" mood but also targets energy 0.92 (a contradiction built in on purpose). Sacred Geometry won with score 3.23 because it matched genre and mood — but its energy similarity was only 0.23, meaning the song scored at the third dimension barely at all. The #2 through #5 recommendations were Storm Runner, Gym Hero, Eclipse Drop, and Crown the Night: four of the loudest, heaviest songs in the catalog, recommended to someone who said they wanted peace.

The *Ghost Genre* case (requesting "classical," which doesn't exist in the catalog) exposed that the genre bonus simply never fires — the entire top five was decided by mood and energy proximity alone, surfacing jazz and folk tracks that have nothing to do with classical music.

These tests confirmed the core issue: a 2.0-point flat bonus for genre label is large enough to override every other signal, but when that bonus is unavailable or misaligned, the system degrades to a rough energy estimator with no real understanding of what the user wants.

---

## 8. Future Work  

1. **Rebalance the genre weight.** The +2.0 genre bonus is too powerful. One fix would be to normalize all three scoring components to the same scale (0 to 1) before adding them together, so no single factor can automatically override the others.

2. **Use more song features.** Danceability, acousticness, tempo, and valence are tracked but never used in scoring. Adding even one more dimension — like acousticness — would help users who prefer acoustic or electronic sound get better matches.

3. **Add result diversity.** Right now the top 5 results are often all the same genre. A diversity filter that enforces at least 2 or 3 different genres in the top results would give users more useful options, especially when their preferred genre only has one or two songs in the catalog.

---

## 9. Responsible AI Reflection

### What are the limitations or biases in your system?

The most structural bias is the **catalog bias**: the song catalog was hand-curated and reflects the taste of whoever built it. Genres like pop, lofi, and rock have the most songs, so users who prefer those genres receive more diverse and better-matched recommendations. A user who wants R&B, Latin, or classical music gets almost nothing useful — not because the algorithm failed, but because those listeners were never considered when the catalog was built. Representation in training data (or in this case, the song catalog) shapes who the system serves well.

Beyond the catalog, the **genre-label bias** is the biggest algorithmic flaw. The +2.0 flat bonus for genre means the system treats all genre matches as equally meaningful, regardless of how far off the song is on every other dimension. A pop song with energy 0.95 beats a perfectly-matched folk song for a user who wants quiet — because "pop" fired the bonus and "folk" didn't. Genre is used as a proxy for overall fit when it is really just one dimension of taste.

The system also has a **missing-dimension bias**: tempo, danceability, valence, and acousticness are tracked but never scored. A user who says they want acoustic music and sets `target_acousticness=0.99` receives no benefit from that preference in the rule-based scorer. The system appears to understand more about the user than it actually does.

### Could your AI be misused, and how would you prevent that?

A music recommender seems low-stakes, but a few misuse vectors are worth naming.

**Filter bubble amplification.** If this system were used at scale, it would keep recommending the same genres and moods a user has always picked — never surfacing something new. Repeated exposure narrows taste rather than expanding it. Prevention: add a diversity term to the scoring formula and occasionally surface high-scoring songs from adjacent genres.

**Catalog manipulation.** Because the scoring is transparent and the catalog is editable, someone with write access could inject songs with popular genre/mood labels to make them rank highly regardless of actual quality. A real system would need catalog provenance controls and human review for new additions.

**Preference extraction misuse (agent mode).** The Claude agent extracts a structured user profile from free text. That profile — genre, mood, energy, acousticness — is logged to `logs/agent.log`. If extended to collect richer personal data (age, location, emotional state), those logs would become a privacy liability. The current logging is limited to music preferences, but the pattern could be misapplied to more sensitive contexts without careful policy guardrails.

Prevention in this project is mostly structural: the catalog is a static CSV, logs are local and git-ignored, and the agent's tool schema only asks for music taste. But in a production context, data minimization and access controls would be essential.

### What surprised you while testing your AI's reliability?

The confidence score made something visible that was previously hidden. Before adding it, a song scoring 2.2 and a song scoring 3.9 both printed the same output format — there was no way to see at a glance how certain the system was. Once confidence appeared on every result, the Genre Dominance edge case became immediately legible: the #1 pop recommendation showing 55% confidence while the correct energy match showed 24% made the problem obvious without needing to read the scores or do the math. A number that seemed like a cosmetic addition turned out to be a useful debugging tool.

The ghost genre case also surprised me. I expected "no genre bonus" to produce noticeably worse results, and it did — but the top recommendation still had 50% confidence because mood and energy both matched. The system wasn't failing loudly; it was quietly returning mediocre results that looked acceptable. That's the harder failure mode: not a crash or an obvious wrong answer, but a confident-looking recommendation that doesn't serve the user.

### Collaboration with AI during this project

Claude (via Claude Code) was the primary AI collaborator throughout. The collaboration shaped the project in ways both helpful and occasionally misleading.

**One instance where the AI gave a helpful suggestion:** When I asked Claude to add confidence scoring, it proposed normalizing score by the theoretical maximum (4.0) rather than the observed maximum in the catalog. That choice was better than what I would have done on my own — a max-normalized score would shift whenever the catalog changed, making the metric unstable across versions. The 4.0 constant is anchored to the scoring formula itself, so it remains meaningful even if every song in the catalog changes. I wouldn't have thought of that distinction unprompted.

**One instance where the suggestion was flawed:** Claude's first draft of the ghost genre test created a song with `genre="classical"` and prefs with `favorite_genre="classical"` — meaning they matched perfectly and the test passed for the wrong reason. The test was supposed to verify that a missing genre caps confidence, but instead it verified a perfect genre match. The assertion `score == 2.0` failed because the actual score was 4.0. Claude had described what the test was *meant* to check but written code that checked something else. Catching that required reading the test logic carefully rather than trusting the description. The fix was simple (change the song's genre to `"lofi"` so the catalog-genre mismatch was real), but it was a good reminder that AI-generated tests need the same scrutiny as AI-generated application code.
