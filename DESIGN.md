# Contour Colony — Design Brief for Claude Code

Oct 4, 2026 · @Charlotte

## What, why, how

Contour Colony is a small, systems-driven lunar mining game in Python: you command a mining site from orbit through a CRT vector console, growing two scavenger rovers into a connected factory chain that fills consortium contracts.

**What.** You are a site commander aboard an orbiting consortium ship. Your only view of the surface is a cassette-futurist vector display: glowing contour lines on black, wireframe structures, chevron units leaving phosphor trails. You place structures and direct units; you never touch the ground yourself.

**Why.** The consortium issues **contracts**: deliver set quantities of refined goods by a deadline. Contracts pay credits and reputation. Credits buy supply drops and research; reputation is the run's clock. A site is complete when it fills a standing contract without supply drops, meaning it is self-sufficient and can be handed off. Then the commander moves to the next site.

**How.** Structures and units form one interacting system:

- The lander arrives with two **scavenger rovers** that autonomously collect surface debris and bring it home. This slow trickle means the player can never be fully stuck, and it makes the site look like an ant farm from the first second.
- **Survey rovers** reveal terrain detail and hidden resource fields.
- **Mines** on fields feed a short chain: mine, processor, refinery, manufacturing.
- **Haulers, constructors and maintenance drones** keep that chain moving, built and repaired. Every structure has buffers, power draw and wear, so a single missing link backs up visibly.
- **Terrain manipulation** (grading pads, cutting roads) is a paid site improvement, not the core loop.

**Design rule:** the interesting decisions are about flow: where to put a mine relative to its processor, whether a link deserves a conveyor or a hauler route, which bottleneck to fix next. If a feature doesn't create or relieve a flow problem, it's probably out of scope.

## How to start in Claude Code

Export this document as Markdown, save it as `DESIGN.md` in an empty project folder, and open Claude Code there with the prompt below. Work one milestone at a time and playtest between them.

```
Read DESIGN.md in full. It is the design brief for a small Python game.

Before writing code:
1. Summarize the game back to me in 5 bullet points so I can check you understood it.
2. Propose the folder layout and the list of modules for Milestone 1 only.
3. List anything in the brief that is ambiguous or that you think will cause technical trouble.

Then wait for my go-ahead. When I approve, implement Milestone 1 only, run its tests, and stop.

Constraints: Python 3.12, pygame-ce as the only runtime dependency, must build for the browser with pygbag. Keep all tunable numbers in data tables, never hard-coded in logic.
```

For later milestones, a short prompt is enough: "Implement Milestone N from DESIGN.md. Re-read the relevant sections first. Stop when its exit criteria pass." When the design changes, edit this document (or `DESIGN.md`) rather than describing the change in chat, so Claude Code always has one source of truth.

## Technical constraints

Use Python 3.12 with **pygame-ce** as the only runtime dependency, and build for the web with **pygbag**, which compiles the game to WebAssembly so it can be embedded on a website in an iframe. Pure-standard-library Python can't draw in a browser, so this is the minimum realistic stack.

| Concern | Decision |
| --- | --- |
| Runtime dependencies | pygame-ce only. Standard library for everything else (`dataclasses`, `random`, `heapq`, `json`, `array`, `math`, `asyncio`). No numpy: it complicates the web build and isn't needed at this scale. |
| Web build | pygbag. Output is a static folder (HTML + WASM + game archive) that drops into any website or itch.io. |
| Main loop | Must be `async def main()` with `await asyncio.sleep(0)` once per frame, which pygbag requires. Works identically on desktop. |
| Threads | None. pygbag has no threading; spread heavy work (terrain generation, marching squares) across frames as generators or incremental jobs. |
| Saving | JSON. On desktop, a file; in the browser, `localStorage` via pygbag's `platform.window`. Hide both behind one small `storage` module. |
| Assets | None external. Terrain is procedural; the font is a Hershey vector font stored as Python data (public domain stroke font, ideal for a CRT look); sounds are synthesized at startup with `array` into `pygame.mixer.Sound(buffer=...)`. |
| Resolution | Internal render surface 960×540, scaled to the window. Keeps fill-rate costs predictable in the browser. |
| Performance budget | Python in WASM runs roughly 2–4× slower than native. Target 30 fps in the browser, at most \~3,000 line segments drawn per frame, at most \~150 active units, simulation at 10 ticks per second. |

