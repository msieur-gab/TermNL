"""python3 -m tools.overlap [skill-id…] — where skills clash. Every sentence a skill owns (its ## Also said lines
and its tests.md) goes through the reader; a sentence read as another skill, or left to the person to choose,
is a clash, printed for the author to fix in the skill files (a word for words/, a line for Also said)
before a person hits it. Nothing in how TermNL answers changes. With skill ids, only those skills' sentences
and every other skill's sentences read as them: what to run after dropping a skill in."""
import sys

from termnl.agent import Agent
from termnl.load import load_language
from tests.device import device
from tests.measure import skill_tests


def clashes(agent, skills, only=()):
    tests = skill_tests()
    out = []
    for s in skills:
        for where, line in [("Also said", l) for l in s["also"]] + [("tests.md", l) for l in tests.get(s["id"], [])]:
            r = agent.reader.read(line, agent.reader.clean(line))
            got = r["skill"]["id"] if r and r["how"] != "choose" else "/".join(o["skill"]["id"] for o in r["options"]) if r else "—"
            if got != s["id"] and (not only or s["id"] in only or any(x in only for x in got.split("/"))):
                out.append((s["id"], where, line, got))
    return out


if __name__ == "__main__":
    lang = load_language()
    agent = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0)
    found = clashes(agent, lang["skills"], set(sys.argv[1:]))
    for id, where, line, got in found:
        print("%-18s %-9s %-60s → %s" % (id, where, line[:60], got))
    n = sum(len(s["also"]) for s in lang["skills"]) + sum(len(v) for v in skill_tests().values())
    print("\n%d of %d sentences read as another skill, or as a choice" % (len(found), n))
