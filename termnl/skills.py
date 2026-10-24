"""Reads skill files and the shared lists, and checks them. A skill is one action + object pair:

  ---
  does: create file
  admin: no          needs admin rights (only runs with admin mode on, after approval)
  approve: no        always asks for approval first (destructive, or cuts a connection)
  moves: place       after it runs, you are in that folder (open folder)
  reads: memory      a skill that only reads: the device reads itself (readers.py), no command;
                     or a reader of its command's output (reads: wifi, with iw in ## Command)
  ---
  ## People say     plain sentences (plain.py): a word for the action or object stands for all its
                     words, a/b one of these words, ( ) may be left out, {value} a value
  ## Sentences       or, the older form: templates (template.py), each in `backticks` so <action> and
                     <object> show as written on GitHub instead of vanishing as HTML tags
  ## Also said       how people say it, in plain sentences: for training only, never a rule (Gab's
                     log, 23 Oct: "what is consuming my ram", "chip temperature")
  ## What it needs  - {place}: a folder on the device. If it's not said: where you are. (words/values.md)
  ## Values          or, the older form: - name: kind[, required][, new][, default: x]
                       new: must not exist yet in the place (create file); default: here = where you are
                       @sys.file: a file that must exist, found in the place or anywhere in home
  ## Command         one line; {value} is filled in and quoted
  ## Replies         - key: variant | variant
  ## When it's high  (a reading skill) one reply per line, for when the reader says "high"; the
                     reader's values are written {@sys.memory.used}, the person's name {user}

Kinds: text, secret, a shared list (filetype), or a device list (@sys.folder, @sys.service,
@sys.network, @sys.app, @sys.music)."""
import re

from .readers import FROM_COMMAND, READERS, placeholder
from .plain import read_needs, to_template
from .template import compile_template, uses
from .text import read_list, read_pairs, words

DEVICE_KINDS = ["folder", "file", "service", "network", "app", "running", "music"]


def read_lists(files):
    refs, kinds = {}, {"actions": [], "objects": []}
    for name in ("actions", "objects"):
        for e in read_list(files[name]):
            refs[e["key"]] = [words(w) for w in e["words"]]
            kinds[name].append(e["key"])
    filetypes = []
    for e in read_list(files["filetypes"]):
        m = re.match(r"^(.+?)\s*\((\w+)\)$", e["key"])
        value = m.group(1).strip() if m else e["key"]
        filetypes.append({"value": value, "ext": m.group(2) if m else value, "label": value, "phrases": [words(w) for w in e["words"]]})
    # "- music, track: turn on, switch on → play": words that mean another action with these objects
    in_context = []
    for e in read_list(files["actions"], "Meaning with an object"):
        said, _, action = e["rest"].partition("→")
        in_context.append({"objects": [o.strip() for o in e["key"].split(",") if o.strip()], "action": action.strip(),
                           "phrases": [words(w) for w in said.split(",") if w.strip()]})
    opposites = {e["key"]: set(e["words"]) for e in read_list(files["actions"], "Opposites")}
    topics = [(e["key"], e["words"]) for e in read_list(files["objects"], "Topics")]  # how help groups the skills
    answers = {e["key"]: [words(w) for w in e["words"]] for e in read_list(files["conversation"])}
    replies = {e["key"]: e["rest"] for e in read_list(files["conversation"], "Replies")}
    samples = {e["key"]: e["words"] for e in read_list(files["samples"])}
    # every "- name: words" line of readings.md, whatever its section
    readings = {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r"^- ([^:]+):\s*(.*)$", files["readings"], re.M)}
    return {"samples": samples, "readings": readings, "refs": refs, "actions": kinds["actions"], "objects": kinds["objects"], "filetypes": filetypes,
            "conversation": answers, "replies": replies, "in_context": in_context, "opposites": opposites, "topics": topics, "values_md": files.get("values", "")}


def section(md, name):
    lines = md.split("\n")
    at = next((i for i, l in enumerate(lines) if l.strip().lower() == "## " + name.lower()), -1)
    if at < 0:
        return None
    end = next((i for i, l in enumerate(lines) if i > at and l.startswith("## ")), None)
    return lines[at + 1:end]