**Consequence for design:** the browser build sets the performance ceiling. Every feature should be tested in a pygbag build, not just on desktop, from Milestone 1 onward.

## Rendering vector contours in Python

The browser prototype drew contours per pixel in a GPU shader; Python can't do that per frame, so here contours become precomputed line geometry. That actually suits a vector-display look better: everything on screen is a list of line segments.

**Contour geometry.**

1. Heightmap is 256×256 floats (a flat Python `array('f')`), each cell about 400 m, so a site is about 100 km square.
2. At site generation, run marching squares once per contour level (about 40 levels) and stitch segments into polylines. Store polylines per 32×32-cell **chunk** so off-screen chunks are skipped.
3. Build three detail tiers: every 4th level (zoomed out), every 2nd, and all levels (zoomed in). Pick a tier by zoom, like the prototype's zoom-adaptive interval.
4. Simplify polylines (drop points that deviate less than a quarter cell) to cut segment count.
5. When terrain changes (site improvements, survey updates), re-march only the affected chunks, spread over several frames.

**Drawing.** Each frame, transform visible polylines to screen space and draw them with `pygame.draw.aalines`. Color is per contour level from the height palette in survey view, and a dim gray-green in operations view.

**Glow (bloom).** Draw all lines to a separate surface, `smoothscale` it down to quarter size and back up, then blit that blurred copy onto the frame with `BLEND_ADD` under the sharp lines. This costs a few milliseconds per frame and gives the CRT halo. Make it a setting.

**Phosphor persistence.** Units draw onto a persistent trail surface that is faded each frame with a `BLEND_MULT` fill of about 0.92. Moving units leave decaying trails for free. Clear it on camera moves, or keep trails in world space as short point lists if camera-stable trails are wanted.

**CRT dressing** (all optional, all cheap): a pre-rendered scanline overlay blitted at low alpha, slight per-frame jitter on damaged structures, and a brief bright flash on alerts. Skip barrel distortion; it is expensive in software.

## Run structure: contracts, reputation and orbital passes

A run is one site, 40–60 minutes long, driven by a sequence of consortium contracts. A light campaign of linked sites comes later and is out of scope for the first playable build.

**Contracts.** At most 3 are open at once. Each names a good, a quantity and a deadline, e.g. "40 iron ingots in 6 minutes". Goods count as delivered when they reach the lander's export bay. Contracts escalate from raw-ish goods (iron) to manufactured ones (machine parts, fuel cells).

**Pace (decided by playtest).** Two modes, chosen on the landing briefing. *Calm* (default): contracts arrive as offers on the board; the player accepts the ones they want (click, or K), the clock starts on acceptance, an offer nobody takes is withdrawn without penalty, and reputation never drains, so only accepted contracts can cost reputation. *Pressure*: contracts are assigned at once and reputation drains after a 15-minute grace, as originally written. The game should feel zen first; pressure is opt-in.

| Outcome | Effect |
| --- | --- |
| Filled on time | Credits plus reputation (+10) |
| Filled late | Credits only |
| Expired | Reputation −15 |

**Reputation** (0–100, starts at 50) is the run's clock and fail state. In pressure mode it also drains slowly (−1 per minute) to keep pressure on. At 0, the consortium pulls the plug and the run is lost.

**Credits** pay for research, supply drops and site improvements. Scavenged debris can be sold for a trickle of credits, which pairs with the scavengers to prevent a hard stall.

**Orbital passes** are the commander-in-orbit mechanic. The ship's orbit brings it overhead for 90 seconds out of every 4 minutes, shown as a pass timer on the HUD. During a pass:

- **Supply drops** land. Order them anytime, but they arrive only during a pass. Each drop is a crate of parts, a pre-built unit, or a structure kit, bought with credits.
- **Orbital scans** run: one free coarse scan of a chosen region per pass.
- Out of pass, everything on the surface still runs autonomously; you just can't receive anything from orbit. This makes the pass a rhythm the player plans around.

