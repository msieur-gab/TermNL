"""The dialogue: one turn in five steps. Reading the sentence is reading.py's job; this file keeps the
conversation (the question waiting, the last request done) and turns a reading into what happens next.

Every request ends in one of four outcomes:
  act      understood, everything known, nothing to approve: the command is ready to run
  ask      a value is missing or isn't on the device, or the request isn't surely understood:
           a question, with chips when there are choices
  approve  the action is destructive or needs admin rights: the person approves first
  abstain  nothing understood, or the settings don't allow it: the agent says so

One turn (respond):
  1. clean       fillers off, a typo read as the word it is one letter from (reading.py)
  2. answer      a question is waiting: yes, no, one of its chips, or a value for "Which one?"
  3. read        a template reads the sentence exactly, or the model its action and object (reading.py);
                 a sentence that says part of a request ("now delete it", "and in downloads?") is
                 completed by the last request done, its frame (follow_up)
  4. safety      not sure, a typo in a change, "don't…": ask before anything
  5. next_step   the next value to ask, a file to find, the settings, the approval; or act

The agent never runs anything and never writes a command: it fills in the command a skill declares,
with every value quoted. Running it is the device's job (runner.py)."""
import random as _random
import re

from .reading import Reader, SURE, at, best_in, original, where
from .text import close, fill, pick, tokenize, words


