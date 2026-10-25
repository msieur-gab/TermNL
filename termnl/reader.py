"""How a sentence is read, since 25 October 2026 (ALIGN.md): one reader, no trained model.

Every skill reads every sentence, two ways, on one scale from 0 to 1, and all the readings of all the
skills are ranked together (readings):

  exact    one of the skill's sentences reads the words as written (template.py), its values in their
           places. Fit 1, less a little for a typo read along the way, a value the device's list doesn't
           have, or a word for an object taken as a name ("is bluetooth running": the service called
           bluetooth). The People say lines and the Also said lines alike (plain.also_template).
  near     the skill explains the sentence, in three measures averaged (near):
             explained   how much of the sentence's weight its own words account for (coverage)
             alike       how close the sentence is to one of its sentences (similar: a weighted Jaccard)
             agreement   how much the sentence's words say its action and its object, against every other
                         action and object, counted over the skills that share them (agree: the split
                         Gab chose, by counting; "turn … on" learnt from Wi-Fi, Bluetooth and the sound alike)
           Its values are found by their own readers (values_in), wherever they are in the sentence.

Nothing is trained. When the skills load, each skill's words are counted from its People say and Also said
lines (with the words for its action and object, and its own ## Words), and weighed by how telling each is:
a word only one skill says weighs most, one every skill says weighs nothing (the inverse document frequency,
over skills); small words weigh nothing. A word no skill knows is unknown: it costs the reading, and the
agent names it when it asks. What no skill does (out-of-scope.md) reads sentences too, as a skill with no
command: when it reads one best, nothing is understood. A skill folder dropped in is known at once.

What is said in so many words is never read as something else: an object ("turn on the pi" is the board,
which no skill turns on, so nothing is offered), an action by its opposite (words/actions.md, Opposites),
a name the device has ("The Tune", an album) by a skill with no value for it. An exact reading stands anyway.
An action said alone ("turn on") is every skill that does it, for the person to choose.

Standard library only; counting the words takes a tenth of a second for 77 skills, on a laptop."""
import math

from .template import best, parses
from .text import close, stem, words

EXACT_TYPO = 0.1  # taken off an exact reading, per word read as a typo of another
UNKNOWN_VALUE = 0.15  # taken off an exact reading, per value read that the device's list doesn't have
OBJECT_AS_NAME = 0.12  # taken off an exact reading that takes a word for an object (bluetooth) as a name on a list
NEAR_TYPO = 0.75  # a word one letter away from one the skill knows: three quarters of its weight
SLOT_TEXT = 1.0  # a name or other free text found for a value: a word's ordinary weight
SMALL = 0.5  # a small word in a skill's sentence ("go up", "put it back"): little, but not nothing


def file_shaped(word, exts):
    return "." in word and word.rsplit(".", 1)[1].lower() in exts


