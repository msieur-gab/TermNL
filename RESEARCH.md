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
- **F, real words aren't typos, tested 25 Oct: gains, no wrong action added**, on the branch
  `research/f-common-words` for Gab's decision. 4 more out-of-scope sentences refused, one wrong reading
  fixed; one request now asked first instead of handled ("how's it going with the board").
- **F with 15 skills at the edge, tested 25 Oct: still gains, no wrong action added.** 5 sentences
  better, 2 worse but asked ("turn the sound dawn"). The new skills (`feat/new-skills`) work on their
  blind sentences but cost older ones some confidence; Gab's call on both branches.
- **G, each label scored on its own, tested 25 Oct: not kept.** No better than today's model once both
  have their own lines, and one wrong action more.
- **B, measured lines, tested 25 Oct: the safest result so far, for Gab's decision.** The act line
  measured for today's model is 0.84, not 0.5; the ask line 0.007, not 0.15. Wrong actions 1 → 0, not
  understood 23 → 9, but 47 sentences handled before now ask first.
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

| F | Real words aren't typos | A list of common English words, plain text: a word on it is never "corrected" into a taught one (game ≠ name, stick ≠ stuck). Found by testing A | 10,713 words, 90 KB on disk, about 1 MB in memory; no slower |
| G | Each label scored on its own | As OpenVoiceOS's Padatious (one small model per intent): every action and object gets its own yes/no score, so a new skill takes nothing from the others. The split into action × object stays (IMPROVEMENTS.md: the joint model acted wrongly) | The same size; training a little longer |

C is independent and can go in at any time. E only if the misses left are mostly unknown words.
**A was tested on 25 Oct and not kept; F was tested the same day and gains** (see Tested).

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

### F — Real words aren't typos: gains, for Gab's decision (25 October 2026)

**Result: 4 more out-of-scope sentences refused, one wrong reading fixed, no wrong action added; one
request now asked first instead of handled.** On the branch `research/f-common-words`, not on `main`
until Gab decides.

**What changed.**
- `termnl/languages/en/words/common.md`: 10,713 common English words, from SCOWL (Kevin Atkinson's word
  lists, sizes 10 and 20, the most common words; free to use with its notice, which the file carries).
  Names, possessives and anything not plain letters left out. Built by `python3 -m tools.common_words`.
- `agent.py`, `correct`: a word on that list is never read as a typo of a taught word. A word TermNL knows
  is read as itself as before; a word on neither list is still corrected ("memroy" → "memory").
- `load.py` reads the list when it is there; without it, TermNL behaves as before. Two tests added in
  `tests/test_dialogue.py` (98 pass).

**How it was measured.** The five test sets with `python3 -m tests.measure`, sentence by sentence against
the baseline (`-v`, the two outputs compared line by line), at three sizes of the list: 3,939 words
(SCOWL 10), 10,713 (20) and 38,015 (35). **All three gave exactly the same readings** on every sentence; 20
was kept as the middle: it protects more real words than 10, and corrects more true typos than 35, neither
measured yet. Then `python3 -m unittest`, `python3 -m termnl.check`, `python3 -m tests.compare_agents` and
`python3 -m tools.speed`. Not measured here: Gab's real turns (`python3 -m tests.real`, his laptop only).

| Set | Handled | Asked first | Wrong skill, asked | Wrong skill, acted | Not understood | Out of scope: refused / asked / acted |
|---|---|---|---|---|---|---|
| phrasings | 40 (41) | 16 (15) | 2 | 0 | 1 | — |
| probes | 76 (75) | 4 | 6 (7) | 0 | 3 | 3 / 1 / 0 |
| heldout | 113 | 5 | 3 | 0 | 1 | 10 (9) / 0 (1) / 0 |
| blind | 69 | 35 | 7 | 1 | 4 | 14 (13) / 1 (2) / 0 |
| scale-blind | 32 | 38 | 3 | 0 | 7 | 23 (21) / 5 (7) / 0 |
| **all** | **330** | **98 (97)** | **21 (22)** | **1** | **16** | **50 (46) / 7 (11) / 0 of 57** |

