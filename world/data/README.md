# Game data tables

YAML tables the engine loads, validated by `src/pantheon/world/schemas.py`. The prose in `world/*.md` is the readable rulebook; these files hold the same names and, from M1 on, the numbers. A test checks that the two agree. Canon: change only in `canon:` commits (WLD-03).

`regions.yaml` holds the regions, key locations and named notables from `world/geography.md`, so the engine can refuse a duplicate place or person and a stranger above a region's Tier cap.
