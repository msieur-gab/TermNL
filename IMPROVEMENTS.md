# Improvements — the `feat/improvements` branch

24 October 2026. Gab asked for the fixes Claude had listed, tested until the model improves, a grammar
people can write "without a PhD degree", and every choice, test and result written down. This branch is
Claude's own proposal; nothing in it is decided until Gab says so. Gab's words during the work:

> "turn on the wifi, turn on the music, turn on bluetooth should after your test be clearly
> disambiguated. TermNL should be able to act with confidence or ask for disambiguation or abstain."

> "actions should be split of subject to allow their combination to clear distinctive pattern bringing
> more confidence in the results, but i let you judge the benefits"

## In short

- **No wrong action left** on any test set, including 131 sentences written blind by an agent that never
  saw a skill file.
- **On the blind set, 10 sentences in 111 weren't understood; now 1.** 61 were handled straight away;
  now 67. All 20 out-of-scope sentences (delete, kill, install, format…) are refused or asked about,
  never acted on (before: 14 refused, 6 asked about another skill).
- **Gab's three sentences are told apart**, and an action said alone ("turn off") asks which one.
- **Skills are written in plain sentences** now (`## People say`, `## What it needs`). All 37 were
  rewritten, and 8,767 sentences are read exactly as before.
- **Action and object stay split.** Measured against one model over whole skills, the split is safer
  (details below). What it lacked was the action seeing its object; that is now a readable list.

## The results, stage by stage

Each cell: handled / checked first ("Do you want me to…?") / wrong skill, but asked or stopped /
**wrong skill acted on** / not understood. Then, for sentences TermNL must not act on: refused / asked /
**acted on**.

