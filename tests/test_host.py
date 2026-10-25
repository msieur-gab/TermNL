"""TermNL held by a host (Symbiot's desk): the skills the host simulates, and the commands its screen does."""
import os
import tempfile
import unittest

from termnl.server import TermNL


class Quiet(TermNL):
    """nothing written to logs/: these aren't anyone's real sentences"""
    def log(self, *args, **kwargs):
        pass


def lent_scan():
    """a host's scan, as the desk's desk-wifi answers: one line of JSON"""
    f = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
    f.write("""echo '{"networks": [{"ssid": "Wonderland", "signal": -40}]}'\n""")
    f.close()
    return f.name


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


    def test_a_command_the_host_lends_replaces_the_skill_s_own(self):
        """the desk's board scans and joins only through desk-wifi (25 Oct): the networks offered come from it too"""
        app, home = self.app(commands={"show wifi": "sh " + lent_scan(), "connect wifi": "cat > $HOME/joined"})
        app.device._hearing.join()
        r = app.say("which wifi networks are around", "w1")
        self.assertEqual((r["ran"], r["table"]["rows"][0][0]), ("read", "Wonderland"))
        self.assertIn("Wonderland", [n["value"] for n in app.device.list("network")])

    def test_a_wifi_password_is_given_exactly_and_never_logged_nor_shown(self):
        """Gab's board, 25 Oct: the password lost its "!" and was written in the log in plain text"""
        lines = []
        class Kept(TermNL):
            def log(self, session, text, r, command=None):
                lines.append(repr((text, r, command)))
        home = tempfile.mkdtemp()
        app = Kept(home=home, commands={"show wifi": "sh " + lent_scan(), "connect wifi": "cat > $HOME/joined"})
        app.settings = {"admin mode": "on", "show commands": "on", "simulate": ""}
        app.device._hearing.join()
        said = [app.say(t, "w2") for t in ("connect to the wifi", "Wonderland", "s3cret pass!", "yes")]
        self.assertEqual(said[-1]["ran"], "ran")
        with open(os.path.join(home, "joined")) as f:
            self.assertEqual(f.read(), "s3cret pass!\n")
        self.assertNotIn("s3cret", repr(said) + "".join(lines))
        self.assertIn("'•••'", lines[2])

    def test_a_host_lends_replies_with_its_command(self):
        """the desk's join says what desk-wifi did: kept, not joined, is not a failure (Gab, 25 Oct: "Save, say it honestly")"""
        lent = {"command": "cat > /dev/null; echo Saved {network}.", "replies": {"done": "{output}", "approve": "Save {network}?"}}
        app, _ = self.app(commands={"show wifi": "sh " + lent_scan(), "connect wifi": lent})
        app.device._hearing.join()
        self.assertEqual(app.say("connect to Wonderland", "w3")["say"].split("?")[0][-8:], "password")
        self.assertEqual(app.say("a password", "w3")["say"], "Save Wonderland?")
        self.assertEqual(app.say("yes", "w3")["say"], "Saved Wonderland.")

if __name__ == "__main__":
    unittest.main()