class Reader:
    def __init__(self, lists, skills):
        self.lists, self.skills = lists, skills
        said = lists["conversation"]
        self.words = lambda key: said.get(key, [])
        joined = lambda key: {" ".join(p) for p in said.get(key, [])}
        self.small = joined("small words") | joined("pointing words") | {w for k in ("filler start", "filler end", "negation") for ph in said.get(k, []) for w in ph}
        self.stops, self.ends, self.places = joined("not a name start"), joined("name ends before"), joined("before a place")
        self.leads = {ph[0] for ph in said.get("before a name", []) if len(ph) == 1}
        self.object_words = {ph[0] for o in lists["objects"] for ph in lists["refs"].get(o, []) if len(ph) == 1}
        self.object_words_all = {w for o in lists["objects"] for ph in lists["refs"].get(o, []) for w in ph}
        self.action_words = {w for a in lists["actions"] for ph in lists["refs"].get(a, []) for w in ph} - {"on", "off", "up", "down"}
        self.verb_ends = {w for ph in said.get("verb ends", []) for w in ph}
        self.exts = {x for t in lists["filetypes"] for x in t.get("exts", [t["ext"]])}
        self.opposites = lists.get("opposites", {})
        self._cache = {}
        self.build()

    # ---- the vocabulary, counted when the skills load

    def build(self):
        """each skill's words, and how much each is its own: a word in most of a skill's sentences is fully its
        ("create" for create file), one in a single Also said line of a skill that mostly says other things is
        little (the same "create" in copy file's "create a copy"): the count of the skill's sentences that say
        the word, against the most any skill says it"""
        self.count = {}  # skill id → {word: sentences that say it}
        self.count_all = {}
        self.phrases = {}  # skill id → the phrases its sentences say, as said ("turn on", not "turn … on")
        for s in self.skills:
            c, phrases = {}, set()
            for nodes in s["compiled"]:
                for w in set(self._node_words(nodes, self.refs_for(s))):
                    c[w] = c.get(w, 0) + 1
                phrases.update(self._node_phrases(nodes, self.refs_for(s)))
            for line in s["also"]:
                ws = words(line)
                for w in set(ws):
                    c[w] = c.get(w, 0) + 1
                phrases.update(tuple(ws[i:i + n]) for n in (1, 2, 3) for i in range(len(ws) - n + 1))
            self.count[s["id"]] = {w: n for w, n in c.items() if w not in self.small}
            self.count_all[s["id"]] = c  # small words too: "on" and "off" are what tells turning on from off
            self.phrases[s["id"]] = phrases
        # what no skill does (out-of-scope.md), read like a skill with no action, object or command: when it
        # reads a sentence best, nothing is understood
        none = {}
        for line in self.lists.get("out_of_scope", []):
            for w in set(words(line)):
                none[w] = none.get(w, 0) + 1
        self.count["none"] = {w: n for w, n in none.items() if w not in self.small}
        self.count_all["none"] = none
        self.none = {"id": "none", "action": None, "object": None, "values": {}, "own": [], "refs": {}, "compiled_also": [],
                     "compiled": [[{"t": "w", "w": w} for w in words(line)] for line in self.lists.get("out_of_scope", []) if words(line)]}
        self.phrases["none"] = set()
        # the same counts pooled by action and by object, over every skill that does that action or is about that
        # object: what "turn … on" looks like, learnt from Wi-Fi, Bluetooth and the sound alike (the split Gab chose)
        self.pooled = {"action": {}, "object": {}}
        self.lines = {"action": {}, "object": {}}
        for sk in self.skills:
            for family, name in (("action", sk["action"]), ("object", sk["object"])):
                c = self.pooled[family].setdefault(name, {})
                for w, k in self.count_all[sk["id"]].items():
                    c[w] = c.get(w, 0) + k
                self.lines[family][name] = self.lines[family].get(name, 0) + len(sk["compiled"]) + len(sk["also"])
        for family in ("action", "object"):  # what no skill does is a candidate too, so "the lights" pull away from every object
            self.pooled[family]["none"] = dict(none)
            self.lines[family]["none"] = len(self.none["compiled"])
        self.pooled_stems = {family: {cand: _by_stem(c) for cand, c in pools.items()} for family, pools in self.pooled.items()}
        self.vocab = {k: set(c) for k, c in self.count.items()}
        self.stems = {k: {stem(w): w for w in v} for k, v in self.vocab.items()}  # "using" reads as the skill's "used"
        self.known = set().union(*self.vocab.values())  # a word some skill knows is a real word, never a typo of another
        self.by_length = {}  # the known words by length, for typos (a typo is at most two letters longer or shorter)
        for w in self.known:
            self.by_length.setdefault(len(w), []).append(w)
        n = len(self.vocab)
        df, most = {}, {}
        for c in self.count.values():
            for w, k in c.items():
                df[w] = df.get(w, 0) + 1
                most[w] = max(most.get(w, 0), k)
        self.most = most
        self.idf = {w: math.log((n + 1) / (c + 1)) for w, c in df.items()}
        self.unknown_weight = math.log(n + 1)
        kinds = {}
        for s in self.skills:
            for spec in s["values"].values():
                kinds[spec["kind"]] = kinds.get(spec["kind"], 0) + 1
        self.kind_weight = {k: math.log((n + 1) / (c + 1)) for k, c in kinds.items()}

    def refs_for(self, skill, toks=None):
        """the words this skill reads: the shared ones, and its own for its action (## Words) when one of their
        objects is said in the sentence (every one of them when no sentence is given)"""
        own = []
        for objects, phrases in skill.get("own", []):
            if toks is None or any(_where(toks, ph) for o in objects for ph in self.lists["refs"].get(o, [])):
                own += [p for p in phrases if p not in own]
        if not own:
            return skill["refs"]
        return {**skill["refs"], skill["action"]: skill["refs"].get(skill["action"], []) + [p for p in own if p not in skill["refs"].get(skill["action"], [])]}

    def _node_phrases(self, nodes, refs):
        """the phrases a sentence says as written: each word, each phrase of an action or object, and words side by side"""
        run = []
        for node in nodes:
            if node["t"] == "w":
                run.append(node["w"])
                continue
            yield from (tuple(run[i:i + n]) for n in (1, 2, 3) for i in range(len(run) - n + 1))
            run = []
            if node["t"] == "ref":
                yield from (tuple(ph) for ph in refs.get(node["name"], []))
            elif node["t"] == "alt":
                for a in node["alts"]:
                    yield from self._node_phrases(a, refs)
        yield from (tuple(run[i:i + n]) for n in (1, 2, 3) for i in range(len(run) - n + 1))

    def _node_words(self, nodes, refs):
        for node in nodes:
            if isinstance(node, list):
                yield from self._node_words(node, refs)
            elif node["t"] == "w":
                yield node["w"]
            elif node["t"] == "ref":
                for ph in refs.get(node["name"], []):
                    yield from ph
            elif node["t"] == "alt":
                for a in node["alts"]:
                    yield from self._node_words(a, refs)

    def agree(self, family, name, toks, used):
        """how much the sentence's words say this action (or object), against every other: each word's count in the
        lines of the skills that do it, over all the lines, as a likelihood (naive Bayes, add-one), with a small word
        at a third of its say. → 0 to 1: 1 for the likeliest action (or object), less for the others."""
        key = (family, tuple(sorted(used)))
        scores = self._cache.get(key)
        if scores is None:
            pooled, lines = self.pooled[family], self.lines[family]
            vocab = len(self.known) + 1
            # a word for an action says nothing about the object, and the other way round ("turn off the lights":
            # "turn off" is no evidence of Bluetooth); the ends of verbs ("off") say the action in full
            other = self.action_words | self.verb_ends if family == "object" else self.object_words_all
            ends = self.verb_ends if family == "action" else set()
            said = [(t["word"], stem(t["word"]), 1.0 if t["word"] in ends or t["word"] not in self.small else 0.3)
                    for i, t in enumerate(toks) if i not in used and t["word"] not in other]
            scores = {}
            for cand, c in pooled.items():
                stems, total = self.pooled_stems[family][cand], 0.0
                for w, st, weight in said:
                    k = c.get(w) or (stems.get(st, 0) if len(w) >= 4 else 0)
                    total += weight * math.log((k + 1) / (lines[cand] + vocab))
                scores[cand] = total
            self._cache[key] = scores
        top = max(scores.values())
        return math.exp(scores[name] - top) if name in scores else 0  # 1 for the likeliest, less for the others

    def typos(self, w):
        """the words some skill knows that this word may be a typo of (none for a word some skill knows: it is a word)"""
        key = ("typos", w)
        if key not in self._cache:
            near = set()
            if len(w) >= 4 and w.isalpha() and w not in self.known:
                near = {v for n in range(max(4, len(w) - 2), len(w) + 3) for v in self.by_length.get(n, ()) if close(w, v)}
            self._cache[key] = near
        return self._cache[key]

    def share(self, skill, w):
        """how much a word is this skill's: the count of its sentences that say it against the most any skill's do,
        softened (the square root), so a word said once in a short skill still counts for something"""
        return math.sqrt(self.count[skill["id"]][w] / self.most[w])

    def weight(self, w):
        if w in self.small:
            return 0.0
        return self.idf.get(w, self.unknown_weight)

    # ---- what the sentence says in so many words

    def said(self, toks, family):
        """the actions (or objects) a sentence names by a phrase that stands for one of them only"""
        refs, out = self.lists["refs"], set()
        names = self.lists[family]
        for a in names:
            for ph in refs.get(a, []):
                if _where(toks, ph) and sum(1 for b in names if ph in refs.get(b, [])) == 1:
                    out.add(a)
        return out

    def knows(self, skill, name):
        """the skill's own sentences say a phrase for this action or object, as said"""
        return any(tuple(ph) in self.phrases[skill["id"]] for ph in self.lists["refs"].get(name, []))

    def variants(self, toks):
        """the sentence as typed, and with a split verb joined ("turn the music off" → "turn off the music";
        conversation.md, split verbs and verb ends). The offsets stay, so a name keeps what was typed."""
        out, changed = list(toks), False
        verbs, ends = {w for ph in self.words("split verbs") for w in ph}, {w for ph in self.words("verb ends") for w in ph}
        for i in range(len(out)):
            if out[i]["word"] in verbs and not (i + 1 < len(out) and out[i + 1]["word"] in ends):
                j = next((j for j in range(i + 2, min(i + 5, len(out))) if out[j]["word"] in ends), None)
                if j is not None:
                    out.insert(i + 1, out.pop(j))
                    changed = True
        return [toks, out] if changed else [toks]

    # ---- the readings

    def readings(self, text, toks, list_of):
        """every reading of the sentence, best first → [{skill, vals, fit, how, unknown, fixes, toks}]
        list_of(kind) → the device's values of a kind (with their words), or None for free text"""
        self._cache = {}  # what is the same for every skill of one sentence (agree, typos)
        out = []
        for said in self.variants(toks):
            out += self.exact(text, said, list_of)
        bare = next((b for said in self.variants(toks) for b in [self.bare(said)] if b), [])
        if bare and not out:  # the same fit for each: the person chooses
            return [{"how": "near", "skill": s, "vals": {}, "fit": 0.9, "p": 0.9, "unknown": [], "fixes": [], "toks": toks} for s in bare]
        exact = {}
        for r in out:
            if r["skill"]["id"] not in exact or r["fit"] > exact[r["skill"]["id"]]["fit"]:
                exact[r["skill"]["id"]] = r
        out = list(exact.values())
        said = self.variants(toks)[-1]
        objects, actions = self.said(said, "objects"), self.said(said, "actions")
        for s in self.skills:
            if s["id"] in exact:
                continue
            if any(s["action"] in self.opposites.get(a, ()) for a in actions):
                continue  # an action said in so many words is never answered with its opposite
            # an object or an action said in so many words is never read as another one, unless the skill's own
            # sentences say that word too ("create a file in the Documents folder": create file says "folder")
            if any(o != s["object"] and not self.knows(s, o) for o in objects):
                continue
            if any(a != s["action"] and not self.knows(s, a) for a in actions):
                continue
            r = self.near(s, text, toks, list_of)
            if r:
                r["named"] = s["action"] in actions and s["object"] in objects  # its action and its object, in so many words
                # a near reading contests an exact one only when the sentence names its action or object in so many
                # words, and the exact skill's is another ("is bluetooth running": the service called bluetooth, or
                # the board's Bluetooth); otherwise the exact reading stands
                taken = {v["text"].lower() for e in out if e["how"] == "exact" for v in e["vals"].values() if v.get("text")}
                r["contests"] = s["object"] in objects and not any(e["skill"]["object"] == s["object"] for e in out if e["how"] == "exact") \
                    and any(" ".join(ph) in taken for ph in self.lists["refs"].get(s["object"], []))
                out.append(r)
        none = self.near(self.none, text, toks, list_of)
        if none and (any(all(t["word"] == n["w"] for t, n in zip(toks, nodes)) and len(toks) == len(nodes) for nodes in self.none["compiled"])):
            none["fit"] = 1.0  # said in so many words
        if none:
            none["how"] = "none"
            out.append(none)
        out.sort(key=lambda r: -r["fit"])
        seen = set()
        for r in out:  # the best reading of the object said is the one that contests, not every skill about it
            if r.get("contests"):
                r["contests"] = r["skill"]["object"] not in seen and r["fit"] >= 0.6
                seen.add(r["skill"]["object"])
        return out

    def exact(self, text, toks, list_of):
        """the skills whose sentences read the words as written, the best of each → [reading]"""
        found = []
        for skill in self.skills:
            every = []
            lists = {k: list_of(v["kind"]) for k, v in skill["values"].items()}
            refs = self.refs_for(skill, toks)
            for nodes in skill["compiled"] + skill.get("compiled_also", []):
                every += parses(nodes, toks, refs, lists, self.stops, self.object_words, self.places, self.known)
            if every:
                found.append((skill, best(every)))
        # the readings that read the most words as written (score: one per word, none for a name, less for a
        # value not on the device's list); the rest of the skills are read near, as the others
        top = max((p["score"] for _, p in found), default=0)
        out = []
        for s, p in found:
            if p["score"] < 1 or p["score"] < top:
                continue
            vals = {k: {"text": _original(text, toks, c["start"], c["end"]), "value": c.get("value"), "label": c.get("label"),
                        "unknown": bool(c.get("unknown")), "fuzzy": bool(c.get("fuzzy"))} for k, c in p["caps"].items()}
            fixes = p.get("fixes", [])
            fit = 1.0 - EXACT_TYPO * len(fixes) - UNKNOWN_VALUE * sum(1 for v in vals.values() if v["unknown"])
            # a word TermNL knows as an object (bluetooth, wifi) is more likely that object than a name on the device's
            # list (Gab, 22 Oct: "is bluetooth on" is the board's Bluetooth, not the service called bluetooth): the
            # skill of that object wins when it reads the sentence too, and is offered beside it when it reads it near
            if any(v["text"].lower() in self.object_words for v in vals.values()):
                fit -= OBJECT_AS_NAME
            out.append({"how": "exact", "skill": s, "vals": vals, "fit": fit, "unknown": [], "fixes": fixes, "toks": toks, "p": 1})
        return out

    def bare(self, toks):
        """An action said without its object ("turn on", "switch it off"): the skills that do it, the shared
        action's and those whose own words say it (## Words: "turn off" also stops the music), when there
        are two or more. Nothing else may be said but small and pointing words. → [skill], or []"""
        refs = self.lists["refs"]
        phrases = [ph for a in self.lists["actions"] for ph in refs.get(a, []) if _where(toks, ph)]
        phrases += [ph for s in self.skills for _, phs in s.get("own", []) for ph in phs if _where(toks, ph)]
        if not phrases or any(_where(toks, ph) for o in self.lists["objects"] for ph in refs.get(o, [])):
            return []
        longest = max(len(ph) for ph in phrases)
        said = [ph for ph in phrases if len(ph) == longest]
        covered = {i for ph in said for at in _where(toks, ph) for i in range(at, at + len(ph))}
        if any(i not in covered and t["word"] not in self.small for i, t in enumerate(toks)):
            return []
        fit = [s for s in self.skills if any(ph in self.refs_for(s).get(s["action"], []) for ph in said)]
        return fit if len(fit) >= 2 else []

    def near(self, skill, text, toks, list_of):
        """the skill's reading of a sentence none of its sentences reads as written → the reading, or None"""
        vocab = self.vocab[skill["id"]]
        vals, used = self.values_in(skill, text, toks, list_of)
        # a name the device has ("The Tune", an album) that this skill has no value for is a thing it can't act on:
        # its words count as unknown, unless the skill's own sentences say them
        foreign = {}
        for kind in self.lists.get("device_kinds", ()):
            key = ("device", kind)
            if key not in self._cache:
                self._cache[key] = _best_in(toks, list_of("@sys." + kind) or [], known=self.known)
            hit = self._cache[key]
            if hit and not any(i in used for i in range(hit["i"], hit["i"] + hit["len"])) \
                    and not all(toks[i]["word"] in vocab or toks[i]["word"] in self.small for i in range(hit["i"], hit["i"] + hit["len"])):
                foreign.update({i: self.kind_weight.get("@sys." + kind, SLOT_TEXT) for i in range(hit["i"], hit["i"] + hit["len"])})
        # the new words, side by side, are the value the skill still lacks from the device's list ("kill pipewire":
        # no app of that name): kept as said, so it is answered as not there, never asked for again (Gab, 24 Oct)
        new = [i for i, t in enumerate(toks) if i not in used and i not in foreign and t["word"] not in self.small and t["word"] not in vocab
               and stem(t["word"]) not in self.stems[skill["id"]] and not (self.typos(t["word"]) & vocab)]
        missing = [k for k, spec in skill["values"].items() if k not in vals and spec["required"] and not spec.get("default")]
        acted = any(_where(toks, ph) for ph in self.refs_for(skill, toks).get(skill["action"], []))
        if acted and len(missing) == 1 and skill["values"][missing[0]]["kind"].startswith("@sys.") and list_of(skill["values"][missing[0]]["kind"]) is not None \
                and new and new == list(range(new[0], new[-1] + 1)):
            vals[missing[0]] = {"text": _original(text, toks, new[0], new[-1] + 1), "unknown": True, "kind": skill["values"][missing[0]]["kind"], "used": set(new)}
            used |= set(new)
        own_object = {w for ph in self.lists["refs"].get(skill["object"], []) for w in ph}  # the thing it is about counts double
        explained, total, fixes, unknown = 0.0, 0.0, [], []
        for i, t in enumerate(toks):
            w = t["word"]
            if i in foreign:
                total += foreign[i]
                unknown.append(w)
                continue
            if w in self.small:
                continue
            if i in used:
                v = next(v for v in vals.values() if i in v["used"])
                weight = self.kind_weight.get(v["kind"], SLOT_TEXT) if v.get("value") is not None else SLOT_TEXT
                explained += weight * (0.5 if v.get("unknown") else 1)  # a value the device doesn't have: half known
                total += weight
                continue
            v = w if w in vocab else self.stems[skill["id"]].get(stem(w))
            if v:
                weight = self.weight(v) * (2 if v in own_object else 1)
                explained += weight * self.share(skill, v)
                total += weight
                continue
            near = self.typos(w) & vocab
            if len(near) == 1:
                v = next(iter(near))
                explained += NEAR_TYPO * self.weight(v) * self.share(skill, v)
                total += self.weight(v)
                fixes.append([w, v])
                continue
            total += self.weight(w)
            unknown.append(w)
        if total == 0:
            return None
        coverage = explained / total
        refs = self.refs_for(skill, toks)
        recall = max((self.similar(nodes, refs, toks, vals, used) for nodes in skill["compiled"] + skill.get("compiled_also", [])), default=0)
        if skill["action"] is None:  # out of scope: no action or object to agree on
            split = 0.5 * (coverage + recall)
        else:
            split = self.agree("action", skill["action"], toks, used) * self.agree("object", skill["object"], toks, used)
        fit = (coverage + recall + split) / 3
        clean = {k: {x: v[x] for x in ("text", "value", "label", "fuzzy", "unknown") if x in v} for k, v in vals.items()}
        return {"how": "near", "skill": skill, "vals": clean, "fit": fit, "p": fit, "unknown": unknown, "fixes": fixes, "toks": toks,
                "coverage": coverage, "recall": recall, "split": split}

    def similar(self, nodes, refs, toks, vals, used):
        """how alike the sentence and one of the skill's sentences are: what they share, against everything either
        says (a weighted Jaccard). A word weighs what it is worth (weight), a small word a little (SMALL), a value
        its kind's weight; a word of the skill's sentence that may be left out counts only when said; "using"
        is "used" (stem), "chek" is "check" (close)."""
        ws = [t["word"] for t in toks]
        stems = {stem(w): w for w in ws}
        said = set()  # the sentence's words the skill's sentence accounts for

        def found(w):
            if w in ws:
                said.add(w)
                return True
            if stem(w) in stems:
                said.add(stems[stem(w)])
                return True
            near = next((x for x in ws if w in self.typos(x)), None)
            if near:
                said.add(near)
                return True
            return False

        line, shared = 0.0, 0.0
        for node in nodes:
            if node["t"] == "w":
                weight, hit = (SMALL if node["w"] in self.small else self.weight(node["w"])), found(node["w"])
            elif node["t"] == "ref":
                phrases = refs.get(node["name"], [])
                weight = max((self.weight(w) for ph in phrases for w in ph), default=1.0)
                hit = any(_where(toks, ph) for ph in phrases) or any(all(found(w) for w in ph) for ph in phrases)
                if hit:
                    said.update(w for ph in phrases if _where(toks, ph) for w in ph)
            elif node["t"] == "slot":
                v = vals.get(node["name"])
                weight = self.kind_weight.get(v["kind"], SLOT_TEXT) if v and v.get("value") is not None else SLOT_TEXT
                hit = v is not None
            else:  # a choice of words; one that may be left out counts only when said
                words_ = list(self._node_words(node["alts"], refs))
                hit = any(found(w) for w in words_)
                if node["opt"] and not hit:
                    continue
                weight = max((SMALL if w in self.small else self.weight(w) for w in words_), default=SMALL)
            line += weight
            shared += weight if hit else 0
        sentence = 0.0
        for i, t in enumerate(toks):
            w = t["word"]
            if i in used:
                v = next(v for v in vals.values() if i in v["used"])
                sentence += self.kind_weight.get(v["kind"], SLOT_TEXT) if v.get("value") is not None else SLOT_TEXT
            elif w not in said:
                sentence += SMALL if w in self.small else self.weight(w)
        # what both say, against what either says: the line's units, and the sentence's words not accounted for
        return shared / (line + sentence) if line + sentence else 0

    def values_in(self, skill, text, toks, list_of):
        """Values found by their own readers, anywhere in the sentence: a name from a device list or a shared
        list, a name after "called"/"named", a file-shaped word (for a skill about files)."""
        vals, used = {}, set()
        for k, spec in skill["values"].items():
            key = ("list", spec["kind"])
            if key not in self._cache:  # the same list for every skill with a value of this kind
                self._cache[key] = _best_in(toks, list_of(spec["kind"]) or [], fuzzy=True, known=self.known)
            hit = self._cache[key]
            if hit and not any(i in used for i in range(hit["i"], hit["i"] + hit["len"])):
                span = set(range(hit["i"], hit["i"] + hit["len"]))
                vals[k] = {"value": hit["o"]["value"], "label": hit["o"]["label"], "fuzzy": hit["fuzzy"], "kind": spec["kind"], "used": span}
                used |= span
        about_files = skill["object"] == "file" or any(s["kind"] in ("@sys.file", "filetype") for s in skill["values"].values())
        for k, spec in skill["values"].items():
            if list_of(spec["kind"]) or k in vals:
                continue
            after = next((i for i, t in enumerate(toks) if t["word"] in self.leads), -1)
            end = after + 1
            while 0 <= after and end < len(toks) and toks[end]["word"] not in self.ends and end not in used:
                end += 1
            if after >= 0 and end > after + 1:
                span = set(range(after, end))
                vals[k] = {"text": _original(text, toks, after + 1, end), "kind": spec["kind"], "used": span}
                used |= span
                continue
            if about_files:
                f = next((i for i, t in enumerate(toks) if i not in used and file_shaped(t["word"], self.exts)), -1)
                if f >= 0:
                    vals[k] = {"text": _original(text, toks, f, f + 1), "kind": spec["kind"], "used": {f}}
                    used.add(f)
        return vals, used