def read_skill(id, md):
    front = md[3:md.find("\n---", 3)] if md.startswith("---") else ""
    meta = read_pairs(front)
    sentences = [re.sub(r"^`(.*)`$", r"\1", l[2:].strip()) for l in (section(md, "Sentences") or []) if l.startswith("- ")]
    people = section(md, "People say")  # plain sentences (plain.py), the proposal of 24 Oct 2026
    plain = people is not None
    if plain:
        sentences = [l[2:].strip() for l in people if l.startswith("- ")]
    values = {}
    for e in read_list(md, "Values"):
        parts = e["words"]
        v = {"kind": parts[0] if parts else "text", "required": False}
        for p in parts[1:]:
            if p == "required":
                v["required"] = True
            elif p == "new":
                v["new"] = True
            elif p.startswith("default:"):
                v["default"] = p[8:].strip()
        values[e["key"]] = v
    also = [re.sub(r"^`(.*)`$", r"\1", l[2:].strip()) for l in (section(md, "Also said") or []) if l.startswith("- ")]
    command = next((c for c in (re.sub(r"^`+|`+$", "", l.strip()) for l in (section(md, "Command") or []))
                    if c and not c.startswith("#")), "")
    replies = {e["key"]: e["rest"] for e in read_list(md, "Replies")}
    when, at = {}, None
    for line in md.split("\n"):
        m = re.match(r"^## when (?:it's|it is) (.+?)\s*$", line.strip(), re.I)
        if m:
            at = when.setdefault(m.group(1).lower(), [])
        elif line.startswith("## "):
            at = None
        elif at is not None and line.startswith("- "):
            at.append(line[2:].strip())
    yes = lambda k: bool(re.match(r"^yes$", meta.get(k, ""), re.I))
    # "changes: admin mode to on": a skill that changes a setting (settings.md) instead of running a command
    m = re.match(r"^(.+?)\s+to\s+(.+)$", meta.get("changes", "").strip())
    changes = (m.group(1).strip().lower(), m.group(2).strip()) if m else None
    return {"id": id, "does": meta.get("does", ""), "label": meta.get("label") or meta.get("does") or id,
            "admin": yes("admin"), "approve": yes("approve"), "moves": meta.get("moves", ""), "reads": meta.get("reads", ""), "when": when,
            "sentences": sentences, "also": also, "values": values, "command": command, "replies": replies,
            "plain": plain, "needs": section(md, "What it needs"), "changes": changes,
            "opens": meta.get("opens", "").strip(), "lists": meta.get("lists", "").strip(), "trains": meta.get("trains", "").strip()}


