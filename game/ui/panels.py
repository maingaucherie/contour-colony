"""Inspect panel: what a selected unit or structure is doing, and why."""

import pygame

from game.content import display as D
from game.content import structures as S
from game.content import units as U
from game.content import world as W
from game.content.items import ITEMS
from game.render.hershey import draw_text, line_height
from game.sim import conveyors as CONV
from game.sim import massdriver as MD
from game.sim import production as P
from game.sim import structures as ST
from game.sim import wear
from game.sim import units as US
from game.ui.menus import cost_text

ACTIVITY_LABELS = {
    "idle": "IDLE - NOTHING TO DO IN RANGE",
    "waiting for a dock": "WAITING FOR A FREE DOCK",
    "to_debris": "DRIVING TO DEBRIS",
    "searching": "SEARCHING FOR DEBRIS",
    "pickup": "PICKING UP",
    "to_store": "RETURNING TO UNLOAD",
    "unload": "UNLOADING",
    "to_charge": "GOING TO CHARGE",
    "charging": "CHARGING",
    "to_storage": "FETCHING MATERIALS",
    "load": "LOADING MATERIALS",
    "to_site": "DELIVERING TO SITE",
    "building": "ASSEMBLING",
    "to_teardown": "DRIVING TO DISMANTLE",
    "dismantling": "DISMANTLING",
    "to_survey_spot": "DRIVING TO SURVEY A FIELD",
    "to_frontier": "EXPLORING",
    "surveying": "DETAILED SURVEY",
    "to_order": "FOLLOWING ORDERS",
    "stranded": "STRANDED - SOLAR TRICKLE CHARGING",
    "to_pickup": "DRIVING TO PICK UP",
    "to_dropoff": "DELIVERING",
    "holding cargo - nowhere to take it": "HOLDING CARGO - NOWHERE TO TAKE IT",
    "to_park": "PARKING",
    "fetch_parts": "FETCHING MACHINE PARTS",
    "load_parts": "LOADING PARTS",
    "to_repair": "ON THE WAY TO A REPAIR",
    "repairing": "REPAIRING",
}

STATUS_LABELS = {
    P.WORKING: ("WORKING", D.COLOR_FIELD),
    P.STARVED: ("STARVED - WAITING FOR INPUTS", D.COLOR_ALERT),
    P.BLOCKED: ("BLOCKED - OUTPUT FULL", D.COLOR_ALERT),
    P.UNPOWERED: ("UNPOWERED", D.COLOR_ALERT),
    P.BROKEN: ("BROKEN - NEEDS A REPAIR", D.COLOR_ALERT),
    P.IDLE: ("IDLE", D.COLOR_TEXT_DIM),
}


def _bar(surface, x, y, frac, color):
    w, h = D.PANEL_BATTERY_BAR
    pygame.draw.rect(surface, D.COLOR_FRAME, (x, y, w, h), 1)
    fill = int((w - 4) * max(0.0, min(1.0, frac)))
    if fill:
        pygame.draw.rect(surface, color, (x + 2, y + 2, fill, h - 4))


def _serial(world, unit):
    return 1 + sum(1 for u in world.units.values() if u.kind == unit.kind and u.id < unit.id)


