"""The device's readers on this machine, and the reply chosen for what they find."""
import tempfile
import unittest

from termnl import readers
from termnl.load import load_language
from termnl.server import TermNL


# what the commands of check-wifi and show-wifi (iw), check-network (ip) and check-bluetooth say on Gab's laptop;
# "0.-85 dBm" as the board's driver writes it
WIFI = ("Connected to 70:3a:cb:77:de:72 (on wlp1s0)\n\tSSID: Mesh Network\n\tfreq: 5180.0\n\tsignal: -62 dBm\n"
        "BSS 70:3a:cb:77:de:72(on wlp1s0) -- associated\n\tsignal: -50.00 dBm\n\tSSID: Mesh Network\n\t\t * SSID List\n"
        "BSS 70:3a:cb:77:de:73(on wlp1s0)\n\tsignal: -48.00 dBm\n\tSSID: Mesh Network\n"
        "BSS 11:22:33:44:55:01(on wlp1s0)\n\tsignal: -55.00 dBm\n\tSSID: Wonderland\n"
        "BSS 11:22:33:44:55:02(on wlp1s0)\n\tsignal: -58.00 dBm\n\tSSID: Wonderland\n"
        "BSS 11:22:33:44:55:03(on wlp1s0)\n\tsignal: 0.-85 dBm\n\tSSID: Caf\\xc3\\xa9\n"
        "BSS 11:22:33:44:55:04(on wlp1s0)\n\tsignal: -65.00 dBm\n\tSSID: \\x00\\x00\\x00\n")
NOT_CONNECTED = "Not connected.\n" + WIFI[WIFI.index("BSS "):].replace(" -- associated", "")
ADDRESSES = "lo               UNKNOWN        127.0.0.1/8 \nwlp1s0           UP             192.168.86.51/24 \ndocker0  DOWN  172.17.0.1/16\n"
BLUETOOTH = "Controller F8:94:C2:CE:CC:A9 (public)\n\tName: gab-Eve\n\tAlias: gab-Eve\n\tPowered: no\n"


class Readers(unittest.TestCase):
    def test_every_reader_gives_a_level_it_declares_and_its_values(self):
        args = {"folder": {"place": tempfile.gettempdir()}, "files": {"place": tempfile.gettempdir(), "type": "md,txt"},
                "has": {"place": tempfile.gettempdir(), "type": "md"}, "recent": {"place": tempfile.gettempdir()}, "size": {"place": tempfile.gettempdir()}, "wifi": {"output": WIFI}, "networks": {"output": WIFI},
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
                self.assertIn(r["say"], [l.replace("{@sys.temperature}", t).replace("{@sys.temperature.max}", "80 °C").replace("{user}", "Gab")
                                         for l in skill["when"][level]])
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
        self.assertEqual((r["level"], r["values"]["@sys.wifi"], r["values"]["@sys.wifi.signal"]), ("fine", "Mesh Network", "76%"))  # the access point in use, not the strongest
        self.assertEqual(readers.read("wifi", words=w, output=NOT_CONNECTED)["level"], "not connected")
        self.assertEqual(readers.read("wifi", words=w, output="")["level"], "off")
        r = readers.read("networks", words=w, output=WIFI)
        # one row per name, its strongest access point (the one in use: its signal now); a name with other
        # letters; a hidden network left out
        self.assertEqual([row[:2] for row in r["table"]["rows"]], [["Wonderland", "90%"], ["Mesh Network (connected)", "76%"], ["Café", "30%"]])
        self.assertEqual(r["table"]["levels"], [None, None, "weak"])
        r = readers.read("network", words=w, output=ADDRESSES)
        self.assertEqual((r["level"], r["values"]["@sys.network.address"], r["values"]["@sys.network.through"]), ("connected", "192.168.86.51", "Wi-Fi"))
        self.assertEqual(readers.read("network", words=w, output=ADDRESSES.split("\n")[0])["level"], "not connected")
        r = readers.read("bluetooth", words=w, output=BLUETOOTH)
        self.assertEqual((r["level"], r["values"]["@sys.bluetooth.name"]), ("off", "gab-Eve"))
        self.assertEqual(readers.read("bluetooth", words=w, output="No default controller available\n")["level"], "none")


if __name__ == "__main__":
    unittest.main()
