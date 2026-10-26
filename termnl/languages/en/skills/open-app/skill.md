---
does: open app
label: open an app
admin: no
approve: no
---

## People say

- open (the/a/my) {name} (app)
- open (an/a) app

## Also said

- open an app
- start the browser
- launch the terminal
- i want to browse the web
- open a terminal
- start firefox please
- run the browser
- fire up firefox
- can you start the terminal
- bring up the browser
- I'd like to open firefox
- terminal please
- open the browser, I want to check something online
- get me a terminal, I need to run something

## What it needs

- {name}: an app on the device. If it's missing, ask: Which app? | Which one should I open?

## Command

setsid {name}

## Replies

- done: Opening {name}. | {name} is opening.
