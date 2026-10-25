"""python3 -m tools.common_words <folder> [size] — writes termnl/languages/en/words/common.md, the English words
TermNL never reads as a typo (RESEARCH.md, method F), from SCOWL's lists as packaged on npm:

    npm pack wordlist-english && tar xzf wordlist-english-*.tgz      # gives package/english-words-<n>.json

size is SCOWL's size, 10 (the most common words) to 70; the words of every size up to it are kept (default
20). Names (a capital letter), possessives and anything not plain letters are left out. Standard library."""
import json
import os
import sys

from termnl.load import language_dir

SIZES = (10, 20, 35, 40, 50, 55, 60, 70)

HEADER = """# Common words

English words that are never read as a typo of a word TermNL knows. Without this list, "who won the football
game last night" was read as "name" ("game" → "name", "night" → "right"), and "format my usb stick" as
"stuck" (RESEARCH.md, method F). A word TermNL knows is read as itself whether or not it is here; this list
only stops a real word being changed into another. Words that aren't here and aren't known are still read
as typos ("memroy" → "memory").

Built with `python3 -m tools.common_words <folder> {size}` from SCOWL size {size} and below (Kevin Atkinson,
wordlist-english on npm): {count} words. To change it, rebuild it rather than edit it; a word added by hand
belongs at the end, under "## Added".

SCOWL: Copyright 2000-2016 by Kevin Atkinson. Permission to use, copy, modify, distribute and sell these word
lists, the associated scripts, the output created from the scripts, and its documentation for any purpose is
hereby granted without fee, provided that the above copyright notice appears in all copies and that both
that copyright notice and this permission notice appear in supporting documentation. Kevin Atkinson makes
no representations about the suitability of this array for any purpose. It is provided "as is" without
express or implied warranty.

## Words
"""


def build(folder, size=20):
    words = set()
    for n in SIZES:
        if n > size:
            break
        with open(os.path.join(folder, "english-words-%d.json" % n), encoding="utf-8") as f:
            words |= {w for w in json.load(f) if w.isalpha() and w.isascii() and w.islower()}
    lines, line = [], ""
    for w in sorted(words):
        if line and (line[0] != w[0] or len(line) + 1 + len(w) > 100):  # a line per letter, wrapped
            lines.append(line)
            line = ""
        line = (line + " " + w) if line else w
    lines.append(line)
    return HEADER.format(size=size, count=len(words)) + "\n" + "\n".join(lines) + "\n\n## Added\n", len(words)


if __name__ == "__main__":
    folder = sys.argv[1]
    size = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    text, n = build(folder, size)
    path = os.path.join(language_dir("en"), "words", "common.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("%d words → %s" % (n, os.path.relpath(path)))
