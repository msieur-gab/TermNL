# Research — understanding better, without a bigger model

Started 25 October 2026. Gab, after testing `main` on the board: "Requiring an external NLU to retrain
TermNL is somewhat defeating the purpose of the tiny model made to run without a larger NLU on constrained
and low powered board and devices." Then: rather than training further, "first evaluate by looking online
in latest stage of small similar model, if new technical or logic could helps us improve first the overall
logic and then compare to what we have."

This file holds what was found, what it suggests for TermNL, how each idea is measured, and the results.
Methods tested are added under **Tested**, with their numbers beside the baseline.

## In short

- **MiniLM plays no part in training.** Training needs numpy only, and on the board that numpy was
  borrowed from the folder installed for MiniLM. Decided (Gab, 25 Oct): rewrite the trainer in plain
  Python, same model, same `model.json` (option 1 below).
- **TermNL's overall shape is what the field recommends:** exact patterns first, a small model second, a
  fallback last.
- **The best gains look like logic, not a bigger model:** calibrated asking (conformal prediction) and
  out-of-scope by distance to what was taught, both in plain Python on what TermNL already has (the
  second tested below, not kept).
- **A, out of scope by distance, tested 25 Oct: not kept.** With TermNL's clues, the far sentences are
  as often real requests as out of scope. It found a better lead: the typo corrector turns real words
  into taught ones ("game" → "name"), method F.
- **Word proximity, if ever:** at teaching time on the laptop first; on the device only for unknown words,
  only to ask, never to act, and after a measured test (Model2Vec).

## How TermNL understands a sentence today

1. **Exact patterns first.** Each skill lists what people say ("open the {app}", "delete {file}"). A
   sentence that fits a pattern is understood for sure; the model isn't used.
2. **Otherwise, two small guessers:** one for the **action** (open, delete, turn off…), one for the
   **object** (file, wifi, app…). A skill is one action with one object.
3. **What they look at are clues, not meaning:** each word, each pair of neighbouring words, and 3–4
   letter pieces of each word (why "rebot" still looks like "reboot"). Training gave every clue a weight
   for every action and object; a sentence adds up its clues' weights into a percentage (TF-IDF and
   logistic regression, `termnl/model.py`).
4. **The decision:** action % × object %. At 50% or more with no unknown word, it acts (or asks approval);
   from 15% to 50% it asks "Do you mean…?"; under 15%, not understood (`SURE`, `MAYBE` in `agent.py`).
5. **Around it:** typos read as known words, split verbs joined ("turn the music off"), and an action
   said in so many words is never answered with its opposite.

**Its weak spot:** it only knows clues it has seen. In "fire up the browser", "fire" was never taught,
so it weighs nothing and the guess rests on "browser" alone.

## What MiniLM does, and what retraining really needs

- **Training** (`termnl/train.py`, `model.py`) needs **numpy** only, for the matrix sums of its optimiser
  (L-BFGS). Recognising needs the standard library only.
- **Why MiniLM seemed to be back:** the desk's `board/install.sh` puts onnxruntime **and numpy** in
  `~/.models/shared/python`, to run MiniLM. TermNL's trainer was pointed at that folder (and linked into
  `~/.local`). Remove MiniLM's folder and retraining breaks: a shared package, not a model in the loop.
- **MiniLM's real job** is the desk's, at answer time: when TermNL doesn't understand a sentence (under
  0.40) or only guesses (under 0.45), the desk asks its documents with MiniLM (`ask.py`, the `@doc` hook,
  `NOTES` in `server.py`). TermNL alone runs with `doc=None` and never touches it.

Three ways out were proposed: (1) the same trainer in plain Python; (2) Naive Bayes, counting, instant and
incremental but less well calibrated; (3) numpy kept, in TermNL's own folder. **Gab chose 1** (25 Oct):
it removes the dependency without changing anything already tested.

## What the field does (searched 25 October 2026)

