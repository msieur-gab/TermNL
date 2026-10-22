# TermLU

Talk to your Linux board in plain words. For people who aren't comfortable with the terminal.

TermLU understands a short request ("make a folder called bikes in documents"), asks for whatever is
missing, asks for approval when an action is risky, and only ever runs commands written in its skill
files. It runs offline, on the device, with no large model and no generated commands.

Every request ends in one of four outcomes: **act**, **ask**, **approve**, **abstain**.

## Layout

- `settings.md`: how much the agent may do on this device (admin mode off by default).
- `en/actions.md`, `en/objects.md`: the shared vocabulary, each word with the words people use for it.
- `en/filetypes.md`: a shared list of values.
- `en/skills/<action>-<object>/skill.md`: one skill per action + object pair: its sentences, values,
  command and replies.
- `core/`: the template reader, the skill loader and its checks, the dialogue.

## Status

Early. The exact layer (templates + shared lists + values from the device) works; the learned layer
that understands phrasings nobody wrote down is next. `node test/measure.js` shows how many of the
hand-written phrasings in `test/phrasings.md` are understood.

Playground: `node tools/build-page.js` writes `docs/index.html`, a page where you type a request and see the reply and the command it would run (served by GitHub Pages once Pages is on for `docs/`).

Run: `node core/check.js` (checks every skill file), `node --test test/*.test.js`, `node test/measure.js -v`.
