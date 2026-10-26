# One reader, no trained model — the `feat/align` branch

25 October 2026, from `feat/frames` (10e7295). Gab asked for a review of TermNL, an assessment, and "a
completely new approach that could keep the simplicity, perhaps reduce hard coded logic and improve its
stability without the need of a bigger NLU and much more robustness". This file holds the note and the
proposal as given, what was built from it in one evening, and what it measures. Nothing here is decided
until Gab says so.

## The note

What is right and stays: the skill.md form (People say / What it needs / Command / Replies), the four
outcomes, the device-truth checks (a file found here or elsewhere, a new name never replacing a file, a
typo of a folder confirmed, a password on standard input), and the 466-sentence benchmark discipline.

What was wrong is one structural thing, and every rule grew from it: **TermNL read the same skill
sentences twice, with two readers that couldn't talk to each other.**

- The template parser read exactly. It gave values but no doubt (a match was "certain", hence `doubts`).
- The classifier read loosely. It gave doubt but no values (hence `values_in`), and because it was split
  action × object it couldn't see what a verb means with its object (hence `in_context`, `opposites`,
  `actions_said`, `bare_action`, `as_file`).
- The two were reconciled in `understand` by trying up to three readings in a fixed order (`correct`,
  `hid_a_place`), each accepted by its own hand-written condition.

About ten rules, around 500 of agent.py's 948 lines, whose only job was to glue two readers together.
Methods A, B, F, G, H, "less" and frames all stayed inside that shape, re-ordering the same evidence,
which is why none moved the needle. Training is not the enemy: a local retrain (numpy, a model.json, a
"learn what I taught you" that takes a few minutes on the board) is fine, and it never needs a larger or
external NLU. The problem is the glue rules between the two readers. And whatever is chosen must stay
quick on modest hardware (the Orange Pi Zero 2W): speed is a requirement, not a nice-to-have.

## The proposal

**One reader.** Every skill reads every sentence, two ways, on one scale from 0 to 1, and all the
readings of all the skills are ranked together:

- **exact**: one of the skill's sentences reads the words as written, its values in their places. Fit 1,
  less a little for a typo, a value the device doesn't have, or a word for an object taken as a name.
- **near**: the skill explains the sentence: how much of its words it knows, how close the sentence is
  to one of its own, and how much the words say its action and its object against every other.

**No training.** The skill's words are counted when the skills load, from People say and Also said, and
weighed by how telling each is (a word only one skill says weighs most, one every skill says weighs
nothing). A word no skill knows is unknown: it costs the reading, and the question names it. Out of scope
(out-of-scope.md) reads sentences too, as a skill with no command. A skill folder dropped in is known at
once; "learn what I taught you" reads the files again in a fraction of a second.

