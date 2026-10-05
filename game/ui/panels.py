"""Inspect panel: what a selected unit or structure is doing, and why."""

import pygame

from game.content import display as D
from game.content import units as U
from game.content.items import ITEMS
from game.render.hershey import draw_text, line_height
from game.sim import units as US
from game.ui.menus import cost_text

ACTIVITY_LABELS = {
    "idle": "IDLE - NOTHING TO DO IN RANGE",
    "waiting for a dock": "WAITING FOR A FREE DOCK",
    "to_debris": "DRIVING TO DEBRIS",
    "pickup": "PICKING UP",
    "to_store": "RETURNING TO UNLOAD",
    "unload": "UNLOADING",
    "to_charge": "GOING TO CHARGE",
    "charging": "CHARGING",
    "to_storage": "FETCHING MATERIALS",
    "load": "LOADING MATERIALS",
    "to_site": "DELIVERING TO SITE",
    "building": "ASSEMBLING",
    "to_survey_spot": "DRIVING TO SURVEY A FIELD",
    "to_frontier": "EXPLORING",
    "surveying": "DETAILED SURVEY",
    "to_order": "FOLLOWING ORDERS",
    "stranded": "STRANDED - BATTERY EMPTY",
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
        if not any(u.kind == "constructor" for u in world.units.values()):
            lines.append(("NO CONSTRUCTOR ON SITE", 1, D.COLOR_ALERT))
        lines.append(("DEL: CANCEL (REFUNDS MATERIALS)", 1, D.COLOR_FLOW))
        return lines

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
        for k, n in sorted(s.storage.items()):
            lines.append((f"  {k.upper():8s}{n}", 1, D.COLOR_TEXT_DIM))
    if s.docks:
        used = sum(1 for u in s.dock_users if u is not None)
        what = "CHARGING DOCKS" if spec.get("charge_slots") else "UNLOADING DOCKS"
        lines.append((f"{what} {used}/{len(s.docks)} IN USE", 1, D.COLOR_TEXT_DIM))
    if s.kind == "lander":
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
