# Contour Colony

A small, systems-driven lunar mining game in Python, drawn as a CRT vector
console. `DESIGN.md` is the design brief and the single source of truth.

Status: **Milestone 4 (the chain)**. A full site can be won and lost:
mines, crushers, melters, kilns, electrolyzers, reduction furnaces and machine
shops run recipes with input and output buffers; haulers work a job board with
reservations; consortium contracts pay credits and reputation; the ship's
orbital passes bring supply drops and a free orbital scan. Fill the standing
contract for machine parts twice in a row without ordering a drop and the site
is handed off (won). Let reputation reach zero and it is lost.

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
| O | Orbit and market: order supply drops (crates or ready-built units, land during the next pass), aim the free orbital scan while the ship is overhead, or sell 10 of any stored good |
| Left click | Select a unit or structure (inspect panel) |
| Right click | Order the selected unit: go there, or for a survey rover, survey there |
| 1-4 with a rover bay selected | Build a scavenger, constructor, survey rover or hauler |
| P | Cycle the selected structure's power priority |
| Del | Cancel the selected construction site (materials refunded), or mark a finished structure for a constructor to dismantle (75% back); Del again keeps it |
| X / Shift+X | Sell 10 scrap / all scrap (from any storage) |
| C | Centre on the selection |
| WASD / arrows / drag | Pan |
| Mouse wheel, Q / E | Zoom |
| Space, `,` / `.` | Pause, slower / faster (1x up to 64x for testing; the HUD shows the speed actually managed) |
| Tab or V | Operations / survey view |
| G, F | Glow, performance stats |
| M | Sound: all, effects only, off |
| I | Icons: console symbols or pictorial rovers and structures |
| N twice | Abandon the site and generate a new one (once, after a site ends) |
| Esc | Close menus (desktop: quit when nothing is open) |

How a site goes: contracts (top right) ask for goods by a deadline. Goods
count when a hauler brings them to the lander's export bay. Filled on time
pays credits and +10 reputation, late pays credits only, expired costs 15
reputation, and reputation also drains slowly after the first ten minutes.

A first plan: build a scanner (its radar reveals debris for the scavengers and,
after three sweeps, flags fields as "SIGNAL?"), research Field Survey and
Logistics I, build a rover bay, a survey rover to confirm a field (green dashed
outline) and two haulers, research Extraction, then put a mine on the field.
From there: crusher, ice mine and melter, sinter kiln (sinter builds tier 2),
electrolyzer, reduction furnace and machine shop. Fields far from the lander
need a charging pad (and pylons) nearer to them: rovers top up on the way.
Red, blinking structures are starved or blocked; the thin bars beside them
are their input (left) and output (right) buffers.

Storage is one colony-wide pool: the lander plus every depot. No single good
may fill more than 30% of it (scrap 60%), so a surplus backs up at its
producer instead of clogging the colony; sell surplus from the orbit menu.
Scrap that doesn't fit is sold on arrival, and hydrogen and oxygen are vented
when nothing takes them. The HUD shows colony storage and whether loads are
waiting for haulers. The first contract arrives five minutes in, and
reputation only starts draining after fifteen.

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
construction, research, survey, deterministic replay, recipes, item
conservation across the whole chain, hauler reservations, contracts, orbital
passes and drops, and the Milestone 4 exit: a bot-played site is won and a
neglected one is lost.

`tools/autoplay.py` plays a site headlessly with a simple build order, for
balance runs: `python3.12 tools/autoplay.py --seed 5` (add `--neglect` to
watch a site fail).

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
                   production, job board, contracts, orbit, survey, fields, structures,
                   debris, units + one brain per unit kind
game/content/      tunable numbers only, as plain data tables
game/render/       contours (pure Python), camera + terrain, symbols and pictorial glyphs, entities,
                   glow, Hershey text
game/ui/           HUD, contracts board and orbit menu, inspect panel, build and research menus, input
game/audio/        synth.py (pure Python tones, loops and music plan), player.py (mixer playback)
web/contour.tmpl   page template for the browser build (pygbag 0.9.3's, restyled)
tests/             unittest, headless
tools/             autoplay.py (headless bot for balance runs), display_check.py,
                   hershey_convert.py regenerates game/render/hershey_data.py
```

## Credits

Text uses the Hershey Roman Simplex stroke font.

- The Hershey Fonts were originally created by Dr. A. V. Hershey while
  working at the U. S. National Bureau of Standards.
- The format of the Font data in this distribution was originally created by
  James Hurt, Cognition, Inc., 900 Technology Park Drive, Billerica, MA 01821
  (mit-eddie!ci-dandelion!hurt).
