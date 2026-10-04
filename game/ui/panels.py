"""Inspect panel: what a selected unit or structure is doing, and why."""

import pygame

from game.content import display as D
from game.content import units as U
from game.content.items import ITEMS
from game.render.hershey import draw_text, line_height
from game.sim import units as US

STATE_LABELS = {
    US.IDLE: "IDLE - NOTHING IN RANGE",
    US.TO_DEBRIS: "DRIVING TO DEBRIS",
    US.PICKUP: "PICKING UP",
    US.TO_DOCK: "RETURNING TO LANDER",
    US.UNLOAD: "UNLOADING",
    US.CHARGING: "CHARGING",
    US.STRANDED: "STRANDED - BATTERY EMPTY",
}


def _bar(surface, x, y, frac, color):
    w, h = D.PANEL_BATTERY_BAR
    pygame.draw.rect(surface, D.COLOR_FRAME, (x, y, w, h), 1)
    fill = int((w - 4) * max(0.0, min(1.0, frac)))
    if fill:
        pygame.draw.rect(surface, color, (x + 2, y + 2, fill, h - 4))


def _serial(world, unit):
    """1-based number among units of the same kind, in build order."""
    return 1 + sum(1 for u in world.units.values() if u.kind == unit.kind and u.id < unit.id)


def _unit_lines(world, unit):
    spec = unit.spec
    frac = unit.battery / spec["battery"]
    state = STATE_LABELS.get(unit.state, unit.state.upper())
    if unit.state == US.TO_DOCK:
        if frac < U.LOW_BATTERY_FRACTION:
            state = "LOW BATTERY - RETURNING"
        elif unit.cargo:
            state = "RETURNING WITH CARGO"
    if unit.state == US.UNLOAD and world.lander.stored() >= world.lander.spec["storage"]:
        state = "WAITING - LANDER FULL"
    km = world.heightmap.cell_m / 1000.0
    return [
        (f"{unit.kind.upper()} {_serial(world, unit)}", 2, D.COLOR_TEXT),
        (state, 1, D.COLOR_ALERT if unit.state == US.STRANDED else D.COLOR_TEXT),
        (f"CARGO     SCRAP {unit.cargo}/{spec['cargo']}", 1, D.COLOR_TEXT_DIM),
        (f"BATTERY   {frac * 100:3.0f}%", 1, D.COLOR_TEXT_DIM, ("bar", frac)),
        (f"COLLECTED {unit.collected}", 1, D.COLOR_TEXT_DIM),
        (f"POSITION  {unit.x * km:5.1f}, {unit.y * km:5.1f} KM", 1, D.COLOR_TEXT_DIM),
    ]


def _structure_lines(world, s):
    spec = s.spec
    used = sum(1 for u in s.dock_users if u is not None)
    scrap = s.storage.get("scrap", 0)
    price = ITEMS["scrap"]["sell_price"]
    return [
        (s.kind.upper(), 2, D.COLOR_TEXT),
        (f"STORAGE   {s.stored()}/{spec['storage']}", 1, D.COLOR_TEXT, ("bar", s.stored() / spec["storage"])),
        (f"  SCRAP   {scrap}", 1, D.COLOR_TEXT_DIM),
        (f"DOCKS     {used}/{spec['charge_slots']} IN USE", 1, D.COLOR_TEXT_DIM),
        (f"POWER     +{spec['power_kw']} KW", 1, D.COLOR_TEXT_DIM),
        (f"X  SELL 10 SCRAP  +{10 * price} CR", 1, D.COLOR_FLOW),
        ("SHIFT+X  SELL ALL", 1, D.COLOR_FLOW),
    ]


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
