# Contour Colony

A small, systems-driven lunar mining game in Python, drawn as a CRT vector
console. `DESIGN.md` is the design brief and the single source of truth.

Status: **Milestone 6 (progression), in progress**. Land with scavengers and
a scraper on a 512-cell site, scrape regolith, sort it for minerals, melt scrap
into the first iron, and build the mass driver: four phases of goods, each
opening the next tier of research, then a launch that wins the site. Act I
and the mass driver are playable; the Tier II and III industries are being
built (see DESIGN.md, Progression).

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
| B | Build menu: Left/Right (or A/D, or click) picks a category; Up/Down (or W/S) + Enter, click a row, or press 1-9; then click to place (Shift+click places more), right click or Esc cancels. Conveyors: click the building to send from, then the one to send to. Roads: click one end, then the other (Shift+click carries on from there) |
| R | Research panel: Up/Down + Enter or click a row to start a project |
| K | Contract offers: accept one (or click an offer on the board) |
| L | Production: everything made per minute, and a graph over the whole run |
| U | Minimap on / off (click the minimap to look there) |
| O | Orbit and market: order supply drops (crates or ready-built units, land during the next pass), aim the free orbital scan while the ship is overhead, or sell 10 of any stored good |
| Left click | Select a unit or structure (inspect panel) |
| Right click | Order the selected unit: go there, or for a survey rover, survey there; a scraper sent somewhere sweeps there from then on |
| 1-6 with a rover bay selected | Build a scavenger, scraper, constructor, survey rover, hauler or maintenance drone |
| P | Cycle the selected structure's power priority |
| J | Clock speed of the selected production building: 100%, 50% (less power, less wear), 150% after Overclocking |
| Del | Cancel the selected construction site (materials refunded), or mark a finished structure for a constructor to dismantle (75% back); Del again keeps it |
| X / Shift+X | Sell 10 scrap / all scrap (from any storage) |
| C | Centre on the selection |
| WASD / arrows / drag | Pan |
| Mouse wheel, Q / E | Zoom |
| Space, `,` / `.` | Pause, slower / faster (1x up to 64x for testing; the HUD shows the speed actually managed) |
| Tab or V | Cycle views: operations, survey, power, flow (output per minute, hauler routes), wear |
| G, F | Glow, performance stats (off by default) |
| M | Sound: all, effects only, off |
| I | Icons: console symbols or pictorial rovers and structures |
| N twice | Abandon the site and generate a new one (once, after a site ends) |
| K on the win screen | Keep playing: the site runs on as a sandbox, the score stays as it was |
| Esc | Close menus (desktop: quit when nothing is open) |

The game saves itself every minute and as each orbital pass begins (a file
in `~/.contour_colony` on desktop, browser storage on the web). Next time it
offers to continue the site. Sound, glow, icon style and pace are
remembered too.

How a site goes: the landing briefing names the body you're on and lets you
pick the pace (P). In calm mode (the default) contracts arrive as offers on
the board (top right): click one, or press K, to accept it, and its clock
starts then. Goods count when a hauler brings them to the lander's export
bay. Filled on time pays credits and +10 reputation, late pays credits only,
expired costs 15 reputation. Pressure mode assigns contracts outright and
drains reputation slowly after the first fifteen minutes.

A first plan: place the mass driver (Goal tab) on flat ground near the
lander, then a scrap furnace (scrap to iron), a sinter kiln (regolith to
sinter) and solar power; research Logistics I and build haulers at a rover
bay, plus another scraper or two. Haulers bring the Foundation's sinter and
iron to the mass driver. Phase 1 opens Prospecting (the scanner, survey
rovers and drills for ilmenite, anorthite, KREEP and ice) and the hydrogen
route to iron. A sorter turns regolith into minerals; what it finds depends
on the ground it stands on. Red, blinking structures are starved or blocked;
the thin bars beside them are their input (left) and output (right) buffers.

Buildings have their own quirks: mines slow as a field runs out, the sinter
kiln likes sunlight, the reduction furnace needs to warm up (keep it fed), and
an ice melter beside a working kiln or furnace runs twice as fast. Place a
building touching the one it supplies and it feeds it directly, no hauler
needed; solar arrays click together into farms. Slightly steep ground can be
graded for credits (amber marks while placing). Outposts give far fields
their own power, charging and storage.

A rover that runs flat isn't lost: it trickle-charges from its emergency
panels (faster in sunlight) and drives home when it can.

Buildings wear as they work: past 50% they slow down and ask for a repair (a
machine part per 10%). Constructors repair when idle; maintenance drones
(after Maintenance research) fly straight to them from their hangar.

Conveyors (after the Conveyors research) are belts between two buildings up
to 16 cells apart: a producer to a building that uses its output, a producer
to storage, or storage to a building that uses what it holds. They cost a
sinter block per cell, run on the source's power and move an item a second.
Roads cost credits per cell (more on steep ground) and any constructor grades
them; rovers drive twice as fast on them on less battery, find them on their
own, and can climb a road up ground too steep to drive otherwise.

Tab cycles views. The power view shows what is powered and each grid's reach;
the flow view shows working buildings with their output per minute and the
routes haulers are driving; the wear view colours buildings from fresh
(green) to worn out (red).

Zoom right in to hear the site: machinery thumping, process plant humming,
rovers whining past.

Storage is one colony-wide pool: the lander plus every depot. No single good
may fill more than 30% of it (scrap 60%), so a surplus backs up at its
producer instead of clogging the colony; sell surplus from the orbit menu.
Scrap that doesn't fit is sold on arrival, and hydrogen and oxygen are vented
when nothing takes them. The HUD shows colony storage and whether loads are
waiting for haulers.

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
