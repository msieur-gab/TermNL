# Brief — a lighter model, and how a model should be packaged

Written 22 October 2026 by Claude, at the end of a long session (the context was compacted once). Some
details may have lost accuracy: check every claim here against the code and the brain. This is a topic
**to discuss with Gab first**, then research, then measure. Nothing should be converted before he picks.

Gab, 22 Oct: "JSON files really strange to me. miniLM for instance is not a JSON file... To be discussed
with the next instance."

## Read first

The same list as `2026-10-22-clock-network-real-tests.md` (brain `CLAUDE.md` in full, `projects/termlu/`,
this repo's `README.md`, `HANDOFF.md`, `TODO.md`), and also:
- `termnl/model.py` (training and the pure-Python reading of the model) and `termnl/train.py`;
- in the brain: `knowledge/hardware/orange-pi-zero-2w-onnxruntime-debian.md` and
  `orange-pi-zero-2w-onnxruntime-sherpa-works.md` (what runs on the Orange Pi);
- `~/dev/ptiLU/README.md` (ptiLU dropped weak weights and stored the rest as 1-byte numbers: 358 KB for
  22 skills; it trained in plain JavaScript, with no dependencies, even on the phone);
- Claude's memory note on quantization: never pitch a conversion as a quick job; measure first.

## What exists

`termnl/languages/en/model.json`, 669 KB. Two classifiers (action, object), each with its labels, a bias
and, for each feature (word, word pair…), one number per label, written as decimal text (about 3,270
features for the action model). Plus `taught`: the words each skill was taught. It is made from the skill
files by `python3 -m termnl.train` in about 5 seconds on Eve. Training uses numpy; reading the model is
plain Python.

## Questions to open with Gab

1. **Is the model a source or a cache?** Everything in it comes from the Markdown skills. It could be
   rebuilt at install time instead of shipped, and then its format matters much less.
2. **What "readable" should mean.** The numbers are text but not understandable. One option: keep what a
   person can read (labels, vocabulary, taught words) as text, and put the numbers in a plain binary file.
3. **How small models are usually packaged** (to research, with sources): ONNX (MiniLM's format), safetensors
   (a small JSON header plus raw numbers), GGUF, numpy's `.npz`, fastText's `.bin`/`.ftz` (a close cousin:
   a linear classifier over words, with a quantized form). Pickle-based formats load code and should be
   rejected.
4. **Size.** 1-byte weights and dropping weak weights, as ptiLU did. The test of success: identical
   replies on the 258 turns of `tests.compare_agents` and the same `tests.measure` counts.
5. **Training on the board.** Live training (Gab's decision: a reviewed learning inbox, then retraining on
   the device) needs training to run there. Debian's numpy crashed with "Illegal instruction" on the
   Orange Pi Zero 2W (brain note above). Training without numpy, as ptiLU did, may be needed; measure its
   time on the board before promising it.
6. **Permacomputing:** reading the model must stay standard-library Python.

## Proposed action

Open the discussion with these questions, then write a short research note (in the brain, after reading
its `CLAUDE.md`) with the options and their trade-offs. Measure only what Gab picks.