1. **Patterns, then a small classifier, then a fallback.** Current advice for routing requests is a
   cascade: cheap keyword or pattern matching, then an embedding or small classifier, then a heavy
   catch-all only when unsure; scores above a line act, a middle band acts but is flagged, a low score
   goes on ([Tian Pan, Apr 2026](https://tianpan.co/blog/2026/04/16/intent-classification-agent-routers)).
   TermNL already is one: templates → model → the desk's documents.
   Home Assistant's built-in matcher (hassil) only accepts exact template matches; a community add-on
   fuzzy-matches names against the known lists before handing a clean sentence back
   ([hass-closest-intent](https://community.home-assistant.io/t/hass-closest-intent-garbled-stt-output-in-actual-intent-out/1009765)).
   TermNL does both already.
2. **The closest relative: OpenVoiceOS's Model2Vec intents.** A fixed table of word vectors (distilled from
   a sentence model) with a linear head on top: reading a sentence is a lookup and an average, no neural
   network at run time. The English model is about 16 MB, 99% on its held-out split but about 91% on
   real sentences from skills' tests, and weaker on paraphrases ("lights on now" against "turn on the
   lights") ([model card](https://huggingface.co/OpenVoiceOS/ovos-m2v-intents-en);
   [pipeline](https://deepwiki.com/OpenVoiceOS/ovos-m2v-pipeline)). The same gap as TermNL's test sets
   against Gab's real turns. Model2Vec's small English models score slightly above MiniLM on MTEB
   classification ([results](https://minish.ai/packages/model2vec/results/)).
3. **Asking, with a number behind it: conformal prediction.** Instead of hand-set lines, a held-out set
   calibrates a threshold so the set of candidate intents holds the right one, say, 99% of the time. One
   candidate: act. A few: a clarifying question offering them (about 2.5 to 3 options on average in the
   paper). Too many: ask to rephrase. No retraining, only a calibration set
   ([CICC, 2024](https://arxiv.org/html/2403.18973v1)).
4. **Out of scope, by distance.** A "none" class trained on out-of-scope sentences (what TermNL does,
   `out-of-scope.md`) did well on nonsense close to the domain but fell to about 60% on unrelated
   sentences. Lowering the confidence of a sentence that is far from every taught sentence
   ("discounting") reached about 78% there, and best overall
   ([Out-of-scope detection, 2023](https://arxiv.org/pdf/2301.06544)). "who won the football game last
   night", read as "name", is this case.
5. **Sentences from a big model help less than expected.** Paraphrases from an LLM beat cheap methods
   mainly with 5 to 20 examples per label; from about 30, the gain is small and cheaper methods match it
   ([LLMs vs established augmentation, 2024](https://arxiv.org/html/2408.16502v1)). TermNL trains on 18 to
   186 sentences per skill (median 93), but most come from its own templates; what counts is the
   distinct ways of saying it. `SCALE-TEST.md` saw "Also said" lift new skills from 21 to 35 of 44 blind
   requests: thin skills are where it pays.
6. **Simple first.** TF-IDF with logistic regression, or fastText, stays the baseline to beat; sentence
   models pay off on ambiguous or messy text and scarce examples
   ([Rick Winfrey](https://rickwinfrey.com/writings/small-models-for-text-classification)). Pairing a
   small model with an LLM at reading time is the state of the art in papers
   ([FCSLM, EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.749/)), not something for the board.

## What it suggests for TermNL, in the order to try

| # | Method | What changes | Cost on the board |
|---|---|---|---|
| A | Out-of-scope by distance | A sentence far from every taught sentence is doubted: lower confidence, or refused | Plain Python, the clues TermNL already has |
| B | Calibrated asking | `SURE` and `MAYBE` replaced by a set of candidate skills calibrated on held-out sentences: one → act, two or three → "Do you mean A or B?", more → rephrase | Plain Python, a number stored with the model |
| C | Plain-Python trainer | numpy gone; same `model.json` | Training time, to measure |
| D | Proximity at teaching time | A word table proposes "Also said" words for thin skills; Gab approves | Nothing: laptop only |
| E | Model2Vec for unknown words | Extra clues for words never taught; may only lead to a question | 8–16 MB and a lookup; measured with `tools/neighbours.py` first |

| F | Real words aren't typos | A list of common English words, plain text: a word on it is never "corrected" into a taught one (game ≠ name, stick ≠ stuck). Found by testing A | A word list of some tens of KB, read at start |

C is independent and can go in at any time. E only if the misses left are mostly unknown words.
**A was tested on 25 Oct and not kept** (see Tested).

## How every method is measured

The same sentences each time: `python3 -m tests.measure all` (five sets, three never trained on), and
Gab's real turns on his laptop (`python3 -m tests.real`, `tests/real.md` kept out of git). A method is
kept only if it **adds no wrong action**; then it is judged on handled, asked, not understood and out of
scope refused. Speed with `python3 -m tools.speed`; training time on the board when the trainer changes.

**Baseline, 25 October 2026** (`main`, 4814004, laptop; the board gives the same decisions):

| Set | Sentences | Handled | Asked first | Wrong skill, asked | Wrong skill, acted | Not understood | Out of scope: refused / asked / acted |
|---|---|---|---|---|---|---|---|
| phrasings | 59 | 41 | 15 | 2 | 0 | 1 | — |
| probes | 89 | 75 | 4 | 7 | 0 | 3 | 3 / 1 / 0 |
| heldout | 122 | 113 | 5 | 3 | 0 | 1 | 9 / 1 / 0 |
| blind | 116 | 69 | 35 | 7 | 1 | 4 | 13 / 2 / 0 |
| scale-blind | 80 | 32 | 38 | 3 | 0 | 7 | 21 / 7 / 0 |
| **all** | **466** | **330** | **97** | **22** | **1** | **16** | **46 / 11 / 0 of 57** |

Gab's real turns (24 Oct): 104 of 117 as Claude guessed (`should (Claude):` lines, not yet judged by Gab).

## Tested

Each method gets its own section: the date, what changed in the code, the table above re-run, what moved
(sentences gained and lost, by name), speed and size, and Gab's decision.

### A — Out of scope by distance: not kept (25 October 2026)

**Result: with TermNL's own clues, distance doesn't tell an out-of-scope sentence from a real request.**
Nothing was changed in the agent; the scores above stand. Reproduce with `python3 -m tools.distance`.

**What was measured.** Of the 523 test sentences, 194 are read by the model rather than a template:
11 out of scope (all asked about, none acted on), 170 requests handled or asked first, 13 wrong readings.
The other 46 out-of-scope sentences are already refused, by the "none" class. For each of the 194, the
words it was read with (typos corrected, names and values left out) were compared with all 5,514 sentences
TermNL trains on, using the model's own clues and weights. Ten measures were tried: the closest taught
sentence (any skill, or the guessed skill), the guessed skill's average sentence, the share of words
taught, each on all clues, on words and word pairs, and on words alone; the model's own confidence too.

**What it showed.** No measure refuses more than one out-of-scope sentence without losing a request.

| Measure | Out of scope refused | Requests lost |
|---|---|---|
| Closest taught sentence, all clues (best) | 1 of 11 | 0 |
| the same, one line further | 2 of 11 | 2 |
| Closest taught sentence, words and pairs | 5 of 11 | 4 (and 2 wrong readings refused) |
| Share of words taught | 2 of 11 | 1 |
| The model's confidence alone | 2 of 11 | 2 |

The one refused for free is "who won the football game last night"; a line drawn for one sentence is
fitted to it, not learned. The next farthest are real requests: "take todo.txt and stick it in projects,
thx", "is my disk getting full? i keep downloading stuff…".

**Why.** The paper measured distance with a sentence model, which knows "crank up" is near "turn up". With
TermNL's clues, distance is word overlap, which the model already uses. And the out-of-scope sentences left
are close by nature: "crank up the sound", "connect to home-5g", "format my usb stick", "kill the process
with id 4312" are about the board, with taught words, only not skills yet. The far ones are the blind
sets' requests, written by someone who never saw the skill files. Asking about an out-of-scope sentence is
harmless by the measure's own rule; losing a request is not. So the trade isn't worth it.

**What it found instead: the typo corrector changes real words.** "football game last night" is read as
"name" because "game" was corrected to "name" and "night" to "right"; "format my usb stick" became
"stuck". Of 31 corrections made on the test sets, 9 change a real English word into a taught one:

| Correction | Effect |
|---|---|
| going → doing ("how's it going with the board") | helps: handled |
| connect → connected, tune → tunes | harmless |
| take → make ("take me to the documents folder") | hurts: wrong skill, asked |
| game → name, night → right (football) | hurts: out of scope read as "say name" |
| stick → stuck ("format my usb stick") | hurts: read as "stop process" |
| night → right ("ok shut it all down for the night") | harmless here, asked first anyway |

This becomes method **F** below. The distance idea comes back only with better vectors (E), if ever.

### H — One reading: the views of a sentence ranked by one rule (25 October 2026, `research/one-reading`)

**Result: the same answer on every sentence tried, with the six acceptance conditions of `understand`
replaced by one ranking. Not a gain in understanding; a change of shape, to judge for its own sake.**

**Why.** On `feat/frames`, `understand` read the sentence up to three times (as typed, in its context, with
a typo corrected), each reading accepted or refused by its own hand-written condition, then `bare_action`
and `doubts` with their own guards. Which path ran depended on the order they were tried: a new skill's
word could change the path, not only a score ("take me to the documents folder" turned on whether the
corrected view was tried before the model's reading of the typed one). Gab, 25 Oct: the code "feels like
each skill has its own fix and logic".

**What changed** (`termnl/agent.py`, 53 lines in, 48 out). `views` gives the sentence in up to three
views, each with the typos it reads as words. Each view is read once by `recognise`; an action said alone
(`bare_action`) is one more reading. `rank` picks: a template, then an action said alone, then the model;
then fewer words unknown; then, among templates, more values the device has (what `hid_a_place` did, now
a criterion: that function is gone); then fewer typos read; then the model's confidence. `doubts` still
asks which of two skills when the model disagrees with a template. Nothing else decides.

**Measured.** Against `feat/frames` with the committed model (`python3 -m tools.receipt --against`):
0 of 665 test answers moved. Harder: every `## Also said` sentence of the 77 skills and each one again with
a letter dropped or swapped, 771 sentences, 0 moved; 14 two- and three-turn conversations (the eight
follow-ups, "Which one?" answered, a typo confirmed, "turn off" then "the wifi"), 0 moved. The unit tests:
the same three fail as on `feat/frames`. Speed: median 2.8 → 3.8 ms a sentence on the laptop, as every
view is now read even when the first is a template.

**What it did not do.** `agent.py` is 945 → 950 lines: conditions became criteria, not fewer lines. The
lines come only from the next step, where the answer to a pending question (`fill_value`) and the frame
(`follow_up`) become two more views ranked by the same rule; that step changes how TermNL answers its own
questions and is where the risk of this road lies. This one carries none that the sentences can see.

**New tool.** `python3 -m tools.receipt` writes every test sentence's answer to `data/receipt.json`;
`--against before.json` lists what moved since, each with its cause (a typo read differently, another
path, other unknown words, the model's pair or only its confidence); `--skills a b` trains without those
skill folders and with them, and lists what dropping them in moved. The receipt for a commit.

## Sources

- [The Intent Classification Layer Most Agent Routers Skip](https://tianpan.co/blog/2026/04/16/intent-classification-agent-routers) (Tian Pan, April 2026)
- [hass-closest-intent](https://community.home-assistant.io/t/hass-closest-intent-garbled-stt-output-in-actual-intent-out/1009765) (Home Assistant community)
- [OpenVoiceOS ovos-m2v-intents-en](https://huggingface.co/OpenVoiceOS/ovos-m2v-intents-en) and [ovos-m2v-pipeline](https://deepwiki.com/OpenVoiceOS/ovos-m2v-pipeline)
- [Model2Vec results](https://minish.ai/packages/model2vec/results/) (MinishLab)
- [Conformal Intent Classification and Clarification](https://arxiv.org/html/2403.18973v1) (2024)
- [Distinguish Sense from Nonsense: Out-of-Scope Detection for Virtual Assistants](https://arxiv.org/pdf/2301.06544) (2023)
- [LLMs vs Established Text Augmentation Techniques for Classification](https://arxiv.org/html/2408.16502v1) (2024)
- [On Collaborating Small and Large Models for Few-shot Intent Detection](https://aclanthology.org/2025.findings-emnlp.749/) (EMNLP 2025 Findings)
- [Small Models for On-Device Text Classification](https://rickwinfrey.com/writings/small-models-for-text-classification) (Rick Winfrey)
