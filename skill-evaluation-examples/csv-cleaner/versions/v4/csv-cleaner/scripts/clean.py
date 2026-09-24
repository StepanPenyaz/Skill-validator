#!/usr/bin/env python3
"""Normalizes headers, drops duplicate rows, fixes encoding, and (with
--map) renames headers to canonical names in a CSV file."""
import csv
import json
import sys


def load_mapping(map_path):
    with open(map_path, encoding="utf-8") as f:
        return json.load(f)["mapping"]


def clean(path, in_place=False, map_path=None):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f))
    if not rows:
        return
    header = [h.strip().lower().replace(" ", "_") for h in rows[0]]
    if map_path:
        mapping = load_mapping(map_path)
        header = [mapping.get(h, h) for h in header]
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
    args = sys.argv[1:]
    in_place = "--in-place" in args
    map_path = args[args.index("--map") + 1] if "--map" in args else None
    clean(args[0], in_place=in_place, map_path=map_path)
