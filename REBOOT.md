# research/reboot — one reader, from the skill files

Branch from feat/skill-first, 26 Oct 2026. The agent's cascade of readings (templates, the model, a rewrite
in context, a typo pass, a bare-action chooser, the model doubting a template, a split at commas, each with
its own conditions) is replaced by one reader, `termnl/reading.py`, in four looks, each taken from the skill
files and the word lists. The model stays, as the fourth look only.

A first version of this branch (5c9b83a, 15:55) had no model at all: the fourth look was the nearest
`## Also said` line, by weighted word overlap. Measured against skill-first it asked a wrong question twice
as often (56 against 26 on the skills set) and acted wrongly where skill-first didn't; three forms of word
order in the matching brought the 56 to 47 at best. Gab, 16:20: training is a one-time action when a skill is
dropped in, not a problem; the model is worth it if it serves a purpose. It does: telling sibling skills
apart under free wording. So the model came back, and nothing else of the cascade did.

## The four looks

1. **words** — fillers off; a typo one letter from exactly one known word is read as it, but only when
   that reads better than the sentence as typed (a name keeps its spelling).
2. **funnel** — the sentence as a shape: each action and object by its name ("make" is create, "note" is
   file; "start" is create *and* open), a file-shaped word as `@file`, a value the device has as `@value`
   plus its kind (`@sys.folder`), a word TermNL doesn't know as itself plus `@value`; small words dropped.
   The actions and objects named decide between readings that tie. An action said with nothing else
   ("turn off") is a choice among the skills that do it (the old bare_action, as data).
3. **templates** — `## People say` reads the sentence exactly, as typed or with the words read in their
   context ("turn on the music" plays it; a skill's `## Words`). Three rules added to template.py: free
   text never holds a word for an action or object unless it follows "called"; a list value is never a
   word for an object ("bluetooth" is the board's Bluetooth); a value never crosses a comma ("restart
   ssh, I can't log in" names ssh). A template that read a value not on its list is a guess (p 0.75).
4. **model** — the action and object the trained model reads (model.py, unchanged), the funnel deciding
   among readings nearly as likely, the person when it can't. The opposite of an action said in so many
   words is never offered. When the model is sure of another skill than a template's guess, the person
   chooses. Unknown words are named and asked about, as before.

A sentence with a reason ("restart ssh, I can't log in") is read whole, then by its parts at punctuation;
the part that reads best is the request, and a part is never acted on unasked unless it only reads.
Values are read by one routine (`values_in`): a list value after the preposition the skill's own sentences
put before it, a name after "called", a file-shaped word.

Kept as they were: the dialogue (questions, "Which one?", approval, files found on the device, settings),
the frames ("now delete it"), readers, device, server, training.

## Size and speed

agent.py 999 → 691 lines; reading.py 401 (a quarter of it docstrings). Net, 516 lines in and 366 out
across termnl/, tools/ and web/, of which 41 are `tools/why.py` and 11 the tokenizer noting breaks. So the
understanding is about 60 lines shorter than skill-first's and lives in one file with four named looks,
instead of seven passes in the agent. Speed is the same: 9.0 ms a sentence here against 9.2.

`python3 -m tools.why "sentence"` shows every look: the shape, what is named, the templates that read it,
the model's three best actions and objects. `tools/same_reading.py` is back as it was.

## Measured, same scale (tests/measure.py), against feat/skill-first eaf56e8 in brackets

| set | sentences | acted | asked first | wrong skill, asked | wrong skill, acted | not understood |
|---|---|---|---|---|---|---|
| phrasings | 59 | 38 (39) | 18 (16) | 1 (2) | 0 (0) | 2 (2) |
| probes | 89 | 82 (80) | 2 (1) | 4 (7) | 0 (0) | 1 (1) |
| heldout | 122 | 115 (117) | 3 (3) | 3 (1) | 1 (1) | 0 (0) |
| blind | 116 | 68 (71) | 43 (39) | 3 (4) | 1 (1) | 1 (1) |
| scale-blind | 92 | 42 (45) | 39 (37) | 7 (4) | 0 (0) | 4 (6) |
| edge-blind | 117 | 65 (63) | 45 (49) | 6 (4) | 0 (0) | 1 (1) |
| skills (each skill's tests.md) | 462 | 284 (284) | 131 (129) | 28 (26) | 1 (0) | 18 (23) |
| **all** | **1,057** | **694 (699)** | **281 (274)** | **52 (48)** | **3 (2)** | **27 (34)** |

Out of scope (the `none:` lines): the reboot acted on none; skill-first acted on 1.

The three wrong actions: "which wifi network is this" (show-wifi) and "I want to look at report.pdf"
(find-file) are the same two skill-first gets wrong; the third, "look for files mentioning studio-pi, I wrote
its address down somewhere", is read by find-file's template once the comma cuts the sentence — a search,
nothing changed.

Unit tests: 129 pass, 3 fail. One fails on skill-first too (`test_host`: the documents stay quiet). The two
others are decisions, not bugs, and are listed so you can judge them:
- `test_a_template_the_model_doubts_asks_which_of_two`: "rename the folder photos to pictures" asks "Which
  folder?" with the real folders as chips (the device has no "photos"), instead of "rename a file or a
  folder?"; "is bluetooth running" checks Bluetooth (the model is 95% sure) instead of asking. Nothing runs
  in either case.
- `test_get_rid_of_everything_in_the_trash_asks_which`: the sentence is in empty-trash's own `## Also said`,
  so the model is 85% sure and asks for approval; the test expects a question first. The test and the skill
  file disagree; one of them should change.

## Where it stands

Level with skill-first on 1,057 sentences — 5 fewer handled, 7 more understood, the same mistakes — with
the model's purpose kept and the cascade gone. What it still doesn't have from skill-first: the five
correction passes, each of which fixed real sentences of Gab's; the measure says the funnel and the
template rules cover them. What to watch on the board: nothing new, the model and its training are the
same files as before.