| Stage (commit) | phrasings (59) | probes (88 + 5) | held-out (117 + 15) | blind (111 + 20) |
|---|---|---|---|---|
| Before (c2d8d66) | 33/21/2/**0**/3 | 64/5/12/**1**/6 · 4/1/**0** | 105/8/2/**0**/2 · 9/6/**0** | 61/35/5/**0**/10 · 14/6/**0** |
| 1. Words in context, ask to tell apart (51fe51e) | 35/21/1/**0**/2 | 73/4/8/**0**/3 · 4/1/**0** | 105/8/2/**0**/2 · 9/6/**0** | 61/34/6/**0**/10 · 14/6/**0** |
| 2. Sentences from a larger model (4d5644d) | 40/16/1/**0**/2 | 74/4/9/**0**/1 · 5/0/**0** | 109/6/2/**0**/0 · 12/3/**0** | 67/40/3/**0**/1 · 20/0/**0** |
| 3. Plain sentences, same budget per skill (now) | 42/14/2/**0**/1 | 74/5/8/**0**/1 · 5/0/**0** | 109/6/2/**0**/0 · 12/3/**0** | 67/39/4/**0**/1 · 19/1/**0** |

Unit tests: 80 before, 87 now, all passing. Model: 534 KB before, 663 KB now (more sentences to learn
from). Code: +279 lines in `termnl/`, +186 in `tools/` (the one-time rewrite and its proof; they can go
once the old form is retired), +163 in `tests/`.

How to read it: stage 1 is about safety and telling things apart, so it shows mostly on the probes
written for it; stage 2 is what moved the blind set; stage 3 changes the form, not the behaviour.

## The test sets, and how honest each is

| Set | Written | Tuned against? |
|---|---|---|
| `tests/phrasings.md` | 22 Oct, by Claude and Gab | Yes, since 22 Oct |
| `tests/probes.md` | 24 Oct, by Claude, to diagnose | Yes: every fix was checked on it, so its score flatters |
| `tests/heldout.md` | 24 Oct, by Claude, before any change | No. But Claude had read some templates first, so it suits them: it was already at 105 of 117 |
| `tests/blind.md` | 24 Oct, by a fresh agent given only each skill's name and purpose | No. Looked at once, for a single line (stage 3, below) |

The rule kept: no sentence from a test set enters a skill file. When the larger model's sentences came
back, 71 were word for word the same as a test sentence and were dropped before training, or the scores
would have lied.

`python3 -m tests.measure all` prints the four lines. Gab's own real sentences (`tests/real.md`, kept out
of git) were not on this machine: they remain the judge, to run on his laptop.

**A correction to what Claude said before this branch.** Its first reading counted two silent wrong
actions in the probes. Only one acted ("is bluetooth running" checked a service called bluetooth). The
other, "rename the folder photos to pictures", read a file called "folder photos", found none and said so:
nothing ran. The old `measure.py` counted any wrong skill that wasn't a question as a wrong action; it now
counts only acting or asking for approval. Every number above uses the corrected count.

## 1. Words read in their context

**Why.** "stop the wifi" was read as stopping the music, "start bluetooth" as turning it off, "turn the
sound off" as unmute, and "turn on the music" wasn't understood. The action and the object are recognised
by two separate models whose scores are multiplied, so the action model never knows which object it acts
on. A verb's meaning often depends on its object: that is the vocabulary conflict Gab named on 20 Oct.

**What.** Two readable lists, used only when no template reads the sentence as typed (as typos are):
- `words/actions.md`, a new section **Meaning with an object**: `- music: turn on, switch on, start → play`,
  `- wifi, bluetooth: stop, kill, cut, shut off, disconnect, close → turn off`, and so on. A word changes
  its meaning only when one of those objects is in the sentence. ptiLU lost accuracy on 20 Oct by
  merging verbs everywhere; scoped to an object, the merge can't spill into other skills.
- `words/conversation.md`, **split verbs** and **verb ends**: "turn the music off" is read as "turn off
  the music". Alone, this created a new wrong reading ("bring the wifi back up" became "bring up", an
  open word); with the object list it lands on turning Wi-Fi on.

**Result.** All of Gab's sentences: "turn on the wifi" and "turn on bluetooth" ask for approval (their
skills always do), "turn on the music" plays, "turn the music off" stops, "turn off the sound" mutes,
"start bluetooth" and "stop the wifi" ask for approval. Each is a test (`test_turn_on_is_told_apart_by_its_object`).

**Caveat.** Claude wrote the object list after seeing the probes fail, so the probes' gain from it is
optimistic. Its lines are Claude's and wait for Gab's review.

## 2. An action said alone asks which one

**Why.** "turn on" alone was refused; "turn off" asked to shut the board down.

**What.** When nothing but an action and small words is said ("turn on", "turn it on", "switch it off"),
TermNL offers the skills that do it, including those the object list sends it to: "Do you mean play
music or turn Bluetooth on or turn Wi-Fi on or unmute the sound?", with each as a chip. Only between 2
and 6 choices; otherwise the model's reading goes on as before.

**Changed on the way.** "open" and "show" alone now ask which one (before: "open an app?", and "show"
listed the home folder). "play" alone asks between music and an artist.

## 3. A template votes, it doesn't decide

**Why.** The only wrong action in the probes came from a template, which counts as certain: "is bluetooth
running" matched check-service's `is {name} running`, and the laptop has a service called bluetooth.

**What.** When the model is sure (60%) of another action or object, and a skill does exactly that, TermNL
asks which of the two: "Do you mean check a service or check Bluetooth?". Only when that other skill
exists: "show me the files here" names files, but there is no "show file" skill, so show folder stands.

**Set aside.** A first version just asked "Do you want me to check a service?": a yes would still have
done the wrong thing. Comparing with every object a skill's templates mention also failed: rename file
mentions folders (the place), so it never doubted itself.

## 4. Sentences from a larger model

**Why.** 23 of 37 skills had no `## Also said`: the model learnt them only from their templates' own
words, so most other words were "new" and TermNL asked first, or gave up.

**What.** `briefs/2026-10-24-also-said-paraphrases.md` asked a fresh model, which never read the tests,
for 8 sentences per skill and 25 near misses TermNL must not act on (delete, kill, install, format…).
It delivered a file, `data/also-said-2026-10-24.md` (321 sentences, kept). Checked before training:
71 dropped as identical to a test sentence, 3 dropped because another skill's template already reads
them (findings in themselves, below). 247 went into the skill files and `out-of-scope.md`.

This is "distilling from a larger model" as Claude recommended: the large model writes data once, at
training time; nothing large runs on the board, and the model stays the same small, readable one.

**Result.** The biggest gain of the branch: on the blind set, not understood 10 → 1, handled 61 → 67,
and every out-of-scope sentence refused.

**Three template over-reaches found on the way** (not fixed): "show me the storage" is read by show
folder as a folder called storage; "show me the networks in range" the same; "take me to the parent
folder" is read as create folder, because "take" is corrected as a typo of "make".

## 5. Plain sentences: a grammar without a PhD

**Why.** Gab, 22 Oct: the template grammar "is not bad, it is just not authorable by users", and the
values are "written in a very obscure and misleading way".

**The rules**, all marks from everyday writing:

| Write | Means |
|---|---|
| `make a folder` | the sentence as people say it. A word for an action or object (`words/actions.md`, `objects.md`) stands for all its words: this also hears "create a directory" |
| `called/named` | one of these words |
| `(new)` | may be left out |
| `{name}` | a value, said under What it needs |
| `"run"` | this word only, even though "run" is a word for *open* |

A choice between phrases of several words ("what is" or "what's") is written as two sentences. An action
counts once per sentence: in "make a (new) folder", "new" is just the word new, although it is also a
word for *create*. A word in two families ("start": create and open) means the skill's own; elsewhere the
checker asks for quotes.

**What it needs**, in words from `words/values.md` (so it translates like everything else):

    - {name}: a new name. If it's missing, ask: What should I call it? | What name should the folder have?
    - {place}: a folder on the device. If it's not said: where you are.

The kinds are a short list ("a name", "a new name", "a folder on the device", "a file on the device", "a
service on the device", "a file type"…), and "If it's not said:" takes "where you are", "the folder
above", "the folder {place} is in", or any value as written ("markdown"). The question asked when a value
is missing now sits beside the value, instead of in the replies.

**A whole skill, written from scratch** (it loads and works: `tests/test_plain.py`):

    ---
    does: create folder
    label: make a folder
    ---

    ## People say

    - make a (new) folder called/named {name} (in (the) {place} (folder))
    - make a {name} folder

    ## What it needs

    - {name}: a new name. If it's missing, ask: What should I call it?
    - {place}: a folder on the device. If it's not said: where you are.

    ## Command

    mkdir -p {place}/{name}

    ## Replies

    - done: Done, {name} is in {place}.

It understands "create a new directory named bikes in the documents folder".

**How every skill was rewritten.** `tools/to_plain.py` turned each template into plain sentences;
`tools/same_reading.py` recorded how 8,767 sentences were read before (the templates' own variations,
every test set, every Also said line) and read them again after, with the same model: **0 differ**. The
older `## Sentences` form still loads, so both can live side by side while Gab decides.

**What still reads awkwardly** (left as converted, for Gab to polish): some old choices carried over word
for word ("named/called/call/name/titled"); quotes stay where an old template meant only one word
(`"run" (a) health/system/status check/report`); check-system became 8 sentences, show folder 19. A
person would write fewer. "what is/what's" is valid but means "what is" or "what what's": the guide
says to write two sentences.

**A consequence fixed on the way.** Written plainly, show process went from 5 templates to 16
sentences, and the model's training made 40 sentences from each, so the skill weighed three times more.
After retraining, the blind set showed a wrong reading, and Claude looked at that one line (the only time
the blind set was opened): "start the browser, i want to look something up" was read as opening a file
called "browser…", which wasn't found, so nothing ran. Each skill now gets the same training budget
(160 sentences, shared among its sentences): how much an author writes no longer tips the model. The
line itself is still read that way (open question below).

## Split or joint? Gab's question

Measured on the final code, with the same data, swapping only the model:

| Model | blind | blind, out of scope | held-out, out of scope | phrasings |
|---|---|---|---|---|
| **Split: action × object (kept)** | 67/39/4/**0**/1 | 19/1/**0** | 12/3/0 | 42/14/2/**0**/1 |
| One model over whole skills | 66/38/5/**2**/0 | 15/5/0 | 8/7/0 | 42/16/0/**1**/0 |
| Both, combined | 68/38/4/**0**/1 | 19/1/0 | 12/3/0 | 41/15/2/0/1 |

