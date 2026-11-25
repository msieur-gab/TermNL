# Brief — "Also said" sentences from a larger model

Written 24 October 2026 on the `feat/improvements` branch. The data is distilled from a large model at
training time only: nothing of it runs on the device. Its sentences are proposals; they are reviewed
before they enter a skill file, and they never enter `tests/heldout.md`, `tests/blind.md` or
`tests/probes.md`. The writer must not read those files.

## Why

23 of 37 skills have no `## Also said`: the model learns them only from their templates' own words,
so a person's other words are "new" and TermNL asks "Do you want me to…?". "Also said" is how people
really say a skill, for training only, never a rule (Gab's decision, 23 Oct).

## What to write

For each skill below, **8 sentences** a person not at ease with the terminal would type to a small Linux
board, in plain English:
- varied verbs and order ("turn the wifi off", "no more wifi", "get rid of the wifi for now");
- short ones (two or three words) and chatty ones;
- the skill's own object named in most of them, by any word people use for it;
- no typos (the agent corrects those itself), no names of real people;
- no sentence that would fit another skill of the list just as well;
- values only from the device: folders home, Documents, Downloads, ideas, projects; files note.md,
  todo.txt, report.pdf, groceries.md, seed.md; services ssh, nginx (web server), mpd (music server);
  apps terminal, firefox (browser); music Wax Tailor, Hope & Sorrow, The Tune.

Then **25 sentences for `none`**: what TermNL must not do. Above all the near misses, which look like
its skills but are not: deleting or removing files and folders, killing a process, formatting a disk,
installing, updating or upgrading software, changing a password, creating a user, moving files, changing
the volume to a level, making the screen brighter; and some everyday out-of-scope (weather, timers,
messages, smart home).

## Skills

check-storage, check-memory, check-temperature, check-system, show-system, check-network, check-wifi,
show-wifi, turn-on-wifi, turn-off-wifi, check-bluetooth, turn-on-bluetooth, turn-off-bluetooth,
check-service, restart-service, restart-system, shut-down-system, check-time, create-folder, create-file,
open-file, open-folder, leave-folder, show-folder, rename-file, rename-folder, open-app, close-app,
show-process, play-music, play-track, pause-music, stop-music, next-track, previous-track, mute-sound,
unmute-sound — each as in the skill files' `label:` line.

## Delivery

One Markdown file, `data/also-said-2026-10-24.md`, a `## <skill>` section per skill (and `## none`), one
`- sentence` per line, nothing else. Not pasted in a chat: a file keeps its form and can be read again.
