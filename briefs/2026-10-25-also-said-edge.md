# Brief — "Also said" for the edge-case skills

Written 25 October 2026 on the `feat/new-skills` branch. The data is distilled from a large model at
training time only: nothing of it runs on the device. Its sentences are proposals; they are reviewed
(`tools/merge_also_said.py`) before they enter a skill file. The writer sees only this brief: not the skill
files, not `termnl/`, not `tests/`, not the other files in `data/`.

## Why

A new skill's model learns from how people really say it. "Also said" is that, for training only, never a
rule.

## What to write

For each skill below, **8 sentences** a person not at ease with the terminal would type to a small Linux
board, in plain English:
- varied verbs and order; short ones (two or three words) and chatty ones;
- the skill's own object named in most of them, by any word people use for it;
- no typos (the agent corrects those itself), no names of real people;
- no sentence that would fit another skill of the list just as well;
- values only from the device (below).

## The skills

- show-file: list the files of one kind (images, videos, notes, PDFs) in a folder, or where you are
- check-file: say whether there is any file of one kind (a video, an image…) in a folder or here, subfolders included
- read-file: show what a text file says (its first lines)
- show-recent: list the files changed in the last day
- check-size: say how big a folder is
- show-log: show the last lines of a service's log (why it failed)
- check-usb: say which USB sticks, drives or SD cards are plugged in
- turn-up-sound: make the sound louder
- turn-down-sound: make the sound quieter
- connect-wifi: join a Wi-Fi network by its name, with its password
- unpack-file: unpack an archive (a .tar.gz) where it is
- compress-file: compress a single file into an archive beside it
- send-file: send a file from the board to another computer on the network
- get-file: bring a file from another computer on the network onto the board
- show-remote: list what is on another computer on the network

Close skills that already exist, so don't write sentences that mean them: show-folder (what a folder holds),
find-file, open-file, move-file, compress-folder, check-storage (space left on the disk), download-file
(from a web address), mute-sound, unmute-sound, turn-on-wifi, turn-off-wifi, check-network,
check-service, restart-service.

And **12 sentences for `none`**, near misses TermNL must not act on: formatting or mounting a drive,
deleting a file on another computer, changing the Wi-Fi password, forgetting a network, setting the volume
to an exact number, emailing a file, uploading to a website.

## The device

- folders: home, Documents, Downloads, ideas, projects
- files: note.md, todo.txt, report.pdf, groceries.md, seed.md, movie.mkv, setup.sh, website.html,
  scraper.py, photos.tar.gz, backup.tar.gz
- services: ssh, nginx (the web server), mpd (the music server)
- Wi-Fi networks around: home-5g, cafe-guest
- other computers on the network: laptop, studio pi

## Delivery

One Markdown file, `data/also-said-edge-2026-10-25.md`, written with the file tool, not pasted in a chat: a
`## <skill>` section per skill (and `## none`), one `- sentence` per line, nothing else.
