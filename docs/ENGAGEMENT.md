# What makes factory and colony games engaging, and what Contour Colony can use

Research notes, October 2026, for the design conversation after Milestone 4.
Sources are linked inline. Some sites couldn't be fetched directly, so a few
claims rest on search summaries, and points from forum or Steam threads are
marked *anecdotal*.

The short version: these games are fun when **a problem turns into a machine
that solves it, and you can watch it run**. Calm games keep that loop and
remove the pressure, the punishment and the clutter.

---

## 1. Why the genre works

| Principle | What it means | Who does it well |
| --- | --- | --- |
| **Problem → automation → new problem** | Every fix reveals the next small problem, so there is always one more step ("cookies and milk"). Manual work is mildly inconvenient on purpose, so automating it feels like relief. | Factorio ([review](https://notes.hamatti.org/Gaming/Video-games/Reviews/Factorio); [Steam thread](https://steamcommunity.com/app/427520/discussions/0/4631482569784875944), anecdotal) |
| **Reach the machine fast** | Factorio's own team found its old tutorial took 30-45 minutes before automation, "which is what the game is about", and rebuilt it. | [Factorio FFF #241](https://factorio.com/blog/post/fff-241) |
| **Watching it work** (*Wuselfaktor*) | The joy of many small, predictable agents bustling around a network that grows more complex. Dinosaur Polo Club calls it "the bread and butter of our style of games". | Mini Motorways ([GDC 2023 via Thumbsticks](https://www.thumbsticks.com/hustle-and-bustle-how-mini-motorways-built-its-wuselfaktor/)); Shapez 2's robot arms; Dyson Sphere Program's drones |
| **Bottleneck hunting, with visible causes** | Finding the starved machine is the core puzzle, but only if the player can see *why*. Factorio's most popular mod (Bottleneck) just puts a status light on every machine; Oxygen Not Included is approachable mainly because its overlays make failure "traceable". | [Factorio wiki](https://wiki.factorio.com/Production_statistics); [ONI overlays](https://oxygennotincluded.wiki.gg/wiki/Overlay) |
| **Discovering loops** | The best moments are spotting a hidden structure: a by-product that feeds back in, a chain that could be shorter. | Anno's population tiers; our hydrogen loop and waste-heat melter |
| **Short goals inside a long arc** | Small, frequent wins: a new train every week with a choice of upgrades (Mini Metro), a choice of building packs at each score threshold (Islanders), milestones that make you keep old lines running (Shapez 2). | [Mini Metro](https://www.giantbomb.com/games/3030-45639/), [Islanders](https://en.wikipedia.org/wiki/Islanders_(video_game)) |
| **Constraints that create choices** | Routing limits are what make belts interesting; Factorio's own developers worried that flying robots "flatten" the puzzle. Satisfactory's clock-speed dial trades power for throughput. | [Factorio forum on FFF #225](https://forums.factorio.com/viewtopic.php?p=334625); [Satisfactory clock speed](https://satisfactory.wiki.gg/wiki/Clock_Speed) |
| **A use for surplus** | Satisfactory's AWESOME Sink turns any overproduction into coupons, so an overbuilt factory is never wasted effort. | [Satisfactory wiki](https://satisfactory.wiki.gg/AWESOME_Sink) |
| **Clarity by elimination** | Mini Metro's talk "When Less Is More": design by removing things, and resist "timers, rewards, particles, collectibles and notifications". | [GDC 2017](https://gdcvault.com/play/1024250/-Mini-Metro-When-Less) |
| **Audio from the simulation** | Mini Metro's score is generated from what happens in the game ("90 percent coding"), which makes it meditative rather than stressful. Mini Motorways turned road noise into music. | [Kill Screen](https://www.killscreen.com/music-urban-commute-designing-mini-metros-soundtrack/); [Game Developer](https://www.gamedeveloper.com/design/turning-road-noise-into-music-mini-motorways) |
| **Small juice** | Easing, small pops and sounds make actions feel alive. Calm games use the gentle end of this: chimes and soft brightening, never screen shake. | ["Juice it or lose it"](https://roblog.co.uk/2024/03/juicy-games/) |
| **Adjustable pressure** | RimWorld lets players choose a storyteller, down to a peaceful one "for players who just want to build". Frostpunk sits at the opposite end. | [RimWorld storytellers](https://rimworldwiki.com/wiki/Storyteller) |
| **Short runs keep the best part** | Against the Storm's developers saw that a city-builder's first hours are its best, so their runs keep restarting there. This supports our 30-60 minute sites. | [Game Developer](https://www.gamedeveloper.com/road-to-igf-2023/how-against-the-storm-managed-to-mix-city-building-and-roguelite-play) |
| **Comparing without pressure, sandbox after the goal** | Opus Magnum shows your result against everyone's on three histograms, hinting that better exists without telling you how. Mini Metro, Dorfromantik and Islanders all added endless or creative modes after launch. | [Opus Magnum](https://punishedbacklog.com/opus-magnum-the-gold-standard-of-puzzle-games/) |

## 2. What makes the calm end of the genre work

- **Safety, abundance, softness.** Project Horseshoe's definition of cozy: little risk, no pressing needs, gentle stimuli ([report](https://pixelpoppers.com/link/d64e95/group-report-coziness-in-games-an-exploration-of-safety-softness-and-satisfied-needs/)). Cozy doesn't mean no challenge, only that failing costs little.
- **Keep the puzzle, drop the pressure.** Shapez removes enemies, resource limits and build costs; Islanders removes "resources, time limits, enemies"; Factory Town is praised for having no punishment for inefficient builds (aggregated reviews, anecdotal).
- **Low barrier, short sessions.** Dorfromantik was made for people who "cannot afford to invest hundreds of hours" ([interview](https://www.galaxus.ch/en/page/dorfromantik-developer-success-has-opened-a-lot-of-doors-for-us-23775)). Losing just means starting a fresh map.
- **Playing well extends the run.** Dorfromantik's small quests earn more tiles: success buys more play, with no timer.
- **Toys, not only games.** Townscaper has no goal at all; the pleasure is a system reacting beautifully to small inputs.

## 3. What makes these games tedious or stressful

- **Micromanagement at scale.** Satisfactory players report burnout around the middle tiers, from placing splitters and mergers over and over (Steam threads, anecdotal).
- **Logistics spaghetti.** Many-to-many routing is where tangles come from.
- **Opaque failure.** A machine that has stopped with no visible reason.
- **Alert floods.** A screen full of warnings hides the one that matters.
- **Slow building through middlemen.** Dyson Sphere Program's drone-built belts are "infuriatingly slow" ([review](https://bit-tech.net/reviews/gaming/pc/dyson-sphere-program-review/1/)). This is a direct warning for us, because our constructors build everything.
- **Grind gates.** Long waits that only delay progress.
- **Overwhelming UI, puzzle-like tutorials** (Desynced, Big Pharma reviews).
- **Maintenance as punishment.** In hardcore games a factory that can't feed its own upkeep "tears itself apart" (Captain of Industry players, anecdotal). That suits them, not a zen game.

## 4. What Contour Colony already does right

- **Watching it work:** scavengers, haulers and tracks, plus close-up sounds.
- **Short runs** with a sandbox after the win (keep playing).
- **Calm pace by default.** Contracts are offers you accept, and pressure mode is opt-in.
- **Discoverable loops and synergies:** the hydrogen loop, waste heat, direct feed and solar farms.
- **Generative ambient music**, synthesized at runtime.
- **No hard losses from mistakes:** stranded rovers recover, scrap that doesn't fit is sold, gases vent.
- **Visible causes:** a building's status colour plus its inspect panel explain why it has stopped.

## 5. Suggestions, ranked

Each is tagged with effort (S/M/L), and with **Obvious** (low risk, fits what we've agreed) or **Discuss** (changes the economy or the feel; talk first). Items built in Milestone 5 are marked *(built in Milestone 5)*.

1. **"Why stopped" mark on every structure, and a cause chain in the inspect panel.** A tiny glyph beside a stopped building shows the reason: starved, blocked, unpowered, worn, or no hauler free. The panel follows it upstream, e.g. "FURNACE STARVED < HYDROGEN < ELECTROLYZER UNPOWERED". This is Factorio's Bottleneck mod built in. *S-M, Obvious.*
2. **No ticking in calm mode.** Replace the ticking clock with a soft pulse on the countdown bar. A late contract could offer "extend for half pay" instead of costing reputation. *S, Obvious (the extension is Discuss).*
3. **Music from the colony.** Quantize events to a slow beat in one key: a hauler drop-off is a soft note, each finished cycle a note pitched per building type, the scanner a ping, an orbital pass a change of harmony. The colony becomes a piece of music that grows richer as it grows. This builds on the existing synthesizer and close-up sounds. *M, Discuss (taste and mix).*
4. **Discoveries log.** The first time a loop runs (hydrogen loop closes, waste heat reaches a melter, first solar farm, first direct feed), a teletype line, a chime and a brief brightening of the contours. This rewards systems discovery without pressure. *S, Obvious.*
5. **Flow overlay with rates** *(built in Milestone 5)*. Animated cyan dashes scaled by throughput, items per minute on buffers, and a small production sparkline in the inspect panel. Without these, bottleneck hunting is guesswork. *M, Obvious.*
6. **Watch mode.** One key hides the HUD and drifts the camera slowly, following a hauler or the scanner sweep, with contours a touch brighter. A lunch-break screensaver that is the game. *S, Obvious.*
7. **Surplus beacon after the win.** An orbital export beacon that turns any surplus into credits or a cosmetic rank, like the AWESOME Sink, plus an escalating standing contract. Later, a creative site with free building. *S-M, Obvious.*
8. **Wear that slows rather than breaks, in calm mode** *(built in Milestone 5)*. Worn structures run slower and their lines jitter; only pressure mode lets them stop. Maintenance drones fly out to repair on their own. Wear becomes a gentle sink for machine parts, not a chore. *M, Obvious given our calm default.*
9. **A gift choice each orbital pass.** Each pass offers a free pick of one of two small gifts (a hauler, a pylon kit, a deep scan, an outpost kit), in the style of Mini Metro and Islanders. Passes become something to look forward to. It needs care around the "no supply drops" win rule. *M, Discuss.*
10. **One-to-one conveyors; roads as a pleasant act** *(built in Milestone 5, except contour-snapped roads and roads that brighten with use)*. Answer the open splitter question with "no": direct feed plus one-to-one conveyors avoids spaghetti. Roads snap to contours and glow brighter with use. *M, Obvious.*
11. **Alert hygiene.** Group alerts by cause ("3 STRUCTURES STARVED: HYDROGEN"), alert only on what needs the player, and never flash red for something the colony fixes itself, such as a stranded rover charging home. *S, Obvious.*
12. **Overclock as a two-way dial** *(built in Milestone 5)*. Allow underclocking (less power, less wear) as well. Tie the hum's pitch and line brightness to the clock speed. *S-M, Obvious.*
13. **Made for interrupted sessions.** Autosave each orbital pass, a "while you were away" summary on resume, and maybe a short 20-minute site variant. *M, Obvious (the short sites are Discuss).*
14. **End-of-run card.** A timelapse of the tracks building up over the run, and private histograms comparing this run with your earlier ones (time, parts per minute, road length), in the style of Opus Magnum. *M, Discuss (scope).*
15. **Automation within five minutes.** Tutorial contracts that each teach one idea (scavengers, then scanner, then mine, then hauler), with free-form orders so players learn ideas, not steps. *M, Discuss (Milestone 7).*

**Recommended next, after Milestone 5:** 1, 2, 4, 6 and 11. All are small, low risk, and each removes stress or adds something to watch. **Bigger conversations:** 3 (the biggest calm payoff), 9 and 14.

## 6. Watch out for

- **Constructors are a bottleneck we chose** (the Dyson Sphere Program warning). If building feels slow, add a second constructor early or speed up assembly; don't make the player wait on middlemen.
- **No splitters, no many-to-many belts**, so there's no spaghetti.
- **Keep the screen quiet.** Every new indicator should replace something or appear only when it matters.