def _by_stem(counts):
    out = {}
    for w, n in counts.items():
        out[stem(w)] = out.get(stem(w), 0) + n
    return out


def _where(toks, phrase):
    n = len(phrase)
    return [i for i in range(len(toks) - n + 1) if n and all(toks[i + j]["word"] == w for j, w in enumerate(phrase))]


def _best_in(toks, found, fuzzy=False, known=frozenset()):
    """the longest phrase of a list said in the sentence (a typo of one too, when fuzzy, exact first; a word
    some skill knows is a real word, never a typo: "files" is not "films")"""
    hit = None
    for o in found:
        for ph in o["phrases"]:
            for i in range(len(toks) - len(ph) + 1):
                exact = all(toks[i + j]["word"] == w for j, w in enumerate(ph))
                near = fuzzy and not exact and all(close(toks[i + j]["word"], w) and (toks[i + j]["word"] == w or toks[i + j]["word"] not in known)
                                                   for j, w in enumerate(ph))
                if (exact or near) and (not hit or len(ph) > hit["len"] or (exact and hit["fuzzy"])):
                    hit = {"o": o, "i": i, "len": len(ph), "fuzzy": near}
    return hit


def _original(text, toks, start, end):
    """what the person typed for these words (a name keeps its typos and capitals)"""
    return text.translate(str.maketrans({"’": "'", "‘": "'", "`": "'"}))[toks[start]["start"]:toks[end - 1]["end"]]