**The decision is two numbers**: the best fit, and the margin to the next skill. Exact, or near with fit
0.8 and a margin of 0.1 and no unknown word: act (or approve). Skills within 0.05 of each other: "Do you
mean A or B?". Fit under 0.3, or out of scope reading it best, or a skill that knows less than 30% of the
sentence (unless it names the skill's action and object): nothing understood.

**Skills own their words**: `## Words` says what "turn on" means for play music, when its object is
said. **The conversation stays one frame** (feat/frames): what is said in part is completed by the last
request done.

**Honest about accuracy.** The TF-IDF model never learned meaning either; it learned word overlap plus
3–4-letter pieces, and its gains came when Also said sentences were added. A reader that uses those
sentences directly should land about where the model was. The structural win is that nothing depends on
which rule ran first, and a new skill can't change the path a sentence takes.

## What was built (`termnl/reader.py`, 540 lines; the agent 948 → 744)

- **`reader.py`**: `Reader`, built at load from the lists and skills. `readings(text, toks, list_of)` is
  all the agent calls. Counting at load: each skill's words and the count of its lines that say each,
  the phrases it says as written, the same counts pooled by action and by object, stems ("using" reads as
  "used"), the known words (a word some skill knows is a word, never a typo of another: method F, for
  free).
- **Exact readings**: `template.parses` as before, with three additions. A template word or an action or
  object phrase typed one letter off is read as it and said back (`fixes`), never a name, never a known
  word. A name never holds an object word ("rename the folder photos to pictures" can no longer be a file
  called "folder photos"; it was the silent wrong action of 24 Oct). **Also said lines are read like People
  say lines**: `plain.also_template` turns "put todo.txt in the projects folder" into
  `put {name:file} in the {to} folder` (a sample from words/samples.md or a file-shaped word stands for
  its value, a word for the skill's action or object for all its words). The author's examples become
  rules for exactly what they say, and for synonyms of the action and object.
- **Near readings**: the three measures above (`near`, `similar`, `agree`), with the values found by
  `values_in` (unchanged in spirit: device lists, "called …", a file-shaped word for a skill about files).
  Two things said in so many words are never read as something else, unless the skill's own sentences say
  that word too: an object ("turn on the pi" offers nothing), an action by its opposite, a name the
  device has by a skill with no value for it ("The Tune"). An action said alone is every skill that does
  it, for the person to choose (what `bare_action` did, inside the reader).
- **The agent**: `understand` is one function over the ranked readings (and the frame's follow-up).
  Gone: `recognise`, `in_context`, `bare_action`, `doubts`, `correct`, `as_file`, `hid_a_place`,
  `actions_said`, `values_in`'s copy, the three-reading cascade, `self.vocab`. Kept untouched: the frame,
  the device checks, approval, the settings, help, the replies.
- **The server**: "learn what I taught you" reads the skill files again in a background thread (well
  under a second) and tells the conversation that asked; a skill file with a problem leaves what was known
  before and says what is wrong. No subprocess, no numpy, no model.json, no model.previous.json.
- **Removed**: `model.py`, `train.py`, `examples.py`, `model.json`, `tools/distance.py`,
  `tools/neighbours.py`. The code didn't shrink overall (termnl/*.py 3,115 → 3,323 lines): the reader
  holds what the model, the trainer, the example generator and the agent's rules held, in one place.

## Measured

`python3 -m tests.measure all`, the same 466 sentences (plus the 57 out of scope), `feat/frames` against
this branch. Handled / checked first / wrong skill but asked or stopped / **wrong skill acted on** / not
understood · out of scope refused / asked / **acted on**.

| Set | feat/frames (10e7295) | feat/align |
|---|---|---|
| phrasings (59) | 35/17/4/**0**/3 | 40/14/3/**1**/1 |
| probes (89 + 4) | 76/4/6/**0**/3 · 3/1/**0** | 75/4/9/**0**/1 · 3/1/**0** |
| heldout (122 + 10) | 113/5/2/**1**/1 · 9/1/**0** | 114/1/5/**1**/1 · 7/3/**0** |
| blind (116 + 15) | 66/36/8/**1**/5 · 12/3/**0** | 67/34/6/**0**/9 · 12/3/**0** |
| scale-blind (92 + 16) | 39/36/4/**0**/13 · 13/3/**0** | 37/35/8/**0**/12 · 12/4/**0** |
| edge-blind (117 + 25) | 54/53/4/**0**/6 · 17/7/**1** | 54/54/7/**0**/2 · 18/6/**1** |
| **all (595)** | **383/151/28/2/31 · 54/15/1** | **387/142/38/2/26 · 52/17/1** |

About where the model was, as promised, not better: four more handled, five fewer not understood, ten
more wrong skills offered (asked, nothing ran), the same two wrong actions (one reads the wrong thing:
"which wifi network is this" lists the networks; one is "bluetooth on", read as a check), the same
out-of-scope sentence acted on in both ("download and unzip example.com/pack.zip" downloads).

The three wrong actions it had on the way, now asked: "put report.pdf in Documents" as restoring from the
trash (a device name a skill can't take is unknown to it), "can I hear The Tune please" as playing music
at random (the same), "make the screen brighter" as a file called "the screen brighter" (a file-shaped
word only fits an Also said value).

Unit tests: 127, all passing (on feat/frames, 3 fail: the doubted template, "is there enough space for a
movie", and the documents staying quiet; the first was rewritten here, the other two pass unchanged). Three
tests were changed for the new behaviour, each saying why in its docstring: an Also said line said word for word is
read exactly, so "get rid of everything in the trash" asks the skill's own approval instead of "Do you
want me to…?"; "rename the folder photos to pictures" asks which folder instead of choosing file or
folder; "ping" alone asks "Which computer?" at once instead of waiting for a model to learn the word.

Speed (`python3 -m tools.speed`, laptop): median 18 ms, 90% under 38 ms, slowest 80 ms. feat/frames:
3 ms, 8 ms, 28 ms. Six times slower: every skill now reads every sentence, near as well as exactly. On
the board that is likely 100–400 ms a reply, which a chat bears; `similar` is where the time goes, and it
can be pruned (only the skills whose words cover the sentence need it) if the board says so. Loading the
language, counting included: 0.1 s.

## What changed in how a skill is written

Nothing an author must do. Three things an author gets:

- **Also said lines are read.** "look through my files for permacomputing" now reads exactly, and with
  any word for find or file. A sloppy Also said line is a sloppy rule, for that very sentence only.
- **A value in an Also said line is recognised** when it is a sample (words/samples.md: documents,
  nginx, firefox, wax tailor…) or a file-shaped word; "called" or "named" before a sample makes it the
  name. Any other word is the word.
- **Nothing to train.** Drop the folder in; "learn what I taught you" reads the files again.

## Open, for Gab

1. The thresholds (`SURE` 0.8, `MARGIN` 0.1, `CHOOSE` 0.05, `MAYBE` 0.3, `KNOWN` 0.3 in agent.py; the
   fit's constants at the top of reader.py) were set on the benchmark, phrasings and probes mostly. The
   held-out and blind sets are the judge, and Gab's real sentences (`python3 -m tests.real`, his laptop).
2. Ten more wrong skills offered than before. Most are a choice with the right skill among the chips
   ("go back a song": the previous or the next song) or a reading skill offered for a command
   ("get the wifi back" → check the Wi-Fi). The next gain is there, not in acting more.
3. "bluetooth on" reads as checking Bluetooth, "bluetooth off" asks before turning it off. The weighted
   counts can't tell a bare "X on" from "is X on"; the model could, barely. A line in turn-on-bluetooth's
   Also said settles it.
4. The speed on the board, measured, before pruning anything.
5. Whether the fit's three measures are the right three. `agree` (the split, by counting) is what told
   "turn off the lights" from Bluetooth and "how much ram am I using" from the processes; `similar` is
   what made Also said lines count; `coverage` is what names the unknown words.

## How to check

    python3 -m termnl.check             # 77 skills, no problems
    python3 -m unittest                 # 127 tests
    python3 -m tests.measure all        # the table above, right column
    python3 -m tools.speed              # the timings above
