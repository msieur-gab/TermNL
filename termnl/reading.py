"""Reads a sentence into a skill and its values, in four looks, each taken from the skill files:

  1. words      fillers off ("please", "can you"); a typo of a word TermNL knows, one letter away from
                exactly one, is read as that word (the name a person typed keeps its spelling)
  2. funnel     the actions and objects the sentence names (words/actions.md, words/objects.md, a skill's
                ## Words): "new file called x" names create and file, so only skills doing that fit
  3. templates  a skill's ## People say reads the sentence exactly; when two read it alike, the funnel
                decides, and when it can't, the person does
  4. model      else the action and object the trained model reads (model.py, trained from every skill's
                ## People say and ## Also said: python3 -m termnl.train), the funnel deciding ties; how
                sure the model is says how sure the reading is

A skill folder dropped in is read by the funnel and its templates at once, and by the model once it
is trained again ("learn what I taught you")."""
import re

from .model import classify
from .template import best, parses
from .text import close, tokenize, words

FILE_RE = re.compile(r"\.[a-z0-9]{1,5}$", re.I)
SURE, MAYBE = 0.5, 0.15  # how sure the model must be of its action and object: to go ahead, and to ask at all
NEAR = 0.1  # readings the model holds this close to its best count as one: the funnel decides among their skills
UNSURE = 0.75  # how sure a template is of a reading with a value not on its list
CHOICES = 8  # as many readings as the chips can show


def at(toks, phrase, i):
    """the phrase's words are the sentence's words from i"""
    return 0 < len(phrase) and i + len(phrase) <= len(toks) and all(toks[i + j]["word"] == w for j, w in enumerate(phrase))


def where(toks, phrase):
    return [i for i in range(len(toks)) if at(toks, phrase, i)]


def best_in(toks, found, fuzzy=False, start=None):
    """the longest phrase of a list said in the sentence (a typo of one too, when fuzzy, exact first), or
    only one that starts at word `start` → {o, i, len, fuzzy} or None"""
    hit = None
    for o in found:
        for ph in o["phrases"]:
            for i in range(len(toks) - len(ph) + 1) if start is None else [start] if start + len(ph) <= len(toks) else []:
                exact = at(toks, ph, i)
                near = fuzzy and not exact and all(close(toks[i + j]["word"], w) for j, w in enumerate(ph))
                if (exact or near) and (not hit or len(ph) > hit["len"] or (exact and hit["fuzzy"])):
                    hit = {"o": o, "i": i, "len": len(ph), "fuzzy": near}
    return hit


