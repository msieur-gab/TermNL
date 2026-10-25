"""python3 -m unittest tests.test_drop_in — a skill folder dropped in works alone (FRAMES.md, 25 Oct 2026).

check-kernel brings an object ("kernel") and ping-remote an action ("ping") that no list of words/ has. Born
as test-only skills, shipped since 25 Oct 2026: here they are taken out of the language, then dropped back in
as their folders are, with nothing else edited. Templates read them at once; the model knows them after
"learn what I taught you"."""
import os
import unittest

from termnl.agent import Agent
from termnl.load import LANGUAGES, language_dir, read
from termnl.skills import load
from tests.device import device

LISTS = ("actions", "objects", "filetypes", "conversation", "samples", "readings", "values")
SKILLS = os.path.join(language_dir("en", LANGUAGES), "skills")
DROPPED = ("check-kernel", "ping-remote")


def language(extra):
    """the English skills and words without the two dropped-in skills, with these skill files added: {id: skill.md}"""
    d = language_dir("en", LANGUAGES)
    lists = {k: read(os.path.join(d, "words", k + ".md")) for k in LISTS}
    skills = {id: read(os.path.join(SKILLS, id, "skill.md")) for id in sorted(os.listdir(SKILLS)) if id not in DROPPED}
    skills.update(extra)
    return load(lists, skills)


def dropped():
    return {id: read(os.path.join(SKILLS, id, "skill.md")) for id in DROPPED}


class DropIn(unittest.TestCase):
    def test_a_skill_folder_brings_its_own_action_and_object(self):
        before = language({})
        self.assertNotIn("kernel", before["lists"]["objects"])
        self.assertNotIn("ping", before["lists"]["actions"])
        lang = language(dropped())
        self.assertEqual(lang["errors"], [])
        self.assertIn("kernel", lang["lists"]["objects"])
        self.assertIn("ping", lang["lists"]["actions"])
        self.assertIn(["linux", "version"], lang["lists"]["refs"]["kernel"])
        # its help topic, said in its own front matter
        self.assertIn("kernel", dict(lang["lists"]["topics"])["This device"])

    def test_it_is_understood_and_acts_without_a_word_of_words_changed(self):
        a = Agent(**language(dropped()), settings={}, device=device, random=lambda: 0)
        r = a.hear("check the kernel")
        self.assertEqual((r["outcome"], r["skill"], r["command"]), ("act", "check-kernel", "uname -r"))
        r = a.hear("can you reach the studio pi")
        self.assertEqual((r["outcome"], r["skill"], r["command"]), ("act", "ping-remote", "ping -c 3 'studio-pi'"))
        self.assertEqual(a.hear("ping a remote computer")["say"], "Which computer?")
        # before learning, only its own sentences: "ping" alone needs the model to know it
        a = Agent(**language(dropped()), settings={}, device=device, random=lambda: 0)
        self.assertEqual(a.hear("ping")["outcome"], "abstain")

    def test_what_a_word_means_with_its_object_is_said_by_the_skill(self):
        # play-music says "turn on the music" plays it (## Words), no longer words/actions.md
        r = Agent(**language({}), settings={}, device=device, random=lambda: 0).hear("turn on the music")
        self.assertEqual((r["outcome"], r["skill"]), ("act", "play-music"))

    def test_a_skill_gives_words_only_for_itself(self):
        md = read(os.path.join(SKILLS, "check-kernel", "skill.md"))
        lang = language({"check-kernel": md.replace("- kernel: kernel", "- memory: brain cells\n- kernel: kernel")})
        self.assertTrue(any('"memory" is not its action or object' in e for e in lang["errors"]), lang["errors"])
        lang = language({"check-kernel": md.replace("## Words\n", "## Words\n\n- start → play\n")})
        self.assertTrue(any("a skill says only what words mean for itself" in e for e in lang["errors"]), lang["errors"])


if __name__ == "__main__":
    unittest.main()