def check(skill, lists):
    """Problems that stop a skill from working, as "skill: reason" lines. Empty means fine."""
    errs = []
    say = lambda msg: errs.append("%s: %s" % (skill["id"], msg))
    # does: "<action> <object>"; an action may be two words (turn off, shut down)
    does = skill["does"]
    found = sorted((a for a in lists["actions"] if does == a or does.startswith(a + " ")), key=len, reverse=True)
    action = found[0] if found else None
    obj = does[len(action):].strip() if action else ""
    skill["action"], skill["object"] = action, obj
    if not does:
        say("no does: line")
    elif not action:
        say('does: "%s" starts with no action from words/actions.md' % does)
    elif obj not in lists["objects"]:
        say('unknown object "%s" (words/objects.md)' % obj)
    if not skill["sentences"]:
        say("no sentences")
    if skill.get("needs") is not None:  # ## What it needs, in words from words/values.md
        values, asks, problems = read_needs(skill["needs"], lists.get("values_md", ""))
        skill["values"].update(values)
        skill["replies"].update(asks)
        for p in problems:
            say(p)
    used = set()
    skill["compiled"] = []
    for s in skill["sentences"]:
        try:
            nodes = compile_template(to_template(s, lists, (action, obj)) if skill.get("plain") else s)
            skill["compiled"].append(nodes)
            u = uses(nodes)
            for r in sorted(u["refs"]):
                if r not in lists["refs"]:
                    say('<%s> is not an action or object, in "%s"' % (r, s))
            for v in sorted(u["slots"]):
                used.add(v)
                if v not in skill["values"]:
                    say('{%s} is not declared in ## Values, in "%s"' % (v, s))
        except ValueError as e:
            say(str(e))
    for name, v in skill["values"].items():
        k = v["kind"]
        known = k in ("text", "secret", "filetype") or (k.startswith("@sys.") and k[5:] in DEVICE_KINDS)
        if not known:
            say('value %s: unknown kind "%s"' % (name, k))
        if v["required"] and not v.get("default") and ("ask " + name) not in skill["replies"]:
            say('value %s is required but has no "ask %s" reply' % (name, name))
        in_replies = any("{%s}" % name in l for lines in skill["when"].values() for l in lines)
        if name not in used and ("{%s}" % name) not in skill["command"] and not in_replies:
            say("value %s is used by no sentence, no command and no reply" % name)
    for m in re.finditer(r"\{(\w+)\}", skill["command"]):
        if m.group(1) not in skill["values"]:
            say("command uses {%s}, not declared" % m.group(1))
    if skill.get("changes") and skill["changes"][0] in ("admin mode", "simulate", "home"):
        # a safety: what TermNL may do on the device is never changed by a sentence, only in the settings panel
        say("%s can only be changed in the settings panel, not by a skill" % skill["changes"][0])
    if skill.get("changes") and skill["command"]:
        say("a skill changes a setting or runs a command, not both")
    for m in re.finditer(r"\{(\w+)\}", skill["changes"][1] if skill.get("changes") else ""):
        if m.group(1) not in skill["values"]:
            say("changes: uses {%s}, not said under What it needs" % m.group(1))
    if skill["reads"]:
        reader = READERS.get(skill["reads"])
        if not reader:
            say('reads: "%s" is no reader (termnl/readers.py: %s)' % (skill["reads"], ", ".join(READERS)))
        else:
            _, levels, names = reader
            known = {placeholder(skill["reads"], n) for n in names} | {"user"} | set(skill["values"])
            for level in levels:
                if level != "unknown" and not skill["when"].get(level):
                    say("""no "## When it's %s" replies""" % level)
            for level, lines in skill["when"].items():
                if level not in levels:
                    say("""## When it's %s: the %s reader says %s""" % (level, skill["reads"], ", ".join(levels)))
                for l in lines:
                    if " | " in l:  # each line is one reply, said whole (24 Oct: "You're Gab. | Your name is Gab.")
                        say("## When it's %s: one reply per line, without \" | \"" % level)
                    for m in re.finditer(r"\{([\w@.]+)\}", l):
                        if m.group(1) not in known:
                            say("""## When it's %s uses {%s}; the %s reader gives %s""" % (level, m.group(1), skill["reads"], ", ".join("{%s}" % k for k in sorted(known))))
        if skill["reads"] in FROM_COMMAND and not skill["command"]:
            say("the %s reader reads what a command says: the skill needs a ## Command" % skill["reads"])
        elif skill["reads"] not in FROM_COMMAND and skill["command"]:
            say("the %s reader reads the device itself: the skill has no command" % skill["reads"])
    elif skill.get("trains") and skill["trains"] != "the model":
        say('trains: "%s" — a skill can only train the model' % skill["trains"])
    elif skill.get("lists") and skill["lists"] != "skills":
        say('lists: "%s" — a skill can only list skills' % skill["lists"])
    elif "done" not in skill["replies"]:
        say('no "done" reply')
    if (skill["admin"] or skill["approve"]) and "approve" not in skill["replies"]:
        say('needs approval but has no "approve" reply')
    for key, text in skill["replies"].items():
        for m in re.finditer(r"\{(\w+)\}", text):
            if m.group(1) not in skill["values"] and m.group(1) not in ("output", "user"):
                say('reply "%s" uses {%s}, which is no value' % (key, m.group(1)))
    return errs


def load(list_files, skill_files):
    lists = read_lists(list_files)
    skills, errors = [], []
    for id, md in skill_files.items():
        s = read_skill(id, md)
        errors.extend(check(s, lists))
        skills.append(s)
    for c in lists["in_context"]:
        where = "words/actions.md, Meaning with an object"
        if c["action"] not in lists["actions"]:
            errors.append('%s: "%s" is not an action' % (where, c["action"]))
        for o in c["objects"]:
            if o not in lists["objects"]:
                errors.append('%s: "%s" is not an object' % (where, o))
        if not c["phrases"]:
            errors.append("%s: a line for %s has no words before →" % (where, ", ".join(c["objects"])))
    for a, opp in lists["opposites"].items():
        for b in {a} | opp:
            if b not in lists["actions"]:
                errors.append('words/actions.md, Opposites: "%s" is not an action' % b)
    does, said = {}, {}
    for s in skills:
        if s["does"] in does:
            errors.append('%s: "does: %s" is also %s' % (s["id"], s["does"], does[s["does"]]))
        does[s["does"]] = s["id"]
        for a in s["also"]:  # one sentence teaching two skills would teach neither
            key = " ".join(words(a))
            if key in said and said[key] != s["id"]:
                errors.append('%s: "%s" is also said for %s' % (s["id"], a, said[key]))
            said[key] = s["id"]
    return {"lists": lists, "skills": skills, "errors": errors}