def _unit_lines(world, unit):
    cap = US.capacity(world, unit)
    frac = unit.battery / cap
    state = ACTIVITY_LABELS.get(unit.activity, unit.activity.upper())
    if unit.activity == "to_charge" and frac < U.LOW_BATTERY_FRACTION:
        state = "LOW BATTERY - GOING TO CHARGE"
    if unit.order:
        state = ("SURVEY ORDER" if unit.order[0] == "survey" else "MOVE ORDER") + " - " + state
    cargo = ", ".join(f"{n} {k.upper()}" for k, n in unit.cargo.items()) or "EMPTY"
    km = world.heightmap.cell_m / 1000.0
    lines = [
        (f"{unit.spec['name'].upper()} {_serial(world, unit)}", 2, D.COLOR_TEXT),
        (state, 1, D.COLOR_ALERT if unit.state == US.STRANDED else D.COLOR_TEXT),
    ]
    if unit.spec["cargo"]:
        lines.append((f"CARGO     {cargo}  (MAX {unit.spec['cargo']})", 1, D.COLOR_TEXT_DIM))
    if unit.haul is not None:
        src_id, dst_id, item, amount = unit.haul
        src, dst = world.structures.get(src_id), world.structures.get(dst_id)
        where = (f"{src.spec['name'].upper()} TO " if src else "TO ") + (dst.spec["name"].upper() if dst else "?")
        lines.append((f"HAUL      {amount} {ITEMS[item]['name'].upper()}: {where}", 1, D.COLOR_TEXT_DIM))
    if unit.job is not None and unit.job in world.structures:
        lines.append((f"JOB       {world.structures[unit.job].spec['name'].upper()} SITE", 1, D.COLOR_TEXT_DIM))
    lines.append((f"BATTERY   {frac * 100:3.0f}% OF {cap:.0f}", 1, D.COLOR_TEXT_DIM, ("bar", frac)))
    if unit.kind == "scavenger":
        lines.append((f"COLLECTED {unit.collected}", 1, D.COLOR_TEXT_DIM))
    lines.append((f"POSITION  {unit.x * km:5.1f}, {unit.y * km:5.1f} KM", 1, D.COLOR_TEXT_DIM))
    hint = "RIGHT CLICK: SURVEY HERE" if unit.kind == "survey_rover" else "RIGHT CLICK: GO HERE"
    lines.append((hint, 1, D.COLOR_FLOW))
    return lines


