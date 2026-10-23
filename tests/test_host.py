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


if __name__ == "__main__":
    unittest.main()
