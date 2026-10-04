# Contour Colony

A small, systems-driven lunar mining game in Python, drawn as a CRT vector
console. `DESIGN.md` is the design brief and the single source of truth.

Status: **Milestone 1 (console and terrain)**: procedural site generation,
chunked marching-squares contours with three detail tiers, pan and zoom,
glow, operations and survey views.

## Run

Python 3.12, pygame-ce is the only runtime dependency.

```sh
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python main.py              # random site
.venv/bin/python main.py --seed 1234  # a specific site
```

| Input | Action |
| --- | --- |
| WASD / arrows / left- or middle-drag | Pan |
| Mouse wheel, Q / E (or - / =) | Zoom (wheel zooms toward the cursor) |
| Tab or V | Operations / survey view |
| G | Glow on / off |
| F or F3 | Performance stats |
| N | Generate a new site |
| Esc | Quit (desktop) |

## Tests

```sh
python3.12 -m unittest -v
```

Tests cover the headless parts only (`game/sim`, `game/render/contours.py`),
which never import pygame.

## Browser build

```sh
.venv/bin/python -m pygbag .          # build and serve at http://localhost:8000
.venv/bin/python -m pygbag --build .  # static files only, in build/web
```

`build/web` is a static folder (HTML + game archive) for any web host or
itch.io. pygbag downloads its page template at build time, and the browser
loads the Python WASM runtime at run time, both from `pygame-web.github.io`.

## Layout

```
main.py            async entry point (pygbag needs it at the root)
game/app.py        loading and running states, one frame at a time
game/sim/          simulation: terrain generation and queries (no pygame)
game/content/      tunable numbers only, as plain data tables
game/render/       contours (pure Python), camera + drawing, glow, Hershey text
game/ui/           HUD and input
tests/             unittest, headless
tools/             hershey_convert.py regenerates game/render/hershey_data.py
```

## Credits

Text uses the Hershey Roman Simplex stroke font.

- The Hershey Fonts were originally created by Dr. A. V. Hershey while
  working at the U. S. National Bureau of Standards.
- The format of the Font data in this distribution was originally created by
  James Hurt, Cognition, Inc., 900 Technology Park Drive, Billerica, MA 01821
  (mit-eddie!ci-dandelion!hurt).
