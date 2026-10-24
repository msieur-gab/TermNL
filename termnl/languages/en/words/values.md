# Values

How a skill file says what it needs, under `## What it needs`, one line per value:

    - {name}: a new name. If it's missing, ask: What should I call it? | What name should the folder have?
    - {place}: a folder on the device. If it's not said: where you are.

First what the value is (a line of Kinds), then, if it may be missing, what TermNL does then.

## Kinds

Each line: the words a skill file writes, then what TermNL reads. A value "on the device" is checked
against what the device really has, and offered as choices.

- a name: text
- a new name: text, new
- a secret: secret
- a file type: filetype
- a folder on the device: @sys.folder
- a file on the device: @sys.file
- a service on the device: @sys.service
- an app on the device: @sys.app
- a running app: @sys.running
- music on the device: @sys.music
- a network around: @sys.network

## When it's missing

- ask: if it's missing, ask
- default: if it's not said

## Defaults

Each line: the words a skill file writes after "If it's not said:", then what TermNL takes.
Any other words are taken as they are (a file type: markdown).

- where you are: here
- the folder above: parent
- the folder {value} is in: parent of {value}
