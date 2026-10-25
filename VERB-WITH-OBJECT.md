# Verb with object — the `research/verb-with-object` branch

25 October 2026, from `feat/frames`. Gab, after frames made the agent grow instead of slimming it: "What about
creating a branch for trying option 3?", then "I follow your recommendation": try A (paired clues) first, B
(object first, then its actions) only if A falls short.

The question: can the model learn what a verb means with its object ("turn on the music" plays it), so the
agent's rules for it can go?

## In short

- **No, not enough to be worth it.** The model can take over one rule, the rewrite of "meaning with an
  object", without a new wrong action, but only in a narrow setting, with a bigger model and a little less
  certainty. It would remove about 20 lines of the agent.
- **Two rules must stay whatever the model.** The opposites check: without it, "turn the board on" asks "Shut
  the board down?", the bug it was written for (24 Oct). The joining of split verbs ("turn the music off"):
  the opposites check and the follow-ups need it.
- **Nothing is changed on this branch.** Both experiments are switches, off by default: the model trained here
  is the one of `feat/frames`, weight for weight. `tools/verb_with_object.py` replays every variant.

## What was tried

**A0. A skill's `→` lines become training sentences.** play-music says `- turn on, switch on, start → play`.
Until now that line only fed the agent's rewrite rule. Here, play-music's training sentences are also said with
those verbs, so the model sees "turn on the music" labelled play (`examples.py`, `MEANS_SHARE`).

**A1. Paired clues.** Besides words, word pairs side by side, and letter fragments, the model gets word pairs a
few words apart: "turn … music", "on … music", "turn … off". A linear model can then weigh a verb *with* its
object, which it can't with single words (`model.py`, `PAIRS`).

Each was trained, then measured on the six test sets (665 sentences) with the rewrite rule on and off.

## Results

Each cell over the six sets: handled / checked first / wrong skill, asked / **wrong skill acted on** / not
understood; then out of scope: abstained / asked / **acted on**.

| Model | Rewrite rule | In scope | Out of scope | Size |
|---|---|---|---|---|
| `feat/frames` (today) | on | 383 / 153 / 31 / **2** / 26 | 55 / 14 / **1** | 1.5 MB |
| `feat/frames` (today) | off | 374 / 158 / 33 / **2** / 28 | 55 / 14 / **1** | 1.5 MB |
| A0: `→` lines learned | off | 377 / 158 / 31 / **2** / 27 | 54 / 15 / **1** | 1.5 MB |
| A1: + pairs up to 2 apart | off | 378 / 154 / 34 / **2** / 27 | 54 / 15 / **1** | 2.1 MB |
| A1: + pairs up to 4 apart | off | 377 / 153 / 34 / **2** / 29 | 54 / 15 / **1** | 2.6 MB |
| pairs 2, `→` lines in a quarter of the sentences | off | 379 / 152 / 34 / **3** / 27 | 53 / 16 / **1** | 2.1 MB |
| pairs 2, `→` lines in a tenth of the sentences | off | 379 / 152 / 35 / **2** / 27 | 55 / 14 / **1** | 2.1 MB |

The best learned version handles 379 where the rule handles 383: four sentences move from acting to asking
first. Nudge one setting (a quarter instead of a tenth) and a new wrong action appears: "turn the music off"
mutes the sound. The rule is steadier than what replaces it.

What else moved without the rule, in the best version: "shut down" and "power off" now ask before their own
approval (the object model is less sure of "system" once pairs are in: 0.59 → 0.48), "kill bluetooth" asks
first, "turn the music off" goes to the wrong skill but asks. Gained: "give nginx a kick" and "what network am I
on right now" now act.

Reading a sentence stays fast: 0.28 → 0.30 ms median on the laptop, both models together. Training: 40 → 45 s.

**Opposites and joins, turned off in turn.** Without the opposites check, "turn the board on" asks to shut the
board down. Without joining split verbs, the opposites check can't see "turn … on" and lets it through too, and
follow-ups like "turn it back off" lose their action. Both stay.

## Why it falls short

The model learns from sentences TermNL writes itself, from the skills' templates: a few hundred per skill,
built from the same words. A verb's meaning with an object is one line of a skill, and the model has to learn
it from a share of that skill's sentences, competing with the skill's own words. Give it a small share and it
doesn't fully learn it; give it more and the skill's own words weaken ("shut down" behind "turn off the
board"). A rule says it once, exactly. For a meaning a person can write in one line, the readable line is the
better tool.

## What it says about B

B (object first, then a small action model per object) changes the structure, not the clues: "turn on" could
only mean something music can do. It would make the opposites check and `doubts` structural rather than rules.
But it learns from the same sentences, so the same trade-off between a skill's own words and the `→` lines
would come back, and "shut down" said alone, with no object, still needs the rule for an action said alone.
Expected gain for slimming the agent: small; cost: a rewrite of recognition. Not recommended now.

## What would actually slim TermNL

Not the model. `back_agent.py` (668 lines, a second agent kept for comparison) and folding the answer to
"Which one?" and an action said alone into the frame merge (FRAMES.md, B). And the rules that stay are now
data a skill writes (`## Words`), which was the point of making skills drop-in.

## Reproduce

    python3 tools/verb_with_object.py termnl/languages/en/model.json rules=off

A model with pairs: the tool's docstring. Set `PAIRS` (model.py) and `MEANS_SHARE` (examples.py), retrain.
