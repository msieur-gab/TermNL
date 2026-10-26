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
