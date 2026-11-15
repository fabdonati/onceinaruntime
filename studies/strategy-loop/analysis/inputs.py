"""Deterministic synthetic bars; never interpreted as an observed market history."""
import csv
import math
import random
from pathlib import Path


def synthetic(count, seed):
    # Integer draws make the random source explicit; the CSV is the canonical
    # input because libm's exp can vary across platforms. No short history repeats.
    rng = random.Random(seed)
    previous = 100.0
    bars = []
    for t in range(count):
        gap = rng.randrange(-1000, 1001) * 0.000001
        innovation = rng.randrange(-1000, 1001) * 0.000004
        drift = 0.00015 if (t // 257) % 2 == 0 else -0.00015
        opening = previous * math.exp(gap)
        closing = opening * math.exp(innovation + drift)
        bars.append((t, opening, closing))
        previous = closing
    return bars


def write_bars(path, bars):
    with Path(path).open('w', newline='') as file:
        writer = csv.writer(file, lineterminator='\n')
        writer.writerow(('timestamp', 'open', 'close'))
        writer.writerows(bars)
