# Self-training: the board trains its own model, nothing installed

Branch `feat/frame-self-training`, from `feat/frames`, 26 Oct 2026. Gab: "training must run on the board in
plain Python with no dependencies". On `feat/frames` it didn't: `train_classifier` imported numpy, and on
the board only the official numpy wheel works (HANDOFF.md).

## What changed

Only how the model is trained (`termnl/model.py`). What is learned is unchanged: the same features, TF-IDF,
balanced classes, the same penalty (C = 8), the same model file. Reading a sentence (`classify`) is
untouched, and so is everything above it.

Two steps, both plain Python:

1. **Stochastic gradient descent**, 12 passes, one sentence at a time in an order shuffled by a fixed seed,
   weights averaged over the last 6 passes. Cheap; lands close to the best model.
2. **20 steps of L-BFGS** on all the sentences at once, the algorithm numpy ran, now on plain lists. It
   settles on the one best model, whatever the shuffle.

Step 2 is the one that matters for dropping skills in. SGD alone answered as well, but its answers hung
on the shuffle: another seed moved 31 of 665 answers, so adding any skill would have moved about as many
unrelated ones. With the 20 settling steps, another seed moves 5.

## Measured (same protocol as the branch comparison of 26 Oct, numpy blocked)

| | feat/frames (numpy) | this branch (plain Python) |
|---|---|---|
| Handled, of 595 | 534 | 535 |
| Wrong skill offered | 28 | 29 |
| Wrong action | 2 | 2 (the same two) |
| Out of scope acted on, of 70 | 1 | 1 (the same one) |
| With a typo, still handled | 93% | 92% |
| Adding 10 skills moved, of 640 other answers | 19, 3 lost | 19, 3 lost |
| Unit tests | 3 fail | the same 3 fail; 2 new pass |
| Answers that differ between the two | | 4 of 665 |
| Reply time | 6.7 ms | 6.5 ms |
| Training here (cloud CPU) | 48 s, 191 MB | 161 s, 259 MB |
| Needs installed | numpy wheel | nothing |

Not measured: training time on the Orange Pi. numpy took 3 min there for 48 s here; plain Python loses
more on that CPU, so expect somewhere around 15 to 25 min. Please run `python3 -m termnl.train` on the
board. If it's too long, `settle=10` halves step 2 at the price of more noise (another seed then moves
about 11 answers).

## Knobs (`train_classifier`)

`passes=12, rate=2.0` the first step; `settle=20` the second; `seed=7` the shuffle (same seed, same model).
