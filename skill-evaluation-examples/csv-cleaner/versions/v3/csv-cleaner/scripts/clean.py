#!/usr/bin/env python3
"""Normalizes headers, drops duplicate rows, and fixes encoding in a CSV file."""
import csv
import sys


def clean(path, in_place=False):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    header = [h.strip().lower().replace(" ", "_") for h in rows[0]]
    seen = set()
    deduped = [header]
    for row in rows[1:]:
        key = tuple(row)
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    out_path = path if in_place else f"{path}.cleaned.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(deduped)


if __name__ == "__main__":
    clean(sys.argv[1], in_place="--in-place" in sys.argv[2:])
