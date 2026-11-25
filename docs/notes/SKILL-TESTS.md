# Skill tests and new wordings

Branch `feat/skill-tests`, from `feat/frames`, 26 Oct 2026. Gab: "start with 1" (each skill brings its own
proof, then the wordings it was missing).

## What changed

1. **Each skill folder has a `tests.md`** beside its `skill.md`: 6 sentences people would say (plain twice,
   casual, polite, with a reason added, a fragment). Written blind: the writer saw only the skill's purpose,
   label and the values it needs, never its wordings nor the test sets. 462 sentences, never trained on.
   `python3 -m tests.measure skills` runs them; `python3 -m termnl.check` warns when a skill has fewer
   than 5. A skill dropped in with its tests.md is checked like the rest.
2. **565 new "Also said" lines**, about 7 per skill, every skill. Written by another writer from the
   skill's purpose and its existing wordings, never seeing a test sentence. 51 lines that happened to equal
   a test sentence word for word were removed, so no test passes by having been taught.

The agent, the model and the trainer are untouched.

## Measured (the protocol of 26 Oct, numpy used for training as on feat/frames)

| | before | after |
|---|---|---|
| 6 old sets, handled of 595 | 534 | **553** |
| not understood | 31 | **12** |
| wrong skill offered | 28 | 28 |
| wrong action | 2 | 2 (the same two) |
| out of scope acted on, of 70 | 1 | 1 |
| the skills' own tests, handled of 462 | 378 (82%) | **403 (87%)** |
| wrong skill offered / wrong action | 43 / 1 | 36 / 0 |
| not understood | 40 | 23 |
| with a typo, still handled | 420 of 502 | 439 |
| unit tests failing | 3 | 1 (the documents test, not a skill) |
| adding 10 skills moved, of 1042 other answers | 31, 10 lost | 27, 6 lost |
| reply time | 8.6 ms | 8.5 ms |
| training here | 61 s, 1.7 MB model | 90 s, 2.2 MB model |

The gain shows on sentences nobody tuned against (the blind sets and the skills' tests), so it is not the
test sets being learnt. Training takes about half as long again, as there are 20% more sentences.

## Still not understood on the old sets (12)

everything alright? · I want to write a python script named test · I want a folder for my taxes · restart
ssh, I can't log in from my laptop · can you call seed.md something else, like garden.md · I need a second
todo.txt inside home · log me into home-5g please, the internet isnt working without it · make it quiter
please · I'd like to have gimp on this computer, can you put it on? · i need this one off the internet
https://example.net/guide.zip · call todo.txt chores.txt instead · notes in ideas

Wrong actions, unchanged: "which wifi network is this" (shows the networks around), "I want to look at
report.pdf" (finds it instead of opening it). Two of the 12 carry a reason ("…, I can't log in from my
laptop"): that is how a sentence is read, not a missing wording.

## A request said with its reason (10 lines in agent.py)

"restart ssh, I can't log in from my laptop": the whole sentence fell to a loose model guess, or to nothing,
while "restart ssh" alone is read exactly by the skill's template. Now, when a sentence isn't read surely
and has punctuation, its parts are read alone; when exactly one part is read by a template, it is the
request, asked about first since the rest was left aside. No new word list.

| | before | after |
|---|---|---|
| 6 old sets, handled of 595 | 553 | 555 |
| wrong skill offered | 28 | 27 |
| the skills' own tests, handled of 462 | 403 | 407 |
| wrong skill offered | 36 | 32 |
| wrong actions | 2 | 2 |
| adding 10 skills moved | 27, 6 lost | 26, 5 lost |
| reply time, median / slowest 5% | 8.4 / 20 ms | 8.6 / 31 ms |

8 answers changed, 7 fixed, none broken. A looser version (any one part understood, not only by a
template) fixed 2 more but offered 2 wrong skills where it used to say "I can't": not kept. Only sentences
both unsure and cut by punctuation pay the extra reading, hence the slower tail.

## Every rule re-measured with the new wordings

Do the 565 new wordings make some of the agent's rules unnecessary? Each rule switched off alone (the
switches of research/less, 02d3582, put back for the measure and taken out again), on 1,127 sentences, 567
typos and the 129 unit tests. Numbers are what turning the rule OFF changes: minus means it saves requests.