def _structure_lines(world, s):
    spec = s.spec
    lines = [(spec["name"].upper(), 2, D.COLOR_TEXT)]
    if not s.built:
        need = s.materials_needed()
        lines.append((f"UNDER CONSTRUCTION {s.build_progress() * 100:3.0f}%", 1, D.COLOR_TEXT, ("bar", s.build_progress())))
        delivered = ", ".join(f"{s.delivered.get(k, 0)}/{n} {k.upper()}" for k, n in s.build_cost().items())
        if delivered:
            lines.append((f"MATERIALS {delivered}", 1, D.COLOR_TEXT_DIM))
        else:
            lines.append((f"PAID {s.grade_cr} CR, NO MATERIALS: A CONSTRUCTOR GRADES IT", 1, D.COLOR_TEXT_DIM))
        short = [k for k in need if world.stock(k) < need[k] and not s.incoming.get(k)]
        if short:
            lines.append(("WAITING FOR " + ", ".join(k.upper() for k in short) + " IN STORAGE", 1, D.COLOR_ALERT))
        builders = [u for u in world.units.values() if u.kind == "constructor"]
        if not builders:
            lines.append(("NO CONSTRUCTOR ON SITE", 1, D.COLOR_ALERT))
        elif not US.in_charger_range(world, builders[0], s.x, s.y):
            lines.append(("OUT OF ROVER RANGE - BUILD A CHARGING PAD NEARER", 1, D.COLOR_ALERT))
        if s.grade_deg > 0 and delivered:
            lines.append((f"GRADING   {s.grade_deg:.1f} DEG ({s.grade_cr} CR PAID, +{s.build_time() - s.assembly_time():.0f} S)",
                          1, D.COLOR_TEXT_DIM))
        lines.append(("DEL: CANCEL (REFUNDS " + ("MATERIALS)" if delivered else "CREDITS)"), 1, D.COLOR_FLOW))
        return lines

    if s.deconstruct:
        frac = s.teardown_progress()
        lines.append(("MARKED FOR DECONSTRUCTION" + (f" {frac * 100:3.0f}%" if frac else ""), 1, D.COLOR_ALERT))
        lines.append(("DEL: KEEP IT", 1, D.COLOR_FLOW))
    elif s.kind != "lander":
        refund = int(S.DECONSTRUCT_REFUND * 100)
        lines.append((f"DEL: DECONSTRUCT ({refund}% OF MATERIALS BACK)", 1, D.COLOR_FLOW))
    grid = world.power_grids.get(s.grid)
    if spec.get("power_kw"):
        lines.append((f"OUTPUT    +{s.output_kw:.1f} KW", 1, D.COLOR_TEXT_DIM))
    if spec.get("generates_kw"):
        lines.append((f"OUTPUT    +{s.output_kw:.1f} KW (UP TO {spec['generates_kw'] * s.cooling:.0f} WHILE FUELLED)",
                      1, D.COLOR_TEXT_DIM))
        need = spec.get("cooling_radiators", 0)
        if need:
            n = ST.radiators_near(world, s)
            lines.append((f"RADIATORS {min(n, need)}/{need}  COOLING {s.cooling * 100:.0f}%", 1,
                          D.COLOR_TEXT_DIM if n >= need else D.COLOR_ALERT))
    if spec.get("draw_kw"):
        state = "POWERED" if s.powered else ("NO GRID - BUILD A PYLON" if s.grid == -1 else "UNPOWERED - GRID OVERLOADED")
        lines.append((f"DRAW      {s.draw_kw():.1f} KW  {state}", 1, D.COLOR_TEXT_DIM if s.powered else D.COLOR_ALERT))
        lines.append((f"PRIORITY  {s.priority.upper()}  (P TO CHANGE)", 1, D.COLOR_FLOW))
    if grid:
        lines.append((f"GRID      {grid['supply']:.1f} KW SUPPLY  {grid['demand']:.1f} KW DEMAND", 1, D.COLOR_TEXT_DIM))
    if spec.get("storage"):
        lines.append((f"STORAGE   {s.stored()}/{spec['storage']}   COLONY {world.stored_total()}/{world.capacity()}",
                      1, D.COLOR_TEXT, ("bar", s.stored() / spec["storage"])))
        held = [f"{ITEMS[k]['name'].upper()} {n}" for k, n in sorted(s.storage.items())]
        for i in range(0, len(held), 3):
            lines.append(("  " + "   ".join(held[i:i + 3]), 1, D.COLOR_TEXT_DIM))
        capped = [ITEMS[k]["name"].upper() for k in sorted(ITEMS)
                  if k != "scrap" and world.stock(k) >= world.item_cap(k)]   # surplus scrap sells itself
        if capped:
            lines.append(("AT COLONY CAP: " + ", ".join(capped), 1, D.COLOR_ALERT))
        lines.append((f"EACH GOOD: UP TO {int(W.ITEM_CAP_FRACTION * 100)}% OF COLONY STORAGE", 1, D.COLOR_TEXT_DIM))
    if s.docks:
        used = sum(1 for u in s.dock_users if u is not None)
        what = "CHARGING DOCKS" if spec.get("charge_slots") else "UNLOADING DOCKS"
        lines.append((f"{what} {used}/{len(s.docks)} IN USE", 1, D.COLOR_TEXT_DIM))
    if s.kind == MD.KIND:
        lines.append((f"PRIORITY  {s.priority.upper()}  (P: HIGH TAKES GOODS FIRST, LOW LEAVES THEM FOR PRODUCTION)",
                      1, D.COLOR_FLOW))
        lines.extend(_mass_driver_lines(world, s))
    if s.spec.get("carries"):
        lines.extend(_conveyor_lines(world, s))
    if s.kind == "road":
        lines.append((f"LENGTH    {s.length:.1f} CELLS", 1, D.COLOR_TEXT_DIM))
        lines.append((f"ROVERS DRIVE {U.ROAD_SPEED_MULT:.0f}X FASTER ON IT, ON LESS BATTERY,", 1, D.COLOR_TEXT_DIM))
        lines.append(("AND CAN CLIMB GROUND TOO STEEP TO DRIVE OFF-ROAD", 1, D.COLOR_TEXT_DIM))
    lines.extend(_belts_of(world, s))
    r = P.recipe(s)
    if r:
        lines.extend(_production_lines(world, s, r))
        over = world.research.effect("overclock", False)
        lines.append((f"CLOCK     {s.clock * 100:.0f}%   (J: 50 / 100" + (" / 150%)" if over else "%)"), 1, D.COLOR_FLOW))
    if s.kind == "scanner":
        lines.append((f"RADAR     {spec['scan_radius_cells'] * world.heightmap.cell_m / 1000:.0f} KM RANGE, "
                      f"SWEEP EVERY {spec['sweep_period_s']:.0f} S", 1, D.COLOR_TEXT_DIM))
        lines.append((f"REVEALS DEBRIS; FLAGS FIELDS AFTER {W.FIELD_SIGNAL_PASSES} SWEEPS", 1, D.COLOR_TEXT_DIM))
    if s.kind == "lander":
        lines.append(("EXPORT BAY: CONTRACT GOODS SHIP FROM HERE", 1, D.COLOR_TEXT_DIM))
        if world.storage_full:
            lines.append(("STORAGE FULL - BUILD A DEPOT", 1, D.COLOR_ALERT))
        price = world.price("scrap")
        lines.append((f"X  SELL {D.SELL_BATCH} SCRAP FOR {D.SELL_BATCH * price} CR", 1, D.COLOR_FLOW))
        lines.append(("SHIFT+X  ALL SCRAP    O: SELL OTHER GOODS", 1, D.COLOR_FLOW))
    if s.kind == "rover_bay":
        if s.building_unit:
            total = U.UNITS[s.building_unit]["bay_time_s"] * world.tick_rate
            frac = 1 - s.bay_ticks_left / total
            lines.append((f"BUILDING  {U.UNITS[s.building_unit]['name'].upper()}" + ("" if s.powered else " (PAUSED)"),
                          1, D.COLOR_TEXT, ("bar", frac)))
        if s.queue:
            lines.append(("QUEUE     " + ", ".join(U.UNITS[k]["name"].upper() for k in s.queue), 1, D.COLOR_TEXT_DIM))
        for i, kind in enumerate(U.BAY_MENU):
            spec_u = U.UNITS[kind]
            if world.unlocked(kind):
                lines.append((f"{i + 1}  {spec_u['name'].upper()}: {cost_text(spec_u['bay_cost'])}", 1, D.COLOR_FLOW))
    return lines


