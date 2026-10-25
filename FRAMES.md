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

## A. Skill-owned words — done

25 October, after Gab: "the skill should contain everything it needs to act, hence being really plug and
play or drag and drop".

**What a skill can say now.** A section `## Words`, and one line of front matter:

    topic: This device                       where help lists it, if its object is in no topic yet

    ## Words

    - kernel: kernel, linux version          words for its action or object; one words/ lacks is made here
    - turn on, switch on, start → play       with its object, these words mean its action
    - track: turn off, end → stop            the same, with another object

When the skills are read, these lines join the shared lists, so the agent, the templates and training read
them exactly as if `words/` had them. A skill speaks only for itself: words for another skill's object, or
"→" an action not its own, stop the checker.

**What moved.** The eight lines of "Meaning with an object" left `words/actions.md` for the ten skills they
serve (play-music, stop-music, turn-on/off-wifi, turn-on/off-bluetooth, mute/unmute-sound,
restart-service, shut-down-system). `words/actions.md` keeps the actions and their opposites: the language,
not any one skill.

**Same behaviour, proved.** Moved, then retrained: the model has the same weights as before, and all 665
sentences of the six sets get the same answer as before.

**The drop-in, proved.** `tests/drop-in/` holds two skills TermNL doesn't ship, each bringing what `words/`
doesn't have: check-kernel an object (`uname -r`), ping-remote an action (`ping -c 3 {host}`). Dropped into
a copy of the language, nothing else edited:

- no problems from the checker; "check the kernel" and "can you reach the studio pi" act at once, by their
  own sentences (`tests/test_drop_in.py`);
- after learning, said in other words too: "what kernel is running", "which linux version do i have",
  "kernel version please" act; "is my kernel up to date" asks first ("date" is new);
- help lists the kernel under "This device", from its own `topic:`.

**Found on the way: a new skill moved the others for no reason of language.** Training drew every skill's
sentences from one shared random stream, in alphabetical order. A skill dropped in shifted the stream for
every skill after it, so their training sentences changed, and so did some readings: adding the two test
skills moved 16 of the 665 test sentences. Each skill now has its own stream, from its name
(`examples.py`). With it, the same two skills move 5, none into a wrong action. What still moves is real
competition between skills, the thing `doubts` and asking first are for.

That change redraws every skill's sentences once, so the committed model is retrained (same skill files).
Over the six sets, compared with main retrained:

| | handled | checked first | wrong skill, asked | **wrong acted** | not understood | out of scope: abstained / asked / **acted** |
|---|---|---|---|---|---|---|
| main, retrained | 380 | 156 | 34 | **2** | 23 | 53 / 16 / **1** |
| one stream per skill (this branch) | 383 | 153 | 31 | **2** | 26 | 54 / 15 / **1** |
| + check-kernel, ping-remote | 381 | 154 | 31 | **2** | 27 | 54 / 15 / **1** |

No new wrong action anywhere. The two unit tests that fail on main still fail, the same two: main's skill
files, retrained here, give them; they are not from this branch (105 tests, 103 pass).

**Still not drop-in:** a reading skill (`reads:`) needs its reader in `readers.py`, and a new action can't
yet say its opposites. Gab asked whether an `action.md` per skill should hold the command: today the
command is one line, so a second file adds nothing; for reading skills, an `action.md` declaring how a
command's output is read (ptiLU's `## Answer`) would remove the last Python a skill needs. Next, if wanted.

## B. Frames — done, with an honest count

25 October, Gab: "Okay go", after agreeing a frame is the intent context kept from one turn to the next.

**What TermNL keeps now.** After a request is done, the agent remembers it (`remember`): the skill, its
values, and the thing it touched: the file opened, the folder made or renamed (under its new name), the
folder shown, the service restarted. That is the frame.

