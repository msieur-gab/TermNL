"""python3 -m unittest tests.test_frames — follow-ups: a sentence that says part of a request, completed by the
last request done (FRAMES.md, 25 Oct 2026)."""
import os
import unittest

from termnl.agent import Agent
from tests.device import device
from tests.test_dialogue import agent


def talk(*turns, settings=None):
    a = agent(settings)
    return a, [a.hear(t) for t in turns]


class FollowUps(unittest.TestCase):
    def test_now_delete_it_is_the_file_just_opened_and_the_approval_names_it(self):
        _, (_, r) = talk("open seed.md in ideas", "now delete it")
        self.assertEqual((r["outcome"], r["skill"]), ("approve", "delete-file"))
        self.assertEqual(r["say"], "Move seed.md from ideas to the trash?")

    def test_rename_it_is_the_folder_just_made(self):
        _, (_, r) = talk("create a folder called bikes", "rename it to cycles")
        self.assertEqual((r["outcome"], r["skill"], r["command"]), ("act", "rename-folder", "mv -nT $HOME'/bikes' $HOME'/cycles'"))

    def test_and_in_downloads_is_the_same_request_there(self):
        _, (_, r) = talk("show the files in documents", "and in downloads?")
        self.assertEqual((r["outcome"], r["skill"], r["args"]), ("act", "show-folder", {"place": "$HOME/Downloads"}))

    def test_and_bluetooth_too_is_the_same_action(self):
        _, (_, _, r) = talk("turn on the wifi", "yes", "and bluetooth too", settings={"admin mode": "on"})
        self.assertEqual((r["outcome"], r["skill"]), ("approve", "turn-on-bluetooth"))

    def test_turn_it_back_off_is_the_same_object(self):
        _, (_, _, r) = talk("turn on bluetooth", "yes", "turn it back off", settings={"admin mode": "on"})
        self.assertEqual((r["outcome"], r["skill"]), ("approve", "turn-off-bluetooth"))

    def test_turn_it_off_stops_the_music_by_what_the_skill_says_its_words_mean(self):
        _, (_, r) = talk("play music", "turn it off")
        self.assertEqual((r["outcome"], r["skill"]), ("act", "stop-music"))

    def test_the_other_one_is_the_same_file_elsewhere_looked_for_again(self):
        _, (_, r) = talk("open note.md in ideas", "open the other one in documents")
        self.assertEqual((r["outcome"], r["command"]), ("act", "xdg-open $HOME'/Documents/note.md'"))

    def test_same_for_another_file(self):
        _, (_, r) = talk("copy todo.txt to documents", "same for note.md")
        self.assertEqual((r["outcome"], r["command"]), ("act", "cp $HOME'/note.md' $HOME'/Documents/'"))


class NamesDontMatter(unittest.TestCase):
    """Follow-ups find the folder a thing is in by what a skill says it needs ("a folder on the device. If it's
    not said: where you are"), never by the value's name: here every {place} is renamed {where}."""

    def test_the_same_follow_ups_with_the_folder_named_otherwise(self):
        from tests.test_drop_in import SKILLS, language
        from termnl.load import read
        renamed = {id: read(os.path.join(SKILLS, id, "skill.md")).replace("{place}", "{where}")
                   for id in ("open-file", "delete-file", "copy-file", "restore-file", "show-folder")}
        lang = language(renamed)
        self.assertEqual(lang["errors"], [])

        def talk_(*turns):
            a = Agent(**lang, settings={}, device=device, random=lambda: 0)
            return [a.hear(t) for t in turns]
        r = talk_("open seed.md in ideas", "now delete it")[-1]
        self.assertEqual((r["outcome"], r["say"]), ("approve", "Move seed.md from ideas to the trash?"))
        r = talk_("copy todo.txt to documents", "same for note.md")[-1]
        self.assertEqual(r["command"], "cp $HOME'/note.md' $HOME'/Documents/'")
        r = talk_("open seed.md in ideas", "now delete it", "yes", "bring it back")[-1]
        self.assertEqual(r["command"], "mv -n $HOME'/.local/share/Trash/files/seed.md' $HOME'/ideas/'")

    def test_a_new_name_gets_its_extension_whatever_the_value_is_called(self):
        # 25 Oct (fix B): before, a create-file whose {name} was called {file} made "plans", without .md
        from tests.test_drop_in import SKILLS, language
        from termnl.load import read
        md = read(os.path.join(SKILLS, "create-file", "skill.md")).replace("{name}", "{file}").replace("ask name", "ask file")
        lang = language({"create-file": md})
        self.assertEqual(lang["errors"], [])
        for said, made in (("create a markdown file called plans", "plans.md"), ("create a file called notes.txt", "notes.txt")):
            r = Agent(**lang, settings={}, device=device, random=lambda: 0).hear(said)
            self.assertEqual(r["command"], "touch $HOME'/%s'" % made, said)


class Guards(unittest.TestCase):
    def test_a_full_request_is_never_a_follow_up(self):
        _, (_, r) = talk("open seed.md in ideas", "open firefox")
        self.assertEqual(r["skill"], "open-app")
        _, (_, r) = talk("open seed.md in ideas", "now open firefox")
        self.assertEqual(r["skill"], "open-app")

    def test_a_word_that_isnt_a_value_or_a_small_word_makes_it_a_new_request(self):
        _, (_, r) = talk("show the files in documents", "and what about the weather")
        self.assertNotEqual(r.get("how"), "frame")

    def test_them_never_points_at_one_thing(self):
        _, (_, r) = talk("show the files in documents", "delete them")
        self.assertNotEqual(r.get("how"), "frame")
        self.assertNotEqual(r["outcome"], "approve")

    def test_a_follow_up_said_with_no_is_asked_first(self):
        _, (_, r) = talk("open seed.md in ideas", "don't delete it")
        self.assertEqual(r["outcome"], "ask")
        self.assertNotIn("command", r)

    def test_nothing_done_yet_nothing_to_point_at(self):
        _, (r,) = talk("now delete it")
        self.assertNotEqual(r["outcome"], "approve")
        self.assertNotEqual(r.get("how"), "frame")

    def test_a_request_said_no_to_is_never_what_it_points_at(self):
        a, _ = talk("open seed.md in ideas", "now delete it", "no")
        self.assertEqual(a.frame["skill"]["id"], "open-file")  # still the file opened, not the delete refused

    def test_cancel_and_a_sentence_not_understood_forget_the_request_before(self):
        a, _ = talk("open seed.md in ideas", "cancel")
        self.assertIsNone(a.frame)
        a, _ = talk("open seed.md in ideas", "what's the weather in tokyo")
        self.assertIsNone(a.frame)


if __name__ == "__main__":
    unittest.main()
