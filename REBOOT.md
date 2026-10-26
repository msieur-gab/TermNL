# research/reboot — the skill files read the sentence

Branch from feat/skill-first, 26 Oct 2026. The agent's cascade of readings (templates, a trained model, a
rewrite in context, a typo pass, a bare-action chooser, the model doubting a template, a split at commas,
each with its own conditions) is replaced by one reader, `termnl/reading.py`, that takes everything from
the skill files and the word lists. No model, nothing trained: a skill folder dropped in is read at once.

## The four looks

1. **words** — fillers off; a typo one letter from exactly one known word is read as it, but only when
   that reads better than the sentence as typed (a name keeps its spelling).
2. **funnel** — the sentence as a shape: each action and object by its name ("make" is create, "note" is
   file; "start" is create *and* open), a file-shaped word as `@file`, a value the device has as `@value`
   plus its kind (`@sys.folder`), a word TermNL doesn't know as itself plus `@value`; small words dropped.
   The actions and objects named decide between readings that tie, and whether a reading may act.
3. **templates** — `## People say` reads the sentence exactly (template.py, unchanged in spirit; two rules
   added: free text never holds a word for an action, object or file type unless it follows "called",
   and a list value is never a word for an object, so "bluetooth" is the board's Bluetooth). A template
   that read a value not on its list is a guess (p 0.75), and can lose to the next look.
4. **nearest** — the closest `## Also said` line of any skill, by weighted Dice over the shapes (a word
   rarer among the lines weighs more: "pause" over `@value`). Lines nearly as close count as one and the
   funnel decides among their skills; the person decides when it can't (chips). How close is p.

A sentence with a reason ("restart ssh, I can't log in") is read whole, then by its parts at punctuation;
the part that reads best is the request, asked about first when it changes something.

When a nearest reading may act (agent.py, `sure`): p ≥ 0.8 and the sentence names the skill's action in
so many words; a skill that only reads may also be named by its object or by a value of its kind ("is mpd
up"). A sentence that says an Also said line word for word is as sure as a template. Unknown words are
named and asked about, as before. Values are read by one routine (`values_in`): a list value after the
preposition the skill's own sentences put before it, a name after "called", a file-shaped word.

Kept as they were: the dialogue (questions, "Which one?", approval, files found on the device, settings),
the frames ("now delete it", "and in downloads?"), readers, device, server.

## What went

model.py, train.py, examples.py, model.json (2.2 MB), tools/distance.py and same_reading.py. "Learn what
you taught me" now reads the skill files again (server.py, `train`), in well under a second.

Python: 847 lines out, 508 in. The understanding itself: agent.py 999 → 698 lines, reading.py 368 (60 of
them docstrings), no model. Speed on this machine: 10 ms a sentence, 1.3 s to load the language (shaping
1,400 Also said lines, once).

## Measured, same scale as before (tests/measure.py; numbers for feat/skill-first in brackets)

| set | sentences | acted | asked first | wrong skill, asked | wrong skill, acted | not understood |
|---|---|---|---|---|---|---|
| skills (each skill's tests.md) | 462 | 265 (286) | 114 (121) | 56 (32) | 5 (0) | 22 (23) |
| heldout | 122 | 113 (116) | 5 (3) | 3 (2) | 1 (1) | 0 (0) |
| blind | 116 | 63 (70) | 37 (39) | 10 (5) | 1 (1) | 5 (1) |
| scale-blind | 92 | 43 (45) | 34 (36) | 11 (5) | 1 (0) | 3 (6) |
| edge-blind | 117 | 50 (64) | 44 (47) | 15 (5) | 2 (0) | 6 (1) |

Read this with care: the blind sets were written before many of their wordings went into Also said (565
lines on 26 Oct), so both engines have seen most of them; the skills set is the fairest. The honest
picture: the reboot acts on about as many sentences, asks a wrong question twice as often (a nearest
line with no word order is weaker than a trained classifier on sibling skills: show folder / show type,
check wifi / check network), and acts wrongly on a handful where the old one didn't — 3 of the 5 are
reading skills (nothing changed on the device), the other 2 are a word list gap ("fetch" is download, not
get; "updates" isn't a word for update).

`python3 -m tools.why "sentence"` shows every look: the shape, what is named, the templates that read it,
the nearest lines and their p.

## Where to go from here

- The word lists and Also said lines are now the whole of the reader: a miss is fixed by a line, not code.
  tools/why.py says which line would have caught it.
- Thresholds (reading.py: SURE 0.8, MAYBE 0.5, NEAR 0.1, UNSURE 0.75) were set once by the accuracy per
  band on the skills set (p ≥ 0.9: 97–100% right; 0.6–0.8: 75–90%), not tuned against it.
- Not tried: a little word order in the shape (bigrams of the content words), the one thing the old
  classifier had that this doesn't. Two lines in `shape`, and a measure.
