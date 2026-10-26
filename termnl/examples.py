"""Training sentences made from the skills' own sentences, each word tagged with what it is (tagger.py):
a template becomes many sentences, with its optional words in and out, each alternative, each word for
its action and object, and sample values; an Also said line is tagged by the words it shares with the
skill (its action's and object's words, the samples of its values, a file-shaped word, a name after
"called"). Authors write a few readable lines; the tagger and the classifier learn from all their
variations."""
import zlib

from .tagger import FILE_RE, role_of
from .template import uses
from .text import words


AROUND = 0.1  # the share of sentences said with words around them ("can you", "please", "now")


def samples_for(kind, lists):
    """sample values for training only (words/samples.md); real values come from the device at run time"""
    if kind == "filetype":
        return [" ".join(p) for t in lists["filetypes"] for p in t["phrases"]]
    return lists["samples"].get(kind) or lists["samples"]["text"]


ARTICLES = ("the", "a", "an", "my")


def own_words(skill, lists):
    """the words of the skill's action (and of the words that mean it with its object, ## Words) and of its
    object: a template word written as itself that is one of them is tagged as such ("turn/switch the wifi
    off": "off" is a word of turn off)"""
    refs = lists["refs"]
    acts = {w for ph in refs.get(skill["action"], []) for w in ph}
    for rule in lists.get("in_context", []):
        if rule["action"] == skill["action"] and skill["object"] in rule["objects"]:
            acts |= {w for ph in rule["phrases"] for w in ph}
    return acts, {w for ph in refs.get(skill["object"], []) for w in ph}


def sample_tags(sample, tag):
    """a sample's words tagged as the value, its leading article left as a word ("the web server")"""
    ws = words(sample)
    lead = 1 if len(ws) > 1 and ws[0] in ARTICLES else 0
    return [(w, "_") for w in ws[:lead]] + [(w, tag) for w in ws[lead:]]


def says_action(nodes, actions):
    return any(n["t"] == "ref" and n["name"] in actions or n["t"] == "alt" and any(says_action(a, actions) for a in n["alts"]) for n in nodes)


def phrases_for(name, skill, lists):
    """the words for an action or object in this skill's sentences: for its action, the words that mean it with
    its object too (## Words: "turn on → play")"""
    ph = list(lists["refs"][name])
    if name == skill["action"]:
        ph += [p for rule in lists.get("in_context", []) if rule["action"] == name and skill["object"] in rule["objects"] for p in rule["phrases"]]
    return ph


def walk(nodes, lists, skill, rnd, own=None, fixed=None):
    """one random walk through a template → [(word, tag)]; fixed: {action or object: its phrase}, chosen in
    advance. A word written as itself is tagged as the action when the template names the action in no other
    way ("turn/switch the wifi off"), as the object when it is a word for it."""
    if own is None:
        acts, objs = own_words(skill, lists)
        own = (acts if not says_action(nodes, lists["actions"]) else set(), objs)
    out = []
    for n in nodes:
        if n["t"] == "w":
            out.append((n["w"], "A" if n["w"] in own[0] else "O" if n["w"] in own[1] else "_"))
        elif n["t"] == "ref":
            ph = phrases_for(n["name"], skill, lists)
            tag = "A" if n["name"] in lists["actions"] else "O"
            chosen = (fixed or {}).get(n["name"]) or ph[int(rnd() * len(ph))]
            out += [(w, tag) for w in chosen]
        elif n["t"] == "slot":
            spec = skill["values"][n["name"]]
            s = samples_for(spec["kind"], lists)
            out += sample_tags(s[int(rnd() * len(s))], "V:" + role_of(n["name"], spec))
        elif n["t"] == "alt":
            if n["opt"] and rnd() < 0.5:
                continue
            out += walk(n["alts"][int(rnd() * len(n["alts"]))], lists, skill, rnd, own, fixed)
    return out


def rng(seed=7):
    s = seed & 0xFFFFFFFF

    def r():
        nonlocal s
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        return s / 4294967296
    return r


