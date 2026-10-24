"""python3 -m unittest — the dialogue, against the pretend device."""
import unittest

import importlib
import os

# TERMNL_AGENT=termnl.back_agent python3 -m unittest: the same tests for the version before
Agent = importlib.import_module(os.environ.get("TERMNL_AGENT", "termnl.agent")).Agent
from termnl.load import load_language
from tests.device import device

lang = load_language("en")


def agent(settings=None):
    return Agent(**lang, settings=settings or {}, device=device, random=lambda: 0)


class Dialogue(unittest.TestCase):
    def test_skill_files_have_no_problems(self):
        self.assertEqual(lang["errors"], [])

    def test_every_weight_of_the_model_fits_in_one_byte(self):
        for k in ("action", "object"):
            m = lang["model"][k]
            self.assertGreater(m["scale"], 0)
            self.assertTrue(all(isinstance(x, int) and -127 <= x <= 127 for row in m["weights"].values() for x in row[1:]), k)

    def test_a_template_request_acts_with_values_quoted(self):
        r = agent().hear("create a file named sprout.md in the ideas folder")
        self.assertEqual(r["outcome"], "act")
        self.assertEqual(r["command"], "touch $HOME'/ideas/sprout.md'")

    def test_a_missing_name_is_asked_for_and_the_answer_completes_the_request(self):
        a = agent()
        self.assertEqual(a.hear("make a new folder")["outcome"], "ask")
        r = a.hear("bike photos")
        self.assertEqual(r["outcome"], "act")
        self.assertEqual(r["command"], "mkdir -p $HOME'/bike photos'")

    def test_a_folder_not_on_the_device_is_asked_about_with_the_real_folders_as_chips(self):
        a = agent()
        r = a.hear("create a folder called seeds in the garden folder")
        self.assertEqual(r["outcome"], "ask")
        self.assertIn("ideas", r["chips"])
        self.assertEqual(a.hear("ideas")["command"], "mkdir -p $HOME'/ideas/seeds'")

    def test_a_file_type_gives_the_extension_markdown_by_default(self):
        self.assertEqual(agent().hear("create a python file called test")["command"], "touch $HOME'/test.py'")
        self.assertEqual(agent().hear("make a new file named todo")["command"], "touch $HOME'/todo.md'")

    def test_admin_mode_off_nothing_that_needs_admin_runs(self):
        r = agent().hear("restart the pi")
        self.assertEqual(r["outcome"], "abstain")
        self.assertEqual(r["reason"], "admin mode off")

    def test_admin_mode_on_approval_every_time(self):
        a = agent({"admin mode": "on"})
        self.assertEqual(a.hear("turn off the wifi")["outcome"], "approve")
        self.assertEqual(a.hear("yes")["command"], "iw dev | grep -o 'Interface .*' | cut -d' ' -f2 | xargs -I@ ip link set @ down")
        self.assertEqual(a.hear("turn off the wifi")["outcome"], "approve")
        self.assertEqual(a.hear("no")["reason"], "declined")

    def test_other_wording_the_model_understands_and_checks_first_when_a_word_is_new(self):
        a = agent()
        r = a.hear("is there enough space for a movie")
        self.assertEqual(r["skill"], "check-storage")
        self.assertEqual(r["outcome"], "ask")
        self.assertIn("movie", r["unknown"])
        y = a.hear("yes")
        self.assertEqual((y["outcome"], y["reads"]), ("act", "storage"))
        self.assertEqual(y["teach"], {"skill": "check-storage", "text": "is there enough space for a movie"})

    def test_nothing_understood_abstain_and_the_sentence_goes_to_the_inbox(self):
        r = agent().hear("what's the weather tomorrow")
        self.assertEqual(r["outcome"], "abstain")
        self.assertEqual(r["inbox"], "what's the weather tomorrow")

    def test_a_name_cant_inject_a_command(self):
        r = agent().hear("create a folder called x'; rm -rf ~; echo '")
        self.assertEqual(r["outcome"], "act")
        self.assertTrue(r["command"].startswith("mkdir -p $HOME'/x'\\''"))

    # Gab's first request in the playground, 22 Oct, and its relatives: a name must never swallow a
    # place, and a misspelled folder is confirmed, never ignored.
    def test_add_a_new_note_inside_my_documets_the_folder_is_confirmed_then_the_name_asked(self):
        a = agent()
        r = a.hear("add a new note inside my documets")
        self.assertEqual(r["outcome"], "ask")
        self.assertIn("Documents", r["say"])
        self.assertEqual(a.hear("yes")["outcome"], "ask")
        self.assertEqual(a.hear("shopping list")["command"], "touch $HOME'/Documents/shopping list.md'")

    def test_a_misspelled_folder_can_be_refused_and_chosen_from_the_list(self):
        a = agent()
        a.hear("make a folder called seeds in documets")
        r = a.hear("no")
        self.assertEqual(r["outcome"], "ask")
        self.assertIn("ideas", r["chips"])
        self.assertEqual(a.hear("ideas")["command"], "mkdir -p $HOME'/ideas/seeds'")

    def test_a_name_never_starts_with_a_place_word(self):
        self.assertEqual(agent().hear("make a folder for my bike photos")["outcome"], "ask")
        self.assertEqual(agent().hear("create a file in documents")["outcome"], "ask")

    def test_a_place_without_a_name_the_name_is_asked_the_place_kept(self):
        a = agent()
        self.assertEqual(a.hear("create a file in documents")["outcome"], "ask")
        self.assertEqual(a.hear("draft")["command"], "touch $HOME'/Documents/draft.md'")

    def test_another_name_for_a_folder_still_finds_it(self):
        self.assertEqual(agent().hear("new folder called bikes inside docs")["command"], "mkdir -p $HOME'/Documents/bikes'")

    # Follow-ups (22 Oct, Gab's playground run): an answer to a question is an answer, unless the
    # person clearly asks for something else.
    def test_an_answer_that_is_also_a_skill_word_fills_the_question_no_loop(self):
        a = agent()
        a.hear("add a new note inside my documets")
        a.hear("Documents")
        self.assertEqual(a.hear("note")["reason"], "already exists")  # Documents already has a note.md
        b = agent()
        b.hear("add a new note inside my documets")
        b.hear("Documents")
        self.assertEqual(b.hear("memo")["command"], "touch $HOME'/Documents/memo.md'")

    def test_the_same_request_said_again_completes_the_question_with_what_it_adds(self):
        a = agent()
        a.hear("create a file in documents")
        self.assertEqual(a.hear("create a file called draft")["command"], "touch $HOME'/Documents/draft.md'")

    def test_a_clearly_different_request_replaces_the_question(self):
        a = agent()
        a.hear("create a file in documents")
        self.assertEqual(a.hear("how much space is left")["skill"], "check-storage")

    def test_the_folder_confirmed_earlier_is_kept_until_the_file_is_made(self):
        a = agent()
        a.hear("add a new note inside my documets")
        a.hear("Documents")
        self.assertEqual(a.hear("note.txt")["command"], "touch $HOME'/Documents/note.txt'")

    # Gab's run, 22 Oct 10:25: opening a file.
    def test_open_this_file_a_pointing_word_is_never_a_name_so_the_file_is_asked(self):
        r = agent().hear("open this file")
        self.assertEqual(r["outcome"], "ask")
        self.assertEqual(r["skill"], "open-file")

    def test_can_you_please_open_the_note_md_opens_it(self):
        self.assertEqual(agent().hear("can you please open the note.md")["command"], "xdg-open $HOME'/note.md'")

    def test_open_the_note_md_file_located_inside_my_documents_folder_opens_it_there(self):
        r = agent().hear("can you please open the note.md file located inside my Documents folder")
        self.assertEqual(r["command"], "xdg-open $HOME'/Documents/note.md'")

    def test_opening_an_app_still_opens_the_app(self):
        self.assertEqual(agent().hear("open the terminal")["command"], "setsid 'x-terminal-emulator'")

    # Where you are (Gab, 22 Oct 10:30: "if i say open or go to Documents folder i imagine getting
    # inside its directory"). Files are found on the device, not assumed.
    def test_opening_a_folder_goes_into_it_a_file_is_then_opened_there(self):
        a = agent()
        r = a.hear("open the documents folder")
        self.assertEqual((r["reads"], r["args"]), ("folder", {"place": "$HOME/Documents"}))
        self.assertEqual(a.here["label"], "Documents")
        self.assertEqual(a.hear("open note.md")["command"], "xdg-open $HOME'/Documents/note.md'")

    def test_go_to_ideas_then_creating_a_file_makes_it_there(self):
        a = agent()
        a.hear("go to ideas")
        self.assertEqual(a.hear("create a file called plan")["command"], "touch $HOME'/ideas/plan.md'")

    def test_showing_a_folder_lists_it_without_going_into_it(self):
        a = agent()
        a.hear("show me downloads")
        self.assertEqual(a.here["label"], "home")

    def test_a_file_not_here_but_in_one_other_folder_asked_then_opened_there(self):
        a = agent()
        r = a.hear("open report.pdf")
        self.assertEqual(r["outcome"], "ask")
        self.assertIn("Documents", r["say"])
        self.assertEqual(a.hear("yes")["command"], "xdg-open $HOME'/Documents/report.pdf'")

    def test_the_same_name_in_several_folders_which_one_with_chips(self):
        a = agent()
        a.hear("go to downloads")
        r = a.hear("open note.md")
        self.assertEqual(r["outcome"], "ask")
        self.assertEqual(sorted(r["chips"]), ["Documents", "home", "ideas"])
        self.assertEqual(a.hear("ideas")["command"], "xdg-open $HOME'/ideas/note.md'")

    def test_a_name_without_its_extension_and_a_typo_still_find_the_file(self):
        a = agent()
        a.hear("go to documents")
        self.assertEqual(a.hear("open groceries")["command"], "xdg-open $HOME'/Documents/groceries.md'")
        r = a.hear("open grocries.md")
        self.assertEqual(r["outcome"], "ask")
        self.assertIn("groceries.md", r["say"])

    def test_a_file_found_nowhere_is_said_so_and_nothing_runs(self):
        r = agent().hear("open taxes.pdf")
        self.assertIsNone(r.get("command"))
        self.assertIn("taxes.pdf", r["say"])

    def test_creating_a_file_that_already_exists_runs_nothing(self):
        r = agent().hear("create a file called seed.md in ideas")
        self.assertIsNone(r.get("command"))
        self.assertIn("already", r["say"])

    # Review of 22 Oct: approval comes last, once every value is known, and shows the command.
    def test_approval_is_never_asked_with_a_value_missing(self):
        a = agent({"admin mode": "on"})
        r = a.hear("the service is stuck, restart it")
        self.assertEqual(r["outcome"], "ask")
        self.assertNotIn("Restart ?", r["say"])
        self.assertEqual(a.hear("yes")["outcome"], "ask")  # which service?
        p = a.hear("ssh")
        self.assertEqual(p["outcome"], "approve")
        self.assertIn("ssh", p["say"])
        self.assertIsNone(p.get("command"))
        self.assertEqual(a.hear("yes")["command"], "systemctl restart 'ssh'")

    def test_not_surely_understood_with_every_value_known_one_question_the_approval(self):
        a = agent({"admin mode": "on"})
        r = a.hear("the music server is stuck, restart it")
        self.assertEqual(r["skill"], "restart-service")
        self.assertIn("Restart music server?", r["say"])
        self.assertEqual(a.hear("yes")["command"], "systemctl restart 'mpd'")

    def test_show_commands_on_the_approval_shows_the_command_it_would_run(self):
        r = agent({"admin mode": "on", "show commands": "on"}).hear("restart the pi")
        self.assertEqual(r["outcome"], "approve")
        self.assertEqual(r["show"], "systemctl reboot")
        self.assertIsNone(r.get("command"))
        self.assertIsNone(agent({"admin mode": "on"}).hear("restart the pi").get("show"))

    # Review of 22 Oct: an answer to "What should I call it?" is not always a name.
    def test_no_to_a_name_question_stops_yes_asks_again_neither_becomes_a_name(self):
        a = agent()
        a.hear("make a new folder")
        n = a.hear("no")
        self.assertIsNone(n.get("command"))
        self.assertEqual(n["outcome"], "abstain")
        self.assertIsNone(a.pending)
        b = agent()
        b.hear("make a new folder")
        y = b.hear("yes")
        self.assertEqual(y["outcome"], "ask")
        self.assertIsNone(y.get("command"))
        self.assertEqual(b.hear("bikes")["command"], "mkdir -p $HOME'/bikes'")

    def test_call_it_bikes_the_name_is_what_follows(self):
        for said, name in [("call it bikes", "bikes"), ("name it recipes", "recipes"), ("called seeds", "seeds"), ("let's call it yes", "yes")]:
            a = agent()
            a.hear("make a new folder")
            self.assertEqual(a.hear(said)["command"], "mkdir -p $HOME'/%s'" % name, said)

    # Review of 22 Oct: a place the device doesn't have is asked about, never folded into the name.
    def test_an_unknown_place_is_asked_never_swallowed_by_the_name(self):
        for said in ["make a folder called seeds in garden", "create a note called groceries in garden"]:
            a = agent()
            r = a.hear(said)
            self.assertEqual(r["outcome"], "ask", said)
            self.assertIn("garden", r["say"])
            self.assertIn("ideas", r["chips"])
        a = agent()
        a.hear("make a folder called seeds in garden")
        self.assertEqual(a.hear("ideas")["command"], "mkdir -p $HOME'/ideas/seeds'")

    def test_a_known_place_after_the_name_still_works(self):
        self.assertEqual(agent().hear("make a folder called seeds in ideas")["command"], "mkdir -p $HOME'/ideas/seeds'")
        self.assertEqual(agent().hear("create a note called photos of paris")["command"], "touch $HOME'/photos of paris.md'")

    # Review of 22 Oct: a request with "not", "don't"… is never acted on as if it were positive.
    def test_a_negated_request_is_never_acted_on(self):
        for said in ["do not reboot the pi", "don't turn off the wifi", "don't create a folder called bikes", "never restart ssh"]:
            a = agent({"admin mode": "on"})
            r = a.hear(said)
            self.assertEqual(r["outcome"], "ask", said)
            self.assertIsNone(r.get("command"), said)
            self.assertEqual(r["chips"], ["yes", "no"])
        a = agent({"admin mode": "on"})
        a.hear("do not reboot the pi")
        self.assertEqual(a.hear("no")["outcome"], "abstain")

    def test_a_negated_request_still_needs_its_approval_after_a_yes(self):
        a = agent({"admin mode": "on"})
        a.hear("I don't need wifi right now, switch it off")
        self.assertEqual(a.hear("yes")["outcome"], "approve")
        self.assertEqual(a.hear("yes")["command"], "iw dev | grep -o 'Interface .*' | cut -d' ' -f2 | xargs -I@ ip link set @ down")

    def test_reading_is_not_held_back_by_a_negation(self):
        for said in ["is the board not overheating", "is my memory not full"]:
            self.assertEqual(agent().hear(said)["outcome"], "act", said)


    # Gab's first test on Eve, 22 Oct: seven "yes" in a row after his question was lost.
    def test_a_lone_yes_or_no_with_nothing_waiting_says_so(self):
        for said in ["yes", "no"]:
            r = agent().hear(said)
            self.assertEqual(r["reason"], "nothing waiting")
            self.assertIsNone(r.get("skill"))

    # A skill that only reads names its reader: no command, the reply comes from what the device says.
    def test_a_reading_skill_reads_instead_of_running_a_command(self):
        r = agent().hear("how hot is the board")
        self.assertEqual((r["outcome"], r["reads"]), ("act", "temperature"))
        self.assertIsNone(r.get("command"))

    def test_gabs_new_sentences_reach_the_new_skills(self):
        self.assertEqual(agent().hear("what is this device configuration")["skill"], "show-system")
        for said in ["what is taking my memory", "what is consuming my ram"]:
            self.assertEqual(agent().hear(said)["skill"], "show-process", said)


    # Wi-Fi, the network and Bluetooth: the skill's command runs and is shown, and a reader turns its output into words.
    def test_a_reader_of_a_commands_output_runs_the_skills_command_and_shows_it(self):
        r = agent({"show commands": "on"}).hear("what is my IP address")
        self.assertEqual((r["outcome"], r["reads"], r["command"], r["show"]), ("act", "network", "ip -4 -brief addr", "ip -4 -brief addr"))

    # Gab, 22 Oct: "is bluetooth on" is the board's own Bluetooth, though a service has the same name
    def test_an_object_word_is_the_object_not_a_service_of_the_same_name(self):
        for said in ["is bluetooth on", "is the bluetooth working"]:
            r = agent().hear(said)
            self.assertEqual((r["outcome"], r.get("skill")), ("act", "check-bluetooth"), said)
        self.assertEqual(agent().hear("is ssh running")["skill"], "check-service")

    # Gab asked the time five times on 22 Oct; it was out of scope by oversight.
    def test_the_time_and_the_date_are_read_and_an_alarm_is_still_out_of_scope(self):
        for said in ["what time is it?", "what is the date today", "what day is it"]:
            r = agent().hear(said)
            self.assertEqual((r["outcome"], r.get("skill"), r.get("reads")), ("act", "check-time", "clock"), said)
        self.assertEqual(agent().hear("set an alarm for seven")["outcome"], "abstain")

    # Gab's second run, 22 Oct: "list the files inside my home", "cd ..".
    def test_listing_a_folders_files(self):
        for said, place in [("list the files inside my home", "$HOME"), ("what do I have in downloads", "$HOME/Downloads"),
                            ("show me the files in documents", "$HOME/Documents"), ("list my files", "$HOME")]:
            r = agent().hear(said)
            self.assertEqual((r["outcome"], r.get("skill"), r.get("reads")), ("act", "show-folder", "folder"), said)
            self.assertEqual(r["args"]["place"], place, said)
        a = agent()
        a.hear("go to ideas")
        self.assertEqual(a.hear("what's in here")["args"]["place"], "$HOME/ideas")

    def test_the_same_request_without_the_unknown_place_uses_where_you_are(self):
        a = agent()
        self.assertEqual(a.hear("what do I have in the garden")["outcome"], "ask")
        r = a.hear("list my files")
        self.assertEqual((r["outcome"], r["args"]["place"]), ("act", "$HOME"))

    def test_going_up_a_folder(self):
        for said in ["cd ..", "go back", "go up a folder", "leave this folder"]:
            a = agent()
            a.hear("go to documents")
            r = a.hear(said)
            self.assertEqual((r["outcome"], r.get("skill")), ("act", "leave-folder"), said)
            self.assertEqual(a.here["label"], "home", said)

    def test_going_up_from_home_says_so(self):
        r = agent().hear("cd ..")
        self.assertEqual(r["outcome"], "abstain")
        self.assertIn("home", r["say"])
        self.assertEqual(agent().here["label"], "home")


    # Typos, 22 Oct: about one request in six in Gab's log. A word one letter away from a word TermNL
    # knows is read as that word, and said so; names are never corrected; a change still asks.
    def test_a_typo_in_a_reading_request_is_read_and_said(self):
        r = agent().hear("chek the memory")
        self.assertEqual((r["outcome"], r["skill"]), ("act", "check-memory"))
        self.assertEqual(r["corrections"], [["chek", "check"]])
        self.assertIn("chek", r["note"])

    def test_a_typo_in_a_change_asks_first_and_the_name_stays_as_typed(self):
        a = agent()
        r = a.hear("creat a folder called bikse")
        self.assertEqual(r["outcome"], "ask")
        self.assertIn("creat", r["say"])
        self.assertEqual(a.hear("yes")["command"], "mkdir -p $HOME'/bikse'")

    def test_a_typo_in_a_name_or_a_short_word_is_left_alone(self):
        r = agent().hear("create a folder called recipies")
        self.assertEqual(r["command"], "mkdir -p $HOME'/recipies'")
        self.assertNotIn("corrections", r)

    # Rename (Gab, 22 Oct: "perhaps we will need a rename file/folder skill"): never overwrites.
    def test_renaming_a_file(self):
        self.assertEqual(agent().hear("rename note.md to memo.md")["command"], "mv -nT $HOME'/note.md' $HOME'/memo.md'")
        self.assertEqual(agent().hear("rename note.md to memo")["command"], "mv -nT $HOME'/note.md' $HOME'/memo.md'")
        r = agent().hear("rename note.md to todo.txt")
        self.assertEqual(r["reason"], "already exists")
        self.assertIsNone(r.get("command"))

    def test_renaming_a_folder(self):
        self.assertEqual(agent().hear("rename the ideas folder to thoughts")["command"], "mv -nT $HOME'/ideas' $HOME'/thoughts'")
        self.assertEqual(agent().hear("rename ideas to projects")["reason"], "already exists")
        self.assertEqual(agent().hear("rename ideas to Documents")["reason"], "already exists")  # a name can be a word like "documents"

    def test_a_new_folder_never_replaces_one(self):
        self.assertEqual(agent().hear("create a folder called projects")["reason"], "already exists")

    # Closing an app (Gab's log, 22 Oct: "close expressvpn"): approved first, unsaved work may be lost.
    def test_closing_a_running_app_is_approved_first(self):
        a = agent()
        r = a.hear("close firefox")
        self.assertEqual((r["outcome"], r["skill"]), ("approve", "close-app"))
        self.assertEqual(a.hear("yes")["command"], "pkill -x 'firefox'")
        self.assertEqual(agent().hear("quit the terminal")["skill"], "close-app")

    def test_closing_an_app_that_isnt_running_asks_which(self):
        a = agent()
        self.assertEqual(a.hear("close chrome")["skill"], "close-app")  # "I don't know “chrome” yet…"
        r = a.hear("yes")
        self.assertEqual(r["outcome"], "ask")
        self.assertEqual(sorted(r["chips"]), ["Firefox", "Terminal"])


    # Gab's run, 22 Oct 13:50–13:54: two folders made with the wrong name, and two requests missed.
    def test_a_request_said_again_with_a_typo_while_a_name_is_asked(self):
        a = agent()
        a.hear("make a new folder")
        r = a.hear("crate a folder named Pictures")
        self.assertEqual(r.get("command"), "mkdir -p $HOME'/Pictures'")

    def test_call_and_name_before_a_name(self):
        self.assertEqual(agent().hear("create a folder call Pictures")["command"], "mkdir -p $HOME'/Pictures'")
        self.assertEqual(agent().hear("make a file name groceries")["command"], "touch $HOME'/groceries.md'")

    def test_the_name_before_the_word_folder(self):
        for said in ["create a Pictures folder", "add a Videos folder", "make a new Pictures folder in documents"]:
            r = agent().hear(said)
            self.assertEqual(r["outcome"], "act", said)
            self.assertIn("Pictures" if "Pictures" in said else "Videos", r["command"])
        self.assertEqual(agent().hear("create a new folder")["outcome"], "ask")  # "new" is not a name

    def test_ls_lists_where_you_are(self):
        a = agent()
        a.hear("go to documents")
        r = a.hear("ls")
        self.assertEqual((r["skill"], r["args"]["place"]), ("show-folder", "$HOME/Documents"))

    # Two wrong actions in Gab's first evening with TermNL in the desk (23 Oct)
    def test_a_typo_never_hides_a_place_inside_a_name(self):
        a = agent()
        r = a.hear("add a new file call gab.md insde Documents")  # made "gab.md insde Documents.md" in home
        self.assertEqual(r["outcome"], "ask")  # a typo read is said, and asked
        self.assertEqual(r["corrections"], [["insde", "inside"]])
        self.assertEqual(a.hear("yes")["command"], "touch $HOME'/Documents/gab.md'")

    def test_names_are_still_never_corrected(self):
        self.assertEqual(agent().hear("create a file called chek list")["command"], "touch $HOME'/chek list.md'")
        self.assertEqual(agent().hear("create a folder called holiday photos")["command"], "mkdir -p $HOME'/holiday photos'")

    def test_a_name_ending_in_a_file_type_is_a_file_never_a_folder(self):
        r = agent().hear("create a note.md in the Documents folder")  # was a folder called note.md
        self.assertEqual(r["skill"], "create-file")
        self.assertNotIn("mkdir", r.get("command", ""))

    # Music (Gab, 23 Oct): "play daft punk or play a thousand leaves", "play music start a random playlist",
    # then stop, pause, mute, next and previous. Ordinary commands; the desk's player does them.
    def test_music_is_played_by_name_or_at_random(self):
        for said in ["play some music", "could you play some music?", "play music"]:
            self.assertEqual(agent().hear(said)["command"], "mpc play", said)
        self.assertEqual(agent().hear("play wax tailor")["command"], "mpc searchplay any 'Wax Tailor'")
        self.assertEqual(agent().hear("play hope and sorrow")["command"], "mpc searchplay any 'Hope & Sorrow'")
        self.assertEqual(agent().hear("play something by wax tailor")["command"], "mpc searchplay any 'Wax Tailor'")

    def test_the_player_is_steered_in_plain_words(self):
        for said, command in [("pause", "mpc pause"), ("pause the music", "mpc pause"), ("stop the music", "mpc stop"),
                              ("next", "mpc next"), ("next song", "mpc next"), ("skip", "mpc next"), ("previous song", "mpc prev"),
                              ("mute", "pactl set-sink-mute @DEFAULT_SINK@ 1"), ("unmute the sound", "pactl set-sink-mute @DEFAULT_SINK@ 0")]:
            self.assertEqual(agent().hear(said).get("command"), command, said)

    def test_stop_alone_is_still_a_no(self):
        self.assertNotEqual(agent().hear("stop").get("skill"), "stop-music")

    # ---- 24 Oct 2026, feat/improvements: act with confidence, ask to tell apart, or abstain

    def test_turn_on_is_told_apart_by_its_object(self):
        """Gab, 24 Oct: "turn on the wifi, turn on the music, turn on bluetooth should be clearly
        disambiguated. TermNL should be able to act with confidence or ask for disambiguation or abstain." """
        a = {"admin mode": "on"}
        for said, skill, outcome in [("turn on the wifi", "turn-on-wifi", "approve"), ("turn on the music", "play-music", "act"),
                                     ("turn on bluetooth", "turn-on-bluetooth", "approve"), ("turn the music on", "play-music", "act"),
                                     ("turn the music off", "stop-music", "act"), ("turn off the sound", "mute-sound", "act"),
                                     ("start bluetooth", "turn-on-bluetooth", "approve"), ("stop the wifi", "turn-off-wifi", "approve"),
                                     ("stop bluetooth", "turn-off-bluetooth", "approve")]:
            r = agent(a).hear(said)
            self.assertEqual((r.get("skill"), r["outcome"]), (skill, outcome), said)

    def test_an_action_without_its_object_asks_which_one(self):
        for said in ("turn on", "turn it on", "turn off", "switch it off"):
            r = agent().hear(said)
            self.assertEqual(r["outcome"], "ask", said)
            self.assertIsNone(r.get("skill"), said)
            self.assertGreaterEqual(len(r["chips"]), 2, said)
        a = agent({"admin mode": "on"})
        self.assertIn("turn Wi-Fi on", a.hear("turn on")["chips"])
        self.assertEqual(a.hear("turn Wi-Fi on")["skill"], "turn-on-wifi")

    def test_a_template_the_model_doubts_asks_which_of_two(self):
        """24 Oct: both silent wrong actions found by the probes came from templates, never from the model."""
        for said, labels in [("rename the folder photos to pictures", {"rename a file", "rename a folder"}),
                             ("is bluetooth running", {"check a service", "check Bluetooth"})]:
            r = agent().hear(said)
            self.assertEqual(r["outcome"], "ask", said)
            self.assertEqual(set(r["chips"]), labels, said)
        a = agent()
        a.hear("is bluetooth running")
        self.assertEqual(a.hear("check Bluetooth")["skill"], "check-bluetooth")


    def test_the_board_is_never_offered_the_opposite_of_what_was_said(self):
        """Gab, 24 Oct, for the scale test: "reboot, turn off the board, restart the board"."""
        a = {"admin mode": "on"}
        for said, skill in [("reboot", "restart-system"), ("restart the board", "restart-system"),
                            ("turn off the board", "shut-down-system"), ("turn the pi off", "shut-down-system")]:
            r = agent(a).hear(said)
            self.assertEqual((r.get("skill"), r["outcome"]), (skill, "approve"), said)
        for said in ("turn the board on", "turn on the pi"):
            r = agent(a).hear(said)
            self.assertEqual((r["outcome"], r.get("skill")), ("abstain", None), said)
        self.assertIn("shut the board down", agent(a).hear("turn off")["chips"])


    def test_the_person_sets_their_name_and_their_agency_in_words(self):
        """Gab, 24 Oct: "a specific command to edit their settings or preferences (admin mode, adding their
        name, etc)"; "The TermNL chat system was imagined to be personal, so saying Hey Gab, no problems your
        CPU is at 58 degrees"."""
        settings = {"admin mode": "off", "show commands": "off"}
        a = agent(settings)
        r = a.hear("call me Gab")
        self.assertEqual((r["outcome"], r["changes"]), ("act", {"name": "Gab"}))
        self.assertEqual(a.hear("show me the commands")["changes"], {"show commands": "on"})
        self.assertEqual(a.hear("hide the commands")["changes"], {"show commands": "off"})
        self.assertEqual(settings, {"admin mode": "off", "show commands": "off", "name": "Gab"})

    def test_admin_mode_is_never_changed_by_a_sentence_only_in_the_settings_panel(self):
        """Gab, 24 Oct: "turn on or off admin mode should be kept out of the text skills perhaps as a safety
        measure. but the setting skill should open a small panel with some toggles" """
        settings = {"admin mode": "off"}
        for said in ("turn on admin mode", "enable admin mode", "i want admin rights", "turn on sudo"):
            r = agent(settings).hear(said)
            self.assertNotIn("changes", r, said)
            self.assertNotEqual(r["outcome"], "approve", said)
        self.assertEqual(settings, {"admin mode": "off"})
        r = agent().hear("open my settings")
        self.assertEqual((r["outcome"], r["opens"]), ("act", "settings"))
        from termnl.skills import load
        from termnl.load import language_dir, read
        import os
        d = language_dir("en")
        files = {k: read(os.path.join(d, "words", k + ".md")) for k in ("actions", "objects", "filetypes", "conversation", "samples", "readings", "values")}
        bad = "---\ndoes: turn on admin\nlabel: sneaky\nchanges: admin mode to on\n---\n\n## People say\n\n- please turn on admin\n\n## Replies\n\n- done: Done.\n"
        self.assertTrue(any("settings panel" in e for e in load(files, {"sneaky": bad})["errors"]))

    def test_help_says_what_termnl_can_do_by_topic(self):
        """Gab, 24 Oct: "there is no help skill, one that list what TermNL could do for users" """
        for said in ("help", "what can you do", "what can i ask you"):
            r = agent().hear(said)
            self.assertEqual((r["outcome"], r.get("skill")), ("act", "show-help"), said)
        rows = dict(agent().hear("help")["table"]["rows"])
        self.assertIn("create a folder", rows["Files and folders"])
        self.assertIn("turn Wi-Fi on", rows["Network"])
        listed = ", ".join(rows.values())
        for s in lang["skills"]:
            if s["id"] != "show-help":
                self.assertIn(s["label"], listed, s["id"])

    def test_a_reply_says_the_name_only_when_there_is_one(self):
        from termnl.text import pick
        lines = ["Hey {user}, all good."]
        self.assertEqual(pick(lines + ["All good."], lambda: 0, ""), "All good.")
        self.assertEqual(pick(lines + ["All good."], lambda: 0, "Gab"), "Hey {user}, all good.")
        self.assertEqual(Agent(**lang, settings={"name": "Gab"}, device=device, random=lambda: 0.99).hear("what can you do")["say"][:7], "Hi Gab,")
        self.assertNotIn("{user}", agent().hear("what can you do")["say"])


if __name__ == "__main__":
    unittest.main()
