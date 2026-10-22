# Handoff — 22 October 2026

TermLU was born this morning from ptiLU (repo msieur-gab/ptilu). The design lives in Gab's brain repo,
`projects/termlu/`: read `intention.md`, `brief.md`, `vocabulary.md`, `decisions.md`, `day-one-scope.md`
and the `open-question-*.md` files before changing anything. Gab's decisions there are his; don't
rework them.

## What exists

- 22 skills in `en/skills/`, one per action + object pair (`does: create file`).
- Two layers of understanding (`core/agent.js`):
  1. templates (`core/template.js`, Home Assistant style) read a sentence exactly, values included;
  2. the model (`core/model.js`, ptiLU's TF-IDF + logistic regression, two small classifiers: action
     and object) for other wordings. It acts only when sure (≥ 0.5) and every word is taught;
     otherwise it asks "Do you want me to …?", naming the new words.
- Values: device lists (`@sys.folder`, `@sys.service`, `@sys.app`, `@sys.network`), files found on the
  device (`@sys.file`: here, elsewhere, several, nowhere), the shared `filetype` list, free text.
- Four outcomes: act, ask, approve, abstain. Admin mode off by default (`settings.md`).
- Where you are: "open / go to a folder" goes into it; new files go where you are.
- Rules learned the hard way today, each with tests: a name never starts with a place word, never ends
  with an object word, never is a pointing word (this, that); a misspelled device value is confirmed
  ("Did you mean Documents?"); an answer to a pending question fills it unless the person clearly asks
  for something else (action word or a skill's exact sentence); a new file never replaces one.
- Playground: `node tools/build-page.js` → `docs/index.html` (also published as a claude.ai artifact).

Run: `node core/check.js` · `node core/train.js` · `node --test test/*.test.js` (31 pass) ·
`node test/measure.js -v` (53 phrasings: 18 handled, 27 asked first, 4 wrong skill but asked, 0 wrong
actions, 4 not understood).

## Open, in order of importance

1. **The learning loop doesn't exist.** A "yes" to "I don't know “kill” yet…" returns `teach`, but
   nothing saves or retrains. ptiLU's core promise (the inbox, retraining on the device) isn't built.
2. **The test set is Claude's.** `test/phrasings.md` was written by Claude; one label was changed after
   Gab's "open = go into" rule, and "open the ideas folder" was added to a skill. Gab's own sentences,
   never trained on, are the honest measure. Test real conversations before trusting any number:
   twice today a passing suite hid a failure Gab found in his first sentence.
3. **Authoring** (`open-question-authoring.md`): the template grammar works but users can't write it,
   and the `## Values` lines are obscure. Kept for now "until we find what breaks".
4. **Shared words in two families:** "start" (create + open), "note" (file + markdown). ptiLU learned
   that such words pull the wrong way (`brain/projects/ptilu/what-the-router-sees.md`).
5. **Free names** (`open-question-free-names.md`): fixed for the cases tested; "make a new folder in
   projects for the website" still answers "I don't see “projects for the website”".
6. **Nothing runs.** No executor: listing a folder's files, finding a name in home, running the
   declared command, the admin permission rule. Commands differ per board (nmcli, rfkill, thermal zone).
7. **Results aren't read back.** Read skills reply with `{output}` raw; turning `df` or `free` output
   into plain words is undesigned.
8. **No context beyond a pending question.** Dialogflow-style contexts ("undo that", "and in ideas?")
   aren't built.
9. **Word embeddings for unknown words: tested, not worth it now.** GloVe-50 on the 26 untaught words of
   the phrasings: 3 useful neighbours (warm → hot), 15 wrong (kill → bring, stop → out), because most
   new words are context, not synonyms, and embeddings put opposites side by side. A better embedding
   (Model2Vec, not reachable from the cloud session) could be tried with `tools/neighbours.py`.
10. The model file is 430 KB of JSON floats; it can shrink (ptiLU stored 1-byte weights).
