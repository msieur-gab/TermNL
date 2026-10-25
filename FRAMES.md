# Frames — the `feat/frames` branch

25 October 2026, from `main` (f9dfc15). Gab: "our code is already getting extremely complicated with
different lexicon and conditions, making it feels like each skills as it's own fix and logic", and "the
grammar might miss the concept of followup". The aim he set: "a true drop a skill in place and it simply
work by extending TermNL capabilities".

This file is the inventory asked for before any code: what every special rule does, what a frame would
absorb, and what stands between a new skill and "drop it in". Nothing in TermNL is changed on this branch
yet.

## In short

- **The core is still one system.** Every skill has the same shape (action × object, what it needs, a
  command, replies) and every turn ends in act, ask, approve or abstain. The skills don't carry their own
  logic; the agent does.
- **The agent's rules come from two missing things, not one.**
  - *No conversation state.* TermNL remembers a question it waits on, and where you are. Nothing else.
    Four rules are this gap in disguise, and follow-ups have nowhere to land: 1 of 8 follow-up
    conversations worked below, by luck.
  - *Words that only mean something with an object, kept in one shared place.* Seven rules exist because
    "turn on", "stop" or "start" mean different actions with different objects, and the shared lists
    decide it for every skill at once. This is also what breaks "drop it in".
- **Frames would absorb 4 rules and generalise a fifth.** Real, but half the story.
- **Drop-in fails today for a structural reason.** A skill can't name an action or object the shared
  lists don't have, and can't say what a word means *for it*. Of the 17 commits that changed skill files,
  10 also changed `words/` and 12 also changed the agent, the template reader or the plain-sentence
  reader.
- **ptiLU walked the same road.** Its `RECOMMENDATIONS-FOR-MAIN.md` set aside the folder type, folder
  guessing and "Did you mean Documents?" as patches, "case by case, what a word-counting model can't see",
  and Gab found main "simpler and perhaps better". TermNL is at the same point.

## A frame

A request is a frame: an action, an object, and its values. Today a sentence must say the whole frame
(or answer the one question waiting). With frames, every turn says *part* of a frame, and the rest comes
from what's already on the table:

| Turn | Says | Kept from the frame before |
|---|---|---|
| "rename it to cycles" | action, a value | the object and the thing ("bikes") |
| "and in downloads?" | a value | the action and the object |
| "and bluetooth too" | an object | the action |
| "turn it back off" | an action | the object |
| "same for note.md" | a value | the action, the object, the other values |
| "louder" | an action | the object (sound) |

Then the same decision as today runs on the merged frame. What is still missing is asked, as now.

TermNL already has one piece of this: *where you are*. "go to ideas", then "create a file", makes it in
ideas (`test_go_to_ideas_then_creating_a_file_makes_it_there`). A frame is that idea, for everything a
request says.

## Follow-ups today

On `main`, with the tests' pretend device (`tests/device.py`), admin mode on for Wi-Fi and Bluetooth.
Nothing wrong ran. Only one follow-up worked, and not because of the turn before: "and bluetooth too"
names its object and the model guessed the action.

| First turn | Then | TermNL said |
|---|---|---|
| open seed.md in ideas | now delete it | Do you mean delete a file or delete a folder? |
| create a folder called bikes | rename it to cycles | Which file? *(rename file, not the folder)* |
| show the files in documents | and in downloads? | I can't do that yet. |
| turn on the wifi, yes | and bluetooth too | Turn Bluetooth on? ✓ |
| turn on bluetooth, yes | turn it back off | Do you mean mute the sound or shut the board down or stop the music or… |
| open note.md in ideas | open the other one in documents | I can't find other one in Documents… |
| play music | louder | I can't do that yet. |
| copy todo.txt to documents | same for note.md | I don't know "same" yet. Do you want me to find a file? |

## Inventory

Every rule in `termnl/agent.py` beyond reading templates and asking the model, and the word lists they
read. Each gets one verdict:

- **frame**: a frame would do it, as one case of merging a turn into the frame before
- **skill words**: it exists because the shared lists decide a word's meaning for every skill; it would
  move into the skills that need it
- **keep**: the device's truth, safety, or reading what was typed; a frame doesn't change it

### What a frame would absorb

