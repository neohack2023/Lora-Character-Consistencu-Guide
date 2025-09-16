# Daggerfall-Style Prison Escape Demo

Standalone prototype for a retro, Daggerfall-inspired opening sequence where the
player awakens in a prison cell and must find a way out. This repository bundles
the Python escape logic, a browser-based canvas demo, and design notes so the
project can evolve independently.

## Contents

- [Implementation Plan](docs/prison_cell_intro_plan.md)
- [Python Escape Logic](game/prison_cell_intro.py)
- [Browser Demo](web/prison_cell.html)

## Running Tests

Ensure the logic behaves as expected by running the unit tests:

```bash
pytest -q
```

## Browser Demo

Open `web/prison_cell.html` in any modern browser to play the escape sequence
with chunky pixel visuals reminiscent of classic Daggerfall.