**When a sentence uses it** (`follow_up`): it points ("it", "the other one", "same") or follows on ("and",
"now", "same for", "too"); it names an action or an object, never both; and every word left is a value, a
small word or one of those. The action or object it doesn't say comes from the frame; so do the values it
doesn't say (`carry`): the same request keeps its own ("and in downloads?"), another one takes the thing
("now delete it"). A file is carried by its name only, so it is looked for again where it is asked for.
Words that mean another action with an object work through the frame too, as the skill says them: "turn
it off" after "play music" stops the music (stop-music's `## Words`).

**The eight conversations:**

| First turn | Then | Now |
|---|---|---|
| open seed.md in ideas | now delete it | "Move seed.md from ideas to the trash?" |
| create a folder called bikes | rename it to cycles | `mv -nT $HOME/bikes $HOME/cycles` |
| show the files in documents | and in downloads? | lists Downloads |
| turn on the wifi, yes | and bluetooth too | "Turn Bluetooth on?" |
| turn on bluetooth, yes | turn it back off | "Turn Bluetooth off?" |
| open note.md in ideas | open the other one in documents | opens Documents/note.md |
| play music | louder | still "I can't do that yet": not a frame case, "louder" is a word no skill has |
| copy todo.txt to documents | same for note.md | `cp $HOME/note.md $HOME/Documents/` |

Before: 1 of 8, by luck. Now: 7 of 8.

**Guards, each a test (`tests/test_frames.py`):**
- A full request is never a follow-up: "open firefox" and "now open firefox" after a file opens Firefox.
- A word that isn't a value or a small word makes it a new request: "and what about the weather" is refused.
- Words pointing at several ("them", "these", "those", "all", `words/conversation.md`) never point at one
  thing: "delete them" after showing a folder asks "Which file?", never the folder.
- Negation still asks first: "don't delete it".
- Nothing done yet, nothing to point at: "now delete it" alone asks file or folder, as before.
- A request said no to never becomes the frame: only what was done is remembered.
- "cancel" and a sentence not understood forget the frame: the subject changed.
- An approval always names what it acts on: the checker now refuses a skill that needs approval and whose
  `approve` reply doesn't name its main value. All 16 such skills already did.

**Nothing else moved.** The test sets build a new agent for each sentence, so they check that frames change
nothing without a turn before: 664 of 665 answers are the same. The one that changed is better, by accident:
"who won the football game last night" is now refused instead of asking about your name. "same" became a
known word, so "game" is no longer a typo of only one word ("name"). "them" is now a pointing word: added as
"then" became a known word, which had started reading "them" as a typo of it. Unit tests: 120, the same two
failing as on main.

**The honest count.** Frames add what follow-ups need and remove no rule. `agent.py` went from 840 to 937
lines. The four rules the inventory listed are still there, because they answer when there is no frame:
an action said alone still asks which skill, a pointing word with nothing before is still asked, and the
answer to "Which one?" is still its own code (`fill_value`). Conceptually they are the same merge; in code,
folding them would mean rewriting how TermNL answers its own questions, for no change anyone would see. As
agreed before starting, that is where it stops: frames made TermNL aware of context, not simpler.

## C. `back_agent.py` retired

25 October, Gab: "remove back_agent". The version of the dialogue before 22 October was kept beside
`agent.py` to compare replies; it knew neither skill-owned words' follow-ups nor frames. Gone with it:
`tests/compare_agents.py` and `tests/conversations.json`, which only fed that comparison, the server's
`--agent back`, and `TERMNL_AGENT` in the tests. All stay in git's history. A host that passes `agent="agent"`
works as before. 668 + 45 lines and a 47-conversation file fewer; the tests are the same 120.

## Open, for Gab

- How long a frame lasts. Now: until another request is done, "cancel", or a sentence not understood.
  Should it also fade after some minutes, or a few turns?
- After a refused request, "it" is still the last thing done (the file opened, not the delete refused).
  Right?
- "louder", "quieter": words for turn-up-sound and turn-down-sound to add in their `## Words`?
- Folding the old rules into the merge (a rewrite of `fill_value` and `bare_action`): worth it, or not?
- Readers declared in the skill (`action.md`), for the 20 reading skills: when a new reading skill is wanted.
- The two failing tests: they come from main's skill files (retrained here, they still fail).
