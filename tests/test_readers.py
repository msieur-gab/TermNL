"""The device's readers on this machine, and the reply chosen for what they find."""
import tempfile
import unittest

from termnl import readers
from termnl.load import load_language
from termnl.server import TermNL


class Readers(unittest.TestCase):
    def test_every_reader_gives_a_level_it_declares_and_its_values(self):
        args = {"folder": {"place": tempfile.gettempdir()}}
        for name, (_, levels, names) in readers.READERS.items():
            r = readers.read(name, **args.get(name, {}))
            self.assertIn(r["level"], levels, name)
            for n in names:
                self.assertIn(readers.placeholder(name, n), r["values"], name)

    def test_the_reply_is_the_one_written_for_the_level(self):
        app = TermNL.__new__(TermNL)
        app.lang, app.settings = load_language("en"), {"name": "Gab"}
        skill = next(s for s in app.lang["skills"] if s["id"] == "check-temperature")
        real = readers.READERS["temperature"]
        try:
            for level, t in (("fine", "45 °C"), ("hot", "84 °C")):
                readers.READERS["temperature"] = (lambda level=level, t=t: {"level": level, "values": {"": t, "max": "80 °C"}}, *real[1:])
                r = {"skill": "check-temperature", "reads": "temperature"}

                class A:
                    reply = staticmethod(lambda k, v=None: k)
                app.read(A, r)
                self.assertIn(t, r["say"])
                self.assertIn(r["say"], [l.replace("{@sys.temperature}", t).replace("{@sys.temperature.max}", "80 °C") for l in skill["when"][level]])
        finally:
            readers.READERS["temperature"] = real


if __name__ == "__main__":
    unittest.main()