**Win state.** The site is complete when the player fills the final "Standing contract" (a repeating order of manufactured goods) twice in a row without ordering any supply drop in between. That proves self-sufficiency. Score = credits earned + reputation + time bonus.

## Production chain

Three chains feed each other: ice supplies hydrogen to the ilmenite chain, the ilmenite chain's furnace hands water back and passes titania on to the titanium chain, and machine parts flow out to both manufacturing ends.

&#91;embedded content: production chain · 10 structures, 3 chains\]

Two side chains feed construction rather than contracts: scavengers bring in scrap, and grading produces regolith for the sinter kiln. Every arrow in the diagram is either a hauler job or a conveyor, which is the player's choice.

Text version of the diagram (for Markdown export, where the drawing is dropped):

```
Ice mine -> Ice melter -> Electrolyzer -> Fuel cell plant
Ilmenite mine -> Crusher -> Reduction furnace -> Machine shop
Electrolyzer --hydrogen--> Reduction furnace
Reduction furnace --water--> Electrolyzer
Reduction furnace --titania--> Titanium refinery -> Frame works
Machine shop --parts--> Fuel cell plant
Machine shop --parts--> Frame works
Side chains: Scavengers -> scrap (construction, sale); Grading -> regolith -> Sinter kiln -> sinter blocks (construction)
```

## Resources

Fourteen items in five tiers, loosely grounded in real lunar resource processing. Ilmenite (an iron-titanium oxide common in lunar soil) is the backbone, and the ice chain supplies the hydrogen it needs, so the two chains depend on each other.

| Item | Tier | Comes from | Used for |
| --- | --- | --- | --- |
| Scrap | Raw | Scavengers collecting surface debris | Sold for credits; recycled into iron at low yield |
| Ilmenite ore | Raw | Ilmenite mine on a surveyed field | Crusher |
| Ice | Raw | Ice mine in a shadowed crater field | Ice melter |
| Regolith | Raw | Any excavator or grader activity | Sinter kiln |
| Concentrate | Processed | Crusher | Reduction furnace |
| Water | Processed | Ice melter; recovered from the reduction furnace | Electrolyzer |
| Sinter blocks | Processed | Sinter kiln | Cheap structure building material, roads |
| Hydrogen | Refined | Electrolyzer | Reduction furnace, fuel cell plant |
| Oxygen | Refined | Electrolyzer | Fuel cell plant; contract good |
| Iron | Refined | Reduction furnace | Machine shop; contract good |
| Titanium | Refined | Titanium refinery (from furnace by-product) | Frame works; contract good |
| Machine parts | Manufactured | Machine shop | Building structures and units; contract good |
| Frames | Manufactured | Frame works | Tier 3 structures; contract good |
| Fuel cells | Manufactured | Fuel cell plant | Unit batteries upgrade; late contracts |

**The loop to notice:** the reduction furnace consumes hydrogen and gives back water, which the electrolyzer splits into hydrogen again. Ice only tops up losses. Players who see that loop build a compact, efficient plant; players who don't keep starving the furnace. That's the kind of systems discovery the game should be full of.

All quantities are integers, moved in whole units. Recipe timings and amounts live in data tables (see Code architecture).

## Structures

About 18 structures in four tiers. Each has a footprint, a maximum slope, input and output buffers, a power draw, and a wear rate. Recipes run in cycles: a cycle starts when inputs and power are available and output space is free.

