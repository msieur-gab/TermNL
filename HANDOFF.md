# Handoff — 24 October 2026, evening

Read this first, then `IMPROVEMENTS.md` and `SCALE-TEST.md` (what the merged branches did, and their open
questions), then the brain: `projects/termlu/` (decisions, design seeds, and `.inbox.md`, where today's items
wait for Gab's ratification) and `knowledge/hardware/orange-pi-zero-2w-termnl-training.md`. Gab's decisions
are his; don't rework them. The section of 22 October below is history.

## Where things stand

- **`main` holds everything.** `feat/improvements` → `feat/scale-test` → `feat/personal` were merged on
  24 Oct (Gab: "merge"; a fast-forward, c2d8d66 → 8a7f60d), then four fixes from Gab's own test on the board
  (21fcca3, c7590c3). The three branches still exist on GitHub; deleting them is Gab's call.
- **56 skills, 96 tests pass.** Since the merge: "kill pipewire" says why it can't ("“pipewire” isn't an
  app I can stop. Running now:", the running apps as chips; Gab: apps only, say why); "are you learning"
  (check learning); "what is my name" (say your name; "gab" becomes Gab); "Done learning" goes to the
  conversation that asked, as it happens (`GET /api/learning`, asked by the chat page every 5 s); "list"
  alone shows the folder (Gab's choice).
- **Scores** (`python3 -m tests.measure all`): 330 of 466 handled, 16 not understood, one wrong skill
  acted on, which only reads ("I want to look at report.pdf" finds it instead of opening it), 46 of 57 out of
  scope refused and none acted on. `main` before the merge: 282 handled, 56 not understood, one wrong
  action. Gab's real sentences (`python3 -m tests.real`, his laptop only): 104 of 117 as Claude guessed.
  The `should (Claude):` lines are guesses; Gab hasn't judged them.

## Measured on the board (Orange Pi Zero 2W, 4× Cortex-A53, 1.5 GB), 24 Oct

- **Since 26 Oct (feat/frame-self-training) training is plain Python: numpy is no longer needed.** Before:
- **Training needs numpy, and only the official wheel works.** Debian's `python3-numpy` crashes with
  "Illegal instruction"; numpy 2.5.3 from PyPI (cp313, aarch64) runs. It sits in `~/.models/shared/python`
  (downloaded on the laptop with `pip download --platform … --only-binary`, unpacked with
  `python3 -m zipfile -e`): run with `PYTHONPATH=$HOME/.models/shared/python:.`. The board has no pip, no
  venv (`ensurepip` missing), no git, and sudo asks for Gab's password.
- **Training:** 212 s for 5,446 sentences at normal priority (main before the merge: 59 s for 2,723; the
  laptop: 24 s). Through "learn what I taught you" (nice 19, two threads) 215 s, while replies stayed at
  32 ms (218 ms at most); the trainer peaks at 111 MB. Priority costs nothing; the time grows faster than
  the sentences (twice the sentences, 3.6× the time). The skill file still says "a couple of minutes".
- **Same model:** trained on the board, every weight equals the laptop's; all five test sets score the same.
- **Replies:** server ready in 0.9 s, 26–33 MB; a reply takes 29 ms typically, 150 ms at most.
- **On the board now:** `~/TermNL` is `main` (57ac4c3), used by the desk (was c2d8d66 until 24 Oct, 22:28). `~/TermNL-personal` is
  `feat/personal` before the four fixes, with Gab's test log in its `logs/`. Nothing is installed.

## Open issues, for the next instance

1. **Not seen in a browser:** the chat page waiting for "Done learning" (`web/termnl-chat.js`,
   `waitLearning`). Tested over HTTP only. Open the page in Brave (`/chrome`) and learn once.
2. **The desk (kiosk) and the companion don't have the new features.** The desk answers only `/api/say` and
   `/api/reset`: `/api/settings` and `/api/learning` aren't forwarded, `opens: "settings"` is ignored, so
   "open my settings" replies but nothing opens; "Done learning" arrives with the asker's next reply only.
   Retraining from the kiosk would fail: the desk service has no numpy on its path (`PYTHONPATH`, or numpy
   unpacked into `~/.local/lib/python3.13/site-packages`). Files: the desk's `server.py`,
   `app/js/components/app-assistant.js`; the companion's `app.js`, `index.html`, `sw.js` (bump KEPT).
   Gab's calls first: does TermNL's admin mode replace the desk's `--allow` groups? does "show commands"
   apply where the desk always shows the command? Since asked: the panel goes on both the kiosk and the
   companion (Gab, 24 Oct). Who holds admin is open, an architectural choice for Gab: he first leaned to
   the desk as master, then "perhaps the desk should not be the master, TermNL is the one talking to the
   board, desk is the GUI". Claude's recommendation, kept for that discussion (unratified): permission
   sits where the command runs, so TermNL owns admin mode; a host may only narrow it (as `simulate`:
   "never fewer") and shows TermNL's settings in its GUI. Linked to "perhaps TermNL should not even be
   visible inside the home folder" and to issue 3. Brain: `projects/termlu/.inbox.md`, 24 Oct.
   **Done on the board since:** TermNL `main` runs in the desk (logs and `tests/real.md` kept), and numpy
   is linked into `~/.local/lib/python3.13/site-packages`, so retraining from the kiosk works (3 min).
3. **The device writes tracked files.** "call me Gab" and the settings panel rewrite `settings.md`;
   retraining rewrites `termnl/languages/en/model.json`. A new copy or a `git pull` would overwrite or
   conflict with them. The person's settings and a model trained on the device need their own place,
   out of git, with the shipped files as defaults.
4. **What the retrained model moved** (none acts): "go back to the last track" and "something has hung, can
   you force quit firefox" are no longer understood; "fire up the browser" asks about closing an app; "who
   won the football game last night" reads "game" as "name" and asks about the name instead of refusing.
5. **Still open from `IMPROVEMENTS.md`** ("Open, for Gab"): should reading ask first ("what is currently
   running" asks at 73%), the plain form and the old one, the front matter's words, Claude's object list
   and the 247 sentences from a larger model to review, "start the browser…", three template over-reaches,
   `back_agent.py` (retired on 25 Oct 2026, `feat/frames`).
6. **Training time** will keep growing with skills; measure it on the board when skills are added.

## Gotchas met on 24 Oct

- `pkill -f "<pattern>"` run through `ssh … '…'` also matches the shell running it and kills it: kill by
  process number.
- Python's output through ssh is buffered: use `python3 -u`, or write to a log on the board.
- `ssh host 'nohup … &'` can keep the ssh session open: start servers with output redirected and
  `< /dev/null`, and don't wait on it.
- To reach a TermNL on the board from the laptop without opening it to the Wi-Fi:
  `ssh -f -N -L 8811:127.0.0.1:8811 <board>` (TermNL has no sign-in yet).

# Handoff — 22 October 2026, afternoon (history)

TermNL (born this morning as TermLU, from ptiLU). The design lives in Gab's brain repo, `projects/termlu/`:
read `intention.md`, `brief.md`, `decisions.md`, `review-2026-10-22.md`, both `prior-art-2026-10-22*.md`
and the `open-question-*.md` files before changing anything, and the `.inbox.md` for what Gab said today
that isn't ratified yet. Gab's decisions are his; don't rework them.

## What exists

- **Python only.** The first version in JavaScript was frozen (it gave the same replies as the Python one
  on 139 turns, commit c032e13), then deleted on Gab's request. See `README.md` for the layout.
- **The brain on the device:** `python3 -m termnl.server` serves the chat page and a thin API that takes
  sentences, never commands. Built and tested on Gab's laptop (gab-Eve); files land in `~/TermNL-home`;
  restart, shutdown, Wi-Fi, Bluetooth and services are simulated (`settings.md`, `simulate:`).
- **29 skills** in `termnl/languages/en/skills/`, one per action + object. Reading skills name a reader
  (`reads: memory`) and write a reply per level (`## When it's high`); the reader gives values, a level
  and sometimes a table. Two ways to read, both chosen by Gab on 22 Oct: the reader reads the device
  itself (memory, temperature, storage, the clock), or the skill keeps its command, which runs and is
  shown, and the reader turns its output into words (Wi-Fi, networks around, the address, Bluetooth).
  "Am I online" means connected to a network: nothing leaves the device to ask the internet.
- **Rules learned from Gab's own sentences**, each with tests (`tests/test_dialogue.py`): names never
  swallow a place; misspelled device values are confirmed; typos are read as known words only when that
  reads better, and said; names are never corrected; "not/don't" requests are asked about; approval comes
  last, with every value known; a lone yes/no with nothing waiting says so; a new name never replaces
  what's there.
- **Logs:** `logs/<date>.jsonl` holds every turn Gab typed (not in git). They are the honest test set.

- **Gab's real sentences:** `tests/real.md` (kept out of git: his typos are on purpose, and he doesn't
  want them read as misleading his model) holds his conversations from the logs, each turn with what
  TermNL should do: `should (Claude):` is a guess waiting for his word. `python3 -m tests.real -v`
  replays them; `--add` brings in new days.

Run: `python3 -m termnl.check` · `python3 -m unittest` (67 pass) · `python3 -m tests.measure -v`
(59 phrasings: 29 handled, 22 asked first, 4 wrong skill but asked, 0 wrong actions, 4 not understood:
"can I get the browser" fell under the line after retraining; Gab: leave it, you don't "get" an app;
then his 117 real turns: 95 as Claude guessed).

## Next

- `briefs/2026-10-22-clock-network-real-tests.md`: done on 22 Oct, evening.
- **A question for Gab: should reading ever ask first?** Reading changes nothing, yet "list", "threads",
  "wha time is it" ask "Do you want me to…?", and when unsure about a bare object ("wifi access", "do i
  have bluetooth") the model guesses a change and asks about it. Most differences in `tests/real.md` come
  from this. His call before building.
- `briefs/2026-10-22-model-format.md`: a lighter model and how to package it, to discuss with Gab first.
- Push to talk was tried on 22 Oct and removed: Brave's on-device speech model never downloaded, and its
  default speech service didn't work either.
