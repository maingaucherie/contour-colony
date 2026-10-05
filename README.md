# Contour Colony

A small, systems-driven lunar mining game in Python, drawn as a CRT vector
console. `DESIGN.md` is the design brief and the single source of truth.

Status: **Milestone 3 (build and power)**. On top of the terrain, the
scavenger ant farm and selling scrap: construction sites built by a
constructor, solar arrays, pylons, charging pads, depots, rover bays and mines,
power grids with priority allocation, a research tree, survey rovers, survey
levels that sharpen the contour map, and hidden ilmenite and ice fields.
Mines, crushers, melters and kilns can be built but don't produce yet:
recipes, haulers and contracts arrive with Milestone 4.

## Play

In the browser, nothing to install: **https://maingaucherie.github.io/contour-colony/**
(click once to start). Every push to the default branch runs the tests and
republishes this build (`.github/workflows/web.yml`).

## Run locally

Python 3.12, pygame-ce is the only runtime dependency.

```sh
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python main.py              # random site
.venv/bin/python main.py --seed 1234  # a specific site
```

| Input | Action |
| --- | --- |
| B | Build menu: Up/Down (or W/S) + Enter, click a row, or press 1-0; then click to place (Shift+click places more), right click or Esc cancels |
| R | Research panel: Up/Down + Enter or click a row to start a project |
| Left click | Select a unit or structure (inspect panel) |
| Right click | Order the selected unit: go there, or for a survey rover, survey there |
| 1-3 with a rover bay selected | Build a scavenger, constructor or survey rover |
| P | Cycle the selected structure's power priority |
| Del | Cancel the selected construction site (materials refunded), or mark a finished structure for a constructor to dismantle (75% back); Del again keeps it |
| X / Shift+X | Sell 10 scrap / all scrap from the lander |
| C | Centre on the selection |
| WASD / arrows / drag | Pan |
| Mouse wheel, Q / E | Zoom |
| Space, `,` / `.` | Pause, slower / faster (1x up to 64x for testing; the HUD shows the speed actually managed) |
| Tab or V | Operations / survey view |
| G, F | Glow, performance stats |
| M | Sound: all, effects only, off |
| I | Icons: console symbols or pictorial rovers and structures |
| N twice | Abandon the site and generate a new one |
| Esc | Close menus (desktop: quit when nothing is open) |

A first goal: build a scanner (its radar reveals debris for the scavengers and,
after three sweeps, flags nearby fields as a "SIGNAL?"), research Field Survey,
build a rover bay, build a survey rover to confirm a field (green dashed
outline), sell scrap for Extraction, then build a mine on the field. Debris is
hidden until something spots it: without a scanner, scavengers search blind.

If the game crashes at startup, try `python main.py --no-scale` (a plain
960x540 window without SDL's SCALED mode), then run
`python tools/display_check.py` and send its output: it tries each display
step in a separate process and shows which one fails.

## Tests

```sh
python3.12 -m unittest -v
```

Tests cover the headless parts only (`game/sim`, `game/render/contours.py`),
which never import pygame: terrain, contours, pathing, scrap conservation,
debris reservations, battery safety, power allocation by priority, placement,
construction, research, survey, and deterministic replay, plus an end-to-end
test of the Milestone 3 exit (survey a field, then build a mine on it).

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
game/sim/          simulation, no pygame: terrain, world + tick, pathing, power, research,
                   survey, fields, structures, debris, units + one brain per unit kind
game/content/      tunable numbers only, as plain data tables
game/render/       contours (pure Python), camera + terrain, symbols and pictorial glyphs, entities,
                   glow, Hershey text
game/ui/           HUD, inspect panel, build and research menus, input
game/audio/        synth.py (pure Python tones, loops and music plan), player.py (mixer playback)
web/contour.tmpl   page template for the browser build (pygbag 0.9.3's, restyled)
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
