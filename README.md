# TermNL

TERMinal Natural Language. Talk to your Linux board in plain words, for people who aren't comfortable
with the terminal.

TermNL understands a short request ("make a folder called bikes in documents"), asks for whatever is
missing, asks for approval when an action is risky, and only ever runs commands written in its skill
files. It runs offline, on the device, with no large model and no generated commands.

Every request ends in one of four outcomes: **act**, **ask**, **approve**, **abstain**.

## Try it on this machine

    python3 -m termnl.server            # http://127.0.0.1:8810

Files and folders are made in the folder `home:` names in `settings.md` (`~/TermNL-home`). Skills
listed in `simulate:` (restart, shut down, Wi-Fi, Bluetooth, services) never run here: TermNL says what
it would have done. The page's switches (show commands, admin mode) are written back to `settings.md`.

Python 3.9 or newer, standard library only. Training the model needs numpy (`python3-numpy`).

## Layout

- `settings.md`: how much TermNL may do on this device (admin mode off by default).
- `en/actions.md`, `en/objects.md`: the shared vocabulary, each word with the words people use for it.
- `en/filetypes.md`: a shared list of values. `en/answers.md`: yes, no, fillers, and the agent's own replies.
- `en/skills/<action>-<object>/skill.md`: one skill per action + object pair: its sentences, values,
  command and replies.
- `termnl/`: the brain (templates, model, dialogue), the device's own lists, the runner and the API.
- `web/`: the chat page; `web/termnl-chat.js` is the chat itself, a component any page can hold.
- `core/`, `tools/`, `docs/`: the first version, in JavaScript, and its playground. Kept until the
  Python version has replaced it; `tests/` checks the two give the same replies.

## Checks

    python3 -m termnl.check             # every skill file
    python3 -m unittest                 # the dialogue
    python3 -m tests.measure -v         # how the hand-written phrasings in tests/phrasings.md are understood
    python3 -m termnl.train             # retrain model/en.json from the skill files
