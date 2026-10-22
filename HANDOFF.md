# Handoff — 22 October 2026, afternoon

TermNL (born this morning as TermLU, from ptiLU). The design lives in Gab's brain repo, `projects/termlu/`:
read `intention.md`, `brief.md`, `decisions.md`, `review-2026-10-22.md`, both `prior-art-2026-10-22*.md`
and the `open-question-*.md` files before changing anything, and the `.inbox.md` for what Gab said today
that isn't ratified yet. Gab's decisions are his; don't rework them.

## What exists

- **Python only.** The first version in JavaScript was frozen (it gave the same replies as the Python one
  on 139 turns, commit c032e13), then deleted on Gab's request. See `README.md` for the layout.
- **The brain on the device:** `python3 -m termnl.server` serves the chat page and a thin API that takes
  sentences, never commands. Built and tested on Gab's laptop (my-laptop); files land in `~/TermNL-home`;
  restart, shutdown, Wi-Fi, Bluetooth and services are simulated (`settings.md`, `simulate:`).
- **28 skills** in `termnl/languages/en/skills/`, one per action + object. Reading skills name a reader
  (`reads: memory`) and write a reply per level (`## When it's high`); the reader gives values, a level
  and sometimes a table.
- **Rules learned from Gab's own sentences**, each with tests (`tests/test_dialogue.py`): names never
  swallow a place; misspelled device values are confirmed; typos are read as known words only when that
  reads better, and said; names are never corrected; "not/don't" requests are asked about; approval comes
  last, with every value known; a lone yes/no with nothing waiting says so; a new name never replaces
  what's there.
- **Logs:** `logs/<date>.jsonl` holds every turn Gab typed (not in git). They are the honest test set.

Run: `python3 -m termnl.check` · `python3 -m unittest` (60 pass) · `python3 -m tests.measure -v`
(59 phrasings: 29 handled, 23 asked first, 4 wrong skill but asked, 0 wrong actions, 3 not understood).

## Open, in order of importance

1. **The learning loop.** A "yes" returns `teach`; nothing saves it. Decided (Gab): learning goes to an
   inbox the person reviews, then "live training" on the device. Gab also said it only works if a person
   can say "no, I meant another skill" or "this is new": **who writes a new skill** when the person
   doesn't know the commands is his open question ("I need to sink a bit with it").
2. **`termnl/agent.py` is 636 lines** and grew fix by fix today; read it as a whole and simplify before
   adding more (ptiLU's lesson, `brain/projects/ptilu/review-2026-10-21.md`).
3. **Permacomputing:** Gab wants the surface as light as possible. The model is 669 KB of JSON floats
   (most weights tiny; ptiLU stored 1-byte weights).
4. **The test set is still mostly Claude's** (`tests/phrasings.md`); Gab's sentences are its last section.
   A passing suite hid a failure Gab found in his first sentence, twice today.
5. **What runs when TermNL reads** (`open-question-reading-commands.md`, Gab to decide): reading skills
   read /proc in Python (readers.py), so no skill command runs and "show commands" shows nothing for them;
   the alternative is the skill's command really running and Python converting its output.
6. **Authoring** (`open-question-authoring.md`): the template grammar works but people can't write it.
7. **Shared words in two families:** "start" (create + open), "note" (file + markdown).
8. **Not done:** Wi-Fi, Bluetooth and network replies are still raw command output; no "undo" or
   Dialogflow-style context; pairing and keys deferred until the system proves itself.
9. **Word embeddings for unknown words: tested, not worth it now** (this morning, another session).
   GloVe-50 on the 26 untaught words of the phrasings: 3 useful neighbours (warm → hot), 15 wrong
   (kill → bring, stop → out), because most new words are context, not synonyms, and embeddings put
   opposites side by side. A better embedding (Model2Vec) could be tried with `tools/neighbours.py`.