def sq(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def quote(p):
    """a path's leading $HOME stays outside the quotes, so the shell still expands it"""
    if p.startswith("$HOME"):
        return "$HOME" + (sq(p[5:]) if len(p) > 5 else "")
    return sq(p)


class Agent:
    def __init__(self, lists, skills, model=None, settings=None, device=None, random=_random.random, **_):
        self.lists, self.skills = lists, skills
        self.settings = settings if settings is not None else {}
        self.device, self.random = device, random
        self._sys = {}  # kind → (the device's list, its values with their words)
        self.pending = None  # the question waiting for an answer
        self._here = None  # where you are, like a terminal's working folder: home at first
        self.frame = None  # the last request done: its skill, its values, and the thing it touched (follow_up)
        said = lists["conversation"]
        self.words = lambda key: said.get(key, [])
        joined = lambda key: {" ".join(p) for p in said.get(key, [])}
        self.small, self.stops, self.pointing = joined("small words"), joined("not a name start"), joined("pointing words")
        self.reading = joined("reading actions")
        self.follows = {w for ph in said.get("follow-up words", []) for w in ph}
        self.many = joined("pointing at several")
        # the chips that answer a yes/no question: the first word of each list
        self.yes_no = [" ".join(said["yes"][0]), " ".join(said["no"][0])]
        self.reader = Reader(lists, skills, self.sys, model)

    # ---- the device, the settings, the lists

    @property
    def here(self):
        if self._here:
            return self._here
        h = next((f for f in self.sys("folder") if f["value"] == "$HOME"), None)
        return {"value": h["value"], "label": h["label"]} if h else {"value": "$HOME", "label": "home"}

    def above(self, value):
        """the folder a folder is in"""
        up = value.rsplit("/", 1)[0] if value != "$HOME" else "$HOME"
        found = next((f for f in self.sys("folder") if f["value"] == up), None)
        return {"value": up, "label": found["label"] if found else up.rsplit("/", 1)[-1]}

    def on(self, key):
        return bool(re.match(r"^(on|yes|true)$", self.settings.get(key) or "", re.I))

    def sys(self, kind):
        """the device's values of a kind, their names cut into words once each time the device reads them again
        (a home's folders and services are hundreds of names: cutting them at every sentence took 0.3 s on a board)"""
        found = self.device.list(kind) if self.device else []
        read, values = self._sys.get(kind, (None, None))
        if read is not found:
            values = [{"value": d["value"], "label": d["names"][0], "phrases": [words(n) for n in d["names"]]} for d in found]
            self._sys[kind] = (found, values)
        return values

    def list_of(self, kind):
        return self.reader.list_of(kind)

    def chips(self, found):
        return [o["label"] for o in found][:8] if found else []

    def reply(self, key, values=None):
        """a written reply, in the person's name when they gave one ("call me Gab")"""
        user = self.settings.get("name") or ""
        return fill(pick(self.lists["replies"].get(key) or key, self.random, user), {"user": user, **(values or {})})

    def quoted(self, word):
        """a word as the person typed it, in the language's quotation marks (conversation.md, "quoted")"""
        return self.reply("quoted", {"word": word})

    def is_(self, toks, key):
        return any(len(ph) == len(toks) and at(toks, ph, 0) for ph in self.words(key))

    def only_points(self, v):
        """"this", "that file": a value that only points can't be known here, so it is asked for instead"""
        return v.get("text") is not None and v.get("value") is None and all(t["word"] in self.pointing for t in tokenize(v["text"]))

    @staticmethod
    def original(text, toks, start, end):
        return original(text, toks, start, end)

    # ---- one turn of the conversation

    # ---- one turn of the conversation

    def hear(self, text):
        return self.respond(text)

    def respond(self, text):
        # 1. clean
        toks = self.reader.clean(text)
        if not toks:
            return {"outcome": "abstain", "say": self.reply("abstain")}
        if self.is_(toks, "cancel"):
            self.pending, self.frame = None, None
            return {"outcome": "abstain", "say": self.reply("cancelled"), "reason": "cancelled"}

        # 2. answer the question waiting, when it is a closed one (yes, no, a chip)
        if self.pending and self.pending["waiting"] != "value":
            r = self.answer(toks)
            if r:
                return r
        if not self.pending and (self.is_(toks, "yes") or self.is_(toks, "no")):
            # a lone yes or no with nothing waiting (an old chip, a question lost): say so, don't guess
            return {"outcome": "abstain", "say": self.reply("nothing waiting"), "reason": "nothing waiting"}

        # 3. read
        typed = toks
        u = self.reader.read(text, toks)
        fixed, fixes = self.reader.correct(toks)
        v = self.reader.read(text, fixed) if fixes else None  # a typo read as a word, only when that reads better
        if v and better(v, u):
            u, v["fixes"] = v, fixes
        if u:
            toks = u["toks"]
            u.setdefault("fixes", [])
            u["sure"] = u["how"] == "template" or (u["how"] in ("model", "part") and self.sure(u))

        # 2, still: "Which one?" is answered by a value, unless the person clearly asks for something else
        p = self.pending
        if p and p["waiting"] == "value":
            acts, _ = u["names"] if u else self.reader.names(self.reader.shape(toks))
            other = u and u["sure"] and u["skill"]["id"] != p["skill"]["id"] and (u["how"] == "template" or acts)
            if not other:
                r = self.fill_value(text, typed, u, bool(acts))  # the words as typed: a name is never cut from words re-ordered for reading
                if r:
                    return r
                self.pending = None  # not one of the values asked for, but a request: read as said alone

        # 3, still: a sentence that says only part of a request, completed by the last one done ("now delete it")
        f = self.follow_up(text, toks, u) if self.frame else None
        if f:
            u, toks = f, f["toks"]

        if not u:
            self.pending, self.frame = None, None  # nothing understood: the subject changed
            return {"outcome": "abstain", "say": self.reply("abstain"), "reason": "no skill", "inbox": text}
        if u["how"] == "choose":
            labels = [f["skill"]["label"] for f in u["options"]]
            self.question("choose", keep=True, options=[(f["skill"]["label"], lambda f=f: self.next_step(f["skill"], f["vals"])) for f in u["options"]])
            return {"outcome": "ask", "say": self.reply("choose", {"options": " or ".join(labels)}), "chips": labels}
        self.pending = None
        skill, vals = u["skill"], u["vals"]

        # 4. safety: a change is asked about before anything when a typo was read, or when it says no
        sure = u["sure"] and not (u["fixes"] and skill["action"] not in self.reading)
        negated = [" ".join(ph) for ph in self.words("negation") for _ in where(toks, ph)]
        if negated and skill["action"] not in self.reading:
            self.ask_first(skill, vals, text, approves=False)
            return told({"outcome": "ask", "skill": skill["id"], "chips": self.yes_no,
                         "say": self.reply("negated", {"words": ", ".join(negated), "label": skill["label"]})}, u)
        if sure:
            return told(noted(self.next_step(skill, vals), u["fixes"], self), u)
        if skill["admin"] and not self.on("admin mode"):
            return told({"outcome": "abstain", "skill": skill["id"], "say": self.reply("sounds like", {"label": skill["label"]}), "reason": "admin mode off"}, u)
        # understood, but not surely: ask, naming the words it doesn't know. A skill that needs approval
        # asks its own question, so the person approves once, knowingly, but only when every value is
        # known; otherwise this yes only confirms the skill, and the approval comes later.
        named = ", ".join(self.quoted(w) for w in u["unknown"])
        approves = (skill["admin"] or skill["approve"]) and self.complete(skill, vals)
        self.ask_first(skill, vals, text, approves)
        out = {"outcome": "ask", "skill": skill["id"], "chips": self.yes_no, "unknown": u["unknown"], "p": round(u["p"] * 100) / 100,
               "say": self.reply("not sure", {"words": named, "label": skill["label"]}) if u["unknown"] else self.reply("confirm", {"label": skill["label"]})}
        if approves:
            out["say"] = (self.reply("new words", {"words": named}) + " " if u["unknown"] else "") + self.reply(skill["replies"]["approve"], self.display(skill, vals))
            self.with_show(out, skill, vals)
        return told(noted(out, u["fixes"], self), u)

    def sure(self, u):
        """A reading the model is sure of (SURE), with no word unknown, goes ahead; a request read in part is
        sure only when it reads (nothing changes on the device)."""
        if u["unknown"]:
            return False
        if u["how"] == "part":
            return u["skill"]["action"] in self.reading
        return u["p"] >= SURE

    # ---- 2. answer

    def question(self, waiting, yes=None, no=None, options=(), otherwise=None, keep=False):
        """A closed question waits: what yes, no or a chip does, and what anything else does (dropped,
        kept, or `otherwise`)."""
        self.pending = {"waiting": waiting, "yes": yes, "no": no, "options": list(options), "otherwise": otherwise, "keep": keep}

    def answer(self, toks):
        """the person's answer to the closed question waiting → a reply, or None to read it as a request"""
        q, said = self.pending, " ".join(t["word"] for t in toks)
        pick_ = next((f for label, f in q["options"] if " ".join(words(label)) == said), None)
        if self.is_(toks, "yes") and q["yes"]:
            pick_ = q["yes"]
        if not pick_ and self.is_(toks, "no") and q["no"]:
            pick_ = q["no"]
        if pick_:
            self.pending = None
            return pick_()
        if q["otherwise"]:
            q["otherwise"]()
        elif not q["keep"]:
            self.pending = None
        return None

    def declined(self, skill=None, inbox=None):
        r = {"outcome": "abstain", "say": self.reply("declined"), "reason": "declined"}
        if skill:
            r["skill"] = skill["id"]
        if inbox:
            r["inbox"] = inbox
        return r

    def ask_first(self, skill, vals, text, approves):
        """ "Do you want me to …?": yes goes on (approved when the question was the approval itself)"""
        def yes():
            r = self.next_step(skill, vals, approves)
            r["teach"] = {"skill": skill["id"], "text": text}
            return r
        self.question("understand", yes=yes, no=lambda: self.declined(inbox=text))

    def ask_value(self, skill, vals, slot, approved, say, chips):
        """ "Which one?": the answer is a value (fill_value), not a yes or a chip"""
        self.pending = {"waiting": "value", "skill": skill, "vals": vals, "slot": slot, "approved": approved}
        return {"outcome": "ask", "skill": skill["id"], "say": say, "chips": chips}

    def not_there(self, skill, slot, said, found):
        """ "I don't see pipewire. Which one?": a value said but not on the device's list. A skill can say why in
        its own words, before the list as chips (stop process, "unknown name": "pipewire isn't an app I can
        stop. Running now:"); with nothing on the list, the plain reply."""
        own = skill["replies"].get("unknown " + slot)
        if own and found:
            return self.reply(own, {slot: self.quoted(said)})
        folder = skill["values"][slot]["kind"] == "@sys.folder"  # "I don't see a folder called photos" (Gab, 26 Oct)
        return self.reply("unknown folder" if folder else "unknown value", {"value": self.quoted(said)})

    def begins(self, skill, slot, said):
        """A folder said by its beginning ("doc" for Documents): the one folder whose name starts so, to propose
        as a typo is (Gab, 26 Oct: "if the name is close hence doc for documents then it should propose"). → it, or None."""
        if skill["values"][slot]["kind"] != "@sys.folder":
            return None
        w = " ".join(words(said))
        w = re.sub(r"^(?:the|my) ", "", w)
        fits = [o for o in self.list_of("@sys.folder") or [] if len(w) >= 3 and " " not in w
                and any(ph and ph[0].startswith(w) and ph[0] != w for ph in o["phrases"])]
        return fits[0] if len(fits) == 1 else None

    def fill_value(self, text, toks, u, says_action=False):
        """An answer to "Which one?" or "What should I call it?". The same request said again adds its
        values; "no" stops; "yes" asks again; "call it bikes" gives the name after its lead-in words
        (conversation.md, "before a name"); a value on the list, or free text for a name. None when the
        sentence is none of the listed values but a request that says its action: it is read as said alone
        ("create note_02 inside document" isn't a file type; Gab, 26 Oct). A name is free text: never None."""
        p = self.pending
        skill, vals, slot, approved = p["skill"], p["vals"], p["slot"], p["approved"]
        if u and u["sure"] and u["skill"]["id"] == skill["id"]:
            doubt = lambda v: v.get("unknown") or v.get("fuzzy")  # not on the list, or a typo not yet confirmed
            # a value in doubt the request said again doesn't repeat goes ("list my files" after "Which one?":
            # its default applies; "noe" read as a note, Gab, 26 Oct); what was settled stays
            dropped = [k for k, v in vals.items() if doubt(v) and k not in u["vals"]]
            for k in dropped:
                del vals[k]
            for k, v in u["vals"].items():
                if not vals.get(k) or doubt(vals[k]):
                    vals[k] = v
            if slot in dropped or vals.get(slot):
                self.pending = None
                return self.next_step(skill, vals, approved)
        if self.is_(toks, "no"):
            self.pending = None
            return self.declined(skill)
        found = self.list_of(skill["values"][slot]["kind"])
        if self.is_(toks, "yes"):
            v, ask = vals.get(slot) or {}, skill["replies"].get("ask " + slot)
            say = self.reply(ask) if ask else self.reply("unknown value", {"value": self.quoted(v.get("text") or v.get("label") or "")})
            return {"outcome": "ask", "skill": skill["id"], "say": say, "chips": self.chips(found)}
        if found is None and skill["values"][slot]["kind"] == "secret":  # a password, exactly as typed ("!" included)
            vals[slot] = {"text": text.strip()}
            return self.next_step(skill, vals, approved)
        if found is None:
            start, end = max((len(ph) for ph in self.words("before a name") if len(ph) < len(toks) and at(toks, ph, 0)), default=0), len(toks)
            if skill["values"][slot]["kind"] == "@sys.file":  # a file to find, said as people say it (Gab, 30 Oct)
                around = {w for ph in self.words("around a file") for w in ph}
                while end - start > 1 and toks[start]["word"] in around:  # "the proton file": proton
                    start += 1
                while end - start > 1 and toks[end - 1]["word"] in around:
                    end -= 1
            vals[slot] = {"text": self.original(text, toks, start, end)}
            return self.next_step(skill, vals, approved)
        hit = best_in(toks, found)
        if not hit and u and says_action:
            return None
        near = None if hit else self.begins(skill, slot, text.strip())
        if near:  # "doc": Documents, proposed
            vals[slot] = {"value": near["value"], "label": near["label"], "text": text.strip(), "fuzzy": True}
            return self.next_step(skill, vals, approved)
        if not hit:
            return {"outcome": "ask", "skill": skill["id"], "say": self.not_there(skill, slot, text.strip(), found), "chips": self.chips(found)}
        vals[slot] = {"value": hit["o"]["value"], "label": hit["o"]["label"]}
        return self.next_step(skill, vals, approved)

    # ---- 3. understand


    def follow_up(self, text, toks, u):
        """A sentence that says part of a request, completed by the last one done (self.frame): "now delete it"
        (an action: the thing it touched), "and in downloads?" (a value: the same request there), "and
        bluetooth too" (an object: the same action), "turn it back off". Only when the sentence points ("it",
        "the other one") or follows on ("and", "now", "same for"), names an action or an object but not both,
        and has no word left that isn't a value, a small word or one of those: anything else is a new request.
        A template that reads the sentence surely, with nothing pointing, is a new request too.
        → the reading, as understand gives it, or None."""
        if u and u["how"] == "template" and u["sure"] and not any(self.only_points(v) for v in u["vals"].values()):
            return None
        said = self.reader.joined(toks)
        ws = [t["word"] for t in said]
        follows = [ph for ph in self.words("follow-up words") if where(said, ph)]
        if not follows and not any(w in self.pointing for w in ws):
            return None
        if any(w in self.many for w in ws):  # "delete them" after a folder was shown means its files, never the folder
            return None
        refs, lists, frame = self.lists["refs"], self.lists, self.frame
        acts = self.reader.alone(said)
        objs = {o for o in lists["objects"] for ph in refs.get(o, []) if where(said, ph)}
        if not acts and not objs and u and u.get("skill") and u["skill"]["object"] == frame["skill"]["object"] \
                and any(len(ph) > 1 and all(w in ws for w in ph) for ph in refs.get(u["skill"]["action"], [])):
            acts = {u["skill"]["action"]}  # its words said, split around "it" ("bring it back"): the model's reading
        if len(acts) > 1 or len(objs) > 1 or (acts and objs):
            return None
        action = next(iter(acts)) if acts else frame["skill"]["action"]
        obj = next(iter(objs)) if objs else frame["skill"]["object"]
        allowed = {w for x in (action, obj) for ph in refs.get(x, []) for w in ph}
        skill = next((s for s in self.skills if (s["action"], s["object"]) == (action, obj)), None)
        if not skill and acts:  # a word that means another action with the thing's object ("turn it off": the music stops)
            for rule in lists.get("in_context", []):
                if obj in rule["objects"] and any(where(said, ph) for ph in rule["phrases"]):
                    skill = next((s for s in self.skills if (s["action"], s["object"]) == (rule["action"], obj)), None)
                    allowed |= {w for ph in rule["phrases"] for w in ph}
                    break
        if not skill or skill.get("changes") or skill.get("lists") or skill.get("trains") or skill.get("opens"):
            return None
        vals = self.reader.values_in(skill, text, said)
        if u and u.get("vals") and u.get("skill") and u["skill"]["action"] == skill["action"]:
            # what a template read in the sentence ("rename it to cycles": the new name), where the skill has it too
            for k, v in u["vals"].items():
                if k in skill["values"] and skill["values"][k]["kind"] == u["skill"]["values"][k]["kind"] and not self.only_points(v):
                    vals[k] = v
        allowed |= {w for v in vals.values() for w in words(v.get("text") or v.get("label") or "")}
        allowed |= self.small | self.pointing | self.follows
        if any(w not in allowed for w in ws):
            return None
        return {"how": "frame", "skill": skill, "vals": self.carry(skill, vals), "p": 1, "unknown": [], "sure": True, "fixes": [], "toks": said}

    def carry(self, skill, vals):
        """The values a follow-up didn't say, from the last request done: the same request keeps its values
        ("and in downloads?"); another one takes the thing it touched ("now delete it": that file, in its
        folder). A file is carried by its name, so it is looked for again where it is asked for."""
        frame, out = self.frame, {k: v for k, v in vals.items() if not self.only_points(v)}
        same, thing = frame["skill"]["id"] == skill["id"], frame["thing"]
        main = skill.get("main")
        for k, spec in skill["values"].items():
            if k in out:
                continue
            v = frame["vals"].get(k) if same else None
            if not v and thing and k == main and spec["kind"] == thing["kind"]:
                v = thing
            elif not v and thing and spec["kind"] == "text" and spec["required"] and not spec.get("new") \
                    and k == next(x for x, sp in skill["values"].items() if sp["required"]):
                v = thing  # a file or folder said by its name ("bring it back": the file just deleted)
            elif not v and thing and thing.get("place") and k == skill.get("where"):
                v = thing["place"]  # the folder the thing is in, into the skill's folder that says where things are
            if v:
                out[k] = {"text": v.get("label") or v.get("text")} if spec["kind"] == "@sys.file" else \
                    {x: v[x] for x in ("value", "label", "text") if v.get(x) is not None}
        return out

    def remember(self, skill, vals):
        """After a request is done: what a follow-up may point at. The thing it touched is its main value, or
        the file or folder it made or renamed (create folder bikes: the folder bikes, in its place)."""
        new = next((k for k, s in skill["values"].items() if s.get("new") and vals.get(k)), None)
        thing = None
        if new and skill["object"] in ("file", "folder"):
            name = vals[new]["text"]
            k = skill.get("where")
            where_ = vals[k] if k and vals.get(k) and vals[k].get("value") else None
            if skill["object"] == "folder":
                value = (where_["value"] if where_ else self.here["value"]) + "/" + name
                thing = {"kind": "@sys.folder", "value": value, "label": name}
            else:
                thing = {"kind": "@sys.file", "label": name, "place": where_ and {"value": where_["value"], "label": where_["label"]}}
        elif skill.get("main") and vals.get(skill["main"]):
            k = skill["main"]
            v, kind = vals[k], skill["values"][k]["kind"]
            thing = {"kind": kind, **{x: v[x] for x in ("value", "label", "text") if v.get(x) is not None}}
            at = skill.get("where")
            if kind == "@sys.file" and at and vals.get(at):
                thing["place"] = {x: vals[at][x] for x in ("value", "label") if vals[at].get(x) is not None}
        self.frame = {"skill": skill, "vals": {k: dict(v) for k, v in vals.items()}, "thing": thing}


    # ---- 5. next step: values, files, settings, approval, act

    def gap(self, skill, vals):
        """What still stands between the request and its command, first first: a value to confirm (a
        typo), a value not on the device, a required value not said, a file still to find. None: nothing."""
        for kind in ("fuzzy", "unknown"):
            k = next((k for k, v in vals.items() if v.get(kind)), None)
            if k:
                return kind, k
        for k, spec in skill["values"].items():
            if not vals.get(k) and spec["required"] and not spec.get("default"):
                return "required", k
        for k, spec in skill["values"].items():
            if vals.get(k) and spec["kind"] == "@sys.file" and vals[k].get("value") is None:
                return "file", k
        return None

    def complete(self, skill, vals):
        """every value known and sure: an approval can name exactly what runs"""
        return self.gap(skill, {k: v for k, v in vals.items() if not self.only_points(v)}) is None

    def next_step(self, skill, vals, approved=False):
        for k in [k for k, v in vals.items() if self.only_points(v)]:
            del vals[k]
        gap = self.gap(skill, vals)
        if gap and gap[0] == "fuzzy":  # a typo of a value on the device's list: confirmed, never used silently
            return self.confirm_typo(skill, vals, gap[1], approved)
        if gap and gap[0] == "unknown":  # said, but not on the device's list: which one, with the list as chips
            k = gap[1]
            near = self.begins(skill, k, vals[k]["text"])
            if near:  # "doc" for Documents: proposed, as a typo is
                vals[k] = {"value": near["value"], "label": near["label"], "text": vals[k]["text"], "fuzzy": True}
                return self.confirm_typo(skill, vals, k, approved)
            found = self.list_of(skill["values"][k]["kind"])
            return self.ask_value(skill, vals, k, approved, self.not_there(skill, k, vals[k]["text"], found), self.chips(found))
        for k, spec in skill["values"].items():
            d = spec.get("default") or ""
            if vals.get(k):
                continue
            if d == "here":
                vals[k] = dict(self.here)
            elif d.startswith("parent of "):
                if vals.get(d[10:]):
                    vals[k] = self.above(vals[d[10:]]["value"])
            elif d == "parent":
                if self.here["value"] == "$HOME":
                    self.pending = None
                    return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("already home"), "reason": "already home"}
                vals[k] = self.above(self.here["value"])
            elif d:
                hit = next((o for o in self.list_of(spec["kind"]) or [] if d in (o["value"], o["label"]) or any(" ".join(p) == d for p in o["phrases"])), None)
                vals[k] = {"value": hit["value"], "label": hit["label"]} if hit else {"text": d}
            elif spec["required"]:
                return self.ask_value(skill, vals, k, approved, self.reply(skill["replies"]["ask " + k]), self.chips(self.list_of(spec["kind"])))
        self.finish_filetype(skill, vals)
        r = self.find_files(skill, vals, approved) or self.already_there(skill, vals)
        if r:
            return r
        # the home folder itself compressed, deleted or renamed needs admin and approval, as any admin skill (Gab,
        # 26 Oct: "Any skill on whole home"); home as where something happens, or read, stays free
        main = skill["main"]
        home = (not skill.get("reads") and main != skill["where"] and skill["values"].get(main, {}).get("kind") == "@sys.folder"
                and (vals.get(main) or {}).get("value") == "$HOME")
        if (skill["admin"] or home) and not self.on("admin mode"):
            self.pending = None
            return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("admin off"), "reason": "admin mode off"}
        if (skill["admin"] or skill["approve"] or home) and not approved:
            self.question("approve", yes=lambda: self.act(skill, vals), no=lambda: self.declined(skill))
            return self.with_show({"outcome": "approve", "skill": skill["id"], "say": self.reply(skill["replies"]["approve"], self.display(skill, vals)),
                                   "chips": self.yes_no}, skill, vals)
        return self.act(skill, vals)

    def confirm_typo(self, skill, vals, k, approved):
        """ "Did you mean Documents?": yes (or the name) takes it; no shows the list; another name answers"""
        v = vals[k]

        def take():
            vals[k] = {"value": v["value"], "label": v["label"]}
            return self.next_step(skill, vals, approved)

        def refuse():
            found = self.list_of(skill["values"][k]["kind"])
            return self.ask_value(skill, vals, k, approved, self.not_there(skill, k, v.get("text") or v["label"], found), self.chips(found))

        self.question("fuzzy", yes=take, no=refuse, options=[(v["label"], take)],
                      otherwise=lambda: setattr(self, "pending", {"waiting": "value", "skill": skill, "vals": vals, "slot": k, "approved": approved}))
        return {"outcome": "ask", "skill": skill["id"], "say": self.reply("did you mean", {"value": v["label"]}), "chips": [v["label"], self.yes_no[1]]}

    def find_files(self, skill, vals, approved):
        """Files are checked on the device. A file to open must exist: here, or else anywhere in home
        (one place: "That one?"; several: "Which one?"; none: said so)."""
        if not self.device or not hasattr(self.device, "files"):
            return None
        place_key = next((k for k, s in skill["values"].items() if s["kind"] == "@sys.folder"), None)
        place = vals.get(place_key) if place_key else None
        k = next((k for k, s in skill["values"].items() if s["kind"] == "@sys.file" and vals.get(k) and vals[k].get("value") is None), None)
        if not place or not k:
            return None
        name = vals[k]["text"]
        lower, has_ext = name.lower(), bool(re.search(r"\.\w+$", name))
        stem = lambda f: re.sub(r"\.[^.]+$", "", f)
        same = lambda f: f.lower() == lower or (not has_ext and stem(f).lower() == lower)
        files = self.device.files(place["value"])
        hit = next((f for f in files if same(f)), None)
        if hit:
            vals[k] = {"value": hit, "label": hit}
            return None
        typo = next((f for f in files if close(lower, f.lower()) or (not has_ext and close(lower, stem(f).lower()))), None)
        if typo:
            vals[k] = {"value": typo, "label": typo, "text": name, "fuzzy": True}
            return self.next_step(skill, vals, approved)
        elsewhere = [r for r in self.device.find(same) if r["folder"] != place["value"]]
        named = not elsewhere and self.device.find(lambda f: lower in f.lower())  # none by that name: the files it is part of, as find file finds them
        elsewhere = elsewhere or named

        def there(r):
            vals[k], vals[place_key] = {"value": r["file"], "label": r["file"]}, {"value": r["folder"], "label": r["label"]}
            return lambda: self.next_step(skill, vals, approved)

        if len(elsewhere) == 1:
            r = elsewhere[0]
            self.question("elsewhere", yes=lambda: there(r)(), no=lambda: self.declined(skill))
            say = self.reply("did you mean", {"value": r["file"]}) if named else self.reply("elsewhere", {"file": r["file"], "here": place["label"], "folder": r["label"]})
            return {"outcome": "ask", "skill": skill["id"], "say": say, "chips": self.yes_no}
        if elsewhere:
            labels = [r["file"] if named else r["label"] for r in elsewhere]
            self.question("where", no=lambda: self.declined(skill), options=[(l, lambda r=r: there(r)()) for l, r in zip(labels, elsewhere)])
            return {"outcome": "ask", "skill": skill["id"], "say": self.reply("several named" if named else "several", {"count": len(elsewhere), "file": name if named else elsewhere[0]["file"], "folders": ", ".join(labels)}), "chips": labels}
        self.pending = None
        return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("not found", {"file": name, "here": place["label"]}), "reason": "not found"}

    def already_there(self, skill, vals):
        """A new name never replaces what is there. The folder it goes into is the one written before it
        in the command ({place}/{name}); a new name without an extension keeps the old file's
        (rename notes.md to ideas → ideas.md)."""
        if not self.device or not hasattr(self.device, "exists"):
            return None
        old = next((vals[k] for k, s in skill["values"].items() if s["kind"] == "@sys.file" and vals.get(k)), None)
        for k, spec in skill["values"].items():
            v = vals.get(k)
            if not spec.get("new") or not v or not v.get("text"):
                continue
            ext = re.search(r"\.\w+$", str(old.get("value") or "")) if old else None
            if ext and not re.search(r"\.\w+$", v["text"]):
                vals[k] = v = {"text": v["text"] + ext.group(0)}
            m = re.search(r"\{(\w+)\}/\{%s\}" % k, skill["command"])
            folder = vals.get(m.group(1)) if m else None
            if folder and self.device.exists(folder["value"] + "/" + v["text"]):
                self.pending = None
                return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("already", {"file": v["text"], "folder": folder["label"]}), "reason": "already exists"}
        return None

    def finish_filetype(self, skill, vals):
        """A file's name gets the extension of its type, unless it already has a known one (seed.md)."""
        type_key = next((k for k, s in skill["values"].items() if s["kind"] == "filetype"), None)
        name_key = next((k for k, s in skill["values"].items() if s.get("new") and s["kind"] == "text"), None)  # the new name, whatever it is called
        if not type_key or not name_key or not vals.get(name_key):
            return
        name = vals[name_key]["text"]
        m = re.search(r"\.(\w+)$", name)
        known = next((t for t in self.lists["filetypes"] if t["ext"] == (m.group(1).lower() if m else "")), None)
        if known:
            vals[type_key] = {"value": known["value"], "label": known["label"]}
            return
        said = vals.get(type_key) or {}
        kind = next((t for t in self.lists["filetypes"] if t["value"] in (said.get("value"), said.get("text"))), self.lists["filetypes"][0])
        vals[name_key] = {"text": "%s.%s" % (name, kind["ext"])}

    def topics(self, exclude=None):
        """the skills by topic (words/objects.md, Topics), the most ordinary actions first (the order of
        words/actions.md: check, show, find, create…); a topic with no objects holds the rest"""
        order = {a: i for i, a in enumerate(self.lists["actions"])}
        out, shown = [], set()
        for topic, objects in self.lists.get("topics", []):
            found = [s for s in self.skills if (s["object"] in objects or not objects) and s["id"] not in shown and s is not exclude]
            shown.update(s["id"] for s in found)
            rank = {o: i for i, o in enumerate(objects)}
            found.sort(key=lambda s: (order.get(s["action"], 99), rank.get(s["object"], 99)))
            if found:
                out.append((topic, found))
        return out

    def help(self, skill):
        """One line per topic: two of its skills, and how many more; the topics as chips, a tap shows the topic
        whole (24 Oct, Gab: "perhaps we could try a denser version")."""
        topics = self.topics(exclude=skill)
        rows = []
        for topic, found in topics:
            first = [found[0]] + [s for s in found[1:] if s["object"] != found[0]["object"]][:1] or found[:2]
            first = (first + [s for s in found if s not in first])[:2]
            more = len(found) - len(first)
            rows.append([topic, ", ".join(s["label"] for s in first) + (" " + self.reply("and more", {"count": more}) if more else "")])

        def whole(topic, found):
            def show():
                ask()  # the other topics stay a tap away
                return {"outcome": "act", "skill": skill["id"], "say": self.reply("help topic", {"topic": topic}),
                        "table": {"columns": [""], "rows": [[s["label"]] for s in found]}, "chips": [t for t, _ in topics if t != topic]}
            return show

        def ask():
            self.question("topic", options=[(topic, whole(topic, found)) for topic, found in topics])

        ask()
        return {"outcome": "act", "skill": skill["id"], "say": self.reply(skill["replies"]["done"]),
                "table": {"columns": ["", ""], "rows": rows}, "chips": [t for t, _ in topics]}

    def display(self, skill, vals):
        out = {"output": "{output}"}
        for k, v in vals.items():
            out[k] = "•••" if skill["values"][k]["kind"] == "secret" else (v.get("label") if v.get("label") is not None else v.get("text"))
        return out

    def command_for(self, skill, vals):
        def value(m):
            v = vals.get(m.group(1))
            return "" if not v else str(v["value"] if v.get("value") is not None else v.get("text", ""))
        return " ".join(quote(re.sub(r"\{(\w+)\}", value, p)) if "{" in p else p for p in skill["command"].split(" "))

    def with_show(self, out, skill, vals):
        """"show commands" on: the command is shown when acting, and before it, when the person approves"""
        if self.on("show commands"):
            out["show"] = self.command_for(skill, vals)
        return out

    def act(self, skill, vals):
        self.pending = None
        if skill.get("trains"):  # the server trains the model again, in the background (server.py, train)
            return {"outcome": "act", "skill": skill["id"], "trains": True, "say": self.reply(skill["replies"]["done"])}
        if skill.get("opens"):  # a panel of the page: the settings' toggles
            return {"outcome": "act", "skill": skill["id"], "opens": skill["opens"], "say": self.reply(skill["replies"]["done"])}
        if skill.get("lists") == "skills":  # help: what TermNL can do, by topic (words/objects.md, Topics)
            return self.help(skill)
        if skill.get("changes"):  # a setting, changed here at once; the server writes it to settings.md
            key, value = skill["changes"]
            value = fill(value, {k: v.get("text") or v.get("label") for k, v in vals.items()}).strip()
            if key == "name" and value == value.lower():  # "call me gab" → Gab; "McKenzie" stays as written (Gab, 24 Oct)
                value = " ".join(w[:1].upper() + w[1:] for w in value.split())
                vals = {k: {"text": value} if k == "name" else v for k, v in vals.items()}
            self.settings[key] = value
            return {"outcome": "act", "skill": skill["id"], "changes": {key: value},
                    "say": self.reply(skill["replies"]["done"], self.display(skill, vals))}
        self.remember(skill, vals)  # what a follow-up may point at ("now delete it")
        if skill["moves"] and vals.get(skill["moves"]):
            v = vals[skill["moves"]]
            self._here = {"value": v["value"], "label": v["label"]}
        if skill["reads"]:  # the device reads itself; the reply is chosen once it has (server.py)
            args = {k: v["value"] if v.get("value") is not None else v.get("text") for k, v in vals.items()}
            for k, spec in skill["values"].items():  # a kind of file is read by its extensions (readers.py, files)
                t = next((t for t in self.lists["filetypes"] if t["value"] == args.get(k)), None) if spec["kind"] == "filetype" else None
                if t:
                    args[k] = ",".join(t.get("exts", [t["ext"]]))
            out = {"outcome": "act", "skill": skill["id"], "say": "", "reads": skill["reads"], "args": args, "values": self.display(skill, vals)}
            if skill["command"]:  # a reader of the command's output (check wifi: iw)
                out["command"] = self.command_for(skill, vals)
                self.with_show(out, skill, vals)
            return out
        out = self.with_show({"outcome": "act", "skill": skill["id"], "say": self.reply(skill["replies"]["done"], self.display(skill, vals)),
                              "command": self.command_for(skill, vals)}, skill, vals)
        secret = next((vals[k]["text"] for k, v in skill["values"].items() if v["kind"] == "secret" and vals.get(k)), None)
        if secret is not None:  # read by the command on its standard input, never written in it (skills.py)
            out["given"] = secret
        return out

    def waits_for_secret(self):
        """the question waiting asks for a password: the next sentence is one, never logged nor searched"""
        p = self.pending
        return bool(p and p["waiting"] == "value" and p["skill"]["values"][p["slot"]]["kind"] == "secret")




