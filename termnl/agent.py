"""The dialogue, written as one turn in five steps (since 22 Oct 2026; the version before it is kept
as back_agent.py, and tests/compare_agents.py checks the two still agree).

Every request ends in one of four outcomes:
  act      understood, everything known, nothing to approve: the command is ready to run
  ask      a value is missing or isn't on the device, or the request isn't surely understood:
           a question, with chips when there are choices
  approve  the action is destructive or needs admin rights: the person approves first
  abstain  nothing understood, or the settings don't allow it: the agent says so

One turn (respond):
  1. clean       fillers off ("please", "can you"…)
  2. answer      a question is waiting: yes, no, one of its chips, or a value for "Which one?"
  3. understand  a skill's template reads the sentence exactly; else the model recognises its action
                 and object; a typo is read as a known word, and a word in its context ("turn on the
                 music" plays it), when that reads better; when the model doubts a template, or an
                 action comes without its object ("turn off"), the person chooses
  4. safety      not sure, a typo in a change, "don't…": ask before anything
  5. next_step   the next value to ask, a file to find, the settings, the approval; or act

The agent never runs anything and never writes a command: it fills in the command a skill declares,
with every value quoted. Running it is the device's job (runner.py)."""
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
# how sure the model must be of another action or object to doubt a template's reading (doubts)
DOUBT = 0.6


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
        said = lists["conversation"]
        self.words = lambda key: said.get(key, [])
        joined = lambda key: {" ".join(p) for p in said.get(key, [])}
        self.small, self.stops, self.pointing = joined("small words"), joined("not a name start"), joined("pointing words")
        self.places, self.reading = joined("before a place"), joined("reading actions")
        self.name_ends = joined("name ends before")  # … called bikes | in documents
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
            self.pending = None
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
        u = self.understand(text, toks)
        if u:
            toks = u["toks"]

        # 2, still: "Which one?" is answered by a value, unless the person clearly asks for something else
        p = self.pending
        if p and p["waiting"] == "value":
            says_action = any(where(toks, ph) for a in self.lists["actions"] for ph in self.lists["refs"].get(a, []))
            other = u and u["sure"] and u["skill"]["id"] != p["skill"]["id"] and (u["how"] == "template" or says_action)
            if not other:
                return self.fill_value(text, toks, u)

        if not u:
            self.pending = None
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
        if found is None:
            start = max((len(ph) for ph in self.words("before a name") if len(ph) < len(toks) and at(toks, ph, 0)), default=0)
            vals[slot] = {"text": self.original(text, toks, start, len(toks))}
            return self.next_step(skill, vals, approved)
        hit = best_in(toks, found)
        if not hit:
            return {"outcome": "ask", "skill": skill["id"], "say": self.reply("unknown value", {"value": self.quoted(text.strip())}), "chips": self.chips(found)}
        vals[slot] = {"value": hit["o"]["value"], "label": hit["o"]["label"]}
        return self.next_step(skill, vals, approved)

    # ---- 3. understand

    def understand(self, text, toks):
        """What the sentence asks for → {how, skill, vals, p, unknown, sure, fixes, toks}, or None.
        A typo is read as a known word only when the sentence as typed isn't read by a template, and only
        if the corrected sentence reads better (by a template, or with fewer words unknown). Words are read
        in their context the same way (in_context). An action said alone asks which one (bare_action); a
        template the model doubts asks which of two skills (doubts)."""
        u = self.recognise(text, toks)
        if not u or u["how"] == "model":
            # as typed, no template reads it: the words read in their context may ("turn on the music")
            said = self.in_context(toks)
            v = self.recognise(text, said) if said is not toks else None
            if v and (not u or v["how"] != "model" or (v["p"] > u["p"] and len(v["unknown"]) <= len(u["unknown"]))):
                v["toks"] = said
                u = v
        if not u or u["how"] != "choose":
            base = u["toks"] if u and "toks" in u else toks
            fixed, fixes = self.correct(base)
            fixed = self.in_context(fixed) if fixes else fixed  # "stop the bluetoth"
            v = self.recognise(text, fixed) if fixes else None
            if v and v["how"] != "choose" and ((not u or u["how"] == "model") and (not u or v["how"] == "template" or len(v["unknown"]) < len(u["unknown"]))
                                               or u and u["how"] == "template" and self.hid_a_place(u, v)):
                v["fixes"], v["toks"] = fixes, fixed
                u = v
        if u:
            u.setdefault("fixes", [])
            u.setdefault("toks", toks)
            u["sure"] = u["how"] == "template" or (u["how"] == "model" and u["p"] >= SURE and not u["unknown"])
        bare = self.bare_action(text, self.in_context(toks)) if not u or u["how"] == "model" else None
        if bare:
            return bare
        if u:
            other = self.doubts(text, u) if u["how"] == "template" else None
            if other:  # two readings: the person chooses ("Do you mean rename a file or rename a folder?")
                said = u["toks"]
                u = {"how": "choose", "options": [{"skill": u["skill"], "vals": u["vals"]},
                                                  {"skill": other, "vals": self.values_in(other, text, said)[0]}],
                     "toks": said, "fixes": u["fixes"], "sure": False}
        return u

    def in_context(self, toks):
        """Words read in their context, tried when the sentence as typed isn't read by a template. A split
        verb is joined ("turn the music off" → "turn off the music"; conversation.md, "split verbs" and
        "verb ends"), then a word that means another action with an object said in the sentence becomes
        that action ("turn on the music" → "play the music", "stop the wifi" → "turn off the wifi";
        words/actions.md, "Meaning with an object"). The offsets stay, so a name keeps what was typed.
        → the same list when nothing changed."""
        out, changed = list(toks), False
        verbs, ends = {w for ph in self.words("split verbs") for w in ph}, {w for ph in self.words("verb ends") for w in ph}
        for i in range(len(out)):
            if out[i]["word"] in verbs and not (i + 1 < len(out) and out[i + 1]["word"] in ends):
                j = next((j for j in range(i + 2, min(i + 5, len(out))) if out[j]["word"] in ends), None)
                if j is not None:
                    out.insert(i + 1, out.pop(j))
                    changed = True
        refs = self.lists["refs"]
        for rule in self.lists.get("in_context", []):
            if not any(where(out, ph) for o in rule["objects"] for ph in refs.get(o, [])):
                continue
            to = refs[rule["action"]][0]
            for ph in sorted(rule["phrases"], key=len, reverse=True):
                for i in reversed(where(out, ph)):
                    span = out[i:i + len(ph)]
                    out[i:i + len(ph)] = [{"word": w, "start": span[0]["start"], "end": span[-1]["end"]} for w in to]
                    changed = True
        return out if changed else toks

    def bare_action(self, text, toks):
        """An action said without its object ("turn on", "switch it off"): the person chooses among the skills
        that do it, those of the action and those the action means with an object (words/actions.md,
        "Meaning with an object": "turn off" also stops the music). Only when nothing else is said but small
        and pointing words, and two to eight skills fit, as many as the chips show (24 Oct: with the settings
        skills, "turn off" fits seven); otherwise the model's reading goes on."""
        refs, lists = self.lists["refs"], self.lists
        said = [a for a in lists["actions"] for ph in refs.get(a, []) if where(toks, ph)]
        if not said or any(where(toks, ph) for o in lists["objects"] for ph in refs.get(o, [])):
            return None
        longest = max((len(ph) for a in said for ph in refs[a] if where(toks, ph)))
        action = next(a for a in said for ph in refs[a] if len(ph) == longest and where(toks, ph))
        covered = {i for ph in refs[action] for at_ in where(toks, ph) for i in range(at_, at_ + len(ph))}
        if any(i not in covered and t["word"] not in self.small | self.pointing for i, t in enumerate(toks)):
            return None
        pairs = {(action, s["object"]) for s in self.skills if s["action"] == action}
        spoken = [ph for ph in refs[action] if where(toks, ph)]
        for rule in lists.get("in_context", []):
            if any(ph in spoken for ph in rule["phrases"]):
                pairs |= {(rule["action"], o) for o in rule["objects"]}
        fit = [s for s in self.skills if (s["action"], s["object"]) in pairs]
        if not 2 <= len(fit) <= 8:
            return None
        return {"how": "choose", "options": [{"skill": s, "vals": {}} for s in fit], "toks": toks, "fixes": [], "sure": False}

    def doubts(self, text, u):
        """A template's reading is a strong vote, not a verdict: when the model is sure (DOUBT) of another
        action or object, and a skill does that action on that object, the person chooses between the two
        readings. → that other skill, or None. (24 Oct: "is bluetooth running" was read by check-service's
        template as a service called bluetooth; "rename the folder photos to pictures" renamed a file
        called "folder photos".)"""
        if not self.model:
            return None
        ws, s = [t["word"] for t in u["toks"]], u["skill"]
        pa, po = classify(self.model["action"], text, ws)[0], classify(self.model["object"], text, ws)[0]
        action = pa["label"] if pa["p"] >= DOUBT and pa["label"] != "none" else s["action"]
        obj = po["label"] if po["p"] >= DOUBT and po["label"] != "none" else s["object"]
        # only when another skill is that action on that object: "show the files here" names files, but
        # there is no "show file" skill, so show folder's reading stands
        if (action, obj) == (s["action"], s["object"]):
            return None
        return next((o for o in self.skills if o["action"] == action and o["object"] == obj), None)

    def recognise(self, text, toks):
        """a template's exact reading (several, if they tie: "choose"), or the model's best action + object"""
        found = []
        for skill in self.skills:
            every = []
            for nodes in skill["compiled"]:
                every += parses(nodes, toks, self.lists["refs"], {k: self.list_of(v["kind"]) for k, v in skill["values"].items()},
                                self.stops, self.object_words, self.places)
            if every:
                found.append((skill, best(every)))
        top = max((p["score"] for _, p in found), default=0)
        tops = [{"skill": s, "vals": {k: {"text": self.original(text, toks, c["start"], c["end"]), "value": c.get("value"), "label": c.get("label"),
                                          "unknown": bool(c.get("unknown")), "fuzzy": bool(c.get("fuzzy"))} for k, c in p["caps"].items()}}
                for s, p in found if p["score"] == top]
        # a word TermNL knows as an object (bluetooth, wifi) is that object, not a name on the device's list
        # (Gab, 22 Oct: "is bluetooth on" is the board's Bluetooth, not the service called bluetooth)
        if len(tops) > 1:
            tops = [t for t in tops if not any(v["text"].lower() in self.object_words for v in t["vals"].values())] or tops
        if tops and top >= 1:
            return {"how": "choose", "options": tops} if len(tops) > 1 else {"how": "template", **tops[0], "p": 1, "unknown": []}
        if not self.model:
            return None
        ws = [t["word"] for t in toks]
        pa, po = classify(self.model["action"], text, ws), classify(self.model["object"], text, ws)
        P = lambda found, label: next((x["p"] for x in found if x["label"] == label), 0)
        skill, p = max(((s, P(pa, s["action"]) * P(po, s["object"])) for s in self.skills), key=lambda x: x[1], default=(None, 0))
        if not skill or p < MAYBE or max(P(pa, "none"), P(po, "none")) > p:
            return None
        # an action said in so many words is never answered with its opposite (words/actions.md, Opposites)
        # (24 Oct: "turn the board on" asked "Shut the board down?")
        said = self.actions_said(self.in_context(toks))
        if any(skill["action"] in self.lists.get("opposites", {}).get(a, ()) for a in said):
            return None
        skill = self.as_file(skill, toks)
        vals, used = self.values_in(skill, text, toks)
        taught = set(self.model["taught"].get(skill["id"], []))
        negation = {w for ph in self.words("negation") for w in ph}  # handled by its own rule
        unknown = [t["word"] for i, t in enumerate(toks) if i not in used and t["word"] not in self.small | taught | negation]
        return {"how": "model", "skill": skill, "vals": vals, "p": p, "unknown": unknown}

    def actions_said(self, toks):
        """the actions a sentence names in so many words, each by a phrase of one action only (words/actions.md):
        "turn on" names turn on; "start" names none, as it is a word for both create and open"""
        refs, out = self.lists["refs"], set()
        for a in self.lists["actions"]:
            for ph in refs.get(a, []):
                if where(toks, ph) and sum(1 for b in self.lists["actions"] if ph in refs.get(b, [])) == 1:
                    out.add(a)
        return out

    def as_file(self, skill, toks):
        """a name ending in a known file type (note.md) is a file: the same action on a file, never on a folder
        (Gab, 23 Oct: "create a note.md in the Documents folder" was read as a folder called note.md)"""
        exts = {t["ext"] for t in self.lists["filetypes"]}
        if skill["object"] != "folder" or not any("." in t["word"] and t["word"].rsplit(".", 1)[1] in exts for t in toks):
            return skill
        return next((s for s in self.skills if s["action"] == skill["action"] and s["object"] == "file"), skill)

    def hid_a_place(self, u, v):
        """a typo inside a name hid a place (Gab, 23 Oct: "add a new file call gab.md insde Documents" made a file
        named "gab.md insde Documents.md"): corrected, the same skill reads a value the device has, a folder, that
        the name had swallowed. The name itself is still never corrected: it is what comes before the place."""
        return v["how"] == "template" and v["skill"]["id"] == u["skill"]["id"] and any(
            k not in u["vals"] and x.get("value") is not None and not x.get("unknown") for k, x in v["vals"].items())

    def values_in(self, skill, text, toks):
        """Values found by their own readers, anywhere in the sentence (when no template read it): a
        name from a device list or a shared list, a name after "called"/"named", a file-shaped word."""
        vals, used = {}, set()
        for k, spec in skill["values"].items():
            hit = best_in(toks, self.list_of(spec["kind"]) or [], fuzzy=True)
            if hit:
                vals[k] = {"value": hit["o"]["value"], "label": hit["o"]["label"], "fuzzy": hit["fuzzy"]}
                used.update(range(hit["i"], hit["i"] + hit["len"]))
        leads = {ph[0] for ph in self.words("before a name") if len(ph) == 1}  # called, named, titled
        for k, spec in skill["values"].items():
            if self.list_of(spec["kind"]) or k in vals:
                continue
            after = next((i for i, t in enumerate(toks) if t["word"] in leads), -1)
            end = after + 1
            while 0 <= after and end < len(toks) and toks[end]["word"] not in self.name_ends and end not in used:
                end += 1
            if after >= 0 and end > after + 1:
                vals[k] = {"text": self.original(text, toks, after + 1, end)}
                used.update(range(after, end))
                continue
            f = next((i for i, t in enumerate(toks) if i not in used and re.search(r"\.[a-z0-9]{1,5}$", t["word"], re.I)), -1)
            if f >= 0:
                vals[k] = {"text": self.original(text, toks, f, f + 1)}
                used.add(f)
        return vals, used

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
            return self.ask_value(skill, vals, k, approved, self.reply("unknown value", {"value": self.quoted(vals[k]["text"])}),
                                  self.chips(self.list_of(skill["values"][k]["kind"])))
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
            return self.ask_value(skill, vals, k, approved, self.reply("unknown value", {"value": self.quoted(v.get("text") or v["label"])}),
                                  self.chips(self.list_of(skill["values"][k]["kind"])))

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
        if skill.get("opens"):  # a panel of the page: the settings' toggles
            return {"outcome": "act", "skill": skill["id"], "opens": skill["opens"], "say": self.reply(skill["replies"]["done"])}
        if skill.get("lists") == "skills":  # help: what TermNL can do, by topic (words/objects.md, Topics)
            return self.help(skill)
        if skill.get("changes"):  # a setting, changed here at once; the server writes it to settings.md
            key, value = skill["changes"]
            value = fill(value, {k: v.get("text") or v.get("label") for k, v in vals.items()}).strip()
            self.settings[key] = value
            return {"outcome": "act", "skill": skill["id"], "changes": {key: value},
                    "say": self.reply(skill["replies"]["done"], self.display(skill, vals))}
        if skill["moves"] and vals.get(skill["moves"]):
            v = vals[skill["moves"]]
            self._here = {"value": v["value"], "label": v["label"]}
        if skill["reads"]:  # the device reads itself; the reply is chosen once it has (server.py)
            args = {k: v["value"] if v.get("value") is not None else v.get("text") for k, v in vals.items()}
            out = {"outcome": "act", "skill": skill["id"], "say": "", "reads": skill["reads"], "args": args, "values": self.display(skill, vals)}
            if skill["command"]:  # a reader of the command's output (check wifi: iw)
                out["command"] = self.command_for(skill, vals)
                self.with_show(out, skill, vals)
            return out
        return self.with_show({"outcome": "act", "skill": skill["id"], "say": self.reply(skill["replies"]["done"], self.display(skill, vals)),
                               "command": self.command_for(skill, vals)}, skill, vals)


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
