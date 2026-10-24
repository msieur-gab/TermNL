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

## Said in words: your name and your settings

"call me Gab", "show me the commands", "hide the commands": each changes its line in `settings.md`. A skill does
this with `changes: show commands to on` in its header instead of a command. Admin mode is never changed by a
sentence (the checker refuses a skill that tries): "open my settings" opens the settings panel, where it is a
toggle beside the commands and your name. "help" lists what TermNL can do, by the topics in
`words/objects.md`.

"learn what I taught you" (approved first) trains the model again from the skill files, in the background, at
the lowest priority and on two threads: the board stays usable, and the next reply says when it is done. The
model in use is replaced only once the new one is whole; the one before is kept as `model.previous.json`. Replies can say `{user}`: "Hey {user}, no problem: your CPU is at…"; a variant
with `{user}` is only used once a name is set.

## Layout

    termnl/                     the system
      languages/en/             everything English; another language is a copy of this folder
        words/                  the shared vocabulary, each word with the words people use for it
          actions.md            create, open, restart…, and what a word means with an object
                                ("turn on the music" plays it)
          objects.md            file, folder, wifi…
          filetypes.md          markdown → .md…
          conversation.md       yes, no, fillers, the rules' word lists, and TermNL's own replies
          samples.md            sample values the model trains with
          readings.md           the words shown with what the device reads (tables, "3 days")
          values.md             how a skill says what it needs ("a folder on the device")
        skills/<action>-<object>/skill.md
                                one skill per action + object, written in plain sentences: what people
                                say, what it needs, its command or reader, and replies (plain.py;
                                IMPROVEMENTS.md says how to write one)
        out-of-scope.md         what TermNL should not try to do
        model.json              trained from the above: python3 -m termnl.train
      agent.py                  the dialogue: one turn in five steps (templates, model, questions, approval)
      back_agent.py             the version before, same behaviour, kept for comparison (python3 -m
                                termnl.server --agent back); tests/compare_agents.py checks they agree
      plain.py                  plain sentences and "What it needs" read into what the agent uses
      readers.py                the device read in words people use (temperature, memory…)
      device.py, runner.py      the device's own lists, and running a command
      server.py                 the thin API and the chat page
    web/                        the chat page; termnl-chat.js is the chat, a component any page can hold
    tests/                      the dialogue tests, the readers, the measure on phrasings.md, and
                                real.py: the conversations people really had (real.md, from logs/,
                                kept out of git), replayed against today's TermNL
    tools/neighbours.py         a test of word embeddings for unknown words (22 Oct: not worth it yet)
    tools/to_plain.py           rewrites a skill from the older template form to plain sentences;
    tools/same_reading.py       and proves it reads every sentence the same
    settings.md                 this device's settings
    logs/                       every turn the server hears, one line of JSON (kept out of git)

## Checks

    python3 -m termnl.check             # every skill file
    python3 -m unittest                 # the dialogue and the readers
    TERMNL_AGENT=termnl.back_agent python3 -m unittest   # the same tests, for back_agent
    python3 -m tests.compare_agents     # agent and back_agent, reply by reply, on tests and logs
    python3 -m tests.measure -v         # how the phrasings in tests/phrasings.md are understood
    python3 -m tests.measure all        # and tests/probes.md, heldout.md and blind.md (never trained on)
    python3 -m tests.real -v            # the real conversations in tests/real.md, turn by turn
    python3 -m tests.real --add         # adds the conversations in logs/ that real.md doesn't hold yet
    python3 -m termnl.train             # retrain termnl/languages/en/model.json
