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

## 9. Personal Reflection  

Building this system made it clear how much a single design choice can break everything else. I expected the scoring to fail in subtle ways, but the genre bonus failure was blunt — a song could be wrong on every measurable dimension and still win just because its genre label matched.

The most surprising thing was how much the edge cases taught me. The "contradictory" and "ghost genre" profiles were not exotic corner cases — they are realistic user situations that a real app would encounter every day. That made me realize good testing is as important as the algorithm itself.

This project changed how I think about apps like Spotify. The recommendations feel magical, but underneath they are making similar tradeoffs: which signal gets how much weight, what happens when preferences conflict, and what the system does when it has no good answer. There is no perfect algorithm — there are just choices, and the job is to understand the consequences of each one.