| Rule | Where | What it does | Proved by |
|---|---|---|---|
| Answering "Which one?" | `fill_value` | the answer fills the value waiting; the same request said again adds its values; said without the value, its default applies | `test_the_same_request_said_again_completes…`, `test_a_missing_name_is_asked_for…` |
| A different request replaces the question | `respond`, step 2 | while a value is asked, a sentence with another sure skill starts over | `test_a_clearly_different_request_replaces_the_question` |
| An action said alone | `bare_action` | "turn on" alone offers the skills that do it (2 to 8). With a frame before, the object is already known | `test_an_action_without_its_object_asks_which_one` |
| Pointing words | `only_points` | "this", "that file" is never a name, so it is asked. With a frame before, it is that frame's value | `test_open_this_file_a_pointing_word…` |
| Where you are *(generalised, not removed)* | `here`, `moves:` | the working folder carried between turns: already a one-value frame | `test_go_to_ideas_then_creating…`, `test_opening_a_folder_goes_into_it…` |

### What skill-owned words would absorb

| Rule | Where | What it does | Proved by |
|---|---|---|---|
| Meaning with an object | `in_context`, `words/actions.md` | "turn on the music" plays it, "stop the wifi" turns it off | `test_turn_on_is_told_apart_by_its_object` |
| Split verbs | `in_context`, `words/conversation.md` | "turn the music off" read as "turn off the music" | same |
| Opposites | `recognise`, `words/actions.md` | "turn the board on" is never offered a shut down | `test_the_board_is_never_offered_the_opposite…` |
| Actions said in so many words | `actions_said` | "start" names no action, as it means both create and open | same |
| A template the model doubts | `doubts` | "rename the folder photos to pictures" asks file or folder | `test_a_template_the_model_doubts…` (fails on main today, below) |
| An object word is the object | `recognise` | "is bluetooth on" is the board's Bluetooth, not a service called bluetooth | `test_an_object_word_is_the_object…` |
| A file name makes it a file | `as_file` | "create a note.md in Documents" is a file, never a folder called note.md | `test_a_name_ending_in_a_file_type…` |

These seven share one cause: the model reads the action and the object separately (the split Gab chose and
measured, `IMPROVEMENTS.md`), so the meaning of a verb *with* an object has to be fixed outside the model.
Today that fix lives in shared lists and code. Most of it belongs to a skill: "turn on, start" are words
play-music has for itself; "file name with a known type" is something create-file knows about its value.

### What stays

| Rule | Where | Why it stays |
|---|---|---|
| Fillers off | `clean` | reading what was typed |
| Typos read as known words, never in a name | `correct`, `hid_a_place` | reading what was typed |
| Values found anywhere in the sentence | `values_in` | how a value is read when no template reads the sentence |
| Unknown words become the missing device value | `recognise` ("kill pipewire") | the device's truth |
| A typo of a device value is confirmed | `confirm_typo` | the device's truth |
| A file is found here, elsewhere, or said missing | `find_files` | the device's truth |
| A new name never replaces what is there | `already_there` | the device's truth, and safety |
| A file type gives the extension | `finish_filetype` | a value's meaning |
| Negation asks first | `respond`, step 4 | safety |
| A typo in a change asks first | `respond`, step 4 | safety |
| Admin mode, approval | `next_step` | safety |
| Lone yes or no with nothing waiting | `respond`, step 2 | honesty: never guess |
| Skill kinds when acting (reads, changes, opens, lists, trains) | `act` | a fixed, small vocabulary the checker knows; fine as it is |

**Count:** 4 rules absorbed by frames and 1 generalised; 7 rules that are skill words in shared lists;
13 that stay. `back_agent.py` (668 lines) is the whole agent a second time, kept for comparison.

## The drop-in test, today

What a new skill folder can't do on its own:

1. **Name a new action or object.** `skills.py` refuses a `does:` whose action or object is not in
   `words/actions.md` or `words/objects.md`. A battery skill needs `objects.md` edited first.
2. **Say what a word means for it.** "turn on the music" needed a line in `words/actions.md`, read by
   every skill.
3. **Read the device in a new way.** `reads: memory` needs a reader written in `termnl/readers.py`.
4. **Choose its help topic.** Topics map objects in `words/objects.md`; a new object falls into "Something
   else".

