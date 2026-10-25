# Brief — blind test sentences for the edge-case skills

Written 25 October 2026 on the `feat/new-skills` branch (RESEARCH.md: testing method F, "real words aren't
typos", with skills whose words sit close to everyday English). The writer sees only this brief: not the
skill files, not `termnl/`, not any other file in `tests/`, not `data/`. The sentences are frozen once
written: none of them ever enters a skill file. They judge; they don't teach.

## Who types them

A person not at ease with the terminal, typing to a small Linux board (an Orange Pi) from a chat page on
their phone or laptop. Plain English, sometimes chatty, sometimes two words.

## The skills (name: what it does)

New:
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

Already there, close to the new ones:
- show-folder: list what a folder holds
- find-file: find where a file is, by (part of) its name
- open-file: open a file
- move-file: move a file to another folder
- compress-folder: compress a folder
- check-storage: say how much disk space is left
- download-file: download a file from a web address
- mute-sound / unmute-sound: cut the sound / bring it back
- turn-on-wifi / turn-off-wifi: switch Wi-Fi on or off
- check-network: say whether the board is online, and its address
- check-service / restart-service: is a service running / restart it
- delete-file: delete a file
- shut-down-system: shut the board down

## The device (use only these values)

- folders: home, Documents, Downloads, ideas, projects
- files: note.md, todo.txt, report.pdf, groceries.md, seed.md, movie.mkv, setup.sh, website.html,
  scraper.py, photos.tar.gz, backup.tar.gz
- services: ssh, nginx (the web server), mpd (the music server)
- Wi-Fi networks around: home-5g, cafe-guest
- other computers on the network: laptop, studio pi
- music: Wax Tailor, Hope & Sorrow, The Tune

## What to write

- **4 sentences per new skill** (60), varied verbs, order and length.
- **2 per close existing skill** (24).
- **Edge sentences, 30, each labelled with the skill it means:** this test is about words.
  - 10 with a **typo that happens to be a real English word**: "lunch the browser" (launch), "sing the
    file to my laptop" (send), "show me my fills" (files), "make the sound louder, its to quite" — a real
    word typed for the intended one. Pick the words yourself; don't reuse these examples.
  - 10 with **another form of a word**: plurals and verb forms ("show my photos", "unpacking backup.tar.gz",
    "compressed report.pdf please", "the logs of nginx").
  - 10 with **real words one letter from the skills' own words**, used in their own meaning, that must
    NOT be read as that word: "movie" (not move), "film" (not file), "remote" (not remove), "count" (not
    mount), "wait"/"want", "click"/"clock". Label each with the skill the whole sentence really means, or
    `none` if no skill fits.
- **Out of scope, 20, labelled `none`:** near misses TermNL must not act on (format the USB stick, mount a
  drive, delete a remote file, change the Wi-Fi password, set the volume to an exact number, forget a
  network, unzip a .zip from the web, upload to a website, email a file) and some everyday ones (weather,
  football, a timer, a recipe).

No sentence should fit two skills equally well. No names of real people.

## Delivery

One Markdown file, `tests/edge-blind.md`, written with the file tool, not pasted in a chat. It starts with:

    # Edge cases, blind — never trained on, never tuned against

    Written on 25 Oct 2026 by an agent that saw only skill names and purposes
    (briefs/2026-10-25-edge-skills-blind.md). `python3 -m tests.measure edge-blind`.

then one line per sentence, `- <skill>: <sentence>` (for example `- check-usb: is my usb stick plugged in`),
grouped with a blank line between groups, nothing else.