| Rule | Old sets | Skills' tests | Typos | Wrong actions | Wrong offers | Unit tests failing |
|---|---|---|---|---|---|---|
| typos read as known words | −2 | −1 | −27 | −1 | +5 | 3 |
| object words never end a name | −7 | −1 | −4 | +1 | +11 | 1 |
| a template the model doubts asks which | −1 | −4 | −1 | +5 | +1 | 1 |
| a request said with its reason (today) | −2 | −4 | −1 | 0 | +6 | 0 |
| meaning with an object | −2 | 0 | −4 | 0 | +4 | 2 |
| an object word is the object, not a name | −2 | −1 | 0 | 0 | +3 | 1 |
| a name stops before a place | 0 | −2 | 0 | +2 | 0 | 2 |
| a typo in a change asks first | 0 | 0 | 0 | +2 | −1 | 2 (162 answers act instead of asking) |
| a name never starts with a place word | 0 | −1 | 0 | 0 | +1 | 1 |
| split verbs joined | −1 | +1 | 0 | 0 | −2 | 5 (follow-ups, "turn it back off") |
| opposites | 0 | +1 | 0 | 0 | 0 | 1 ("turn the board on" never offers shut down) |
| an action said alone asks which | 0 | 0 | 0 | 0 | 0 | 2 |
| said again without the value, its default | 0 | 0 | 0 | 0 | 0 | 1 |
| an unknown name is the missing device value | 0 | 0 | 0 | 0 | 0 | 1 |
| a typo never hides a place in a name | 0 | 0 | 0 | 0 | 0 | 1 |
| a name ending in a file type is a file | 0 | 0 | 0 | 0 | 0 | 0 → **removed** (9 lines; 0 of 1,694 answers change) |

The wordings did not make the rules obsolete: every rule but one still saves sentences, prevents a wrong
action, or holds a behaviour a unit test asks for. The last four rows save no sentence; what they keep is
dialogue (a question instead of a guess) and values, which only the unit tests see.

## Does TermNL understand its own sentences?

Each skill's 1,113 "Also said" lines, heard one by one: 83 came back as another skill or a choice. 46 of
them were caught by one skill, check-type ("is there…", "do I have…"), 9 by show-type. Not because the
sentences were ignored: a slot expecting a value from a list (a file type, a folder) also takes words it
doesn't know, so it can ask "I don't see X. Which one?". In "is there a way to see if bluetooth is enabled",
check-type's {type} took "way to see if bluetooth is enabled" as an unknown file type.

**Kept (template.py, 5 lines): a value a list doesn't have is at most 3 words, never a clause.**

| | before | after |
|---|---|---|
| the skills' own sentences read as their skill, of 1,113 | 1,030 | 1,074 |
| 6 old sets, handled of 595 / wrong offers | 555 / 27 | 556 / 26 |
| the skills' tests, handled of 462 / wrong offers | 407 / 32 | 408 / 31 |
| typos, handled of 502 | 440 | 439 |
| unit tests failing | 1 | 1 (the same) |

What the test sets can't see, the values: "create a file called notes.txt in projects, I need somewhere to
jot things" asked "I don't see 'projects, I need somewhere to jot things'. Which one?"; now it reads
projects, and asks only "Do you want me to create a file?". "send an email to my boss…", out of scope, is
refused instead of asked about.

**Tried and not kept: the "Also said" lines matched as patterns.** Values made general ("fetch {name} from
the {host}"): 10 fewer requests handled, 11 more wrong offers, twice as slow, 7 unit tests broken, because
a slot takes unknown words (above), "show me {name}" swallowed "show me what's running". Word for word,
values general: still 3 fewer handled. Only the lines naming no value, word for word: 1 more handled out of
1,127, nothing worth its code. The model already learns these lines; the problem was the loose slots.
