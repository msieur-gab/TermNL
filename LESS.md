# Less — the `research/less` branch

25 October 2026, from `feat/frames`. Gab: "let us start to test the substraction on a new branch, aiming for
less is more and testing the outcome. And then we will evaluate."

The method: every rule of the agent got an off switch, then each was turned off alone and measured on the six
test sets (665 sentences) and the 126 unit tests. A rule that saves nothing goes. The switches were scaffolding
and are gone; they stay in git's history (02d3582) to redo the audit.

## In short

- **One rule was dead weight, and is removed:** "a name ending in a file type is a file" (`as_file`). With it
  off, not one answer and not one test changed: other rules now do its job. All 665 answers are identical
  without it.
- **One rule costs more than it saves:** "a typo in a change asks first". Off, 15 more requests are handled,
  all by the right skill, none wrongly. But it is a caution rule: Gab's call, below.
- **Every other rule earns its place.** Each saves sentences, prevents a wrong action, or prevents a wrong
  value a test remembers.
- **The test sets can't see values.** They judge the skill only. Five rules show 0 sentences moved, yet their
  unit tests show what they prevent: a folder called "for my bike photos", a file called "gab.md insde
  Documents.md". Only the unit tests judge values today.

## The audit

Each rule off alone. Sentences: requests handled, compared with all rules on (383 handled, 2 wrong actions).

| Rule | What it does | Off: sentences | Off: wrong actions | Off: tests failing | Verdict |
|---|---|---|---|---|---|
| a name ending in a file type is a file (`as_file`) | "create a note.md in Documents" is a file | 0 | 0 | 0 | **removed** |
| a typo in a change asks first | "remvoe note.md" asks before acting | **+15** | 0 | 2 | **Gab's call** |
| meaning with an object | "turn on the music" plays | −9 | 0 | 2 | keep |
| typos read as known words | "chek the memory" | −6 | 0 | 3 | keep |
| object words are never the end of a name | "the ideas folder" is a folder | −4 | **+1** | 1 | keep |
| split verbs joined | "turn the music off" | −2 | 0 | 5 | keep |
| an object word is the object, not a device name | "is bluetooth on": the board's, not a service | −2 | 0 | 1 | keep |
| a template the model doubts asks which | "rename the folder photos…" | 0 | **+1** | 0 | keep |
| opposites | "turn the board on" never offers shut down | 0 (1 out of scope) | 0 | 1 | keep |
| an action said alone asks which | "turn off" alone | 0 | 0 | 2 | keep |
| a name stops before a place | "seeds in garden" | +1 | 0 | 2 | keep: values |
| a name never starts with a place word | not a folder "for my bike photos" | 0 | 0 | 1 | keep: values |
| a typo never hides a place in a name | not "gab.md insde Documents.md" (Gab, 23 Oct) | 0 | 0 | 1 | keep: values |
| said again without the value, its default | no loop on "Which one?" | 0 | 0 | 1 | keep |
| an unknown name is the missing device value | "kill pipewire": "isn't an app I can stop" | 0 | 0 | 1 | keep, a nicety |

## The typo rule, for Gab

When a word in a request that changes something was read as a typo of a known word, TermNL asks "Do you want
me to…?" before anything, and says how it read the typo. Off, it says the typo the same way but acts at once,
or asks its approval at once for a skill that always does. The 15 sentences it holds back, all read right:

    activate the bluetoth · switch off bluetoth · blutooth on · go up one levle · lauch the terminal ·
    pasue the song · update all the sofware · remvoe note.md please · please instal gimp for me ·
    compres my Downloads folder please · enough of The Tune, turn the music off · restrat it ·
    unpick backup.tar.gz · turn the sound dawn · get seed.md form laptop

For delete, install, update and restart, the approval still comes: the rule only adds a second question
before it. For the others (open, pause, unpack, compress, get) it is the only question. Removing it is one
line. The risk it guards against, a typo read as the wrong word in a change, never happened in the 665
sentences; "unpick" read as "unpack" is the closest.

## What the audit says

The agent's rules are not dead weight: they are the price of reading single words with a small model. Less
code will not come from cutting rules, but from what made them necessary: values the measure can't see, and
verbs whose meaning hangs on their object (VERB-WITH-OBJECT.md: the model can't take that over cheaply).

Two small things the audit points at:
- **A test set for values.** The six sets check the skill; a set that checks the values ("the folder is
  called bikes, in Documents") would let value rules be weighed like the others.
- **Narrowing "object words never end a name"** to file and folder words: today "which notes mention wifi"
  can't read "wifi" as what to look for (find-text). Measured: −4 sentences and one wrong action if removed
  whole, so narrowing, not removing.

Unit tests: 126, the same three failing as on `feat/frames`.