Baseline in brackets where it differs.

**Every sentence that moved (8 of 523):**

| Sentence | Before | With F |
|---|---|---|
| who won the football game last night | out of scope, asked "say name" | refused |
| format my usb stick | out of scope, asked "stop process" | refused |
| connect to my phone | out of scope, asked "check network" | refused |
| connect to home-5g | out of scope, asked "check network" | refused |
| take me to the documents folder | wrong skill (create folder), asked | **open folder, handled** |
| how's it going with the board | check system, handled ("going" read as "doing") | **check system, asked first**: "I don't know “going” yet" |
| enough of The Tune, turn the music off | stop music, asked first | the same; "tune" now named as new |
| ok shut it all down for the night | shut down, asked first | the same; "night" now named as new |

**The one loss, and why it is honest.** "how's it going" was handled because "going" was read as "doing",
a lucky correction of a real word. TermNL now asks first and names "going" as a word it doesn't know.
Teaching it ("how's it going" in check system's Also said) would bring it back the right way.

**Cost.** The list is 90 KB on disk, about 1 MB in memory, read once at start (the whole language loads in
0.8 s on the laptop, as before). Understanding a sentence: median 2.3 ms with and without F
(`tools.speed`, 415 sentences). Not yet measured on the board.

**Also.** `back_agent.py`, the version before kept for comparison, doesn't read the list: one more reply
differs in `tests.compare_agents` (9 of 145, was 8), and one more test fails for it (11, was 10 before F).
Whether to port or retire `back_agent.py` is already open (`IMPROVEMENTS.md`).

### F with skills at the edge: still gains, for Gab's decision (25 October 2026)

Gab, before merging F: "we should test it with skills getting closer to the edge cases. I believe I anyway
miss some skills." Fifteen skills were added on their own branch, `feat/new-skills` (from `main`), measured
there, then merged into `research/f-common-words` to measure F on top of them.

**In short**
- **F still gains and still adds no wrong action.** On top of the new skills it moves 8 of 665 sentences:
  5 better, 1 still wrong but differently, 2 worse; the 2 worse still ask, they never act.
- **The new skills work on the sentences written for them**: of 60 blind requests, 30 handled straight
  away and 25 asked first, 2 read as another skill but asked, 3 not understood.
- **They cost the older skills some confidence:** a few sentences handled before are now asked first
  ("shut down", "scan for wifi"), and some phrases moved to the new skills ("is there any…", "movie",
  "sd card"). No sentence of the older sets became a wrong action. Two unit tests that hold earlier
  decisions now fail (below): they are Gab's to weigh before `feat/new-skills` goes anywhere.

**The skills** (`feat/new-skills`; commands default on Debian-family boards except where said):

| Skill | Does | How | Asks first |
|---|---|---|---|
| show-type | lists the files of a kind (images, videos, notes, PDFs) in a folder or here | reads the folder (`reads: files`) | no |
| check-type | is there any file of a kind, folders included | reads (`reads: has`) | no |
| read-file | shows a file's first 40 lines | `head` | no |
| show-recent | the files changed in the last day | reads (`reads: recent`) | no |
| check-size | how big a folder is | reads (`reads: size`) | no |
| show-log | the last 20 lines of a service's log | `journalctl` | no |
| check-usb | the drives and cards plugged in | `lsblk` | no |
| turn-up-sound, turn-down-sound | the sound 10% louder or quieter | `amixer` (not on every board) | no |
| connect-wifi | joins a network, with its password | `nmcli` (not on every board) | approval |
| unpack-file, compress-file | a .tar.gz unpacked, or a file compressed, where it is | `tar` | no |
| send-file | a file to another computer's home folder | `scp` | approval |
| get-file | a file from another computer, here | `scp` | no |
| show-remote | what another computer's home folder holds | `ssh … ls` | no |

On 24 Oct, joining Wi-Fi and the volume were set aside with Gab because `nmcli` and `amixer` aren't on
every board; Gab asked for them again on 25 Oct. The commands themselves were not run here, only how
TermNL understands the sentences.

**What else changed to make them:**
- **A kind of file is the object** (Gab: "the file format/extension was supposed to be part of the object
  but never made it"). Listing and looking for a kind were first written as show file and check file; then
  "list the files inside my home" asked "show a folder or list files of a kind?", because "list" + "files"
  is exactly show + file. With their own object, `type` ("show type", "check type"), the kind's words
  carry the object and show folder keeps "list the files". The two blind labels were renamed to match.
- `words/filetypes.md` takes several extensions per type: `image (jpg, jpeg, png, gif, webp, svg): image,
  images, photo, photos, picture, pictures, pic, pics`; video, pdf, and note as `.md` or `.txt` (Gab).
- New actions (read, turn up, turn down, connect, unpack, send, get), objects (type, recent, size, log,
  usb, remote, and "volume" for sound), and a device list: the computers in `~/.ssh/config`
  (`a computer on the network`), so "laptop" and "studio pi" are names, offered as chips.

**How it was measured**
- `tests/edge-blind.md`, 142 sentences by a fresh agent that saw only the skills' names and purposes
  (`briefs/2026-10-25-edge-skills-blind.md`): 60 for the new skills, 32 for close older skills, then three
  groups of 10 for F (typos that are real words: "sand report.pdf to laptop"; other forms: "sending
  movie.mkv"; real words next to the skills' words: "what gift should I buy my wife"), and 20 out of
  scope. One label corrected: "turn on bluetooth" was written as out of scope because the brief didn't
  list the Bluetooth skills.
- "Also said" from another fresh agent (`briefs/2026-10-25-also-said-edge.md`): 132 proposed, 114 kept by
  `tools/merge_also_said.py`; 12 dropped as test sentences, 6 because an older skill's template reads
  them (below).
- 12 sentences of `tests/scale-blind.md` set out of scope on 24 Oct (Wi-Fi joining, volume) are back to
  their skills.
- Four runs of `python3 -m tests.measure <set> -v`, kept in `data/measure-2026-10-25/` and compared with
  `python3 -m tools.compare_runs`: `main`; **A**, the skills as written; **B**, with Also said; **B + F**.

Each cell: handled / asked first / wrong skill, asked / **wrong skill acted on** / not understood · out of
scope: refused / asked / **acted on**.

| Set | main | A | B | B + F |
|---|---|---|---|---|
| phrasings (59) | 41/15/2/**0**/1 | 34/19/4/**0**/2 | 34/19/6/**0**/0 | 33/20/6/**0**/0 |
| probes (89 + 4) | 75/4/7/**0**/3 · 3/1/**0** | 75/3/8/**0**/3 · 3/1/**0** | 75/3/8/**0**/3 · 3/1/**0** | 76/3/7/**0**/3 · 3/1/**0** |
| heldout (122 + 10) | 113/5/3/**0**/1 · 9/1/**0** | 113/4/4/**0**/1 · 9/1/**0** | 113/4/4/**0**/1 · 9/1/**0** | 113/4/4/**0**/1 · 9/1/**0** |
| blind (116 + 15) | 69/35/7/**1**/4 · 13/2/**0** | 65/37/8/**1**/5 · 12/3/**0** | 65/37/9/**1**/4 · 11/4/**0** | 65/38/8/**1**/4 · 12/3/**0** |
| scale-blind (80 + 28 → 92 + 16) | 32/38/3/**0**/7 · 21/7/**0** | 32/41/9/**0**/10 · 14/2/**0** | 36/40/6/**0**/10 · 14/2/**0** | 36/40/6/**0**/10 · 14/2/**0** |
| edge-blind (117 + 25) | — | 45/37/9/**0**/25 · 15/9/**2** | 53/55/4/**0**/5 · 17/7/**1** | 54/54/4/**0**/5 · 18/6/**1** |

(In A, edge-blind still had "turn on bluetooth" as out of scope: one of its two "acted on" is that.)
The one wrong action left in blind is the old one ("I want to look at report.pdf" finds it). The one on
edge-blind: "download and unzip example.com/pack.zip" downloads the file without unzipping it; the brief
called it out of scope, half of it is a skill.

**F on top of the new skills: what moved (8 sentences)**

| Sentence | Without F | With F |
|---|---|---|
| take me to the documents folder | create folder, asked | **open folder, handled** |
| who won the football game last night | out of scope, asked "say name" | **refused** |
| what gift should I buy my wife | out of scope, asked "show Wi-Fi" ("wife" → "wifi") | **refused** |
| copy report.pdf from my laptop onto the board | copy file, asked | **get file, handled** |
| everything feels slow, is the memory full or what | show process, asked | **check memory, asked** |
| why is everything so slow, is it the ram | show process, asked | check system, asked (still wrong, asked) |
| how's it going with the board | check system, handled | check system, asked first (as before) |
| turn the sound dawn | turn down sound, asked | **unmute sound, asked**: "dawn" was a typo of "down" and is a real word |

By group, on edge-blind: real-word typos 9 right (asked) → 8; other forms unchanged (2 handled, 6
asked, 2 not understood); real words next to the skills' words, 4 refused → 5.

**What the new skills did to the older ones** (A and B against `main`; none acts):
- **More skills, less confidence.** Sentences handled before now ask first: "shut down", "shut it all
  down", "scan for wifi", "the board feels really warm", "what network am I on right now". With 71 skills
  instead of 56 the model's certainty spreads over more classes and falls under 50% more often.
- **A new skill takes a phrase or a word:** "is there any acitve threads" and "are there any updates? if
  so install them all" go to check type ("is there any…"); "is there enough space for a movie" too,
  "movie" being a kind of file now; "is my sd card almost full" goes to check USB; "restart ssh, I can't
  log in from my laptop" to get file ("laptop" is a computer now). All asked, none acted.
- **Gained:** the volume and Wi-Fi sentences set aside on 24 Oct ("can you raise the volume?", "too
  loud!", "bring the sound down", "connect to home-5g" handled); "can you pull up groceries.md" asked
  instead of not understood.
- **Two unit tests now fail**, both decisions from 23–24 Oct: "is there enough space for a movie" should
  ask about check storage (now check type), and "rename the folder photos to pictures" should ask rename
  a file or a folder (now it looks for a file called "folder photos", doesn't find it, and says so;
  "photos" and "pictures" are kinds of file now, so the model is less sure it's a folder).

**Found on the way**
- **A password said in the sentence isn't read**: "connect to home-5g, the password is sunflower42" asks
  again, and the sentence, password included, is written to `logs/`. A secret should be read out of the
  sentence, and kept out of the log.
- **Templates read "delete report.pdf on the laptop" as deleting a local file**: the name swallows "on the
  laptop", isn't found, and nothing runs. Safe by luck, not by design.
- "fetch photos.tar.gz from studio pi" goes to download file ("fetch" is a download word).

**Cost.** 71 skills. Model 1,032 KB → 1,518 KB. Training on the laptop 17 s for 5,514 sentences → 36 s for
7,579: about twice as long, so roughly 7 minutes on the board (not measured there). Understanding a
sentence: median 2.4 → 2.7 ms.

**Not measured:** Gab's real turns (his laptop only), the board, and the new commands themselves.

### G and B — each label on its own, and lines measured instead of chosen (25 October 2026)

After reading how OpenVoiceOS works (one small model per intent in Padatious), and seeing more skills
lower TermNL's confidence: does scoring each label on its own help (G), and where should TermNL's two
lines really sit (B)? Both on the branch `research/g-independent-scores`, made from
`research/f-common-words` (71 skills, F on), so every number below is with F.

**In short**
- **G is not kept.** With the lines chosen for today's model, it understands far less (not understood
  23 → 68): its scores are on another scale. With lines measured for it, it does no better than today's
  model, and acts wrongly once more.
- **B changes the most, in the direction TermNL was designed for: ask rather than guess.** Measured on
  sentences the model never learned from, the act line is 0.84 and the ask line 0.007. With them: no
  wrong action left (the old "I want to look at report.pdf" is now asked), not understood 23 → 9; but 47
  sentences handled straight away before now ask "Do you want me to…?" first, and 5 fewer out-of-scope
  sentences are refused (they are asked about instead, harmless by the measure's rule).
- **It's a dial, not a verdict.** 0.84 comes from "wrong at most 1 time in 100 when acting"; a looser
  promise acts more. Which promise TermNL makes is Gab's call.

**What G changed** (`model.py`, `train.py`): each action and each object label gets its own yes/no
score (a sigmoid per label instead of one softmax shared by all). The split into action × object stays:
a joint model over whole skills was measured on 24 Oct and acted wrongly (`IMPROVEMENTS.md`). Off by
default; `TERMNL_INDEPENDENT=1 python3 -m termnl.train` turns it on.

**What B changed** (`tools/calibrate.py`, `agent.py`): the 517 "Also said" lines are cut into 5 parts;
the model is trained 5 times, each time without one part, and reads it: 517 sentences, each read by a model
that never saw it. From them:
- **ask line**: the right skill scores at least this in 95 of 100 sentences (conformal prediction, as in
  the CICC paper above): 0.007 for today's model.
- **act line**: the lowest score where the skill read is wrong in at most 1 sentence in 100: 0.844.

The hand-set lines were 0.5 and 0.15. On those 517 sentences the right skill came first 420 times (81%);
above 0.5 the model was wrong more than 1 time in 100. No test set was used: they stay judges.
`python3 -m tools.calibrate --write` stores the lines in `model.json` as `"lines"`; `agent.py` uses them
when they are there, its own otherwise. On this branch `model.json` has no lines yet: TermNL behaves as
on `research/f-common-words` until Gab decides.

**Results, all six sets** (595 requests and 70 out of scope; each cell: handled / asked first / wrong
skill, asked / **wrong skill acted on** / not understood · out of scope: refused / asked / **acted on**):

| Model and lines | Requests | Out of scope |
|---|---|---|
| Today's model, hand-set lines (B + F above) | 377/159/35/**1**/23 | 56/13/**1** |
| G, hand-set lines | 356/143/25/**1**/70 | 58/11/**1** |
| G, its measured lines (0.801, 0.001) | 328/210/39/**1**/17 | 54/15/**1** |
| **Today's model, measured lines (0.844, 0.007)** | **330/214/42/0/9** | **51/18/1** |

The one out-of-scope acted on is "download and unzip example.com/pack.zip" in all four (it downloads).
G's extra wrong action is on the held-out set. Every run is in `data/measure-2026-10-25/`.

**What the measured lines moved, sentence by sentence** (`python3 -m tools.compare_runs`):
- 47 handled → asked first: mostly sentences the model was between 0.5 and 0.84 on ("free memroy?",
  "scan for wifi", "shut down"…).
- 19 not understood → asked about; 7 of those ask about the wrong skill ("go back a song" → leave folder,
  "notes in ideas" → create file): nothing runs, the person says no.
- "I want to look at report.pdf": wrong skill acted → asked first. The only wrong action of the older
  sets is gone.

**Unit tests**: with the measured lines, two more tests fail ("free memroy?" should act; "kill pipewire"
should say it isn't running): both acted at 0.5 and now ask first. They describe behaviour chosen with
the old lines; whether they change is part of Gab's decision.

**Cost.** Calibrating is 5 trainings: about 3 minutes on the laptop, roughly half an hour on the board, so
it belongs on the laptop when skills change; a model retrained on the board would keep the lines it had.

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
