"""TermNL held by a host (Symbiot's desk): the skills the host simulates, and the commands its screen does."""
import os
import tempfile
import unittest

from termnl.server import TermNL


class Quiet(TermNL):
    """nothing written to logs/: these aren't anyone's real sentences"""
    def log(self, *args, **kwargs):
        pass


class Host(unittest.TestCase):
    def app(self, **host):
        home = tempfile.mkdtemp()
        app = Quiet(home=home, **host)
        app.settings = {"admin mode": "on", "show commands": "on", "simulate": "restart system"}
        return app, home

    def test_a_skill_the_host_simulates_does_not_run(self):
        app, home = self.app(simulate={"create folder"})
        r = app.say("make a folder called bikes", "s1")
        self.assertEqual(r["ran"], "simulated")
        self.assertFalse(os.path.exists(os.path.join(home, "bikes")))

    def test_the_host_simulates_more_never_less(self):
        app, _ = self.app(simulate=set())
        app.say("restart the system", "s2")
        self.assertEqual(app.say("yes", "s2")["ran"], "simulated")  # settings.md's own line still holds

    def test_a_command_the_host_screen_does_comes_back_instead_of_running(self):
        app, home = self.app(screen=lambda command: command.startswith("xdg-open "))
        open(os.path.join(home, "notes.md"), "w").close()
        r = app.say("open notes.md", "s3")
        self.assertEqual(r["ran"], "screen")
        self.assertTrue(r["screen"].startswith("xdg-open ") and "notes.md" in r["screen"])
        r = app.say("make a folder called bikes", "s3")  # any other command still runs here
        self.assertEqual(r["ran"], "ran")
        self.assertTrue(os.path.isdir(os.path.join(home, "bikes")))

    def notes(self, best):
        asked = []
        def doc(question):
            asked.append(question)
            return {"best": best, "results": [{"title": "Permacomputing", "path": "Articles/permacomputing.md", "kind": "article", "score": best, "passage": "…"}]}
        app, _ = self.app(doc=doc)
        return app, asked

    def test_the_documents_answer_what_termnl_does_not_understand_or_only_guesses(self):
        app, _ = self.notes(0.5)
        for said in ["how does AI impact democracy?", "what is permacomputing?"]:  # no skill; a guess with an unknown word
            r = app.say(said, said)
            self.assertEqual((r["outcome"], r["skill"]), ("act", "@doc"), said)
            self.assertEqual(r["documents"][0]["path"], "Articles/permacomputing.md")
            self.assertEqual(app.say("yes", said)["outcome"], "abstain")  # the guess's question went with it

    def test_a_command_never_goes_to_the_documents(self):
        app, asked = self.notes(0.9)
        self.assertEqual(app.say("make a folder called bikes", "c")["ran"], "ran")
        self.assertEqual(app.say("how hot is the board", "c")["skill"], "check-temperature")
        self.assertEqual(asked, [])

    def test_the_documents_stay_quiet_when_they_do_not_really_match(self):
        app, asked = self.notes(0.42)  # over the floor for what TermNL doesn't understand, under it for a guess
        self.assertEqual(app.say("what is permacomputing?", "q")["outcome"], "ask")
        self.assertEqual(app.say("how does AI impact democracy?", "r")["skill"], "@doc")
        app, _ = self.notes(0.3)
        self.assertEqual(app.say("how does AI impact democracy?", "s")["outcome"], "abstain")


if __name__ == "__main__":
    unittest.main()
