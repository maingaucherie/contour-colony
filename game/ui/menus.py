"""Keyboard-driven panels: build menu and research."""

import pygame

from game.content import display as D
from game.content.research import RESEARCH, RESEARCH_MENU
from game.content.structures import BUILD_MENU, STRUCTURES
from game.render.hershey import draw_text, line_height

BUILD_KEYS = "1234567890"
RESEARCH_KEYS = "ABCDEFGHIJKLMN"


def cost_text(cost):
    return "  ".join(f"{n} {k.upper()}" for k, n in cost.items())


def _panel(surface, x, y, w, lines, title):
    lh = D.HUD_LINE_HEIGHT
    h = line_height(2) + 10 + lh * len(lines) + 12
    rect = pygame.Rect(x, y, w, h)
    surface.fill(D.COLOR_BACKGROUND, rect)
    pygame.draw.rect(surface, D.COLOR_FRAME, rect, 1)
    draw_text(surface, title, (x + 10, y + 6), 2)
    ty = y + line_height(2) + 12
    for text, color in lines:
        # A line is plain text or columns [(x offset, text), ...]: the font is proportional,
        # so spaces can't line columns up.
        for dx, part in ([(0, text)] if isinstance(text, str) else text):
            draw_text(surface, part, (x + 10 + dx, ty), 1, color)
        ty += lh
    return rect


def build_entries(world):
    out = []
    for key, kind in zip(BUILD_KEYS, BUILD_MENU):
        spec = STRUCTURES[kind]
        out.append((key, kind, spec, world.unlocked(kind)))
    return out


def draw_build_menu(surface, world, x, y):
    lines = []
    for key, kind, spec, unlocked in build_entries(world):
        cost = cost_text(spec["build_cost"])
        c1, c2 = D.MENU_COLUMNS
        if unlocked:
            short = [k for k, n in spec["build_cost"].items() if world.stock(k) < n]
            note = "  SHORT OF " + ", ".join(s.upper() for s in short) if short else ""
            lines.append(([(0, key), (c1, spec["name"].upper()), (c2, cost + note)],
                          D.COLOR_TEXT if not short else D.COLOR_TEXT_DIM))
        else:
            need = RESEARCH[spec["unlocked_by"]]["name"].upper()
            lines.append(([(0, key), (c1, spec["name"].upper()), (c2, "RESEARCH " + need)], D.COLOR_TEXT_DIM))
    lines.append(("", D.COLOR_TEXT_DIM))
    lines.append(("NUMBER: PLACE   ESC/B: CLOSE", D.COLOR_TEXT_DIM))
    return _panel(surface, x, y, D.MENU_WIDTH, lines, "BUILD")


def build_key(world, key):
    """Structure kind for a pressed key, if it is unlocked."""
    for k, kind, spec, unlocked in build_entries(world):
        if k == key and unlocked:
            return kind
    return None


def draw_research(surface, world):
    r = world.research
    lines = []
    for key, node in zip(RESEARCH_KEYS, RESEARCH_MENU):
        spec = RESEARCH[node]
        status = r.status(node)
        if status == "done":
            text, color = "DONE", D.COLOR_TEXT_DIM
        elif status == "active":
            secs = r.ticks_left / world.tick_rate
            text, color = f"RESEARCHING {r.progress() * 100:3.0f}%  {secs:3.0f} S LEFT", D.COLOR_FLOW
        elif status == "available":
            text = f"{spec['cost']:4d} CR  {spec['time_s']:3d} S"
            color = D.COLOR_TEXT if world.credits >= spec["cost"] and r.current is None else D.COLOR_TEXT_DIM
        else:
            need = ", ".join(RESEARCH[p]["name"].upper() for p in spec["requires"] if p not in r.done)
            text, color = f"NEEDS {need}", D.COLOR_TEXT_DIM
        c1, c2, c3 = D.RESEARCH_COLUMNS
        lines.append(([(0, key), (c1, spec["name"].upper()), (c2, text), (c3, _effect_text(spec))], color))
    lines.append(("", D.COLOR_TEXT_DIM))
    lines.append((f"CREDITS {world.credits}     LETTER: START   ESC/R: CLOSE", D.COLOR_TEXT_DIM))
    w = D.RESEARCH_WIDTH
    x = (surface.get_width() - w) // 2
    return _panel(surface, x, D.RESEARCH_TOP, w, lines, "RESEARCH")


def _effect_text(spec):
    if spec.get("unlocks"):
        names = [STRUCTURES[k]["name"] if k in STRUCTURES else k.replace("_", " ") for k in spec["unlocks"]]
        return ", ".join(n.upper() for n in names)
    eff = spec.get("effects", {})
    if "battery_mult" in eff:
        return f"UNIT BATTERY +{(eff['battery_mult'] - 1) * 100:.0f}%"
    if "linger_mult" in eff:
        return "FASTER DETAILED SURVEY, RICHNESS AT LEVEL 1"
    if "wear_mult" in eff:
        return f"WEAR -{(1 - eff['wear_mult']) * 100:.0f}%"
    if "overclock" in eff:
        return "OVERCLOCK STRUCTURES"
    return ""


def research_key(key):
    if key in RESEARCH_KEYS:
        i = RESEARCH_KEYS.index(key)
        if i < len(RESEARCH_MENU):
            return RESEARCH_MENU[i]
    return None
