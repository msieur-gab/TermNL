"""python3 -m tools.speed — how long TermNL takes to understand a sentence, on every test set's sentences."""
import statistics
import time

from termnl.agent import Agent
from termnl.load import load_language
from tests.device import device
from tests.measure import lines_of

if __name__ == "__main__":
    lang = load_language("en")
    texts = [t for name in ("phrasings", "probes", "heldout", "blind") for _, t in lines_of(name)]  # the same sentences each time
    times = []
    for t in texts:
        a = Agent(**lang, settings={"admin mode": "on"}, device=device, random=lambda: 0)
        t0 = time.perf_counter()
        a.hear(t)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    print("%d skills, %d sentences: median %.1f ms, 90%% under %.1f ms, slowest %.1f ms" % (
        len(lang["skills"]), len(times), statistics.median(times), times[int(len(times) * 0.9)], times[-1]))