class Reader:
    def __init__(self, lists, skills, sys, model=None):
        """sys(kind) → the device's values of a kind, [{value, label, phrases}], read live"""
        self.lists, self.skills, self.sys, self.model = lists, skills, sys, model
        said = lists["conversation"]
        joined = lambda key: {" ".join(p) for p in said.get(key, [])}
        self.small = joined("small words") | joined("filler start") | joined("filler end") | joined("pointing words") | joined("follow-up words") \
            | joined("negation")  # "not" is read by its own rule (agent.py): a reading isn't held back by it
        self.stops, self.places, self.name_ends = joined("not a name start"), joined("before a place"), joined("name ends before")
        self.verbs, self.ends = joined("split verbs"), joined("verb ends")
        self.object_words = {ph[0] for o in lists["objects"] for ph in lists["refs"].get(o, []) if len(ph) == 1}
        self.name_words = self.object_words | {ph[0] for a in lists["actions"] for ph in lists["refs"].get(a, []) if len(ph) == 1}
        self.named = {ph[-1] for ph in said.get("before a name", [])}  # called, named: what follows is a name
        # a phrase → everything it means: "start" means create and open; longest phrases first
        self.means = {}
        for key in lists["actions"] + lists["objects"]:
            for ph in lists["refs"].get(key, []):
                self.means.setdefault(tuple(ph), set()).add(key)
        for t in lists["filetypes"]:
            for ph in t["phrases"]:
                self.means.setdefault(tuple(ph), set()).add("filetype")
        self.phrases = sorted(self.means, key=len, reverse=True)
        # every word TermNL knows how to read: a typo of one of them is read as it (correct)
        self.vocab = {w for phs in list(lists["refs"].values()) + list(said.values()) for ph in phs for w in ph}
        self.vocab |= {w for ph in self.means for w in ph} | {w for s in skills for nodes in s.get("compiled", []) for w in _template_words(nodes)}
        self.known = self.vocab | {w for s in skills for line in s["also"] for w in words(line)}  # a word an Also said line uses is known
        for s in skills:  # once per skill, however many agents read it: the words each value follows in its own sentences (values_in)
            if "leads" not in s:
                s["leads"] = leads(s.get("compiled", []), self.stops)

    # ---- 1. words

    def clean(self, text):
        """Fillers ("please", "can you", "for me") are dropped at the start and end of a sentence."""
        toks, said = tokenize(text), self.lists["conversation"]
        changed = True
        while changed:
            changed = False
            for ph in said.get("filler start", []):
                if len(toks) > len(ph) and at(toks, ph, 0):
                    toks, changed = toks[len(ph):], True
            for ph in said.get("filler end", []):
                if len(toks) > len(ph) and at(toks, ph, len(toks) - len(ph)):
                    toks, changed = toks[:-len(ph)], True
        return toks

    def correct(self, toks):
        """A word TermNL doesn't know, one letter away from exactly one word it knows ("chek" → "check"), is
        read as that word. The offsets stay, so a name keeps what was typed. Short words, file names and
        the device's own names are left as they are. → the words, and the fixes made [[typed, read], …]"""
        known = self.vocab | {w for kind in ("folder", "service", "app", "running") for d in self.sys(kind) for ph in d["phrases"] for w in ph}
        out, fixes = [], []
        for t in toks:
            w = t["word"]
            near = set() if w in known or w in self.known or len(w) < 4 or "." in w or not w.isalpha() else {v for v in self.vocab if len(v) >= 4 and close(w, v)}
            if len(near) == 1:
                fixes.append([w, next(iter(near))])
                t = {**t, "word": fixes[-1][1]}
            out.append(t)
        return out, fixes

    def joined(self, toks):
        """A split verb joined ("turn the music off" → "turn off the music"; conversation.md, "split verbs" and
        "verb ends"), then a word that means another action with an object said in the sentence becomes
        that action ("turn on the music" → "play the music"; a skill's ## Words, "turn on, start → play").
        The offsets stay, so a name keeps what was typed. → the same list when nothing changed."""
        out, changed = list(toks), False
        for i in range(len(out)):
            if out[i]["word"] in self.verbs and not (i + 1 < len(out) and out[i + 1]["word"] in self.ends):
                j = next((j for j in range(i + 2, min(i + 5, len(out))) if out[j]["word"] in self.ends), None)
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

    # ---- 2. funnel

    def shape(self, toks):
        """What the sentence says, as a set: each action, object and file type by its name (every one a phrase
        means: "start" is create and open), a file-shaped word as "@file", a name the device has as "@value"
        and its kind ("@sys.folder"), a word TermNL doesn't know as itself and "@value" (a name, most likely),
        the small words dropped."""
        toks, steps, i = self.joined(toks), [], 0  # steps: what each word means, in order
        lists = [{"value": "@sys." + kind, "phrases": [ph for d in self.sys(kind) for ph in d["phrases"]]}
                 for kind in ("folder", "service", "app", "network", "music", "host")]
        while i < len(toks):
            ph = next((ph for ph in self.phrases if at(toks, ph, i)), None)
            hit = best_in(toks[i:], lists, start=0)
            if hit and (not ph or hit["len"] > len(ph)):  # a value, and its kind when known ("music server" is a service)
                steps.append({"@value", hit["o"]["value"]} if hit["o"]["value"].startswith("@") else {"@value"})
                i += hit["len"]
                continue
            if ph:
                steps.append(self.means[ph])
                i += len(ph)
                continue
            w = toks[i]["word"]
            if FILE_RE.search(w):
                steps.append({"@file"})
            elif w not in self.small:  # a word TermNL doesn't know is a name, most likely, and itself
                steps.append({w} if w in self.known else {w, "@value"})
            i += 1
        return {x for step in steps for x in step}

    def names(self, shape):
        """the actions and objects a shape names (a file-shaped word names a file)"""
        return {x for x in shape if x in self.lists["actions"]}, {x for x in shape if x in self.lists["objects"]} | ({"file"} if "@file" in shape else set())

    def alone(self, toks):
        """the actions a sentence names in so many words, each by a phrase that means one action only: "turn on"
        names turn on; "start" names none, as it is a word for both create and open"""
        return {next(iter(keys)) for ph, keys in self.means.items() if len(keys) == 1 and next(iter(keys)) in self.lists["actions"] and where(toks, list(ph))}

    # ---- 3. templates

    def by_template(self, text, toks, shape):
        """every skill whose template reads the whole sentence, the best reading of each, the ties resolved by
        the funnel → a reading, "choose" among several, or None"""
        found = []
        for skill in self.skills:
            every = []
            for nodes in skill["compiled"]:
                every += parses(nodes, toks, self.lists["refs"], {k: self.list_of(v["kind"]) for k, v in skill["values"].items()},
                                self.stops, self.name_words, self.places, self.named)
            if every:
                found.append((skill, best(every)))
        top = max((p["score"] for _, p in found), default=0)
        tops = [{"skill": s, "vals": {k: {"text": original(text, toks, c["start"], c["end"]), "value": c.get("value"), "label": c.get("label"),
                                          "unknown": bool(c.get("unknown")), "fuzzy": bool(c.get("fuzzy"))} for k, c in p["caps"].items()}}
                for s, p in found if p["score"] == top]
        if not tops or top < 1:
            return None
        if len(tops) > 1:  # a name never holds a word for an object ("folder photos" is the folder photos)
            tops = [t for t in tops if not any(set(words(v["text"])) & self.object_words for v in t["vals"].values() if v.get("value") is None)] or tops
        tops = self.funnel(tops, shape)
        if not tops:
            return None
        # a value not on its list ("what's" as a file type) makes the reading a guess, not an exact one
        p = UNSURE if any(v["unknown"] for t in tops for v in t["vals"].values()) else 1
        if len(tops) > 1:
            return {"how": "choose", "options": tops, "p": p, "toks": toks}
        return {"how": "template", **tops[0], "p": p, "unknown": [], "toks": toks}

    def funnel(self, readings, shape):
        """among readings alike, those of a skill whose action and object the sentence names; failing that, whose
        object, or whose action (the sentence "turn the music off" names turn off and music)"""
        acts, objs = self.names(shape)
        for fits in (lambda s: s["action"] in acts and s["object"] in objs, lambda s: s["object"] in objs, lambda s: s["action"] in acts):
            readings = [r for r in readings if fits(r["skill"])] or readings
        return readings

    # ---- 4. nearest

    def bare(self, toks, shape):
        """An action said without its object ("turn off", "switch it off"): the person chooses among the skills
        that do it, and those the action means with an object (a skill's ## Words: "turn off" also stops the
        music). Only when the sentence names an action and nothing else, and two to CHOICES skills fit."""
        acts, objs = self.names(shape)
        if not acts or objs or any(x not in acts for x in shape):
            return None
        pairs = {(a, s["object"]) for a in acts for s in self.skills if s["action"] == a}
        for rule in self.lists.get("in_context", []):
            if any(where(toks, ph) for ph in rule["phrases"]):
                pairs |= {(rule["action"], o) for o in rule["objects"]}
        fit = [{"skill": s, "vals": {}} for s in self.skills if (s["action"], s["object"]) in pairs]
        if not 2 <= len(fit) <= CHOICES:
            return None
        return {"how": "choose", "options": fit, "p": 1, "toks": toks}

    def opposed(self, skill, toks):
        """a skill that does the opposite of an action said in so many words (words/actions.md, Opposites): "turn
        the board on" is never answered with "Shut the board down?" """
        return any(skill["action"] in self.lists.get("opposites", {}).get(a, ()) for a in self.alone(self.joined(toks)))

    def by_model(self, text, toks, shape):
        """the skill whose action and object the model reads (the chance of both, as p); readings nearly as
        likely count as one and the funnel decides among them, the person when it can't; a reading the model
        holds less likely than "none of them" is no reading → a reading, "choose", or None"""
        if not self.model:
            return None
        ws = [t["word"] for t in toks]
        pa, po = classify(self.model["action"], text, ws), classify(self.model["object"], text, ws)
        P = lambda found, label: next((x["p"] for x in found if x["label"] == label), 0)
        scored = [(P(pa, s["action"]) * P(po, s["object"]), s) for s in self.skills]
        top, best_ = max(scored, key=lambda x: x[0], default=(0, None))
        if top < MAYBE or max(P(pa, "none"), P(po, "none")) > top or self.opposed(best_, toks):
            return None  # an action said in so many words is never answered with its opposite (24 Oct: "turn the board on")
        readings = self.funnel([{"skill": s, "p": p} for p, s in scored if p >= top - NEAR * top], shape)
        top = max(r["p"] for r in readings)
        readings = [r for r in readings if r["p"] >= top - NEAR * top]
        if len(readings) > CHOICES:
            return None
        for r in readings:
            r["vals"] = self.values_in(r["skill"], text, toks)
        if len(readings) > 1:
            return {"how": "choose", "options": readings, "p": top, "toks": toks}
        skill, vals = readings[0]["skill"], readings[0]["vals"]
        taught = set(self.model["taught"].get(skill["id"], ()))  # the words this skill's own sentences use
        taken = {w for v in vals.values() for w in words(v.get("text") or v.get("label") or "")}
        unknown = [t["word"] for t in toks if t["word"] not in self.small | taught | taken and not FILE_RE.search(t["word"])
                   and not self.on_device(t["word"])]
        # the new words, side by side, are the value the skill still lacks from the device's list ("kill pipewire":
        # no app of that name): kept as said, so it is answered as not there, never asked for again (Gab, 24 Oct)
        missing = [k for k, spec in skill["values"].items() if k not in vals and spec["required"] and not spec.get("default")]
        new = [i for i, t in enumerate(toks) if t["word"] in unknown]
        if len(missing) == 1 and skill["values"][missing[0]]["kind"].startswith("@sys.") and self.list_of(skill["values"][missing[0]]["kind"]) is not None \
                and new and new == list(range(new[0], new[-1] + 1)):
            vals[missing[0]] = {"text": original(text, toks, new[0], new[-1] + 1), "unknown": True}
            if top >= SURE:
                unknown = []
        return {"how": "model", **readings[0], "p": top, "unknown": unknown, "toks": toks}

    def on_device(self, word):
        return any(word in ph for kind in ("folder", "service", "app", "network", "music", "host") for d in self.sys(kind) for ph in d["phrases"])

    # ---- values, when no template read them

    def list_of(self, kind):
        """files aren't a list read in advance: they are looked up in the place once it is known"""
        if kind == "filetype":
            return self.lists["filetypes"]
        if kind.startswith("@sys.") and kind != "@sys.file":
            return self.sys(kind[5:])
        return None

    def values_in(self, skill, text, toks):
        """Values found by their own readers, anywhere in the sentence: a name from the device's or a shared
        list, first after the word the skill's own sentences put before it ("from" {place}, "to" {to}), a name
        after "called"/"named", a file-shaped word."""
        vals, used = {}, set()
        leads = skill.get("leads", {})
        listed = [(k, self.list_of(spec["kind"]) or []) for k, spec in skill["values"].items()]

        def after_lead(k, found):
            for i, t in enumerate(toks):
                if t["word"] in leads.get(k, ()):
                    j = i + 1
                    while j < len(toks) and toks[j]["word"] in self.small and toks[j]["word"] not in self.stops:
                        j += 1  # the, my
                    hit = best_in(toks, found, fuzzy=True, start=j)
                    if hit:
                        return hit

        for find in (after_lead, lambda k, found: best_in(toks, found, fuzzy=True)):
            for k, found in listed:
                hit = None if k in vals else find(k, found)
                if hit and not used & set(range(hit["i"], hit["i"] + hit["len"])):
                    vals[k] = {"value": hit["o"]["value"], "label": hit["o"]["label"], "fuzzy": hit["fuzzy"]}
                    used.update(range(hit["i"], hit["i"] + hit["len"]))
        before = {ph[0] for ph in self.lists["conversation"].get("before a name", []) if len(ph) == 1}  # called, named, titled
        for k, spec in skill["values"].items():
            if self.list_of(spec["kind"]) or k in vals:
                continue
            after = next((i for i, t in enumerate(toks) if t["word"] in before), -1)
            end = after + 1
            while 0 <= after and end < len(toks) and toks[end]["word"] not in self.name_ends and end not in used:
                end += 1
            if after >= 0 and end > after + 1:
                vals[k] = {"text": original(text, toks, after + 1, end)}
                used.update(range(after, end))
                continue
            f = next((i for i, t in enumerate(toks) if i not in used and FILE_RE.search(t["word"])), -1)
            if f >= 0:
                vals[k] = {"text": original(text, toks, f, f + 1)}
                used.add(f)
        return vals

    # ---- the four looks, in order

    def read(self, text, toks):
        """→ a reading {how, skill, vals, p, unknown, toks} (or {how: "choose", options}), or None.
        how: "template" (exact), "part" (a template read one part of the sentence: asked about first),
        "model" (the model's action and object, p how sure)."""
        u = self.read_one(text, toks)
        if not u or u["p"] < 1:  # a request said with its reason ("restart ssh, I can't log in"): the part that reads best
            parts = [p for p in re.split(r"[,;:!?]", text) if p.strip()]
            for part in parts if len(parts) > 1 else []:
                v = self.read_one(part, self.clean(part))
                if v and v["how"] != "choose" and (not u or v["p"] > u["p"]) and v["shape"] - v["names"][0]:  # "restart it" names no thing: no request
                    u = {**v, "how": "part"}  # a part is never acted on unasked, however it was read
        return u

    def read_one(self, text, toks):
        """the whole of a sentence, read by a template or the model: the surer reading wins, a template when as sure"""
        shape = self.shape(toks)
        u = self.by_template(text, toks, shape)
        said = self.joined(toks)
        if not u and said is not toks:  # the words read in their context ("turn on the music" plays it)
            u = self.by_template(text, said, shape)
        if u and u["how"] != "choose" and self.opposed(u["skill"], toks):
            u = None
        v = (self.bare(toks, shape) or self.by_model(text, toks, shape)) if not u or u["p"] < 1 else None
        if v and u and u["how"] == "template" and v["how"] == "model" and v["p"] >= SURE and v["skill"]["id"] != u["skill"]["id"]:
            # a template's reading with a value not on its list is a strong vote, not a verdict: when the model is sure
            # of another skill, the person chooses (24 Oct: "rename the folder photos to pictures" renamed a file)
            u = {"how": "choose", "options": [{k: u[k] for k in ("skill", "vals")}, {k: v[k] for k in ("skill", "vals")}], "p": u["p"], "toks": toks}
        elif v and (not u or v["p"] > u["p"] and (u["how"] == "choose" or v["how"] != "model" or v["skill"]["id"] != u["skill"]["id"])):
            u = v  # the model's reading of the same skill adds nothing: the template read its values exactly
        if u:
            u["names"], u["shape"] = self.names(shape), shape
        return u


def original(text, toks, start, end):
    """what the person typed for these words (a name keeps its typos and capitals)"""
    return text.translate(str.maketrans({"’": "'", "‘": "'", "`": "'"}))[toks[start]["start"]:toks[end - 1]["end"]]


def leads(compiled, preps):
    """value → the prepositions said right before it in the skill's sentences (an article between them, or any
    word of an optional part, doesn't count): copy {name} (from (the) {place}) to/into (the/my) {to}"""
    out = {}

    def walk(seq, prev, inside):
        for n in seq:
            if n["t"] == "w":
                prev = {n["w"]} if n["w"] in preps else prev if inside else set()
            elif n["t"] == "ref":
                prev = set()
            elif n["t"] == "slot":
                out.setdefault(n["name"], set()).update(prev)
                prev = set()
            elif n["t"] == "alt":
                after = set(prev) if n["opt"] else set()
                for a in n["alts"]:
                    after |= walk(a, set(prev), True)
                prev = after
        return prev

    for nodes in compiled:
        walk(nodes, set(), False)
    return out


def _template_words(nodes):
    for n in nodes:
        if n["t"] == "w":
            yield n["w"]
        elif n["t"] == "alt":
            for a in n["alts"]:
                yield from _template_words(a)