| Structure | Tier | Recipe (per cycle) | Power | Build cost |
| --- | --- | --- | --- | --- |
| Lander | 0 | Hub: 200 storage, export bay, charges 4 units, sells scrap | +15 kW (internal) | Given |
| Solar array | 0 | Generates power, scaled by site illumination | +10 kW | 10 scrap, 2 parts |
| Power pylon | 0 | Extends the grid 6 cells | 0 | 4 scrap |
| Depot | 0 | 100 storage; home base for haulers | 1 kW | 15 scrap |
| Charging pad | 0 | Recharges 2 units at once | 3 kW | 8 scrap, 2 parts |
| Rover bay | 1 | Builds units (see Units) | 5 kW | 20 scrap, 6 parts |
| Ilmenite mine | 1 | → 2 ore / 6 s; must sit on a surveyed field | 6 kW | 20 scrap, 4 parts |
| Ice mine | 1 | → 2 ice / 8 s; must sit on a surveyed ice field | 6 kW | 20 scrap, 4 parts |
| Crusher | 1 | 2 ore → 1 concentrate / 4 s | 8 kW | 15 scrap, 4 parts |
| Ice melter | 1 | 1 ice → 1 water / 3 s | 5 kW | 10 scrap, 2 parts |
| Sinter kiln | 1 | 3 regolith → 1 sinter block / 5 s | 10 kW | 15 scrap, 3 parts |
| Electrolyzer | 2 | 1 water → 2 hydrogen + 1 oxygen / 4 s | 14 kW | 20 sinter, 6 parts |
| Reduction furnace | 2 | 2 concentrate + 2 hydrogen → 1 iron + 1 titania + 1 water / 6 s | 16 kW | 30 sinter, 8 parts |
| Machine shop | 2 | 2 iron → 1 machine part / 6 s | 8 kW | 20 sinter, 6 parts |
| Maintenance hangar | 2 | Home for maintenance drones; stores spare parts | 3 kW | 20 sinter, 4 parts |
| Conveyor (per segment) | 2 | Moves items between two adjacent structures, 1 item/s | 0.5 kW | 1 sinter per cell |
| Titanium refinery | 3 | 2 titania → 1 titanium / 8 s | 20 kW | 30 sinter, 6 iron, 10 parts |
| Frame works | 3 | 2 titanium + 1 machine part → 1 frame / 8 s | 10 kW | 30 sinter, 10 parts |
| Fuel cell plant | 3 | 2 hydrogen + 1 oxygen + 1 part → 1 fuel cell / 10 s | 10 kW | 20 sinter, 4 frames |

**Construction.** Placing a structure creates a construction site, not a finished building. Constructor units carry the build materials to it and assemble it over time. Cheap tier 0–1 structures cost scrap and parts so the scavenger trickle can fund them. Tier 2+ cost sinter blocks, so a working sinter kiln is the gate into the mid-game.

**Titania** (the titanium dioxide by-product) is a fifteenth item that only matters once the titanium refinery exists. Until then, it piles up in the furnace's output buffer and must be hauled to storage, which is an intentional early nudge toward tier 3.

## Units

Five unit types, all autonomous by default and all running on batteries. The player shapes their behavior through priorities, assignments and the structures they serve, plus direct orders when needed.

| Unit | Starts with | Job | Build cost (rover bay) |
| --- | --- | --- | --- |
| Scavenger | 2 | Finds the nearest unclaimed surface debris, collects it, returns it to the lander or a depot | 6 scrap, 2 parts |
| Survey rover | 0 | Drives to a target region and raises its survey level; reveals resource fields | 10 scrap, 4 parts |
| Hauler | 0 | Takes jobs from the job board: moves items from output buffers to input buffers or storage | 12 scrap, 4 parts |
| Constructor | 1 | Carries materials to construction sites and builds them; performs site improvements | 12 scrap, 6 parts |
| Maintenance drone | 0 | Flies (ignores slope) to structures above 50% wear and repairs them using parts | 8 sinter, 6 parts |

**Shared rules.**

- **Battery.** Every unit has charge (100 units) that drains with distance and work. Below 20%, it abandons its job, returning it to the board, and drives to the nearest charging pad or the lander. Range from charging points is therefore a real constraint on where you can mine.
- **Cargo.** Haulers carry 10 items of one type; scavengers carry 2 scrap; constructors carry 10 build items.
- **Speed.** Base speed divided by (1 + slope ÷ 5°) off-road, doubled on graded roads. Maintenance drones fly at constant speed.
- **Direct orders.** Select a unit and right-click to give a one-off order (go here, survey this, haul from A to B). The unit returns to autonomous mode once it's done.
- **Assignment.** Haulers can be pinned to a depot, so they only take jobs within its radius. This is how the player builds dedicated logistics districts.

**Scavenger behavior** is the opening scene and should be tuned for charm: debris objects (small vector glyphs such as rocks, panels and meteorite fragments) are scattered across the site and respawn slowly (one per 20 s, up to 40 on the map). Scavengers wander toward the nearest one, pause to "pick up" with a little blink, and trundle home. The player should be able to just watch for a minute and enjoy it.

