"""python3 -m tools.compare_runs <before.txt> <after.txt> — two outputs of `python3 -m tests.measure <set> -v` (one set after
another), compared set by set, sentence by sentence: every sentence whose outcome or skill moved."""
import re, sys
def parse(p):
    sets, cur = {}, []
    for l in open(p):
        if re.match(r"^[\w-]+, \d+ sentences", l):
            sets[l.split(",")[0]] = cur; cur = []
        elif l.strip():
            m = re.match(r"^(\S+)\s+(\S+)\s+(\S+)\s+(.*)$", l.rstrip("\n"))
            cur.append(m.groups())
    return sets
a, b = parse(sys.argv[1]), parse(sys.argv[2])
for s in a:
    if s not in b: continue
    for x, y in zip(a[s], b[s]):
        text = re.sub(r"\s+\[new: .*\]$", "", x[3])
        if (x[0], x[2]) != (y[0], y[2]):
            print("%-11s %-16s %-8s %-16s → %-8s %-16s %s" % (s, y[1], x[0], x[2], y[0], y[2], text))