def tag_plain(text, skill, lists):
    """An Also said line, tagged by what it shares with the skill: the longest phrases for its action (and
    the words that mean its action with its object, ## Words) are A, for its object O; a sample of one of
    its values' kinds, a file-shaped word (for a skill with a file or a name), or the words after "called"
    or "named" (for a name) are that value; the rest is _."""
    ws = words(text)
    tags = [None] * len(ws)
    refs = lists["refs"]

    def mark(phrases, tag, once=False):
        for ph in sorted(phrases, key=len, reverse=True):
            lead = 1 if tag.startswith("V:") and len(ph) > 1 and ph[0] in ARTICLES else 0
            for i in range(len(ws) - len(ph) + 1):
                if ws[i:i + len(ph)] == list(ph) and all(t is None for t in tags[i:i + len(ph)]):
                    for j in range(i + lead, i + len(ph)):
                        tags[j] = tag
                    if once:  # an action is said once ("add a new file": the second word for create is just new)
                        return

    acts = list(refs.get(skill["action"], []))
    for rule in lists.get("in_context", []):
        if rule["action"] == skill["action"] and skill["object"] in rule["objects"]:
            acts += rule["phrases"]
    mark(acts, "A", once=True)
    mark(refs.get(skill["object"], []), "O")
    act_words, obj_words = own_words(skill, lists)
    split = "A" not in tags  # "switch the wifi off": no phrase of the action, but its words apart
    for i, w in enumerate(ws):
        if tags[i] is None and w in obj_words:
            tags[i] = "O"
        elif tags[i] is None and split and w in act_words:
            tags[i] = "A"
    roles = {k: role_of(k, spec) for k, spec in skill["values"].items()}
    for k, spec in skill["values"].items():
        mark([words(s) for s in samples_for(spec["kind"], lists)], "V:" + roles[k])
    file_role = next((r for r in roles.values() if r == "file"), None) or next((r for r in roles.values() if r in ("name", "new")), None)
    name_role = next((r for r in roles.values() if r in ("name", "new", "words")), None)
    leads = {ph[0] for ph in lists["conversation"].get("before a name", []) if len(ph) == 1}
    ends = {" ".join(ph) for ph in lists["conversation"].get("name ends before", [])}
    for i, w in enumerate(ws):
        if tags[i] is None and file_role and FILE_RE.match(w):
            tags[i] = "V:" + file_role
    for i, w in enumerate(ws):
        if w in leads and name_role and i + 1 < len(ws) and tags[i + 1] is None:
            j = i + 1
            while j < len(ws) and tags[j] is None and ws[j] not in ends:
                tags[j] = "V:" + name_role
                j += 1
    if "new" in roles.values():  # "rename photos to pictures": the new name is what follows "to" after the old one
        at = next((i for i in range(1, len(ws)) if ws[i] in ("to", "into", "as") and tags[i - 1] and tags[i - 1].startswith("V:")), None)
        if at is not None and all(t is None for t in tags[at + 1:]) and at + 1 < len(ws):
            for j in range(at + 1, len(ws)):
                tags[j] = "V:new"
    return [(w, t or "_") for w, t in zip(ws, tags)]


def examples(skills, lists, per_skill=160, per_template=None, seed=7):
    """→ [{tagged, skill}], deduplicated. Each sentence is walked once for every pair of a word for its action
    and a word for its object ("turn on" with "music", "switch on" with "tunes"…), so the classifier sees
    every pair it may hear, then at random: each skill gets the same number of random walks (per_skill),
    shared among its sentences, at least 10 each: a skill written as many short sentences weighs no more than
    one written as a few long ones. per_template, when given, is the walks per sentence instead."""
    seen, out = set(), []
    said = lists["conversation"]
    # what people put around a request: "can you", "please", "now", "for me" (conversation.md): a quarter of the
    # sentences get some, so the tagger and the classifier read a request with words around it as well
    before = said.get("filler start", []) + said.get("follow-up words", [])
    after = said.get("filler end", [])

    def keep(skill, tagged, only_with, own_objects, rnd=None):
        # a word that means the action with the object ("turn on" is unmute, with the sound) is only said with it
        if [w for w, t in tagged if t == "A"] in only_with and not any(t == "O" and w in own_objects for w, t in tagged):
            return
        if rnd and rnd() < AROUND:
            tagged = [(w, "_") for w in before[int(rnd() * len(before))]] + tagged
        if rnd and rnd() < AROUND * 0.6:
            tagged = tagged + [(w, "_") for w in after[int(rnd() * len(after))]]
        key = skill["id"] + "|" + " ".join(w for w, _ in tagged)
        if key not in seen:
            seen.add(key)
            out.append({"tagged": tagged, "skill": skill["id"]})

    for skill in skills:
        # each skill its own random stream, from its name: a skill dropped in leaves the sentences of every
        # other skill as they were
        rnd = rng(seed ^ zlib.crc32(skill["id"].encode("utf-8")))
        n = per_template or max(10, -(-per_skill // max(1, len(skill["compiled"]))))
        only_with = [p for p in phrases_for(skill["action"], skill, lists) if p not in lists["refs"].get(skill["action"], [])]
        own_objects = {w for ph in lists["refs"].get(skill["object"], []) for w in ph}
        for nodes in skill["compiled"]:
            names = uses(nodes)["refs"]
            acts = phrases_for(skill["action"], skill, lists) if skill["action"] in names else [None]
            objs = phrases_for(skill["object"], skill, lists) if skill["object"] in names else [None]
            for a in acts:
                for o in objs:
                    keep(skill, walk(nodes, lists, skill, rnd, fixed={skill["action"]: a, skill["object"]: o}), only_with, own_objects)
            for _ in range(n):
                keep(skill, walk(nodes, lists, skill, rnd), only_with, own_objects, rnd)
        # what people really say (## Also said), each counted three times: a few plain sentences among the
        # templates' many variations
        for text in skill["also"]:
            out += [{"tagged": tag_plain(text, skill, lists), "skill": skill["id"]}] * 3
    return out


def taught_words(exs, skills=(), lists=None):
    """The words a skill has been taught: every word of its generated sentences, and every word for its action
    and object."""
    by = {}
    for e in exs:
        by.setdefault(e["skill"], set()).update(w for w, _ in e["tagged"])
    for s in skills:
        acts, objs = own_words(s, lists)
        by.setdefault(s["id"], set()).update(acts | objs)
    return by


def text_of(e):
    return " ".join(w for w, _ in e["tagged"])
