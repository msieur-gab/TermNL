"""The dialogue, written as one turn in five steps (since 22 Oct 2026; the version before it, back_agent.py,
was retired on 25 Oct 2026 and stays in git's history).

Every request ends in one of four outcomes:
  act      understood, everything known, nothing to approve: the command is ready to run
  ask      a value is missing or isn't on the device, or the request isn't surely understood:
           a question, with chips when there are choices
  approve  the action is destructive or needs admin rights: the person approves first
  abstain  nothing understood, or the settings don't allow it: the agent says so

One turn (respond):
  1. clean       fillers off ("please", "can you"…)
  2. answer      a question is waiting: yes, no, one of its chips, or a value for "Which one?"
  3. understand  a skill's sentence reads the words exactly (exact); else the tagger says what each word
                 is and the classifier which skill the whole sentence asks for, how surely (read); a typo
                 is read as a known word when that reads better (correct); an action said alone ("turn
                 off"), or two skills too close to tell, the person chooses; a sentence that says part
                 of a request ("now delete it", "and in downloads?") is completed by the last request
                 done, its frame (follow_up)
  4. safety      not sure, a typo in a change, "don't…": ask before anything
  5. next_step   the next value to ask, a file to find, the settings, the approval; or act

The agent never runs anything and never writes a command: it fills in the command a skill declares,
with every value quoted. Running it is the device's job (runner.py)."""
import random as _random
import re

from .model import classify, features
from .tagger import FILE_RE, FOLDERS, NAMES, decode, role_of, same_family, spans
from .template import best, parses, uses
from .text import close, fill, pick, tokenize, words
from .train import context


def sq(s):
    return "'" + str(s).replace("'", "'\\''") + "'"


def quote(p):
    """a path's leading $HOME stays outside the quotes, so the shell still expands it"""
    if p.startswith("$HOME"):
        return "$HOME" + (sq(p[5:]) if len(p) > 5 else "")
    return sq(p)


# how sure the classifier must be of a skill: to act, and to ask at all; how far ahead of the next skill
# it must be to act; and how close two skills may be before the person is asked which
SURE, MAYBE, MARGIN, CHOOSE = 0.6, 0.15, 0.2, 0.05
# how much of a sentence (its words that aren't small) a skill must know, as its own words or as values, to
# be asked about at all: "what gift should I buy my wife" is nobody's
KNOWN = 0.3


def at(toks, phrase, i):
    """the phrase's words are the sentence's words from i"""
    return 0 < len(phrase) and i + len(phrase) <= len(toks) and all(toks[i + j]["word"] == w for j, w in enumerate(phrase))


def where(toks, phrase):
    return [i for i in range(len(toks)) if at(toks, phrase, i)]


def best_in(toks, found, fuzzy=False):
    """the longest phrase of a list said in the sentence (a typo of one too, when fuzzy, exact first)
    → {o, i, len, fuzzy} or None"""
    hit = None
    for o in found:
        for ph in o["phrases"]:
            for i in range(len(toks) - len(ph) + 1):
                exact = at(toks, ph, i)
                near = fuzzy and not exact and all(close(toks[i + j]["word"], w) for j, w in enumerate(ph))
                if (exact or near) and (not hit or len(ph) > hit["len"] or (exact and hit["fuzzy"])):
                    hit = {"o": o, "i": i, "len": len(ph), "fuzzy": near}
    return hit


