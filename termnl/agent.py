"""The dialogue. Every request ends in one of four outcomes:
  act      understood, everything known, nothing to approve: the command is ready to run
  ask      a value is missing or isn't on the device, or the request isn't surely understood:
           a question, with chips when there are choices
  approve  the action is destructive or needs admin rights: the person approves first
  abstain  nothing understood, or the settings don't allow it: the agent says so

Understanding comes in two layers:
  1. a skill's templates, when one reads the sentence exactly (values read precisely);
  2. the model, which recognises the action and the object in any wording, with values found by
     their own readers. It acts only when it is sure and knows every word; otherwise it asks
     "Do you want me to …?", naming the words it doesn't know yet.

The agent never runs anything and never writes a command: it fills in the command a skill
declares, with every value quoted. Running it is the device's job (runner.py)."""
import random as _random
import re

from .model import classify
from .template import best, parses
from .text import close, fill, pick, tokenize, words


def sq(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def quote(p):
    """a path's leading $HOME stays outside the quotes, so the shell still expands it"""
    if p.startswith("$HOME"):
        return "$HOME" + (sq(p[5:]) if len(p) > 5 else "")
    return sq(p)


# how sure the model must be of its action × object pair: to act, and to ask at all
SURE, MAYBE = 0.5, 0.15


class Agent:
    def __init__(self, lists, skills, model=None, settings=None, device=None, random=_random.random, **_):
        self.lists, self.skills, self.model = lists, skills, model
        self.settings = settings if settings is not None else {}
        self.device, self.random = device, random
        self.pending = None
        self._here = None  # where you are, like a terminal's working folder: home at first
        self.last = None
        answers = lists["answers"]
        joined = lambda key: {" ".join(p) for p in answers.get(key, [])}
        self.small = joined("small words")
        self.stops = joined("not a name start")
        self.pointing = joined("pointing words")
        self.places = joined("before a place")
        self.reading = joined("reading actions")
        self.object_words = {ph[0] for o in lists["objects"] for ph in lists["refs"].get(o, []) if len(ph) == 1}

    # ---- the device, the settings, the lists

    @property
    def here(self):
        if self._here:
            return self._here
        h = next((f for f in self.sys("folder") if f["value"] == "$HOME"), None)
        return {"value": h["value"], "label": h["label"]} if h else {"value": "$HOME", "label": "home"}

    def on(self, key):
        return bool(re.match(r"^(on|yes|true)$", self.settings.get(key) or "", re.I))

    def sys(self, kind):
        return [{"value": d["value"], "label": d["names"][0], "phrases": [words(n) for n in d["names"]]}
                for d in (self.device.list(kind) if self.device else [])]

    def list_of(self, kind):
        """files aren't a list read in advance: they are looked up in the place once it is known"""
        if kind == "filetype":
            return self.lists["filetypes"]
        if kind == "@sys.file":
            return None
        if kind.startswith("@sys."):
            return self.sys(kind[5:])
        return None

    def slot_lists(self, skill):
        return {k: self.list_of(v["kind"]) for k, v in skill["values"].items()}

    def reply(self, key, values=None):
        return fill(pick(self.lists["replies"].get(key) or key, self.random), values or {})

    def only_points(self, v):
        """"this", "that file": a value that only points can't be known here, so it is asked for instead"""
        return v.get("text") is not None and v.get("value") is None and all(t["word"] in self.pointing for t in tokenize(v["text"]))

    def is_(self, toks, key):
        return any(len(ph) == len(toks) and all(toks[i]["word"] == w for i, w in enumerate(ph))
                   for ph in self.lists["answers"].get(key, []))

    @staticmethod
    def original(text, toks, start, end):
        return text.translate(str.maketrans({"’": "'", "‘": "'", "`": "'"}))[toks[start]["start"]:toks[end - 1]["end"]]

    def negation(self, toks):
        """the negation words said ("not", "don't"…), as written in en/answers.md"""
        said = []
        for ph in self.lists["answers"].get("negation", []):
            for i in range(len(toks) - len(ph) + 1):
                if all(toks[i + j]["word"] == w for j, w in enumerate(ph)):
                    said.append(" ".join(ph))
        return said

    def chips(self, found):
        return [o["label"] for o in found][:8] if found else []

    # ---- understanding

    def clean(self, text):
        """Fillers ("please", "can you", "for me") are dropped at the start and end of a sentence."""
        toks = tokenize(text)
        starts = self.lists["answers"].get("filler start", [])
        ends = self.lists["answers"].get("filler end", [])
        at_start = lambda ph: len(ph) <= len(toks) and all(toks[i]["word"] == w for i, w in enumerate(ph))
        at_end = lambda ph: len(ph) <= len(toks) and all(toks[len(toks) - len(ph) + i]["word"] == w for i, w in enumerate(ph))
        changed = True
        while changed:
            changed = False
            for ph in starts:
                if len(toks) > len(ph) and at_start(ph):
                    toks = toks[len(ph):]
                    changed = True
            for ph in ends:
                if len(toks) > len(ph) and at_end(ph):
                    toks = toks[:-len(ph)]
                    changed = True
        return toks

    def read(self, text, toks):
        """Layer 1: every skill's best template reading; the top ones (several if they tie)."""
        found = []
        for skill in self.skills:
            every = []
            for nodes in skill["compiled"]:
                every += parses(nodes, toks, self.lists["refs"], self.slot_lists(skill), self.stops, self.object_words, self.places)
            if every:
                found.append((skill, best(every)))
        if not found:
            return []
        top = max(p["score"] for _, p in found)
        out = []
        for skill, parse in found:
            if parse["score"] != top:
                continue
            vals = {k: {"text": self.original(text, toks, c["start"], c["end"]), "value": c.get("value"), "label": c.get("label"),
                        "unknown": bool(c.get("unknown")), "fuzzy": bool(c.get("fuzzy"))}
                    for k, c in parse["caps"].items()}
            out.append({"skill": skill, "vals": vals, "score": top})
        return out

    def read_values(self, skill, text, toks):
        """Values found by their own readers, anywhere in the sentence (when no template read it):
        a name from a device list or a shared list, a name after "called"/"named", a file-shaped word."""
        vals, used = {}, set()
        for k, spec in skill["values"].items():
            found = self.list_of(spec["kind"])
            if not found:
                continue
            hit = None
            for o in found:
                for ph in o["phrases"]:
                    for i in range(len(toks) - len(ph) + 1):
                        exact = all(toks[i + j]["word"] == w for j, w in enumerate(ph))
                        fuzzy = not exact and all(close(toks[i + j]["word"], w) for j, w in enumerate(ph))
                        if (exact or fuzzy) and (not hit or len(ph) > hit["len"] or (exact and hit["fuzzy"])):
                            hit = {"o": o, "i": i, "len": len(ph), "fuzzy": fuzzy}
            if hit:
                vals[k] = {"value": hit["o"]["value"], "label": hit["o"]["label"], "fuzzy": hit["fuzzy"]}
                used.update(range(hit["i"], hit["i"] + hit["len"]))
        for k, spec in skill["values"].items():
            if self.list_of(spec["kind"]) or k in vals:
                continue
            after = next((i for i, t in enumerate(toks) if t["word"] in ("called", "named", "titled")), -1)
            if after >= 0 and after + 1 < len(toks):
                end = after + 1
                while end < len(toks) and toks[end]["word"] not in ("in", "inside", "into", "on", "at", "to", "under") and end not in used:
                    end += 1
                if end > after + 1:
                    vals[k] = {"text": self.original(text, toks, after + 1, end)}
                    used.update(range(after, end))
                    continue
            f = next((i for i, t in enumerate(toks) if i not in used and re.search(r"\.[a-z0-9]{1,5}$", t["word"], re.I)), -1)
            if f >= 0:
                vals[k] = {"text": self.original(text, toks, f, f + 1)}
                used.add(f)
        return vals, used

    def understand(self, text, toks):
        """What the sentence asks for: a template's exact reading, or the model's best action + object."""
        found = self.read(text, toks)
        if found and found[0]["score"] >= 1:
            if len(found) > 1:
                return {"how": "choose", "options": found}
            return {"how": "template", "skill": found[0]["skill"], "vals": found[0]["vals"], "p": 1, "unknown": []}
        if not self.model:
            return None
        ws = [t["word"] for t in toks]
        pa = classify(self.model["action"], text, ws)
        po = classify(self.model["object"], text, ws)
        P = lambda found, label: next((x["p"] for x in found if x["label"] == label), 0)
        top = None
        for skill in self.skills:
            p = P(pa, skill["action"]) * P(po, skill["object"])
            if not top or p > top["p"]:
                top = {"skill": skill, "p": p}
        none = max(P(pa, "none"), P(po, "none"))
        if not top or top["p"] < MAYBE or none > top["p"]:
            return None
        vals, used = self.read_values(top["skill"], text, toks)
        taught = set(self.model["taught"].get(top["skill"]["id"], []))
        negation = {w for ph in self.lists["answers"].get("negation", []) for w in ph}  # handled by its own rule
        unknown = [t["word"] for i, t in enumerate(toks) if i not in used and t["word"] not in self.small and t["word"] not in taught and t["word"] not in negation]
        return {"how": "model", "skill": top["skill"], "vals": vals, "p": top["p"], "unknown": unknown}

    # ---- filling in, approving, acting

    def display(self, skill, vals):
        out = {"output": "{output}"}
        for k, v in vals.items():
            out[k] = "•••" if skill["values"][k]["kind"] == "secret" else (v.get("label") if v.get("label") is not None else v.get("text"))
        return out

    def resolve(self, skill, vals, approved=False):
        for k in [k for k, v in vals.items() if self.only_points(v)]:
            del vals[k]
        # a value close to one on the device's list (a typo): confirm it, never use it silently
        for k, v in vals.items():
            if v.get("fuzzy"):
                self.pending = {"skill": skill, "vals": vals, "waiting": "fuzzy", "slot": k, "approved": approved}
                return {"outcome": "ask", "skill": skill["id"], "say": self.reply("did you mean", {"value": v["label"]}), "chips": [v["label"], "no"]}
        # a value said but not on the device's list: ask which one, with the list as chips
        for k, v in vals.items():
            if v.get("unknown"):
                self.pending = {"skill": skill, "vals": vals, "waiting": "value", "slot": k, "approved": approved}
                return {"outcome": "ask", "skill": skill["id"], "say": self.reply("unknown value", {"value": "“%s”" % v["text"]}),
                        "chips": self.chips(self.list_of(skill["values"][k]["kind"]))}
        for k, spec in skill["values"].items():
            if vals.get(k):
                continue
            if spec.get("default") == "here":
                vals[k] = dict(self.here)
            elif spec.get("default"):
                found = self.list_of(spec["kind"])
                d = spec["default"]
                hit = next((o for o in found or [] if o["value"] == d or o["label"] == d or any(" ".join(p) == d for p in o["phrases"])), None)
                vals[k] = {"value": hit["value"], "label": hit["label"]} if hit else {"text": d}
            elif spec["required"]:
                self.pending = {"skill": skill, "vals": vals, "waiting": "value", "slot": k, "approved": approved}
                return {"outcome": "ask", "skill": skill["id"], "say": self.reply(skill["replies"]["ask " + k]),
                        "chips": self.chips(self.list_of(spec["kind"]))}
        self.finish_filetype(skill, vals)
        found = self.find_files(skill, vals, approved)
        if found:
            return found
        if skill["admin"] and not self.on("admin mode"):
            self.pending = None
            return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("admin off"), "reason": "admin mode off"}
        if (skill["admin"] or skill["approve"]) and not approved:
            self.pending = {"skill": skill, "vals": vals, "waiting": "approve"}
            return self.with_show({"outcome": "approve", "skill": skill["id"], "say": self.reply(skill["replies"]["approve"], self.display(skill, vals)),
                                   "chips": ["yes", "no"]}, skill, vals)
        return self.act(skill, vals)

    def complete(self, skill, vals):
        """Every value known and sure: nothing is left to ask, so an approval can name exactly what runs."""
        for k, spec in skill["values"].items():
            v = vals.get(k)
            if not v:
                if spec["required"] and not spec.get("default"):
                    return False
                continue
            if v.get("unknown") or v.get("fuzzy") or self.only_points(v) or (spec["kind"] == "@sys.file" and v.get("value") is None):
                return False
        return True

    def find_files(self, skill, vals, approved):
        """Files are checked on the device. A file to open must exist: here, or else anywhere in home
        (one place: "That one?"; several: "Which one?"; none: said so). A file to create must not."""
        if not self.device or not hasattr(self.device, "files"):
            return None
        place_key = next((k for k, s in skill["values"].items() if s["kind"] == "@sys.folder"), None)
        place = vals.get(place_key) if place_key else None
        for k, spec in skill["values"].items():
            v = vals.get(k)
            if not v or not place:
                continue
            if spec.get("new") and v.get("text") and v["text"] in self.device.files(place["value"]):
                self.pending = None
                return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("already", {"file": v["text"], "folder": place["label"]}), "reason": "already exists"}
            if spec["kind"] != "@sys.file" or v.get("value") is not None:
                continue
            name = v["text"]
            lower = name.lower()
            has_ext = bool(re.search(r"\.\w+$", name))
            stem = lambda f: re.sub(r"\.[^.]+$", "", f)
            same = lambda f: f.lower() == lower or (not has_ext and stem(f).lower() == lower)
            files = self.device.files(place["value"])
            hit = next((f for f in files if same(f)), None)
            if hit:
                vals[k] = {"value": hit, "label": hit}
                continue
            typo = next((f for f in files if close(lower, f.lower()) or (not has_ext and close(lower, stem(f).lower()))), None)
            if typo:
                vals[k] = {"value": typo, "label": typo, "text": name, "fuzzy": True}
                return self.resolve(skill, vals, approved)
            elsewhere = [r for r in self.device.find(same) if r["folder"] != place["value"]]
            if len(elsewhere) == 1:
                r = elsewhere[0]
                self.pending = {"waiting": "elsewhere", "skill": skill, "vals": vals, "approved": approved, "options": [{**r, "k": k, "place_key": place_key}]}
                return {"outcome": "ask", "skill": skill["id"], "say": self.reply("elsewhere", {"file": r["file"], "here": place["label"], "folder": r["label"]}), "chips": ["yes", "no"]}
            if len(elsewhere) > 1:
                self.pending = {"waiting": "where", "skill": skill, "vals": vals, "approved": approved, "options": [{**r, "k": k, "place_key": place_key} for r in elsewhere]}
                labels = [r["label"] for r in elsewhere]
                return {"outcome": "ask", "skill": skill["id"], "say": self.reply("several", {"count": len(elsewhere), "file": elsewhere[0]["file"], "folders": ", ".join(labels)}), "chips": labels}
            self.pending = None
            return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("not found", {"file": name, "here": place["label"]}), "reason": "not found"}
        return None

    @staticmethod
    def choose(o, vals):
        vals[o["k"]] = {"value": o["file"], "label": o["file"]}
        vals[o["place_key"]] = {"value": o["folder"], "label": o["label"]}

    def finish_filetype(self, skill, vals):
        """A file's name gets the extension of its type, unless it already has a known one (seed.md)."""
        type_key = next((k for k, s in skill["values"].items() if s["kind"] == "filetype"), None)
        if not type_key or not vals.get("name"):
            return
        name = vals["name"]["text"]
        m = re.search(r"\.(\w+)$", name)
        known = next((t for t in self.lists["filetypes"] if t["ext"] == (m.group(1).lower() if m else "")), None)
        if known:
            vals[type_key] = {"value": known["value"], "label": known["label"]}
            return
        said = vals.get(type_key) or {}
        kind = next((t for t in self.lists["filetypes"] if t["value"] in (said.get("value"), said.get("text"))), self.lists["filetypes"][0])
        vals["name"] = {"text": "%s.%s" % (name, kind["ext"])}

    def command_for(self, skill, vals):
        def part(p):
            if "{" not in p:
                return p
            return quote(re.sub(r"\{(\w+)\}", lambda m: "" if not vals.get(m.group(1)) else str(
                vals[m.group(1)]["value"] if vals[m.group(1)].get("value") is not None else vals[m.group(1)].get("text", "")), p))
        return " ".join(part(p) for p in skill["command"].split(" "))

    def with_show(self, out, skill, vals):
        """"show commands" on: the command is shown when acting, and before it, when the person approves"""
        if self.on("show commands"):
            out["show"] = self.command_for(skill, vals)
        return out

    def act(self, skill, vals):
        self.pending = None
        command = self.command_for(skill, vals)
        if skill["moves"] and vals.get(skill["moves"]):
            v = vals[skill["moves"]]
            self._here = {"value": v["value"], "label": v["label"]}
        if skill["reads"]:  # the device reads itself; the reply is chosen once it has (server.py)
            return {"outcome": "act", "skill": skill["id"], "say": "", "reads": skill["reads"]}
        return self.with_show({"outcome": "act", "skill": skill["id"], "say": self.reply(skill["replies"]["done"], self.display(skill, vals)), "command": command}, skill, vals)

    def fill_pending(self, text, toks):
        """An answer to "Which folder?": a value on the list, or free text for a text value.
        "no" stops the request; "yes" answers nothing, so the question is asked again; "call it bikes"
        gives the name after its lead-in words (en/answers.md, "before a name")."""
        p = self.pending
        skill, vals, slot, approved = p["skill"], p["vals"], p["slot"], p["approved"]
        if self.is_(toks, "no"):
            self.pending = None
            return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("declined"), "reason": "declined"}
        found = self.list_of(skill["values"][slot]["kind"])
        if self.is_(toks, "yes"):
            v = vals.get(slot) or {}
            ask = skill["replies"].get("ask " + slot)
            say = self.reply(ask) if ask else self.reply("unknown value", {"value": "“%s”" % (v.get("text") or v.get("label") or "")})
            return {"outcome": "ask", "skill": skill["id"], "say": say, "chips": self.chips(found)}
        if found is None:
            leads = [ph for ph in self.lists["answers"].get("before a name", [])
                     if len(ph) < len(toks) and all(toks[i]["word"] == w for i, w in enumerate(ph))]
            start = max((len(ph) for ph in leads), default=0)
            vals[slot] = {"text": self.original(text, toks, start, len(toks)) if toks else text.strip()}
            return self.resolve(skill, vals, approved)
        hit = None
        for o in found:
            for ph in o["phrases"]:
                for i in range(len(toks) - len(ph) + 1):
                    if all(toks[i + j]["word"] == w for j, w in enumerate(ph)) and (not hit or len(ph) > hit["len"]):
                        hit = {"o": o, "len": len(ph)}
        if not hit:
            return {"outcome": "ask", "skill": skill["id"], "say": self.reply("unknown value", {"value": "“%s”" % text.strip()}), "chips": self.chips(found)}
        vals[slot] = {"value": hit["o"]["value"], "label": hit["o"]["label"]}
        return self.resolve(skill, vals, approved)

    # ---- one turn of the conversation

    def hear(self, text):
        self.last = None
        r = self.respond(text)
        u = self.last
        if u:
            r["how"] = u["how"]
            if u.get("p") is not None:
                r["p"] = round(u["p"] * 100) / 100
            if u.get("unknown"):
                r["unknown"] = u["unknown"]
        return r

    def respond(self, text):
        toks = self.clean(text)
        if not toks:
            return {"outcome": "abstain", "say": self.reply("abstain")}
        if self.is_(toks, "cancel"):
            self.pending = None
            return {"outcome": "abstain", "say": self.reply("cancelled"), "reason": "cancelled"}
        said = " ".join(t["word"] for t in toks)
        p = self.pending

        if p and p["waiting"] == "approve":
            if self.is_(toks, "yes"):
                return self.act(p["skill"], p["vals"])
            if self.is_(toks, "no"):
                self.pending = None
                return {"outcome": "abstain", "skill": p["skill"]["id"], "say": self.reply("declined"), "reason": "declined"}
            self.pending = None  # something else: a new request
        p = self.pending
        if p and p["waiting"] == "understand":
            if self.is_(toks, "yes"):
                self.pending = None
                r = self.resolve(p["skill"], p["vals"], bool(p.get("approves")))
                r["teach"] = {"skill": p["skill"]["id"], "text": p["text"]}
                return r
            if self.is_(toks, "no"):
                self.pending = None
                return {"outcome": "abstain", "say": self.reply("declined"), "reason": "declined", "inbox": p["text"]}
            self.pending = None
        p = self.pending
        if p and p["waiting"] in ("elsewhere", "where"):
            if p["waiting"] == "elsewhere":
                o = p["options"][0] if self.is_(toks, "yes") else None
            else:
                o = next((x for x in p["options"] if " ".join(words(x["label"])) == said), None)
            if o:
                self.pending = None
                self.choose(o, p["vals"])
                return self.resolve(p["skill"], p["vals"], p["approved"])
            if self.is_(toks, "no"):
                self.pending = None
                return {"outcome": "abstain", "skill": p["skill"]["id"], "say": self.reply("declined"), "reason": "declined"}
            self.pending = None
        p = self.pending
        if p and p["waiting"] == "fuzzy":
            skill, vals, slot, approved = p["skill"], p["vals"], p["slot"], p["approved"]
            v = vals[slot]
            if self.is_(toks, "yes") or " ".join(words(v["label"])) == said:
                vals[slot] = {"value": v["value"], "label": v["label"]}
                self.pending = None
                return self.resolve(skill, vals, approved)
            if self.is_(toks, "no"):
                self.pending = {"skill": skill, "vals": vals, "waiting": "value", "slot": slot, "approved": approved}
                return {"outcome": "ask", "skill": skill["id"], "say": self.reply("unknown value", {"value": "“%s”" % (v.get("text") or v["label"])}),
                        "chips": self.chips(self.list_of(skill["values"][slot]["kind"]))}
            self.pending = {**p, "waiting": "value"}  # another folder named instead: read it as the answer
        p = self.pending
        if p and p["waiting"] == "choose":
            chosen = next((o for o in p["options"] if " ".join(words(o["skill"]["label"])) == said), None)
            if chosen:
                self.pending = None
                return self.resolve(chosen["skill"], chosen["vals"])
        # a lone yes or no with nothing waiting (an old chip, a question lost): say so, don't guess
        if not self.pending and (self.is_(toks, "yes") or self.is_(toks, "no")):
            return {"outcome": "abstain", "say": self.reply("nothing waiting"), "reason": "nothing waiting"}
        if self.is_(toks, "help"):
            self.pending = None
            names = [s["label"] for s in self.skills]
            return {"outcome": "act", "say": self.reply("help", {"skills": ", ".join(names)}), "chips": names}

        u = self.understand(text, toks)
        self.last = u if u and u["how"] != "choose" else None
        sure = bool(u) and (u["how"] == "template" or (u["how"] == "model" and u["p"] >= SURE and not u["unknown"]))
        # While a question waits, what the person says answers it, unless it clearly asks for something
        # else (another skill, surely understood). The same skill said again adds its values to the
        # question; then whatever is still asked for is filled from the words themselves.
        p = self.pending
        if p and p["waiting"] == "value":
            # another request: a skill's own sentence, or the model sure of another skill AND an action word
            # said ("open…", "check…"); a lone word like "note" is always an answer
            says_action = any(ph and i + len(ph) <= len(toks) and all(toks[i + j]["word"] == w for j, w in enumerate(ph))
                              for a in self.lists["actions"] for ph in self.lists["refs"].get(a, []) for i in range(len(toks)))
            other = sure and u["skill"]["id"] != p["skill"]["id"] and (u["how"] == "template" or says_action)
            if not other:
                if sure and u["skill"]["id"] == p["skill"]["id"]:
                    for k, v in u["vals"].items():
                        if not p["vals"].get(k) or p["vals"][k].get("unknown"):
                            p["vals"][k] = v
                    if p["vals"].get(p["slot"]):
                        self.last = None
                        self.pending = None
                        return self.resolve(p["skill"], p["vals"], p["approved"])
                self.last = None  # an answer, not a new request: nothing to report about understanding it
                return self.fill_pending(text, toks)

        if not u:
            self.pending = None
            return {"outcome": "abstain", "say": self.reply("abstain"), "reason": "no skill", "inbox": text}
        if u["how"] == "choose":
            self.pending = {"waiting": "choose", "options": u["options"]}
            labels = [f["skill"]["label"] for f in u["options"]]
            return {"outcome": "ask", "say": self.reply("choose", {"options": " or ".join(labels)}), "chips": labels}
        self.pending = None
        skill = u["skill"]
        # "do not reboot", "don't turn off the wifi": a request that changes something is never acted on
        # when it says no; it is asked about, and its approval, if any, still comes after the yes
        negated = self.negation(toks)
        if negated and skill["action"] not in self.reading:
            self.pending = {"waiting": "understand", "skill": skill, "vals": u["vals"], "text": text, "approves": False}
            return {"outcome": "ask", "skill": skill["id"], "chips": ["yes", "no"],
                    "say": self.reply("negated", {"words": ", ".join(negated), "label": skill["label"]})}
        if sure:
            return self.resolve(u["skill"], u["vals"])

        # understood, but not surely: ask before doing anything, naming the words it doesn't know
        if skill["admin"] and not self.on("admin mode"):
            return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("sounds like", {"label": skill["label"]}), "reason": "admin mode off"}
        label = skill["label"]
        named = ", ".join("“%s”" % w for w in u["unknown"])
        say = self.reply("not sure", {"words": named, "label": label}) if u["unknown"] else self.reply("confirm", {"label": label})
        # A skill that needs approval asks its own question, so the person approves once, knowingly, but
        # only when every value is known: otherwise this yes only confirms the skill, and the approval
        # comes later, naming what will run.
        approves = (skill["admin"] or skill["approve"]) and self.complete(skill, u["vals"])
        self.pending = {"waiting": "understand", "skill": skill, "vals": u["vals"], "text": text, "approves": approves}
        out = {"outcome": "ask", "skill": skill["id"], "say": say, "chips": ["yes", "no"], "unknown": u["unknown"], "p": round(u["p"] * 100) / 100}
        if approves:
            out["say"] = (self.reply("new words", {"words": named}) + " " if u["unknown"] else "") + self.reply(skill["replies"]["approve"], self.display(skill, u["vals"]))
            self.with_show(out, skill, u["vals"])
        return out