The joint model understands about as much but acts wrongly twice on the blind set and once in the
phrasings, and refuses fewer out-of-scope sentences. Combining both gains one sentence for a second model
of 776 KB. Gab's intuition holds: the split gives distinct patterns that combine, and its two votes make
"I'm not sure" easier to see. Its one weakness was that the action didn't see the object, which section
1 addresses in a readable file, not in the model.

## Tried, measured, not applied

- **Reading without asking first.** Most "checked first" answers left are a reading skill and a word it
  wasn't taught ("is the connection down", "memory status", "my disk feels full"), with the model 80–90%
  sure. If reading skills answered without asking when the model is sure: blind 67 → 77 handled; but a
  wrong reading would answer twice, in the probes and the held-out set (reading changes nothing, yet the
  answer is wrong). This is HANDOFF's open question, "should reading ever ask first?": Gab's call.
- **Word vectors distilled from a sentence model (Model2Vec)**, to read words no skill teaches: the
  download is blocked from this workspace. `tools/neighbours.py` can try it on Gab's machine. Expected to
  help the object ("headphones" → bluetooth), never the on/off of an action.

## Not changed

- **`back_agent.py`.** Untouched: it fails the three new dialogue tests, and `tests.compare_agents` shows
  7 differences, all of them the new behaviour ("open", "show", "kill the wifi", "disconnect from wifi",
  "stop bluetooth", and two confidence values). Porting the changes or retiring it is Gab's call (inbox,
  22 Oct).
- Templates, thresholds (act at 50%, ask from 15%), typo correction, replies, readers, the server.

## Open, for Gab

1. Should reading ask first? (The measured trade-off above.)
2. Keep the plain form, polish the converted sentences, retire the old form and `tools/to_plain.py`?
3. The front matter is still terse (`admin: no`, `approve: no`); "needs admin: no", "asks first: yes"
   would read better. Not done.
4. Review the object list (Claude's lines) and the 247 sentences from the larger model.
5. "start the browser…" read as a file to open: a value that names an app on the device could point to
   open app. Not done (one sentence, and it stops safely).
6. The three template over-reaches (section 4).
7. `back_agent.py`: port or retire.
8. Run `tests.real` on Gab's laptop, his own sentences being the judge.

## How to check

    python3 -m termnl.check             # 37 skills, no problems
    python3 -m unittest                 # 87 tests
    python3 -m tests.measure all        # the four lines of the last table row
    python3 -m tests.compare_agents     # 7 differences, listed above
    python3 -m tests.real -v            # on Gab's laptop
