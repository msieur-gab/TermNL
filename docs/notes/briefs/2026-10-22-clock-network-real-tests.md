# Brief — the clock, network replies in plain words, a test set from real sentences

Written 22 October 2026 by Claude, at the end of a long session (the context was compacted once). Some
details may have lost accuracy: check every claim here against the code and the brain before relying on
it. Gab chose these three tasks for the next session. Everything under "Proposed" is Claude's proposal,
not his decision: present it to him and wait for his yes before building.

## Read first

In Gab's brain (`~/dev/agent/brain`):
- `CLAUDE.md`, in full, before writing anything in the brain (Gab's rule, no exception).
- `projects/termlu/`: `intention.md`, `brief.md`, `vocabulary.md`, `day-one-scope.md`, `decisions.md`,
  `review-2026-10-22.md`, `open-question-reading-commands.md` (it bears on task 2), the other
  `open-question-*.md`, and `.inbox.md` (what Gab said on 22 Oct, not ratified yet).
- `projects/termlu/journal/`: the three entries of 22 Oct, the last one is `2026-10-22-the-bigger-picture.md`.

In this repo (`~/dev/TermNL`): `README.md`, `HANDOFF.md`, `TODO.md`, then the code each task names.

Working rules from Gab (Claude's memory and the brain): proposals before building; flag trade-offs
instead of changing working behaviour quietly; test with his real sentences, not only Claude's; see UI
work in his Brave through Claude in Chrome; stop any server you started before saying it's ready; no
mention of Claude in commit messages.

## 1. A clock skill

**Why it fails today.** No skill reads the time, and `termnl/languages/en/out-of-scope.md` lists
"what time is it" as an example of what TermNL refuses, so the model is trained to say "none". Gab asked
the time five times in his log of 22 Oct. Nobody decided against a clock; it was Claude's oversight.

**Proposed.**
- A reading skill (for example `check-time`) with `reads: clock`, sentences such as "what time is it",
  "what's the date", "what day is it", and replies per level under `## When it's …`.
- A `clock` reader in `termnl/readers.py` beside `temperature` and `memory`: the time, the date and the
  day, with words from `words/readings.md` (it already has `today`, `date`, `months`).
- Levels: `fine`; `unsure` when the clock is not synchronised; `wrong` when the year is obviously wrong
  (a board without a clock battery can start in 1970 or on its image's build date after a power cut).
  This reason is Claude's reading, not ratified by Gab.
- Whether the clock is synchronised needs `timedatectl` (a command) or the kernel's adjtimex call. That
  is the same open question as `open-question-reading-commands.md`: ask Gab which way, don't choose.
- Remove "what time is it" from `out-of-scope.md` (keep "set an alarm for seven": an alarm is another
  skill), add a word for the object (time, date) to `words/objects.md`, retrain, add tests.

## 2. Wi-Fi, Bluetooth and network replies in plain words

**Today.** `check-wifi`, `show-wifi`, `check-network` and `check-bluetooth` run a command from their
skill file (`nmcli …`, `ip -4 -brief addr`, `bluetoothctl show`) and show its raw output.

**Proposed.** Readers that turn that output into values, a level and a table (networks: name and signal,
coloured by level), as memory and storage do. One point to raise with Gab first: there is no `/proc` file
for Wi-Fi names, so here the command has to run, and Python only converts its output. That is option B
of the open question, arriving by itself. Proposal: keep the command in the skill file so "show
commands" shows what really ran, and say so to Gab, since he hasn't decided A, B or C.

## 3. A test set from real sentences

**Today.** `tests/phrasings.md` (59 sentences) is mostly Claude's; Gab's are its last section. A passing
suite hid failures Gab found with his first sentences, twice on 22 Oct. `logs/<date>.jsonl` holds every
turn typed in the chat (126 turns on 22 Oct; fields `at`, `session`, `text`, `outcome`, `say`, …), kept
out of git.

**Proposed.**
- Turn the logs into a readable file of real conversations (for example `tests/real.md`): each
  conversation, what TermNL did, and what it should have done.
- "Should have done" is Gab's to say. Claude may pre-fill a guess, marked as Claude's, for Gab to confirm
  or correct; never mix guesses with his answers.
- `tests.measure` reports the real sentences apart from Claude's.
- Ask Gab before putting his sentences in git: the logs are kept out on purpose.

## Before saying done

`python3 -m termnl.check` · `python3 -m unittest` · `python3 -m tests.measure -v` ·
`python3 -m tests.compare_agents` (must show 0 differences, or explain each one) · retrain with
`python3 -m termnl.train` · try it in the chat (`python3 -m termnl.server`, port 8810) in Gab's Brave,
then stop the server.
