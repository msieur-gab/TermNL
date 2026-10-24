"""python3 -m unittest — plain sentences and "What it needs" (termnl/plain.py), the proposal of 24 Oct 2026."""
import unittest

from termnl.load import load_language
from termnl.plain import read_needs, to_template
from termnl.skills import load

lang = load_language("en")
lists = lang["lists"]


class Plain(unittest.TestCase):
    def test_a_sentence_as_people_say_it(self):
        for plain, template in [
            ("make a (new) folder called/named {name} (in {place})", "<create> a [ new ] <folder> (called|named) {name} [ in {place} ]"),
            ("turn the wifi off", "turn the <wifi> off"),
            ("what/which files are here", "(what|which) <file> are here"),
            ('"reboot" now', "reboot now"),
            ("make a folder in the {place} folder", "<create> a <folder> in the {place} <folder>"),
        ]:
            self.assertEqual(to_template(plain, lists, ("create", "folder")), template, plain)

    def test_mistakes_are_said_in_words(self):
        for bad in ("make a (folder", "make a folder)", "make a folder/"):
            with self.assertRaises(ValueError, msg=bad):
                to_template(bad, lists)
        with self.assertRaisesRegex(ValueError, "create and open"):
            to_template("start the music", lists, ("play", "music"))

    def test_what_it_needs_in_words(self):
        values, asks, problems = read_needs([
            "- {name}: a new name. If it's missing, ask: What should I call it? | What name should it have?",
            "- {place}: a folder on the device. If it's not said: where you are.",
            "- {up}: a folder on the device. If it's not said: the folder {place} is in.",
            "- {type}: a file type. If it's not said: markdown.",
        ], lists["values_md"])
        self.assertEqual(problems, [])
        self.assertEqual(values["name"], {"kind": "text", "required": True, "new": True})
        self.assertEqual(asks["ask name"], "What should I call it? | What name should it have?")
        self.assertEqual(values["place"]["default"], "here")
        self.assertEqual(values["up"]["default"], "parent of place")
        self.assertEqual(values["type"], {"kind": "filetype", "required": False, "default": "markdown"})
        _, _, problems = read_needs(["- {x}: a colour."], lists["values_md"])
        self.assertEqual(len(problems), 1)

    def test_a_skill_written_from_scratch_loads_and_is_understood(self):
        md = """---
does: create folder
label: make a folder
---

## People say

- make a (new) folder called/named {name} (in (the) {place} (folder))
- make a {name} folder

## What it needs

- {name}: a new name. If it's missing, ask: What should I call it?
- {place}: a folder on the device. If it's not said: where you are.

## Command

mkdir -p {place}/{name}

## Replies

- done: Done, {name} is in {place}.
"""
        from termnl.load import language_dir, read
        import os
        d = language_dir("en")
        files = {k: read(os.path.join(d, "words", k + ".md")) for k in ("actions", "objects", "filetypes", "conversation", "samples", "readings", "values")}
        loaded = load(files, {"make-folder": md})
        self.assertEqual(loaded["errors"], [])
        from termnl.agent import Agent
        from tests.device import device
        r = Agent(**loaded, device=device, random=lambda: 0).hear("create a new directory named bikes in the documents folder")
        self.assertEqual((r["outcome"], r["command"]), ("act", "mkdir -p $HOME'/Documents/bikes'"))


if __name__ == "__main__":
    unittest.main()
