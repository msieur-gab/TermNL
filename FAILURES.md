# What fails, sentence by sentence

Branch `feat/frame-self-training`, 26 Oct 2026. The 665 test sentences of `tests/*.md`, each heard by a fresh
agent (scoring of `tests/measure.py`). feat/frames with numpy fails on the same sentences but 4.

- **3 wrong actions**: something ran that wasn't asked.
- **29 wrong skills offered**: a wrong skill asked about ("Do you want me to…?") or offered among choices. Nothing ran; you say no.
- **29 not understood**: "I can't do that yet."
- **15 out-of-scope sentences asked about** instead of refused. Harmless, listed at the end.

40 of the 63 skills tested miss at least one sentence. The worst: previous-track 4/7, rename-folder 4/6,
get-file 4/6, show-system 5/7, install-app 5/7, check-storage 14/19.

## 1. Wrong actions (3)

| Sentence | Wanted | Did | Harm |
|---|---|---|---|
| which wifi network is this | check-wifi (the network I'm on) | show-wifi (the networks around) | none, read only |
| I want to look at report.pdf | open-file | find-file (where report.pdf is) | none, read only |
| download and unzip example.com/pack.zip | out of scope (two actions) | download-file | did half: downloaded, didn't unzip |

## 2. Wrong skills offered (29), by cause

**"Show me…", "is there any…" read as listing files of a kind (7).** check-type, show-type and show-folder
pull in sentences that start like a listing.

| Sentence | Wanted | Offered |
|---|---|---|
| show me the file called notes.md | open-file | show a folder / list files of a kind |
| show me the specs | show-system | show a folder / list files of a kind |
| show me what's inside the downloads folder | show-folder | list files of a kind / show a folder (right one among two) |
| show me everything in ideas | show-folder | show-type, "Which one?" with file kinds |
| is there any acitve threads | show-process | check-type, file kinds |
| are there any updates? if so install them all | update-system | check-type, file kinds |
| is there enough space for a movie | check-storage | check-type |

**Words it doesn't know steer it to a neighbour (9).** It says which words it doesn't know, then guesses.

| Sentence | Wanted | Offered | Unknown words |
|---|---|---|---|
| is my sd card almost full | check-storage | check-usb | almost, full |
| what's eating my disk | check-storage | show-process | disk |
| why is everything so slow, is it the ram | check-memory | check-system | why, slow, ram |
| everything feels slow, is the memory full or what | check-memory | show-process | feels, full; "slow" read as "show" |
| which model am i runing on | show-system | check-learning | runing |
| turn on bluetooth, I want to connect my speaker | turn-on-bluetooth | unmute-sound | bluetooth, connect |
| fetch photos.tar.gz from studio pi | get-file | download-file | studio, pi |
| copy movie.mkv over to the studio pi | send-file | copy-file, asks which folder | |
| reed todo.txt | read-file | move-file | reed |

**A sibling skill (8).** The right family, the wrong member.

| Sentence | Wanted | Offered |
|---|---|---|
| can I get the browser | open-app | close-app |
| my music won't stop, make it stop | stop-music | stop-process |
| something has hung, can you force quit firefox | stop-process | stop-music |
| can you squash ideas into one zip file so I can send it? | compress-folder | compress-file |
| rename the folder photos to pictures | rename-folder | rename-file (then can't find it) |
| copy report.pdf from my laptop onto the board | get-file | copy-file |
| is bluetooth running | check-bluetooth | check a service / check Bluetooth (right one among two) |
| hey could you turn it off and back on again for me | restart-system | six "turn off" skills to choose from |

**"Get rid of", "start" read as file actions (3).**

| Sentence | Wanted | Offered |
|---|---|---|
| can you get rid of the wifi for a while, I want to save battery | turn-off-wifi | delete-file (looks for a file) |
| get rid of the browser window, I'm done with it | close-app | delete-file (looks for a file) |
| start the browser, i want to look something up | open-app | open-file (looks for a file) |

**Two right answers offered (2).** do I have internet → look for a kind of file / check the network; do i
have room for more files → look for a kind of file / check storage. The right skill is in both choices.

## 3. Not understood (29)

**Skills that never learned an everyday wording (11).**

| Skill | Sentences |
|---|---|
| previous-track | go back a song · go back to the last track · go back to the last song |
| turn-up-sound | louder (twice, in two sets) |
| turn-down-sound | make it quiter please |
| delete-file / delete-folder | can you throw todo.txt in the bin · bin the Downloads folder |
| install-app | I'd like to have gimp on this computer, can you put it on? · can you get me the vlc player |
| restart-service | give nginx a kick |

**A reason added to the request (4).** The request alone would pass; the extra clause sinks it.

restart ssh, I can't log in from my laptop · can you turn it off and on again, the whole thing is acting
weird · log me into home-5g please, the internet isnt working without it · connecting to home-5g, password
sunflower42

**Other wordings (14).**

| Skill | Sentence |
|---|---|
| check-system | everything alright? |
| check-storage | how many gigs are free |
| create-file | I want to write a python script named test |
| create-folder | I want a folder for my taxes |
| rename-file | can you call seed.md something else, like garden.md · call todo.txt chores.txt instead |
| rename-folder | i want the projects folder to be called work instead |
| copy-file | I need a second todo.txt inside home |
| find-file | search the whole computer for website.html |
| download-file | i need this one off the internet https://example.net/guide.zip |
| close-app | I'm done with the terminal, you can shut it |
| show-type | notes in ideas |
| show-remote | browse the studio pi |
| check-usb | which drives are connected |

## 4. Out of scope, asked instead of refused (15)

| Offered | Sentences |
|---|---|
| check-usb | format the sd card · format my usb stick · format the usb stick · eject the sd card · partition the usb drive |
| send-file | send a message to my mom · send an email to my boss saying I'm late |
| connect-wifi | connect to my phone · forget the cafe-guest network |
| others | delete all my files (delete-folder) · kill the process with id 4312 (stop-process) · empty the trash completly (empty-trash) · what gift should I buy my wife (show-wifi) · is the oven still on (check-service) · what time is it in Tokyo (check-time) |

## 5. Failing unit tests (3, the same on feat/frames)

| Test | Expected | Got |
|---|---|---|
| a template the model doubts asks which of two | "rename the folder photos to pictures" asks | gives up: can't find a file called photos |
| other wording the model understands and checks first | "is there enough space for a movie" → check-storage | check-type |
| the documents stay quiet when they do not really match | "what is permacomputing?" asks | answers from a document |

The first two are sentences listed above; the third is about the host's documents, not a skill.
