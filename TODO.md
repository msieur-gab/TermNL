# To do — parked

Gab's list of 22 October 2026. The next tasks have briefs in `briefs/`; everything below is parked until
he picks it. Nothing here is decided unless it says so. The thinking behind each item is in his brain,
`projects/termlu/` (and `.inbox.md` for what isn't ratified yet).

## Next (with a brief)

- ~~The clock, network replies in plain words, a test set from real sentences~~ → done 22 Oct, evening
- Should reading ever ask first? (see HANDOFF, Next): Gab's call
- A lighter model, and how a model should be packaged (to discuss first) →
  `briefs/2026-10-22-model-format.md`

## Needs a full session

- **Who writes a skill** (`open-question-authoring.md`). Gab: "a very interesting topic, but need a full
  session since I still believe user should be able to write their own skills", implying that all the
  @sys and @data values could be offered "in drop down or alike", and "perhaps that we rethink the
  grammar". The template grammar works, but people can't write it today.

## Parked

- **What runs when TermNL reads** (`open-question-reading-commands.md`: /proc in Python, the skill's
  command, or both). Gab: it "reveals perhaps a confusion that should be addressed in another session".
- **A layer for where information comes from:** `@sys` for the machine, and something like `@data` or
  `@src.articles` for what people keep (articles, notes, memos): "what's in my articles", "anything about
  wifi in my notes". Possibilities only; the saved articles already have a MiniLM decision in the desk
  (Symbiot) project, `projects/desk/decisions.md`, 15–16 Oct.
- **TermNL in Symbiot:** replacing ptiLU, and reaching the board from the phone companion without a
  screen. Pairing and security come with it.
- **A connector:** TermNL installs anywhere on its own; with Symbiot, one merged index. Method open.

## Not placed yet

- **Connecting to a network** ("connect to wonderland", Gab's test of 22 Oct): no skill yet.
- **A dataset as a takeaway** (Gab, 22 Oct): one day, sentences people can reuse to train their own model,
  apart from his private logs.
- **Speaking to TermNL:** push to talk through the browser failed in Brave (22 Oct); something local, like
  sherpa-onnx, stays possible.

- **The learning loop.** A "yes" returns `teach`; nothing saves it. Decided (Gab): learning goes to an
  inbox the person reviews, then "live training" on the device. It needs "no, I meant another skill" and
  "this is new", which depends on who writes skills.
- **Shared words in two families:** "start" (create + open), "note" (file + markdown).
- **No "undo"**, no Dialogflow-style context.
- **Further cuts in `agent.py`** mean removing behaviour (for example "not here, but in Documents"):
  Gab's call. `back_agent.py` and `tests.compare_agents` keep the two versions in step.
- **Word embeddings for unknown words:** tested 22 Oct, not worth it now (GloVe-50: 3 useful neighbours
  of 26; opposites side by side). Model2Vec could be tried with `tools/neighbours.py`.