def better(v, u):
    """the corrected sentence reads better than the typed one: it is read at all, or by a template, or with more
    values the device has (Gab, 23 Oct: "gab.md insde Documents" was a name until "inside" was read), or closer"""
    known = lambda r: sum(1 for x in r.get("vals", {}).values() if x.get("value") is not None)
    return not u or v["how"] == "template" and u["how"] != "template" or v["how"] == u["how"] == "template" and known(v) > known(u) \
        or v["how"] == "said" and u["how"] == "said" and v["p"] > u["p"]


def told(r, u):
    """how the sentence was understood, with the reply: by a template, or the model and how sure"""
    r["how"] = u["how"]
    if u.get("p") is not None:
        r["p"] = round(u["p"] * 100) / 100
    if u.get("unknown"):
        r["unknown"] = u["unknown"]
    return r


def noted(r, fixes, agent):
    """the typos read as words, said with the reply: "I read “chek” as “check”." """
    if fixes:
        r["corrections"] = fixes
        read = [agent.reply("a word read as", {"typed": agent.quoted(a), "word": agent.quoted(b)}) for a, b in fixes]
        r["note"] = agent.reply("read as", {"fixes": ", ".join(read)})
        if r.get("say"):
            r["say"] = r["note"] + " " + r["say"]
    return r
