"""python3 -m unittest tests.test_trash_and_space — the four skills dropped in on 25 Oct 2026 (FRAMES.md, E):
empty-trash, restore-file, find-text, show-size."""
import unittest

from tests.test_frames import talk


class TrashAndSpace(unittest.TestCase):
    def test_emptying_the_trash_is_approved_first(self):
        for said in ("empty the trash", "take out the trash", "clear out the bin"):
            _, (r,) = talk(said)
            self.assertEqual((r["outcome"], r["skill"]), ("approve", "empty-trash"), said)

    def test_get_rid_of_everything_in_the_trash_asks_before_emptying_it(self):
        # was "Do you mean delete a file or empty the trash?": delete file read it only by taking "everything in the
        # trash" as a file's name, so the skill the sentence names reads it (Gab, 26 Oct: "do you have carrots")
        _, (r,) = talk("get rid of everything in the trash")
        self.assertEqual((r["outcome"], r.get("skill")), ("approve", "empty-trash"))
        self.assertNotIn("command", r)

    def test_a_file_comes_back_from_the_trash(self):
        _, (r,) = talk("bring todo.txt back")
        self.assertEqual((r["outcome"], r["command"]), ("act", "mv -n $HOME'/.local/share/Trash/files/todo.txt' $HOME'/'"))

    def test_bring_it_back_undoes_the_delete_into_the_folder_it_came_from(self):
        for said in ("bring it back", "restore it"):
            _, rs = talk("open seed.md in ideas", "now delete it", "yes", said)
            self.assertEqual((rs[-1]["outcome"], rs[-1]["command"]),
                             ("act", "mv -n $HOME'/.local/share/Trash/files/seed.md' $HOME'/ideas/'"), said)

    def test_text_is_looked_for_inside_the_files_names_by_find_file(self):
        _, (r,) = talk("find the text permacomputing in documents")
        self.assertEqual((r["outcome"], r["command"]), ("act", "grep -rIil -- 'permacomputing' $HOME'/Documents' || true"))
        _, (r,) = talk("find note.md")
        self.assertEqual(r["skill"], "find-file")

    def test_the_biggest_things_where_you_are_or_in_a_folder(self):
        _, (r,) = talk("what takes the most space in downloads")
        self.assertEqual((r["outcome"], r["command"]), ("act", "du -ah -d 1 $HOME'/Downloads' | sort -rh | head -n 9"))
        _, (r,) = talk("show me the biggest files here")
        self.assertEqual(r["skill"], "show-size")
        _, (r,) = talk("how big is the documents folder")
        self.assertEqual(r["skill"], "check-size")


if __name__ == "__main__":
    unittest.main()