## Systems rules

Five small systems interact to create the game: buffers, the job board, power, wear and connections. Each is simple on its own; the depth comes from their interplay, and every one of them is visible on screen.

**1. Buffers.** Every structure has typed input and output buffers with fixed capacities (inputs: 2–3 cycles' worth; outputs: 10). A full output buffer stops production (backpressure). An empty input buffer starves it. Both states are shown as gauges beside the structure and as a status color on its wireframe.

**2. Job board** (provider/requester model).

- Output buffers *offer* items once they hold at least 5 (or are full).
- Input buffers *request* items up to their capacity. Storage (lander, depots) requests anything, at lowest priority.
- Haulers pick the job with the best score: amount ÷ (trip distance + 10), with a priority multiplier. Picking a job **reserves** the items at both ends, so two haulers never chase the same load.
- Structure priority (high / normal / low, set by the player) multiplies job scores and also decides who gets power first.

**3. Power.** A structure is on the grid if it lies within a pylon's, solar array's or the lander's connection radius of another grid structure. Supply and demand are summed per connected grid. On a shortfall, structures are served in priority order and the rest go **unpowered**, shown as dimmed, flickering wireframes. No batteries in the first version; keep it legible.

**4. Wear.** Each completed cycle adds wear (0.2–0.5% depending on structure). At 50% the structure posts a repair job; at 100% it **breaks** and stops. Repairs consume 1 machine part per 10% and are done by maintenance drones, or by constructors at half speed. Wear creates a steady demand for machine parts, which closes the loop: the factory must partly feed itself.

**5. Connections: haulers versus conveyors.**

|  | Haulers | Conveyors |
| --- | --- | --- |
| Flexibility | Any source to any destination | Fixed link between two adjacent structures |
| Throughput | Limited by unit count and trip time | Constant 1 item/s |
| Terrain | Slowed by slope; faster on graded roads | Need ground graded under 5° along their whole path |
| Cost | Unit build cost plus charging infrastructure | Sinter per cell plus grading cost |
| Failure mode | Congestion, battery runs, competing jobs | Upstream stall if the downstream structure stops |

The intended arc: haulers for everything early, then conveyors for the two or three highest-volume links once the player can afford grading. That choice is where terrain reenters the game without terraforming being the main verb.

**Tick model.** All systems update at 10 ticks per second in a fixed order: power → production → job board → units → wear → contracts. Fixed order keeps the simulation deterministic and testable.

## Terrain, survey and site improvements

Terrain is the board the systems play on, not the main verb: it decides where fields are, how fast units move, and where conveyors can go. Reshaping it is a paid improvement.

**Generation.** Reuse the prototype's approach (fractal value noise, flooded basins, power-law craters with flat floors and central peaks) at 256×256. Also generate:

- **Resource fields:** 4–6 ilmenite fields (on mare-like flats and crater ejecta) and 2–3 ice fields (in deep crater floors), hidden until surveyed.
- **Illumination:** a per-cell sunlight factor from height plus a cheap horizon check toward a fixed sun direction. It scales solar output (40–100%). Static for the whole run; no day/night in the first version.
- **Debris spawn weights**, favoring crater rims and flat ground.

**Survey levels.** Each cell has a survey level of 0–2. Level 0 (orbital) shows contours at a coarse interval and no fields. Level 1 (orbital scan during a pass, or survey rover) shows normal contours and *hints* at fields as flickering dotted outlines. Level 2 (survey rover lingering 5 s) shows fine contours and confirms a field's exact boundary and richness. Mines can only be placed on level-2 cells inside a field.

**Slope rules.**

| Slope | Meaning |
| --- | --- |
| < 5° | Buildable; conveyors allowed |
| 5–15° | Units pass at reduced speed; structures need a graded pad |
| 15–25° | Units pass only on graded roads |
| > 25° | Impassable for ground units; maintenance drones fly over |

**Site improvements.** Done by constructors, paid in credits plus time, and limited to small areas:

- **Grade pad:** flattens a circular area to its average height, so a structure can be built on 5–15° ground.
- **Grade road:** a drawn path that units drive at double speed with halved slope penalty. Holding Shift snaps the road along the nearest contour (the marching-squares tracer from the prototype), giving a level road.
- **Conveyor bed:** grading along a conveyor's route, automatically priced when a conveyor is placed over ground steeper than 5°.

Grading produces regolith as a by-product, which feeds the sinter kiln. So improvements partly pay for themselves in material, but cost credits and constructor time, which compete with building new structures.

## Research tree

Fourteen nodes bought with credits, each taking 30–90 seconds to complete, one at a time. Half unlock structures; half upgrade existing structures or units, so research is a real choice between expanding and improving.

| Node | Requires | Cost (credits) | Effect |
| --- | --- | --- | --- |
| Field survey | — | 50 | Unlocks survey rover and the rover bay |
| Extraction | Field survey | 80 | Unlocks ilmenite mine, ice mine, crusher, ice melter |
| Sintering | Extraction | 80 | Unlocks sinter kiln and site improvements |
| Logistics I | — | 60 | Unlocks hauler and depot |
| Electrolysis | Sintering | 150 | Unlocks electrolyzer |
| Reduction | Electrolysis | 200 | Unlocks reduction furnace and machine shop |
| Conveyors | Sintering, Logistics I | 150 | Unlocks conveyors |
| Maintenance | Reduction | 120 | Unlocks maintenance hangar and drones |
| Titanium | Reduction | 300 | Unlocks titanium refinery and frame works |
| Fuel cells | Titanium | 300 | Unlocks fuel cell plant |
| Better batteries | Logistics I | 100 | Unit battery +50% |
| Hardened bearings | Maintenance | 150 | All wear −40% |
| Deep survey | Field survey | 120 | Survey rovers reach level 2 twice as fast; reveals field richness from level 1 |
| Overclocking | Reduction | 200 | Player can set any structure to 150% speed at 200% power and 200% wear |

Overclocking is the late-game knob: it turns power and maintenance capacity into throughput, so a player who over-built solar and drones can cash that in.

## UI and CRT vector aesthetic

The whole screen is one cassette-futurist console: vector lines on black, a Hershey stroke font, and a strict brightness hierarchy where your operation is always the brightest thing visible.

**Brightness hierarchy.** Terrain contours sit at 25–35% brightness in operations view. Structures and units are full brightness. Alerts flash. A survey view (Tab) brings terrain to full height-colored brightness for planning.

**Color vocabulary** (reserved meanings; pair each with a line style for colorblind players):

| Color | Meaning | Line style backup |
| --- | --- | --- |
| White | Structures and units, normal | Solid |
| Amber | Power: grid links, unpowered warnings | Dotted |
| Cyan | Item flow: hauler routes, conveyors, buffer gauges | Dashed |
| Green | Resource fields and survey data | Long dash |
| Red | Broken, starved or blocked; contract deadlines | Double line, blinking |

**Entities.** Structures are small oblique wireframes that plot themselves line by line while under construction. Units are chevrons or simple glyphs, with state shown by motion (idle blink, low-battery flicker). Every structure has compact gauges for its input and output buffers.

**Overlays** (number keys): power grid, item flow (animated dashes along active routes, thickness by throughput), wear, survey coverage. Overlays recolor existing lines rather than drawing filled areas.

**HUD.** Framed like a terminal: credits and reputation top left; open contracts as a list with countdown bars top right; orbital pass timer as a sweeping arc; a teletype event log bottom left; build menu and research as keyboard-driven panels. All text in the Hershey font, sized 1×/2×.

**Inspect panel.** Clicking a structure shows its recipe, buffer contents, power state, wear and the jobs touching it. Clicking a unit shows its job, cargo and battery. This is the main tool for diagnosing flow problems, so make it fast and readable.

**Audio** (synthesized at startup): square-wave UI blips, a low hum that rises with total power load, a ticking clock under contracts close to expiry, a chime on contract filled, and a static burst for the orbital pass beginning and ending.

## Code architecture

The simulation never imports pygame; rendering reads simulation state and never changes it. That split makes the game testable headlessly with the standard library's `unittest`, and keeps the browser build's rendering costs isolated.

```
contour_colony/
  main.py              # async entry point (pygbag requires main.py at the root)
  game/
    sim/
      world.py         # World: terrain, structures, units, items, tick()
      terrain.py       # heightmap gen, fields, illumination, slope, survey levels
      power.py         # grid connectivity + allocation by priority
      production.py    # recipe cycles, buffers, backpressure
      jobs.py          # job board: offers, requests, reservations, scoring
      units.py         # unit state machines, battery, movement
      pathing.py       # A* on a 64x64 cost grid (slope + roads), cached
      wear.py          # wear accumulation, repair jobs, breakdowns
      contracts.py     # contract generation, deadlines, reputation, credits
      orbit.py         # pass timer, drops, scans
      research.py
    content/           # plain Python data tables: no logic
      items.py  structures.py  units.py  research.py  contracts.py
    render/
      contours.py      # marching squares, chunked polylines, detail tiers
      draw.py          # world -> line segments, camera transform
      glow.py          # bloom + phosphor surfaces
      hershey.py       # vector font data + text drawing
    ui/
      hud.py  panels.py  input.py  overlays.py
    audio/synth.py     # tone generation with array + mixer.Sound
    storage.py         # save/load: file on desktop, localStorage in browser
  tests/               # unittest: sim only
  tools/headless.py    # runs a scripted build order for N minutes, prints resource curves
```

**Conventions.**

- Fixed-step simulation at 10 Hz; rendering interpolates unit positions between ticks.
- Entities are `@dataclass(slots=True)` objects in dictionaries keyed by integer id; no ECS framework.
- One seeded `random.Random` per world, so a site is reproducible from its seed.
- Every tunable number lives in `content/`. Logic files contain no magic numbers.
- Heavy setup (terrain generation, contour marching) runs as a generator that yields every few milliseconds, so the browser build shows a progress bar instead of freezing.
- Saves are JSON: world seed, terrain edits as changed-cell lists, and all entities.

## Milestones

Seven milestones; each ends playable and is checked in a pygbag browser build. Milestone 4 is the first version worth showing anyone.

1. **Console and terrain.** Async main loop, 960×540 surface, Hershey font, terrain generation as a generator with a progress bar, chunked marching-squares contours with detail tiers, pan and zoom, glow, operations/survey views. *Exit:* a generated site renders at 30 fps in the browser with glow on.
2. **Ant farm.** Lander, debris spawning, two scavengers with batteries and charging, A\* pathing with slope cost, phosphor trails, inspect panel for units. Scrap accumulates and can be sold. *Exit:* you can watch the scavengers for two minutes and it looks alive.
3. **Build and power.** Construction sites and constructors, solar, pylons, depots, charging pads, power grid with priority allocation, research panel, survey rovers, survey levels, resource fields. *Exit:* you can survey a field and place a mine on it.
4. **The chain.** Buffers, recipes, job board with reservations, haulers, mines through to machine shop, contracts, reputation, credits, orbital passes and drops, win and loss. *Exit:* one full site is winnable and losable. Playtest here and rebalance before going further.
5. **Depth.** Wear and maintenance, conveyors, site improvements (pads, roads with contour snap), overlays, overclocking. *Exit:* a mid-game player chooses between conveyors and haulers for real reasons.
6. **Tier 3 and polish.** Titanium, frames, fuel cells, synthesized audio, CRT dressing, settings, save and load. *Exit:* a complete 45-minute run with saves.
7. **Balance and ship.** Headless runner for balance curves, tutorial contracts, web embed page. *Exit:* a stranger can learn it without you explaining.

**Tests to write as you go:** item conservation (no items created or destroyed outside recipes), job reservations (no double-claims), power allocation by priority, unit battery returns home before dying, deterministic replay (same seed and inputs produce the same state after 5,000 ticks).

## Changes from playtesting

Decisions made while playtesting Milestones 2–4, recorded here so this document stays the source of truth.

- **Finding things.** Debris is hidden until something sees it: scavengers (short sight), survey rovers (wider), the lander, and the **scanner**, a powered structure whose slow, faint radar sweep reaches most of the map. Fields are never found by ground units: the scanner flags a field after three sweeps (or an orbital scan does), then a survey rover confirms it with a detailed survey. Parts of a field behind cliffs are surveyed from the nearest reachable spot; a field whose remaining ground is unreachable counts as fully surveyed.
- **Storage is one colony-wide pool** (the lander plus depots). No single good may fill more than 30% of it (scrap 60%); haulers stop adding a good at its cap, so the producer backs up instead of the colony clogging. Scrap that doesn't fit is sold on arrival. Hydrogen and oxygen are vented when nothing takes them. Every good can be sold on the market (orbit menu) at 30% of its contract value; scrap at 2 credits. Input buffers hold at least a full hauler load (10).
- **Range.** Units top up at chargers on the way to jobs beyond one battery's reach, hopping charger to charger; charging pads are how the colony reaches far fields. Idle units give their dock back, and units without cargo prefer charging pads to the lander's docks.
- **Feel.** Units are distinct top-down silhouettes that turn with their heading (no ship-like arrows); frequently driven ground wears visible tracks that fade when unused; the landing opens with the lander coming down and a briefing on the body (a generated moon, dwarf planet or asteroid); drop pods fall with a trail, retro flare and dust ring.
- **Buildings play differently.** Each recipe building has its own rule: mines slow as their field's reserves run out (to 35% speed: move to fresh fields); the sinter kiln is a solar concentrator, faster in sunlight; the reduction furnace warms up while working and cools when starved (so it wants a steady feed); the ice melter runs twice as fast beside a working kiln or furnace (waste heat).
- **Dense building.** Solar arrays snap edge to edge into farms (+5% per touching neighbour). A building placed touching one that consumes its output feeds it directly (an item a second, no hauler): the early, free form of the conveyors planned for Milestone 5.
- **Grading.** Ground up to 15° can be built on if the colony pays to grade it (credits and extra build time, by degrees over the limit and footprint); grading turns up regolith. Placement marks show buildable (green), gradable (amber) and too steep (red).
- **Outposts** (Logistics I): a self-powered hub with two charging docks and a little storage, placeable anywhere reachable, so the colony spreads to distant fields without pylon chains.
- **A larger-looking world.** The site stays 256 × 256 cells, but a band of coarse, never-simulated scenery terrain surrounds it, matching the site's heights at its edge and fading out with distance; the camera can look a little past the edge.
- **Close-up sound.** Zoomed in, working machines and moving rovers near the middle of the screen are heard: thumping machinery (mines, crusher), humming process plant (melter, kiln, electrolyzer, furnace, shop) and rover motors.
- **Starting kit.** 300 credits, 100 scrap, 40 parts (the scrap trickle alone can't pay for the opening).

## Later: touch screens and teaching

Not built yet, kept in mind:

- **Touch.** Every action is a named action (`App._do`), so a touch toolbar can send the same ones keys do. New UI must be reachable by tap (board offers and menu rows are clickable). Still needed: on-screen buttons for build, research, contracts, orbit, pause and speed; long-press instead of right-click for orders; pinch to zoom and drag to pan; larger hit areas; no hover-only information.
- **Teaching.** The project should stay readable enough to rebuild from scratch as a Python course: plain data in `game/content`, a pygame-free simulation in `game/sim`, small modules with a docstring saying what each does and why, and tests that show each rule in isolation.

## Open questions

These are deliberately unresolved; decide them by playtesting, not up front.

- [x] Is the reputation drain (−1/min) plus contract deadlines too stressful for a systems game? Yes: calm mode (offers you accept, no drain) is the default; the drain lives on in pressure mode.
- [ ] Should orbital passes also gate direct unit orders (comms only while overhead)? More flavor, but possibly just frustrating.
- [ ] Do conveyors need splitters/mergers, or is one-to-one enough? Start with one-to-one.
- [ ] Day/night and batteries: worth adding in Milestone 6, or keep power static?
- [ ] Campaign: after one site works, is the next step a chain of sites with carried-over research, or a single long site with expansion?
- [ ] Does the scavenger trickle need to taper off over time so players can't stall forever on scrap alone?
- [ ] Browser performance: if 30 fps can't hold with glow on, drop glow to a cheaper single-pass halo or reduce the contour tier at default zoom.
- [ ] Lore hook: is the consortium a faceless company, or does it belong to an existing fictional setting with named corporations and contract flavor text?