def _mass_driver_lines(world, s):
    out = []
    phases = MD.phases(s)
    ph = MD.current(s)
    for i, p in enumerate(phases):
        mark = "DONE" if i < s.phase else ("NOW" if i == s.phase else "")
        out.append((f"PHASE {i + 1}  {p['name'].upper():12s} {mark}", 1, D.COLOR_TEXT if i == s.phase else D.COLOR_TEXT_DIM))
    if ph is not None:
        out.append((f"DELIVERING FOR {ph['name'].upper()}", 1, D.COLOR_TEXT, ("bar", MD.progress(s))))
        for k, n in ph["needs"].items():
            got = min(s.inputs.get(k, 0), n)
            out.append((f"  {ITEMS[k]['name'].upper():14s} {got:4d}/{n}", 1,
                        D.COLOR_FLOW if got >= n else D.COLOR_TEXT_DIM))
        out.append(("HAULERS AND CONVEYORS DELIVER; EACH PHASE OPENS RESEARCH", 1, D.COLOR_TEXT_DIM))
    else:
        state = "FIRED" if s.status == MD.FIRED else ("CHARGING" if s.powered else "WAITING FOR POWER")
        out.append((f"LAUNCH    {state}  {s.spec['launch_kw']:.0f} KW FOR {s.spec['launch_charge_s']:.0f} S", 1,
                    D.COLOR_TEXT, ("bar", MD.progress(s))))
    return out


def _conveyor_lines(world, c):
    a, b = world.structures.get(c.src), world.structures.get(c.dst)
    if a is None or b is None:
        return []
    kinds = CONV.items_for(a.kind, b.kind, c.kind)
    carries = "EVERYTHING STORED" if len(kinds) > 6 else ", ".join(ITEMS[k]["name"].upper() for k in kinds)
    state = {P.WORKING: "MOVING", P.UNPOWERED: "UNPOWERED"}.get(c.status, "WAITING")
    if state == "WAITING":
        if not (a.built and b.built):
            state = "WAITING FOR " + (a if not a.built else b).spec["name"].upper()
        else:
            state = "WAITING: NOTHING TO SEND OR NO ROOM"
    return [
        (f"FROM {a.spec['name'].upper()} TO {b.spec['name'].upper()}", 1, D.COLOR_TEXT),
        (f"CARRIES   {carries}", 1, D.COLOR_TEXT_DIM),
        (f"LENGTH    {c.length:.1f} CELLS   {c.spec['items_per_s']:.0f} ITEM/S", 1, D.COLOR_TEXT_DIM),
        (f"STATUS    {state}   MOVED {c.moved}", 1, D.COLOR_FLOW if c.status == P.WORKING else D.COLOR_TEXT_DIM),
    ]


