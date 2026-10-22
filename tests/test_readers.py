"""The device's readers on this machine, and the reply chosen for what they find."""
import tempfile
import unittest

from termnl import readers
from termnl.load import load_language
from termnl.server import TermNL


# what the commands of check-wifi and show-wifi (nmcli), check-network (ip) and check-bluetooth say on Gab's laptop
WIFI = " :Garden Network:100\n*:Garden Network:76\n :Wonderland:90\n :Wonderland:85\n :Caf\\:e:30\n ::70\n"
ADDRESSES = "lo               UNKNOWN        127.0.0.1/8 \nwlp1s0           UP             192.168.1.51/24 \ndocker0  DOWN  172.17.0.1/16\n"
BLUETOOTH = "Controller 02:00:5e:10:00:aa (public)\n\tName: my-laptop\n\tAlias: my-laptop\n\tPowered: no\n"


class Readers(unittest.TestCase):
    def test_every_reader_gives_a_level_it_declares_and_its_values(self):
        args = {"folder": {"place": tempfile.gettempdir()}, "wifi": {"output": WIFI}, "networks": {"output": WIFI},
                "network": {"output": ADDRESSES}, "bluetooth": {"output": BLUETOOTH}}
        for name, (_, levels, names) in readers.READERS.items():
            r = readers.read(name, words=load_language("en")["lists"]["readings"], **args.get(name, {}))
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
                readers.READERS["temperature"] = (lambda w, level=level, t=t: {"level": level, "values": {"": t, "max": "80 °C"}}, *real[1:])
                r = {"skill": "check-temperature", "reads": "temperature"}

                class A:
                    reply = staticmethod(lambda k, v=None: k)
                app.read(A, r)
                self.assertIn(t, r["say"])
                self.assertIn(r["say"], [l.replace("{@sys.temperature}", t).replace("{@sys.temperature.max}", "80 °C") for l in skill["when"][level]])
        finally:
            readers.READERS["temperature"] = real

    def test_the_clock_is_trusted_only_when_synchronised_and_after_termnl_was_made(self):
        words = load_language("en")["lists"]["readings"]
        real, now = readers._synchronised, readers.datetime
        try:
            readers._synchronised = lambda: False
            self.assertEqual(readers.read("clock", words=words)["level"], "unsure")
            readers._synchronised = lambda: None  # can't tell: the clock is taken as it is
            self.assertEqual(readers.read("clock", words=words)["level"], "fine")

            class Then(now.datetime):
                @classmethod
                def now(cls):
                    return cls(1970, 1, 1, 0, 3)
            readers.datetime = type("D", (), {"datetime": Then})
            r = readers.read("clock", words=words)
            self.assertEqual((r["level"], r["values"]["@sys.clock.date"], r["values"]["@sys.clock.day"]), ("wrong", "1 January 1970", "Thursday"))
        finally:
            readers._synchronised, readers.datetime = real, now

    def test_wifi_network_and_bluetooth_are_read_from_their_commands_output(self):
        w = load_language("en")["lists"]["readings"]
        r = readers.read("wifi", words=w, output=WIFI)
        self.assertEqual((r["level"], r["values"]["@sys.wifi"], r["values"]["@sys.wifi.signal"]), ("fine", "Garden Network", "76%"))  # the access point in use, not the strongest
        self.assertEqual(readers.read("wifi", words=w, output=WIFI.replace("*", " "))["level"], "not connected")
        self.assertEqual(readers.read("wifi", words=w, output="")["level"], "off")
        r = readers.read("networks", words=w, output=WIFI)
        # one row per name, its strongest access point; a ":" in a name; a hidden network left out
        self.assertEqual([row[:2] for row in r["table"]["rows"]], [["Wonderland", "90%"], ["Garden Network (connected)", "76%"], ["Caf:e", "30%"]])
        self.assertEqual(r["table"]["levels"], [None, None, "weak"])
        r = readers.read("network", words=w, output=ADDRESSES)
        self.assertEqual((r["level"], r["values"]["@sys.network.address"], r["values"]["@sys.network.through"]), ("connected", "192.168.1.51", "Wi-Fi"))
        self.assertEqual(readers.read("network", words=w, output=ADDRESSES.split("\n")[0])["level"], "not connected")
        r = readers.read("bluetooth", words=w, output=BLUETOOTH)
        self.assertEqual((r["level"], r["values"]["@sys.bluetooth.name"]), ("off", "my-laptop"))
        self.assertEqual(readers.read("bluetooth", words=w, output="No default controller available\n")["level"], "none")


if __name__ == "__main__":
    unittest.main()
