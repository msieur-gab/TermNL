"""python3 -m unittest — the dialogue, against the pretend device."""
import unittest

from termnl.agent import Agent
from termnl.load import load_language
from tests.device import device

lang = load_language("en")


def agent(settings=None):
    return Agent(**lang, settings=settings or {}, device=device, random=lambda: 0)


class Dialogue(unittest.TestCase):
    def test_skill_files_have_no_problems(self):
        self.assertEqual(lang["errors"], [])

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
        self.assertEqual(a.hear("yes")["command"], "nmcli radio wifi off")
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
        self.assertEqual(a.hear("yes")["command"], "nmcli radio wifi off")

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


if __name__ == "__main__":
    unittest.main()
