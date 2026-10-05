"""Inspect panel: what a selected unit or structure is doing, and why."""

import pygame

from game.content import display as D
from game.content import structures as S
from game.content import units as U
from game.content import world as W
from game.content.items import ITEMS
from game.render.hershey import draw_text, line_height
from game.sim import production as P
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
    "stranded": "STRANDED - BATTERY EMPTY",
    "to_pickup": "DRIVING TO PICK UP",
    "to_dropoff": "DELIVERING",
    "holding cargo - nowhere to take it": "HOLDING CARGO - NOWHERE TO TAKE IT",
    "to_park": "PARKING",
}

STATUS_LABELS = {
    P.WORKING: ("WORKING", D.COLOR_FIELD),
    P.STARVED: ("STARVED - WAITING FOR INPUTS", D.COLOR_ALERT),
    P.BLOCKED: ("BLOCKED - OUTPUT FULL", D.COLOR_ALERT),
    P.UNPOWERED: ("UNPOWERED", D.COLOR_ALERT),
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
        delivered = ", ".join(f"{s.delivered.get(k, 0)}/{n} {k.upper()}" for k, n in spec["build_cost"].items())
        lines.append((f"MATERIALS {delivered}", 1, D.COLOR_TEXT_DIM))
        short = [k for k in need if world.stock(k) < need[k] and not s.incoming.get(k)]
        if short:
            lines.append(("WAITING FOR " + ", ".join(k.upper() for k in short) + " IN STORAGE", 1, D.COLOR_ALERT))
        builders = [u for u in world.units.values() if u.kind == "constructor"]
        if not builders:
            lines.append(("NO CONSTRUCTOR ON SITE", 1, D.COLOR_ALERT))
        elif not US.in_charger_range(world, builders[0], s.x, s.y):
            lines.append(("OUT OF ROVER RANGE - BUILD A CHARGING PAD NEARER", 1, D.COLOR_ALERT))
        lines.append(("DEL: CANCEL (REFUNDS MATERIALS)", 1, D.COLOR_FLOW))
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
    if spec.get("draw_kw"):
        state = "POWERED" if s.powered else ("NO GRID - BUILD A PYLON" if s.grid == -1 else "UNPOWERED - GRID OVERLOADED")
        lines.append((f"DRAW      {spec['draw_kw']:.1f} KW  {state}", 1, D.COLOR_TEXT_DIM if s.powered else D.COLOR_ALERT))
        lines.append((f"PRIORITY  {s.priority.upper()}  (P TO CHANGE)", 1, D.COLOR_FLOW))
    if grid:
        lines.append((f"GRID      {grid['supply']:.1f} KW SUPPLY  {grid['demand']:.1f} KW DEMAND", 1, D.COLOR_TEXT_DIM))
    if spec.get("storage"):
        lines.append((f"STORAGE   {s.stored()}/{spec['storage']}", 1, D.COLOR_TEXT, ("bar", s.stored() / spec["storage"])))
        held = [f"{ITEMS[k]['name'].upper()} {n}" for k, n in sorted(s.storage.items())]
        for i in range(0, len(held), 3):
            lines.append(("  " + "   ".join(held[i:i + 3]), 1, D.COLOR_TEXT_DIM))
    if s.docks:
        used = sum(1 for u in s.dock_users if u is not None)
        what = "CHARGING DOCKS" if spec.get("charge_slots") else "UNLOADING DOCKS"
        lines.append((f"{what} {used}/{len(s.docks)} IN USE", 1, D.COLOR_TEXT_DIM))
    r = P.recipe(s)
    if r:
        lines.extend(_production_lines(world, s, r))
    if s.kind == "scanner":
        lines.append((f"RADAR     {spec['scan_radius_cells'] * world.heightmap.cell_m / 1000:.0f} KM RANGE, "
                      f"SWEEP EVERY {spec['sweep_period_s']:.0f} S", 1, D.COLOR_TEXT_DIM))
        lines.append((f"REVEALS DEBRIS; FLAGS FIELDS AFTER {W.FIELD_SIGNAL_PASSES} SWEEPS", 1, D.COLOR_TEXT_DIM))
    if s.kind == "lander":
        lines.append(("EXPORT BAY: CONTRACT GOODS SHIP FROM HERE", 1, D.COLOR_TEXT_DIM))
        if world.storage_full:
            lines.append(("STORAGE FULL - BUILD A DEPOT", 1, D.COLOR_ALERT))
        price = ITEMS["scrap"]["sell_price"]
        lines.append((f"X  SELL {D.SELL_BATCH} SCRAP FOR {D.SELL_BATCH * price} CR", 1, D.COLOR_FLOW))
        lines.append(("SHIFT+X  SELL ALL SCRAP", 1, D.COLOR_FLOW))
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


def _amounts(d):
    return " + ".join(f"{n} {ITEMS[k]['name'].upper()}" for k, n in d.items()) or "NOTHING"


def _production_lines(world, s, r):
    label, color = STATUS_LABELS.get(s.status, (s.status.upper(), D.COLOR_TEXT))
    if s.status == P.STARVED:
        short = [ITEMS[k]["name"].upper() for k, n in r["in"].items() if s.inputs.get(k, 0) < n]
        label = "STARVED - NEEDS " + ", ".join(short)
    out = [
        (f"RECIPE    {_amounts(r['in'])} > {_amounts(r['out'])}", 1, D.COLOR_TEXT_DIM),
        (f"          EVERY {P.cycle_time(s):.1f} S" + (f"  (FIELD RICHNESS {s.richness:.1f}X)"
                                                        if s.spec.get("requires_field") else ""), 1, D.COLOR_TEXT_DIM),
        (f"STATUS    {label}", 1, color, ("bar", P.progress(s))),
    ]
    for k, n in r["in"].items():
        cap = P.input_cap(s, k)
        out.append((f"  IN   {ITEMS[k]['name'].upper()}  {s.inputs.get(k, 0)}/{cap}", 1, D.COLOR_TEXT_DIM))
    for k in r["out"]:
        cap = P.output_cap(s, k)
        out.append((f"  OUT  {ITEMS[k]['name'].upper()}  {s.outputs.get(k, 0)}/{cap}", 1, D.COLOR_TEXT_DIM))
    out.append((f"CYCLES    {s.cycles}", 1, D.COLOR_TEXT_DIM))
    if s.status == P.BLOCKED and world.storage_full:
        out.append(("STORAGE FULL - BUILD A DEPOT OR USE THE OUTPUT", 1, D.COLOR_ALERT))
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
