#!/usr/bin/env python

import json
import random
import sys
from pathlib import Path


def split(qs, n):
    return [qs[i : i + n] for i in range(0, len(qs), n)]


def load_questions(filename):
    with open(filename) as f:
        return [line[:-1].split("\t") for line in f]


def to_number(s):
    clean = "".join(c for c in s if c.isdigit() or c in {".", "-"})
    if clean != s:
        print(f"Cleaned {s} => {clean}", file=sys.stderr)
    return float(clean)


if __name__ == "__main__":

    tsv = sys.argv[1]
    n = int(sys.argv[2])

    base = Path(tsv).stem
    qs = load_questions(tsv)
    random.shuffle(qs)
    chunks = split(qs, n)

    for i, c in enumerate(chunks):
        name = f"{base}-{i+1}"
        print(f"Writing {name}")
        with open(f"question-sets/{name}.json", mode="w") as f:
            data = {q: to_number(a) for q, a in c}
            json.dump(data, fp=f, indent=2, ensure_ascii=False)
            print("", file=f)
        if len(c) < n:
            print(f"*** chunk {i+1} only has {len(c)} question(s).")