def _belts_of(world, s):
    """Lines for the conveyors that start or end at a building."""
    out = []
    for c in CONV.attached(world, s):
        other = world.structures.get(c.dst if c.src == s.id else c.src)
        if other is None:
            continue
        verb = "CONVEYOR TO" if c.src == s.id else "CONVEYOR FROM"
        state = "" if c.built else " (BEING BUILT)"
        out.append((f"{verb} {other.spec['name'].upper()}{state}", 1, D.COLOR_FLOW))
    return out


def _amounts(d):
    return " + ".join(f"{n} {ITEMS[k]['name'].upper()}" for k, n in d.items()) or "NOTHING"


def _wear_lines(world, s):
    if not s.spec.get("wear_per_cycle"):
        return []
    lines = []
    text = f"WEAR      {s.wear * 100:.0f}%"
    if wear.speed_factor(s) < 1.0:
        text += f"  (RUNNING AT {wear.speed_factor(s) * 100:.0f}%)"
    lines.append((text, 1, D.COLOR_ALERT if s.wear >= 0.75 else D.COLOR_TEXT_DIM, ("bar", s.wear)))
    if wear.needs_repair(s):
        who = world.units.get(s.repairer)
        if who is not None:
            note = f"BEING REPAIRED BY {who.spec['name'].upper()}"
        elif world.stock("parts") <= 0:
            note = f"REPAIR NEEDS {wear.parts_needed(s)} MACHINE PARTS - NONE IN STORAGE"
        else:
            note = f"REPAIR QUEUED ({wear.parts_needed(s)} MACHINE PARTS)"
        lines.append((note, 1, D.COLOR_POWER))
    return lines


def _speed_lines(world, s):
    """Why this building runs at the speed it does: one line per rule."""
    spec, lines = s.spec, []
    if spec.get("requires_field"):
        f = P.field_of(world, s)
        if f is not None:
            left = f.reserves_left()
            lines.append((f"FIELD     RICHNESS {f.richness:.1f}X, RESERVES {left * 100:.0f}%"
                          + ("  (DEPLETED: TRY A FRESH FIELD)" if left <= 0 else ""), 1,
                          D.COLOR_ALERT if left < 0.2 else D.COLOR_TEXT_DIM))
    if "sun_speed" in spec:
        light = world.illumination_at(s.x, s.y)
        lines.append((f"SUNLIGHT  {light * 100:.0f}%  (SOLAR KILN: FASTER IN SUN)", 1, D.COLOR_TEXT_DIM))
    if "heat" in spec:
        cold = s.heat < 0.999
        lines.append((f"HEAT      {s.heat * 100:.0f}%" + ("  WARMING UP - KEEP IT FED" if cold else "  AT TEMPERATURE"), 1,
                      D.COLOR_POWER if cold else D.COLOR_TEXT_DIM, ("bar", s.heat)))
    if "waste_heat" in spec:
        if s.warm:
            lines.append((f"WARMED BY A NEIGHBOUR: {spec['waste_heat']['speed']:.0f}X SPEED", 1, D.COLOR_FLOW))
        else:
            lines.append((f"BESIDE A WORKING KILN OR FURNACE: {spec['waste_heat']['speed']:.0f}X SPEED", 1,
                          D.COLOR_TEXT_DIM))
    return lines


