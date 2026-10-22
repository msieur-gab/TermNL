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

    termnl/                     the system
      languages/en/             everything English; another language is a copy of this folder
        words/                  the shared vocabulary, each word with the words people use for it
          actions.md            create, open, restart…
          objects.md            file, folder, wifi…
          filetypes.md          markdown → .md…
          conversation.md       yes, no, fillers, the rules' word lists, and TermNL's own replies
        skills/<action>-<object>/skill.md
                                one skill per action + object: its sentences, values, command or
                                reader, and replies
        out-of-scope.md         what TermNL should not try to do
        model.json              trained from the above: python3 -m termnl.train
      agent.py                  the dialogue (templates, model, questions, approval)
      readers.py                the device read in words people use (temperature, memory…)
      device.py, runner.py      the device's own lists, and running a command
      server.py                 the thin API and the chat page
    web/                        the chat page; termnl-chat.js is the chat, a component any page can hold
    tests/                      the dialogue tests, the readers, the measure on phrasings.md
    tools/neighbours.py         a test of word embeddings for unknown words (22 Oct: not worth it yet)
    settings.md                 this device's settings
    logs/                       every turn the server hears, one line of JSON (kept out of git)

## Checks

    python3 -m termnl.check             # every skill file
    python3 -m unittest                 # the dialogue and the readers
    python3 -m tests.measure -v         # how the phrasings in tests/phrasings.md are understood
    python3 -m termnl.train             # retrain termnl/languages/en/model.json