class Agent:
    def __init__(self, lists, skills, model=None, settings=None, device=None, random=_random.random, **_):
        self.lists, self.skills, self.model = lists, skills, model
        self.settings = settings if settings is not None else {}
        self.device, self.random = device, random
        self._sys = {}  # kind → (the device's list, its values with their words)
        self.pending = None  # the question waiting for an answer
        self._here = None  # where you are, like a terminal's working folder: home at first
        self.frame = None  # the last request done: its skill, its values, and the thing it touched (follow_up)
        self._ctx = None  # what the tagger looks up on this device (context)
        # skill → the actions its Also said lines say it with ("copy movie.mkv over to the studio pi" is sending it),
        # and the objects its sentences name: its own, and any other it mentions ("unmute the sound/music")
        phrases = {name: {" ".join(p) for p in lists["refs"].get(name, [])} for name in lists["actions"] + lists["objects"]}
        self.actions_of, self.objects_of = {}, {}
        for s in skills:
            also = words_of(s["also"])
            self.actions_of[s["id"]] = {a for a in lists["actions"] if also & phrases[a]}
            self.objects_of[s["id"]] = {s["object"]} | {r for nodes in s.get("compiled", []) for r in uses(nodes)["refs"] if r in lists["objects"]} \
                | {o for o in lists["objects"] if also & phrases[o]}
        # skill → the phrases that mean its action with its object (## Words: "turn on, start → play"), for exact
        self.means = {}
        for s in skills:
            for rule in lists.get("in_context", []):
                if rule["action"] == s["action"] and s["object"] in rule["objects"]:
                    self.means.setdefault(s["id"], []).extend(ph for ph in rule["phrases"] if ph not in lists["refs"].get(s["action"], []))
        said = lists["conversation"]
        self.words = lambda key: said.get(key, [])
        joined = lambda key: {" ".join(p) for p in said.get(key, [])}
        self.small, self.stops, self.pointing = joined("small words"), joined("not a name start"), joined("pointing words")
        self.places, self.reading = joined("before a place"), joined("reading actions")
        self.follows = {w for ph in said.get("follow-up words", []) for w in ph}
        self.many = joined("pointing at several")
        self.name_ends = joined("name ends before")  # … called bikes | in documents
        self.leads = {ph[0] for ph in said.get("before a name", []) if len(ph) == 1}  # called, named, titled
        # the chips that answer a yes/no question: the first word of each list
        self.yes_no = [" ".join(said["yes"][0]), " ".join(said["no"][0])]
        self.object_words = {ph[0] for o in lists["objects"] for ph in lists["refs"].get(o, []) if len(ph) == 1}
        # every word TermNL knows how to read: a typo of one of them is read as it (correct)
        self.vocab = {w for phs in list(lists["refs"].values()) + list(said.values()) for ph in phs for w in ph}
        self.vocab |= {w for t in lists["filetypes"] for ph in t["phrases"] for w in ph}
        self.vocab |= {w for s in skills for nodes in s.get("compiled", []) for w in _template_words(nodes)}

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
        """files aren't a list read in advance: they are looked up in the place once it is known"""
        if kind == "filetype":
            return self.lists["filetypes"]
        if kind.startswith("@sys.") and kind != "@sys.file":
            return self.sys(kind[5:])
        return None

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
        """what the person typed for these words (a name keeps its typos and capitals)"""
        return text.translate(str.maketrans({"’": "'", "‘": "'", "`": "'"}))[toks[start]["start"]:toks[end - 1]["end"]]

    # ---- one turn of the conversation

    def hear(self, text):
        return self.respond(text)

    def respond(self, text):
        # 1. clean
        toks = self.clean(text)
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

        # 3. understand
        typed = toks
        u = self.understand(text, toks)
        if u:
            toks = u["toks"]

        # 2, still: "Which one?" is answered by a value, unless the person clearly asks for something else
        p = self.pending
        if p and p["waiting"] == "value":
            says_action = any(where(toks, ph) for a in self.lists["actions"] for ph in self.lists["refs"].get(a, []))
            other = u and u["sure"] and u["skill"]["id"] != p["skill"]["id"] and (u["how"] == "template" or says_action)
            if not other:
                return self.fill_value(text, typed, u)  # the words as typed: a name is never cut from words re-ordered for reading

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

    # ---- 1. clean

    def clean(self, text):
        """Fillers ("please", "can you", "for me") are dropped at the start and end of a sentence."""
        toks = tokenize(text)
        changed = True
        while changed:
            changed = False
            for ph in self.words("filler start"):
                if len(toks) > len(ph) and at(toks, ph, 0):
                    toks, changed = toks[len(ph):], True
            for ph in self.words("filler end"):
                if len(toks) > len(ph) and at(toks, ph, len(toks) - len(ph)):
                    toks, changed = toks[:-len(ph)], True
        return toks

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
        return self.reply(own, {slot: self.quoted(said)}) if own and found else self.reply("unknown value", {"value": self.quoted(said)})

    def fill_value(self, text, toks, u):
        """An answer to "Which one?" or "What should I call it?". The same request said again adds its
        values; "no" stops; "yes" asks again; "call it bikes" gives the name after its lead-in words
        (conversation.md, "before a name"); a value on the list, or free text for a name."""
        p = self.pending
        skill, vals, slot, approved = p["skill"], p["vals"], p["slot"], p["approved"]
        if u and u["sure"] and u["skill"]["id"] == skill["id"]:
            spec = skill["values"][slot]
            if slot not in u["vals"] and spec.get("default") and (vals.get(slot) or {}).get("unknown"):
                del vals[slot]  # "list my files" after "Which one?": said without it, its default applies
                self.pending = None
                return self.next_step(skill, vals, approved)
            for k, v in u["vals"].items():
                if not vals.get(k) or vals[k].get("unknown"):
                    vals[k] = v
            if vals.get(slot):
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
            start = max((len(ph) for ph in self.words("before a name") if len(ph) < len(toks) and at(toks, ph, 0)), default=0)
            vals[slot] = {"text": self.original(text, toks, start, len(toks))}
            return self.next_step(skill, vals, approved)
        hit = best_in(toks, found)
        if not hit:
            return {"outcome": "ask", "skill": skill["id"], "say": self.not_there(skill, slot, text.strip(), found), "chips": self.chips(found)}
        vals[slot] = {"value": hit["o"]["value"], "label": hit["o"]["label"]}
        return self.next_step(skill, vals, approved)

    # ---- 3. understand

    def understand(self, text, toks):
        """What the sentence asks for → {how, skill, vals, p, unknown, sure, fixes, toks}, or None.
        A skill's sentence that reads the words exactly is trusted (how: template; several tied: the
        person chooses), unless it is weak and the classifier is sure of another skill. Otherwise the tagger
        says what each word is and the classifier which skill the whole sentence asks for, with how surely
        (how: model). A typo is read as a known word only when the sentence as typed isn't read exactly, or
        when the corrected sentence reads a place the typo had hidden in a name."""
        u = self.exact(text, toks)
        fixed, fixes = self.correct(toks)
        if fixes:
            v = self.exact(text, fixed)
            if v and (not u or u["how"] != "template" or self.hid_a_place(u, v)):
                v["fixes"], v["toks"] = fixes, fixed
                u = v
        if u and u["how"] == "template" and self.weak(u):
            # read exactly, but for a value the device doesn't have, or free text where a name should be ("show me
            # what's inside the downloads folder" fits show-type's sentence, with "what's inside" as the type; "create
            # a note.md in the Documents folder" fits create-folder's, with a file's name). When the classifier is sure
            # of another skill, the person chooses between the two.
            r = self.read(text, u["toks"] if "toks" in u else toks)
            if r and r["how"] == "model" and r["skill"] is not u["skill"] and r["p"] >= SURE and not self.weak(r):
                u = {"how": "choose", "options": [{"skill": r["skill"], "vals": r["vals"]}, {"skill": u["skill"], "vals": u["vals"]}],
                     "toks": u.get("toks", toks), "fixes": u.get("fixes", []), "sure": False}
        if not u:
            u = self.read(text, toks)
            if fixes:
                v = self.read(text, fixed)
                if v and (not u or u["how"] == "choose" or v["how"] != "choose" and v["p"] > u["p"] and len(v["unknown"]) <= len(u["unknown"])):
                    v["fixes"], v["toks"] = fixes, fixed
                    u = v
        if u and u["how"] != "choose":
            self.as_file(u)
        if u:
            u.setdefault("fixes", [])
            u.setdefault("toks", toks)
            u["sure"] = u["how"] == "template" or (u["how"] == "model" and u["p"] >= SURE and u["margin"] >= MARGIN and not u["unknown"])
        return u

    def as_file(self, u):
        """a new name ending in a known file type (note.md, words/filetypes.md) is a file: the same action on a
        file, never on a folder (Gab, 23 Oct: "create a note.md in the Documents folder" was a folder called note.md)"""
        skill = u["skill"]
        exts = {x for t in self.lists["filetypes"] for x in t.get("exts", [t["ext"]])}
        named = [v for k, v in u["vals"].items() if skill["values"][k].get("new") and v.get("text")]
        if skill["object"] != "folder" or not any("." in v["text"] and v["text"].rsplit(".", 1)[1].lower() in exts for v in named):
            return
        other = next((s for s in self.skills if s["action"] == skill["action"] and s["object"] == "file"), None)
        if other:
            u["skill"], u["vals"] = other, {k: v for k, v in u["vals"].items() if k in other["values"]}

    @staticmethod
    def weak(u):
        """an exact reading that leans on a value it couldn't check: a listed value the device doesn't have, or
        free text taken as a name"""
        return any(v.get("unknown") or v.get("value") is None for v in u["vals"].values())

    def exact(self, text, toks):
        """a skill's sentence that reads the words exactly, its values in their places (several, if they
        tie: "choose"), or None"""
        found, refs = [], self.lists["refs"]
        for skill in self.skills:
            # the words that mean the skill's action with its object (## Words: "turn on → play") read as the action
            # when the object is said ("turn on the music"), with or without a model
            mine = refs
            extra = self.means.get(skill["id"])
            if extra and any(where(toks, ph) for ph in refs.get(skill["object"], [])):
                mine = {**refs, skill["action"]: refs.get(skill["action"], []) + extra}
            every = []
            for nodes in skill["compiled"]:
                every += parses(nodes, toks, mine, {k: self.list_of(v["kind"]) for k, v in skill["values"].items()},
                                self.stops, self.object_words, self.places)
            if every:
                found.append((skill, best(every)))
        top = max((p["score"] for _, p in found), default=0)
        if not found or top < 1:
            return None
        tops = [{"skill": s, "vals": {k: {"text": self.original(text, toks, c["start"], c["end"]), "value": c.get("value"), "label": c.get("label"),
                                          "unknown": bool(c.get("unknown")), "fuzzy": bool(c.get("fuzzy"))} for k, c in p["caps"].items()}}
                for s, p in found if p["score"] == top]
        # a word TermNL knows as an object (bluetooth, wifi) is that object, not a name on the device's list
        # (Gab, 22 Oct: "is bluetooth on" is the board's Bluetooth, not the service called bluetooth)
        if len(tops) > 1:
            tops = [t for t in tops if not any(v["text"].lower() in self.object_words for v in t["vals"].values())] or tops
        if len(tops) == 1:  # … and when a skill does the same action on that object, the person chooses (24 Oct: "is
            # bluetooth running" was a service called bluetooth on a laptop that has one, or the board's Bluetooth)
            t = tops[0]
            named = {v["text"].lower() for v in t["vals"].values() if v.get("value") is not None or v.get("unknown")}
            objects = {o for o in self.lists["objects"] for ph in self.lists["refs"].get(o, []) if " ".join(ph) in named}
            others = [s for s in self.skills if s["action"] == t["skill"]["action"] and s["object"] in objects and s is not t["skill"]]
            if others:
                tops = tops + [{"skill": s, "vals": {}} for s in others]
        return {"how": "choose", "options": tops} if len(tops) > 1 else {"how": "template", **tops[0], "p": 1, "unknown": []}

    @staticmethod
    def hid_a_place(u, v):
        """a typo inside a name hid a place (Gab, 23 Oct: "add a new file call gab.md insde Documents" made a file
        named "gab.md insde Documents.md"): corrected, the same skill reads a value the device has, a folder, that
        the name had swallowed. The name itself is still never corrected: it is what comes before the place."""
        return v["how"] == "template" and v["skill"]["id"] == u["skill"]["id"] and any(
            k not in u["vals"] and x.get("value") is not None and not x.get("unknown") for k, x in v["vals"].items())

    def context(self):
        """what the tagger looks up on this device: its folders, services, apps… as words (train.context)"""
        kinds = ("folder", "service", "network", "app", "running", "music", "host")
        lists = {k: self.sys(k) for k in kinds}
        key = tuple(id(v) for v in lists.values())
        if self._ctx is None or self._ctx[0] != key:
            found = {k: {w for d in v for ph in d["phrases"] for w in ph} for k, v in lists.items()}
            found["type"] = {w for t in self.lists["filetypes"] for ph in t["phrases"] for w in ph}
            self._ctx = (key, context(self.lists, found, self.model["vocab"]))
        return self._ctx[1]

    def tag(self, toks):
        """what each word is (tagger.py): A, O, V:role or _"""
        t = self.model["tagger"]
        return decode(t["weights"], t["tags"], [x["word"] for x in toks], self.context())

    def read(self, text, toks):
        """the tagger's and the classifier's reading → {how: model, skill, vals, p, margin, unknown}; an action
        said alone, or skills too close to tell apart, → {how: choose, options}; nothing → None"""
        if not self.model:
            return None
        ws = [t["word"] for t in toks]
        tags = self.tag(toks)
        acts = self.actions_said(toks, tags)
        bare = self.bare(toks, tags, acts)
        if bare:
            return bare
        ranked = classify(self.model["skill"], features(ws, tags))
        none = next((r["p"] for r in ranked if r["label"] == "none"), 0)
        by_id = {s["id"]: s for s in self.skills}
        # an action said in so many words is the action done ("turn the board on" is never shutting it down), or
        # what a skill says those words mean with its object (## Words: "turn on → play", for the music)
        objs = self.objects_said(toks, tags)
        found = [(by_id[r["label"]], r["p"]) for r in ranked if r["label"] in by_id and self.does(by_id[r["label"]], acts, toks, tags, objs)]
        if not found:
            return None
        # the skills that don't do what was said are out, and the rest share the odds: "the music server is stuck,
        # restart it" is restart a service, however much "stuck" sounded like stopping a process. Only to be asked
        # about, though: to act, a skill needs the classifier's own confidence (sure, below)
        total = sum(q for _, q in found) + none
        skill, p = found[0]
        if p / total < MAYBE or none > p:
            return None
        second = found[1][1] if len(found) > 1 else 0.0
        close = [s for s, q in found if q >= p - CHOOSE * total]
        if 2 <= len(close) <= 8:
            return {"how": "choose", "options": [{"skill": s, "vals": self.slots(s, text, toks, tags)[0]} for s in close],
                    "toks": toks, "fixes": [], "sure": False, "p": p}
        vals, used = self.slots(skill, text, toks, tags)
        taught = set(self.model["taught"].get(skill["id"], []))
        negation = {w for ph in self.words("negation") for w in ph}  # handled by its own rule
        new = [i for i, t in enumerate(toks) if i not in used and t["word"] not in self.small | taught | negation | self.pointing]
        telling = [i for i, t in enumerate(toks) if t["word"] not in self.small | self.pointing]
        if telling and 1 - len([i for i in new if i in telling]) / len(telling) < KNOWN:
            return None
        # the new words, side by side, are the value the skill still lacks from the device's list ("kill pipewire":
        # no app of that name): kept as said, so it is answered as not there, never asked for again (Gab, 24 Oct)
        missing = [k for k, spec in skill["values"].items() if k not in vals and spec["required"] and not spec.get("default")]
        if len(missing) == 1 and skill["values"][missing[0]]["kind"].startswith("@sys.") and self.list_of(skill["values"][missing[0]]["kind"]) is not None \
                and new and new == list(range(new[0], new[-1] + 1)):
            vals[missing[0]] = {"text": self.original(text, toks, new[0], new[-1] + 1), "unknown": True}
            if p >= SURE:
                new = []
        return {"how": "model", "skill": skill, "vals": vals, "p": p, "margin": p - second, "unknown": [toks[i]["word"] for i in new], "tags": tags}

    def does(self, skill, acts, toks, tags, objs=()):
        """the skill does an action said in so many words (any of them), or its ## Words say the words said mean
        its action with its object, and its sentences name an object said in so many words ("turn the board on"
        is nothing the Wi-Fi does); nothing said in so many words: any skill"""
        if objs and not any(o in self.objects_of[skill["id"]] for o in objs):
            return False
        if not acts or skill["action"] in acts or any(a in self.actions_of[skill["id"]] for a in acts):
            return True
        if not any(where(toks, ph) for ph in self.lists["refs"].get(skill["object"], [])):
            return False
        return any(skill["object"] in rule["objects"] and rule["action"] == skill["action"] and any(self.says(toks, tags, ph) for ph in rule["phrases"])
                   for rule in self.lists.get("in_context", []))

    def bare(self, toks, tags, acts):
        """An action said without its object ("turn on", "switch it off"): the person chooses among the skills
        that do it, those of the action and those the action means with an object (a skill's ## Words: "turn
        off" also stops the music). Only when nothing else is said but small and pointing words, and two to
        eight skills fit, as many as the chips show."""
        if not acts or any(t == "O" or t.startswith("V:") for t in tags):
            return None
        if any(t == "_" and tok["word"] not in self.small | self.pointing for t, tok in zip(tags, toks)):
            return None
        refs = self.lists["refs"]
        pairs = {(a, s["object"]) for a in acts for s in self.skills if s["action"] == a}
        spoken = [ph for a in acts for ph in refs[a] if self.says(toks, tags, ph)]
        for rule in self.lists.get("in_context", []):
            if any(ph in spoken for ph in rule["phrases"]):
                pairs |= {(rule["action"], o) for o in rule["objects"]}
        fit = [s for s in self.skills if (s["action"], s["object"]) in pairs]
        if not 2 <= len(fit) <= 8:
            return None
        return {"how": "choose", "options": [{"skill": s, "vals": {}} for s in fit], "toks": toks, "fixes": [], "sure": False}

    def slots(self, skill, text, toks, tags):
        """The skill's values, from the words the tagger says are values: each value takes the span of its
        role (a folder something goes to, a file, a new name…), else one of its family (any folder, any
        name). A value from a list is looked up on it: found, or a typo of one (fuzzy), or not there
        (unknown, said as typed). A list value the tagger missed is still found by its name in the sentence.
        → (vals, the positions used)"""
        ws = [t["word"] for t in toks]
        if tags is None:  # no model yet (a language just dropped in): a file by its shape, a name after "called", lists below
            found = [("file", i, i + 1) for i, w in enumerate(ws) if FILE_RE.match(w)]
            lead = next((i for i, w in enumerate(ws) if w in self.leads), None)
            if lead is not None and lead + 1 < len(ws) and not found:
                end = next((j for j in range(lead + 1, len(ws)) if ws[j] in self.name_ends), len(ws))
                found.append(("name", lead + 1, end))
        else:
            found = [("file", i, j) if all(FILE_RE.match(w) for w in ws[i:j]) else (r, i, j) for r, i, j in spans(ws, tags)]  # a file's name has its shape
        taken, vals, used = set(), {}, set()
        roles = {k: role_of(k, spec) for k, spec in skill["values"].items()}
        for fam in (set(FOLDERS), set(NAMES)):
            # one value of a family said ("put report.pdf in documents": one folder), one the skill can't do without
            # (move file: where to): that one, whatever the tagger called it
            said = [x for x in found if x[0] in fam]
            must = [k for k, spec in skill["values"].items() if roles[k] in fam and spec["required"] and not spec.get("default")]
            if len(said) == 1 and len(must) == 1:
                roles[must[0]] = said[0][0]
        for pick_family in (False, True):
            for k, spec in skill["values"].items():
                if k in vals:
                    continue
                hit = next((x for x in found if x not in taken and (x[0] == roles[k] if not pick_family else same_family(x[0], roles[k]))), None)
                if not hit:
                    continue
                taken.add(hit)
                _, i, j = hit
                if spec["kind"] == "text" and self.after_a_place_word(ws, i):
                    continue  # "make a folder for my bike photos": what follows "for" is not the name (22 Oct)
                listed = self.list_of(spec["kind"])
                if listed is not None:
                    on = best_in(toks, listed, fuzzy=True)
                    if on and on["i"] < j and on["i"] + on["len"] > i:  # the listed name, where the tagger saw a value
                        vals[k] = {"value": on["o"]["value"], "label": on["o"]["label"], "fuzzy": on["fuzzy"]}
                        used.update(range(on["i"], on["i"] + on["len"]))
                    else:
                        vals[k] = {"text": self.original(text, toks, i, j), "unknown": True}
                        used.update(range(i, j))
                else:
                    vals[k] = {"text": self.original(text, toks, i, j)}
                    used.update(range(i, j))
        for k, spec in skill["values"].items():  # a listed name said, that the tagger didn't read as a value
            listed = self.list_of(spec["kind"])
            if k in vals or listed is None:
                continue
            on = best_in([t if n not in used else {"word": ""} for n, t in enumerate(toks)], listed)
            if on:
                vals[k] = {"value": on["o"]["value"], "label": on["o"]["label"]}
                used.update(range(on["i"], on["i"] + on["len"]))
        return vals, used

    def after_a_place_word(self, ws, i):
        """the words before position i, articles apart, end in a word a name never starts after ("in", "for", "with":
        conversation.md, "not a name start")"""
        while i > 0 and ws[i - 1] in ("the", "a", "an", "my"):
            i -= 1
        return i > 0 and ws[i - 1] in self.stops

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
        ws = [t["word"] for t in toks]
        follows = [ph for ph in self.words("follow-up words") if where(toks, ph)]
        if not follows and not any(w in self.pointing for w in ws):
            return None
        if any(w in self.many for w in ws):  # "delete them" after a folder was shown means its files, never the folder
            return None
        refs, lists, frame = self.lists["refs"], self.lists, self.frame
        tags = self.tag(toks) if self.model else None
        acts = self.actions_said(toks, tags)  # with the tags, "turn it off" says turn off
        objs = {o for o in lists["objects"] for ph in refs.get(o, []) if where(toks, ph)}
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
                if obj in rule["objects"] and any(self.says(toks, tags, ph) for ph in rule["phrases"]):
                    skill = next((s for s in self.skills if (s["action"], s["object"]) == (rule["action"], obj)), None)
                    allowed |= {w for ph in rule["phrases"] for w in ph}
                    break
        if not skill or skill.get("changes") or skill.get("lists") or skill.get("trains") or skill.get("opens"):
            return None
        vals, _ = self.slots(skill, text, toks, tags)
        if u and u.get("vals") and u.get("skill") and u["skill"]["action"] == skill["action"]:
            # what a template read in the sentence ("rename it to cycles": the new name), where the skill has it too
            for k, v in u["vals"].items():
                if k in skill["values"] and skill["values"][k]["kind"] == u["skill"]["values"][k]["kind"] and not self.only_points(v):
                    vals[k] = v
        allowed |= {w for v in vals.values() for w in words(v.get("text") or v.get("label") or "")}
        allowed |= self.small | self.pointing | self.follows
        if any(w not in allowed for w in ws):
            return None
        return {"how": "frame", "skill": skill, "vals": self.carry(skill, vals), "p": 1, "unknown": [], "sure": True, "fixes": [], "toks": toks}

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

    def says(self, toks, tags, ph):
        """the phrase is said: its words together (tagged as the action, when the words are tagged: "trash" in
        "empty the trash" is the object), or apart as the words tagged as the action ("turn it back off")"""
        ph = list(ph)
        if not tags:
            return bool(where(toks, ph))
        if any(all(tags[i + j] == "A" for j in range(len(ph))) for i in where(toks, ph)):
            return True
        return [t["word"] for t, g in zip(toks, tags) if g == "A" and t["word"] not in self.follows] == ph

    def actions_said(self, toks, tags=None):
        """the actions a sentence names in so many words, each by a phrase of one action only (words/actions.md):
        "turn on" names turn on; "start" names none, as it is a word for both create and open. With the tags,
        the words of the action apart too ("turn the board on" says turn on)."""
        refs, out = self.lists["refs"], set()
        for a in self.lists["actions"]:
            for ph in refs.get(a, []):
                if self.says(toks, tags, ph) and sum(1 for b in self.lists["actions"] if ph in refs.get(b, [])) == 1:
                    out.add(a)
        return out

    def objects_said(self, toks, tags):
        """the objects a sentence names in so many words: a phrase of one object only, its words tagged as the object"""
        refs, out = self.lists["refs"], set()
        for o in self.lists["objects"]:
            for ph in refs.get(o, []):
                if any(all(tags[i + j] == "O" for j in range(len(ph))) for i in where(toks, ph)) \
                        and sum(1 for b in self.lists["objects"] if ph in refs.get(b, [])) == 1:
                    out.add(o)
        return out

    def correct(self, toks):
        """A word TermNL doesn't know, one letter away from exactly one word it knows ("chek" → "check"),
        is read as that word. The offsets stay, so a name keeps what was typed. Short words, file names
        and the device's own names are left as they are."""
        known = self.vocab | {w for kind in ("folder", "service", "app", "running") for d in self.sys(kind) for ph in d["phrases"] for w in ph}
        out, fixes = [], []
        for t in toks:
            w = t["word"]
            near = set() if w in known or len(w) < 4 or "." in w or not w.isalpha() else {v for v in self.vocab if len(v) >= 4 and close(w, v)}
            if len(near) == 1:
                fixes.append([w, next(iter(near))])
                t = {**t, "word": fixes[-1][1]}
            out.append(t)
        return out, fixes

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
        if skill["admin"] and not self.on("admin mode"):
            self.pending = None
            return {"outcome": "abstain", "skill": skill["id"], "say": self.reply("admin off"), "reason": "admin mode off"}
        if (skill["admin"] or skill["approve"]) and not approved:
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

        def there(r):
            vals[k], vals[place_key] = {"value": r["file"], "label": r["file"]}, {"value": r["folder"], "label": r["label"]}
            return lambda: self.next_step(skill, vals, approved)

        if len(elsewhere) == 1:
            r = elsewhere[0]
            self.question("elsewhere", yes=lambda: there(r)(), no=lambda: self.declined(skill))
            return {"outcome": "ask", "skill": skill["id"], "say": self.reply("elsewhere", {"file": r["file"], "here": place["label"], "folder": r["label"]}), "chips": self.yes_no}
        if elsewhere:
            labels = [r["label"] for r in elsewhere]
            self.question("where", no=lambda: self.declined(skill), options=[(r["label"], lambda r=r: there(r)()) for r in elsewhere])
            return {"outcome": "ask", "skill": skill["id"], "say": self.reply("several", {"count": len(elsewhere), "file": elsewhere[0]["file"], "folders": ", ".join(labels)}), "chips": labels}
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


def words_of(lines):
    """every word and pair of words in these lines, as phrases"""
    out = set()
    for line in lines:
        ws = words(line)
        out.update(ws)
        out.update(" ".join(ws[i:i + 2]) for i in range(len(ws) - 1))
    return out


def _template_words(nodes):
    for n in nodes:
        if n["t"] == "w":
            yield n["w"]
        elif n["t"] == "alt":
            for a in n["alts"]:
                yield from _template_words(a)


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