def _production_lines(world, s, r):
    label, color = STATUS_LABELS.get(s.status, (s.status.upper(), D.COLOR_TEXT))
    if s.status == P.STARVED:
        short = [ITEMS[k]["name"].upper() for k, n in r["in"].items() if s.inputs.get(k, 0) < n]
        label = "STARVED - NEEDS " + ", ".join(short)
    out = [
        (f"RECIPE    {_amounts(r['in'])} > {_amounts(r['out'])}" if r["in"] else f"RECIPE    DIGS {_amounts(r['out'])}",
         1, D.COLOR_TEXT_DIM),
        (f"          EVERY {P.cycle_time(world, s):.1f} S  (SPEED {P.speed(world, s):.2f}X)", 1, D.COLOR_TEXT_DIM),
        (f"STATUS    {label}", 1, color, ("bar", P.progress(s))),
    ]
    if s.id in world.rates:
        made = ", ".join(f"{world.rates[s.id] * n:.0f} {ITEMS[k]['name'].upper()}" for k, n in r["out"].items())
        out.append((f"LATELY    {made} PER MINUTE", 1, D.COLOR_TEXT_DIM))
    out.extend(_speed_lines(world, s))
    out.extend(_wear_lines(world, s))
    for k, n in r["in"].items():
        cap = P.input_cap(s, k)
        out.append((f"  IN   {ITEMS[k]['name'].upper()}  {s.inputs.get(k, 0)}/{cap}", 1, D.COLOR_TEXT_DIM))
    for k in r["out"]:
        cap = P.output_cap(s, k)
        out.append((f"  OUT  {ITEMS[k]['name'].upper()}  {s.outputs.get(k, 0)}/{cap}", 1, D.COLOR_TEXT_DIM))
    out.append((f"CYCLES    {s.cycles}" + (f"   VENTED {s.vented}" if s.vented else "")
                + (f"   FED DIRECTLY {s.fed}" if s.fed else ""), 1, D.COLOR_TEXT_DIM))
    links = [(a, b, k) for a, b, k in world.feed_links() if s in (a, b)]
    for a, b, k in links:
        other = b if a is s else a
        verb = "FEEDS" if a is s else "FED BY"
        out.append((f"{verb}  {other.spec['name'].upper()} ({ITEMS[k]['name'].upper()}), NO HAULER NEEDED", 1,
                    D.COLOR_FLOW))
    if s.status == P.BLOCKED:
        capped = [ITEMS[k]["name"].upper() for k in r["out"] if world.stock(k) >= world.item_cap(k)]
        waste = [k for k in r["out"] if ITEMS[k]["tier"] == "waste" and s.outputs.get(k, 0) >= P.output_cap(s, k)
                 and not any(o.stores() and o.accepts(k) for o in world.structures.values())]
        if waste:
            out.append((", ".join(ITEMS[k]["name"].upper() for k in waste) + " HAS NOWHERE TO GO: BUILD A SLAG HEAP",
                        1, D.COLOR_ALERT))
        elif capped:
            out.append((", ".join(capped) + " AT COLONY CAP: USE OR SELL (O)", 1, D.COLOR_ALERT))
        elif world.storage_full:
            out.append(("STORAGE FULL - BUILD A DEPOT OR SELL (O)", 1, D.COLOR_ALERT))
        else:
            out.append(("WAITING FOR A HAULER", 1, D.COLOR_ALERT))
    vents = [ITEMS[k]["name"].upper() for k in r["out"] if ITEMS[k].get("vents")]
    if vents:
        out.append((", ".join(vents) + " VENTED WHEN ITS OUTPUT IS FULL", 1, D.COLOR_TEXT_DIM))
    if not any(u.kind == "hauler" for u in world.units.values()):
        out.append(("NO HAULERS: RESEARCH LOGISTICS I, BUILD AT A ROVER BAY", 1, D.COLOR_ALERT))
    return out


def draw_inspect(surface, world, selected, top):
    """Draw the panel for the selection, right-aligned, starting at y = top."""
    if selected is None:
        return
    kind, eid = selected
    if kind == "unit" and eid in world.units:
        lines = _unit_lines(world, world.units[eid])
    elif kind == "structure" and eid in world.structures:
        lines = _structure_lines(world, world.structures[eid])
    else:
        return
    w = surface.get_width()
    pad = 8
    x = w - D.HUD_MARGIN - 6 - D.PANEL_WIDTH
    heights = [line_height(line[1]) + 4 + (D.PANEL_BATTERY_BAR[1] + 4 if len(line) > 3 else 0) for line in lines]
    rect = pygame.Rect(x - pad, top, D.PANEL_WIDTH + 2 * pad, sum(heights) + 2 * pad)
    surface.fill(D.COLOR_BACKGROUND, rect)
    pygame.draw.rect(surface, D.COLOR_FRAME, rect, 1)
    y = top + pad
    for line, hgt in zip(lines, heights):
        draw_text(surface, line[0], (x, y), line[1], line[2])
        if len(line) > 3:
            _bar(surface, x, y + line_height(line[1]) + 3, line[3][1], D.COLOR_FLOW)
        y += hgt