Points 1 and 2 are words; they could live in the skill file and be merged into the shared lists when
skills load, as ptiLU's compiler merges `action.md` into its skill. Point 3 is code, and stays code, but a
reader of a command's output could be declared in the skill (ptiLU's `## Answer`). Point 4 is one line in
the front matter.

## ptiLU, side by side

ptiLU (main, 5a4349e): a skill folder holds `skill.md` (what people say, the values, the replies),
`action.md` (what it does: the request it sends, what it reads back, the secrets) and, only when the
Markdown can't say it, `skill.js`. "Delete a folder and the skill is gone. Copy a folder and you have a new
skill." Its dialogue "knows no skill by name".

| ptiLU | TermNL today | Worth taking? |
|---|---|---|
| A skill's own value lists, `key: other, words → output` (`## Values: app`) | values come from the device (`@sys.folder`…) or one shared filetypes list | **Yes, for fixed values** a skill alone uses (sound levels, the board's names). The device lists stay. |
| `action.md`: what it does, apart from what people say | `## Command` in the same file | **Partly.** For reading skills: what to read from a command's output, declared beside the skill, instead of a Python reader for each. |
| Slot options `guess`, `ignore: app window`, `invalid:` | hard-coded rules (object words, name ends, "the ideas folder") | **Yes, as an idea.** These are rules a skill says about its own values. |
| `ctx.state` (a value kept for the session: the volume) and `handover` | `here` only | **The seed of frames.** |
| A part without a verb borrows the verb before ("…and then") | — | **No.** Several commands in one sentence was removed from ptiLU: "interesting on paper but bad in practice". Frames are across turns, not inside one sentence. |
| Example grammar `{a\|b}`, `[x](slot)` | plain sentences (`## People say`) | **No.** TermNL's is more readable. |
| One model over whole skills | action × object | **No.** Measured worse in TermNL (`IMPROVEMENTS.md`, "Split or joint?"). |

## Baseline (main, f9dfc15, the committed model)

Each cell: handled / checked first / wrong skill, but asked or stopped / **wrong skill acted on** / not
understood; then out of scope: abstained / asked / acted on.

| Set | In scope | Out of scope |
|---|---|---|
| phrasings (59) | 35 / 18 / 6 / **0** / 0 | — |
| probes (89) | 75 / 3 / 8 / **0** / 3 | 3 / 1 / **0** |
| heldout (122) | 114 / 4 / 3 / **0** / 1 | 9 / 1 / **0** |
| blind (116) | 66 / 36 / 9 / **1** / 4 | 11 / 4 / **0** |
| scale-blind (92) | 36 / 40 / 6 / **0** / 10 | 14 / 2 / **0** |
| edge-blind (117) | 53 / 55 / 4 / **0** / 5 | 17 / 7 / **1** |

The unit tests: 101, **2 fail on main** with the committed model: "rename the folder photos to pictures"
now abstains instead of asking which (`doubts`), and "is there enough space for a movie" reads check-type instead
of check-storage. The committed `model.json` looks retrained since those tests passed: HANDOFF's issue 3
(the device writes tracked files). `tests/real.md` is not in git, so Gab's real turns are not in this
baseline; they remain the judge, on his laptop.

## What it suggests, in the order to try

| # | Step | Behaviour change | How it's judged |
|---|---|---|---|
| A | **Skill-owned words.** A skill may name a new action or object with its words, say what words mean for it ("turn on, start → play"), and name its help topic. When skills load, these merge into the same lists the agent reads today. | None expected | The numbers above unchanged, and the drop-in test: a new skill with a new object, written only in its folder, works after training. |
| B | **Frames.** Every turn makes a partial frame, merged with the question waiting or the last thing done. The 4 rules above become cases of it; `here` becomes part of it. | Follow-ups | Zero new wrong actions; fewer rules than before; the 8 conversations above. |
| C | Retire `back_agent.py`. | None | One agent to compare. |

A first because it is the drop-in Gab asked for, changes no behaviour, and is easy to prove. B second
because it changes what TermNL does and needs A's numbers to compare against. If B absorbs fewer rules than
listed here once written, it stops there.

## Open, for Gab

- A, B, or both, and in which order.
- "it" after an approval that was declined: the frame before, or nothing? (A refused delete shouldn't be
  what "it" points at next.)
- How long a frame lasts: until the next request, or a few turns, or until the person changes subject?
- The two failing tests: retrain from the skill files first, so the branch starts green?
