#!/usr/bin/env python

import random
import sys
from pathlib import Path


def load_words():
    with open("words.txt") as f:
        return [w[:-1] for w in f]


def random_name(words, used, n=2):
    name = None
    while name is None or name in used:
        name = "-".join(random.choice(words) for _ in range(n))
    return name


if __name__ == "__main__":

    files = sys.argv[1:]

    names = set()
    words = load_words()

    for file in files:
        p = Path(file)
        new_name = random_name(words, names)
        print(f"Renaming {p.stem} to {new_name}")
        p.rename(p.parent / f"{new_name}.json")
