---
does: check model
label: say if I'm learning
reads: learning
admin: no
approve: no
---

Gab, 24 Oct, while TermNL was learning: "are you learning" wasn't understood, and "are you retrainng the
model" was read as starting again. Learning runs in the background (train model); this says whether it is
still going, or when it last ended.

## People say

- are you (still) learning
- are you (still) training/retraining (the/your) model
- are you (still) training/retraining yourself
- is the training/learning done/finished/over
- have you finished learning/training
- when did you last learn

## Also said

- are you done learning
- how is the learning going
- is the model ready
- did you finish training
- is the retraining finished
- how long until you're done learning

## When it's learning

- I'm still learning: {@sys.learning} so far. I'll tell you when I'm done.

## When it's fine

- I'm not learning right now. I last learnt {@sys.learning} ago.

## When it's unknown

- I'm not learning right now.
