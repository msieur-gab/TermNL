# Scale test — the `feat/scale-test` branch

24 October 2026, from `feat/improvements`. Gab: "shall we try adding skills not available yet and evaluate
how it scales?" The skills were proposed first and chosen together. Gab's rule for every command: "all
command we add to TermNL should be default linux command found on any device running linux, or pi like
boards". He added "reboot, turn off the board, restart the board" to stress.

## In short

- **Before the new skills existed, TermNL never acted on them.** 56 blind requests: 27 refused, 29 asked
  about another skill, none acted on.
- **11 skills added, 37 → 48.** No wrong action on the new skills. In the older sets, one sentence is now
  acted on by a new skill that took over its word (below), and a few moved from "handled" to "asked first"
  or "wrong skill, asked" (blind: 4 → 7); more were gained elsewhere (held-out: 109 → 113 handled).
- **What scales a skill is the sentences it learns from, not its grammar.** With only what an author
  writes, the new skills understood 21 of 44 blind requests; with "Also said" from a larger model, 35.
- **Gab's power sentences** all work; testing them found two gaps, fixed with readable lists in
  `words/actions.md`.
- **Cost:** model 663 → 895 KB, training 11 → 24 s, understanding a sentence about 20% slower (median
  2.8 → 3.5 ms on the laptop, slowest 19 → 30 ms). Roughly in step with the number of skills. Not measured
  on the board.

## The skills

| Skill | Command | Asks first |
|---|---|---|
| move-file | `mv` | no |
| copy-file | `cp` | no |
| delete-file, delete-folder | `mv` into `~/.local/share/Trash/files` (a desktop's trash: can be brought back) | approval |
| find-file | `find $HOME -iname` | no |
| install-app | `apt-get install` | admin + approval |
| update-system | `apt-get update && apt-get upgrade` | admin + approval |
| stop-process | `pkill -9` (for a stuck program; close app closes normally) | approval |
| check-uptime | `uptime -p` | no |
| compress-folder | `tar -czf` | no |
| download-file | `wget` | no |

Set aside with Gab: joining a Wi-Fi network (no default command joins a password network on every board)
and the volume (`pactl` and `amixer` aren't on every board). Kept with a caveat: `apt-get` is default on
Debian-family boards only, `wget` on most images but not every minimal one. Not changed: the existing mute
and music skills use `pactl` and `mpc`, which Gab's rule would not allow.

## Tests

`tests/scale-blind.md`, written by a fresh agent from the skill names only, before the skills existed:
4 sentences per new skill, 2 per close existing skill, 12 + 16 for Gab's power sentences (6 reboot,
6 shut down, 4 out of scope such as "turn the board on"), and out-of-scope sentences. The 12 sentences
for Wi-Fi joining and volume were relabelled out of scope when those skills were dropped. In the older
sets, 11 out-of-scope sentences became in scope ("install vlc", "remove todo.txt"…); their labels were
changed before any skill was written. "erase everything in Downloads", "kill the process with id 4312"
and "delete all my files" stay out of scope.

## Results

Each cell: handled / checked first / wrong skill, but asked or stopped / **wrong skill acted on** / not
understood.

| Scale set, by group | Before (37 skills) | A. Skills as an author writes them | B. + Also said, power fixes |
|---|---|---|---|
| New skills (44) | 0/0/23/**0**/21 | 11/10/10/**0**/13 | 12/23/3/**0**/6 |
| Close existing skills (22) | 15/6/0/**0**/1 | 15/7/0/**0**/0 | 14/8/0/**0**/0 |
| Gab's power sentences (14) | 6/7/1/**0**/0 | 6/7/1/**0**/0 | 6/7/1/**0**/0 |
| Out of scope (28): refused / asked / **acted** | 20/8/**0** | 19/9/**0** | 20/8/**0** |

| Older sets | Before | After |
|---|---|---|
| phrasings (59) | 42/14/2/**0**/1 | 41/15/2/**0**/1 |
| probes (89 + 4) | 74/5/8/**0**/2 | 76/4/6/**0**/3 |
| held-out (122 + 10) | 109/6/4/**0**/3 | 113/6/3/**0**/0 |
| blind (116 + 15) | 67/39/4/**0**/6 | 69/35/7/**1**/4 |

88 unit tests pass (one new: the power sentences).

## What the test found

1. **A new skill can take a word from an older one.** "I want to look at report.pdf" now searches for the
   file instead of opening it: find file's sentences taught "look". Harmless here (a search changes
   nothing) and not patched, as it was found on the blind set. Adding a skill means watching the skills
   whose words it shares.
2. **"turn the board on" offered to shut the board down.** The model hears "turn" and "board" more than
   "on". A first fix, "an action said is never answered with another", cost six sentences understood
   before (one through a typo fix, "last" read as "list"). Kept instead: **Opposites** in
   `words/actions.md` ("turn on: turn off, shut down", "play: stop, pause"…). It costs nothing measured.
3. **"turn off" alone didn't offer shutting the board down.** One line in Meaning with an object:
   "system: turn off, switch off → shut down".
4. **Adding a skill touches more than its folder:** 7 new actions and 2 words for *stop* ("kill", "force
   quit"), 1 object (uptime), 2 kinds of value
   ("a program name", "a web address"), and 5 lines out of `out-of-scope.md` that now contradicted a skill.
5. **The plain form held up for 11 new skills,** with one trap: "make a copy of {name}" reads "make" as
   *create* (it still works, but trains on odd sentences such as "add a copy of"). The checker could warn
   when a sentence holds another skill's action.
6. **3 proposed sentences were read by other skills' templates** and kept out: "download and install vlc",
   "install the updates please", "get rid of the downloads folder and everything in it".
7. **A typo fix corrects real words:** "last" is read as "list". Not changed.

## Tools added

- `tools/merge_also_said.py data/<file>.md`: reviews proposed "Also said" sentences (test sentences,
  duplicates, other skills' templates) and adds the rest to the skill files. The step a new skill takes.
- `tools/speed.py`: how long a sentence takes, on the same 415 sentences each time.

## How to check

    python3 -m termnl.check && python3 -m unittest
    python3 -m tests.measure all
    python3 -m tools.speed
