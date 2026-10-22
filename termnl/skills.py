"""Reads skill files and the shared lists, and checks them. A skill is one action + object pair:

  ---
  does: create file
  admin: no          needs admin rights (only runs with admin mode on, after approval)
  approve: no        always asks for approval first (destructive, or cuts a connection)
  moves: place       after it runs, you are in that folder (open folder)
  reads: memory      a skill that only reads: the device reads itself (readers.py), no command;
                     or a reader of its command's output (reads: wifi, with nmcli in ## Command)
  ---
  ## Sentences       templates (template.py), each in `backticks` so <action> and
                     <object> show as written on GitHub instead of vanishing as HTML tags
  ## Values          - name: kind[, required][, new][, default: x]
                       new: must not exist yet in the place (create file); default: here = where you are
                       @sys.file: a file that must exist, found in the place or anywhere in home
  ## Command         one line; {value} is filled in and quoted
  ## Replies         - key: variant | variant
  ## When it's high  (a reading skill) one reply per line, for when the reader says "high"; the
                     reader's values are written {@sys.memory.used}, the person's name {user}

Kinds: text, secret, a shared list (filetype), or a device list (@sys.folder, @sys.service,
@sys.network, @sys.app)."""
import re

from .readers import FROM_COMMAND, READERS, placeholder
from .template import compile_template, uses
from .text import read_list, read_pairs, words

DEVICE_KINDS = ["folder", "file", "service", "network", "app", "running"]


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
    answers = {e["key"]: [words(w) for w in e["words"]] for e in read_list(files["conversation"])}
    replies = {e["key"]: e["rest"] for e in read_list(files["conversation"], "Replies")}
    samples = {e["key"]: e["words"] for e in read_list(files["samples"])}
    # every "- name: words" line of readings.md, whatever its section
    readings = {m.group(1).strip(): m.group(2).strip() for m in re.finditer(r"^- ([^:]+):\s*(.*)$", files["readings"], re.M)}
    return {"samples": samples, "readings": readings, "refs": refs, "actions": kinds["actions"], "objects": kinds["objects"], "filetypes": filetypes,
            "conversation": answers, "replies": replies}


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
    return {"id": id, "does": meta.get("does", ""), "label": meta.get("label") or meta.get("does") or id,
            "admin": yes("admin"), "approve": yes("approve"), "moves": meta.get("moves", ""), "reads": meta.get("reads", ""), "when": when,
            "sentences": sentences, "values": values, "command": command, "replies": replies}


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
    used = set()
    skill["compiled"] = []
    for s in skill["sentences"]:
        try:
            nodes = compile_template(s)
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
                    for m in re.finditer(r"\{([\w@.]+)\}", l):
                        if m.group(1) not in known:
                            say("""## When it's %s uses {%s}; the %s reader gives %s""" % (level, m.group(1), skill["reads"], ", ".join("{%s}" % k for k in sorted(known))))
        if skill["reads"] in FROM_COMMAND and not skill["command"]:
            say("the %s reader reads what a command says: the skill needs a ## Command" % skill["reads"])
        elif skill["reads"] not in FROM_COMMAND and skill["command"]:
            say("the %s reader reads the device itself: the skill has no command" % skill["reads"])
    elif "done" not in skill["replies"]:
        say('no "done" reply')
    if (skill["admin"] or skill["approve"]) and "approve" not in skill["replies"]:
        say('needs approval but has no "approve" reply')
    for key, text in skill["replies"].items():
        for m in re.finditer(r"\{(\w+)\}", text):
            if m.group(1) not in skill["values"] and m.group(1) != "output":
                say('reply "%s" uses {%s}, which is no value' % (key, m.group(1)))
    return errs


def load(list_files, skill_files):
    lists = read_lists(list_files)
    skills, errors = [], []
    for id, md in skill_files.items():
        s = read_skill(id, md)
        errors.extend(check(s, lists))
        skills.append(s)
    does = {}
    for s in skills:
        if s["does"] in does:
            errors.append('%s: "does: %s" is also %s' % (s["id"], s["does"], does[s["does"]]))
        does[s["does"]] = s["id"]
    return {"lists": lists, "skills": skills, "errors": errors}
