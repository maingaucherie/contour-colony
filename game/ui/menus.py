"""Keyboard-driven panels: build menu and research."""

import pygame

from game.content import display as D
from game.content.research import RESEARCH, RESEARCH_MENU
from game.content.structures import BUILD_CATEGORIES, STRUCTURES
from game.content.items import ITEMS
from game.render.hershey import draw_text, line_height, text_width
from game.sim import stats

BUILD_KEYS = "1234567890"


def cost_text(cost):
    return "  ".join(f"{n} {k.upper()}" for k, n in cost.items())


def _panel(surface, x, y, w, lines, title, cursor=None, selectable=0):
    """Draw a framed panel. The first `selectable` lines are menu rows; the row at
    `cursor` is highlighted. Returns (panel rect, [row rects])."""
    lh = D.HUD_LINE_HEIGHT
    h = line_height(2) + 10 + lh * len(lines) + 12
    rect = pygame.Rect(x, y, w, h)
    surface.fill(D.COLOR_BACKGROUND, rect)
    pygame.draw.rect(surface, D.COLOR_FRAME, rect, 1)
    draw_text(surface, title, (x + 10, y + 6), 2)
    ty = y + line_height(2) + 12
    rows = []
    for i, (text, color) in enumerate(lines):
        row = pygame.Rect(x + 4, ty, w - 8, lh)  # capitals sit centred on ty + 7
        if i < selectable:
            rows.append(row)
            if i == cursor:
                pygame.draw.rect(surface, D.COLOR_MENU_CURSOR, row)
                pygame.draw.rect(surface, D.COLOR_FLOW, row, 1)
        # A line is plain text or columns [(x offset, text), ...]: the font is proportional,
        # so spaces can't line columns up.
        for dx, part in ([(0, text)] if isinstance(text, str) else text):
            draw_text(surface, part, (x + 10 + dx, ty), 1, color, additive=True)
        ty += lh
    return rect, rows


def build_entries(world, tab=0):
    """The structures in one build category, each with a number key."""
    out = []
    for i, kind in enumerate(BUILD_CATEGORIES[tab][1]):
        key = BUILD_KEYS[i] if i < len(BUILD_KEYS) else " "
        spec = STRUCTURES[kind]
        out.append((key, kind, spec, world.unlocked(kind)))
    return out


def draw_build_menu(surface, world, x, y, cursor=None, tab=0):
    """The build panel: category tabs on top, then that category's structures.
    Returns (panel rect, [row rects], [(tab rect, tab index)])."""
    lines = [("", D.COLOR_TEXT)]   # room for the tabs, drawn below
    for key, kind, spec, unlocked in build_entries(world, tab):
        if "credits_per_cell" in spec:
            cost = f"{spec['credits_per_cell']} CR PER CELL + GRADING"
        elif "cost_per_cell" in spec:
            cost = cost_text(spec["cost_per_cell"]) + " PER CELL"
        else:
            cost = cost_text(spec["build_cost"])
        c1, c2 = D.MENU_COLUMNS
        if unlocked:
            short = [k for k, n in spec.get("cost_per_cell", spec.get("build_cost", {})).items()
                     if world.stock(k) < n]
            note = "  SHORT OF " + ", ".join(s.upper() for s in short) if short else ""
            lines.append(([(0, key), (c1, spec["name"].upper()), (c2, cost + note)],
                          D.COLOR_TEXT if not short else D.COLOR_TEXT_DIM))
        else:
            need = RESEARCH[spec["unlocked_by"]]["name"].upper()
            lines.append(([(0, key), (c1, spec["name"].upper()), (c2, "RESEARCH " + need)], D.COLOR_TEXT_DIM))
    lines.append(("", D.COLOR_TEXT_DIM))
    lines.append(("LEFT/RIGHT: CATEGORY   UP/DOWN + ENTER, CLICK OR A NUMBER   ESC: CLOSE", D.COLOR_TEXT_DIM))
    rows_n = len(lines) - 2
    rect, rows = _panel(surface, x, y, D.MENU_WIDTH, lines, "BUILD", None if cursor is None else cursor + 1, rows_n)
    tabs = []
    tx, ty = x + 10, rows[0].y
    for i, (name, _) in enumerate(BUILD_CATEGORIES):
        label = name.upper()
        w = text_width(label) + 12
        r = pygame.Rect(tx - 4, ty, w, rows[0].height)
        if i == tab:
            pygame.draw.rect(surface, D.COLOR_MENU_CURSOR, r)
            pygame.draw.rect(surface, D.COLOR_FLOW, r, 1)
        draw_text(surface, label, (tx + 2, ty), 1, D.COLOR_TEXT if i == tab else D.COLOR_TEXT_DIM, additive=True)
        tabs.append((r, i))
        tx += w + 6
    return rect, rows[1:], tabs


def build_key(world, key, tab=0):
    """Structure kind for a pressed key, if it is unlocked."""
    for k, kind, spec, unlocked in build_entries(world, tab):
        if k == key and unlocked:
            return kind
    return None


def draw_research(surface, world, cursor=None):
    r = world.research
    lines = []
    for node in RESEARCH_MENU:
        spec = RESEARCH[node]
        status = r.status(node)
        if status == "done":
            text, color = "DONE", D.COLOR_TEXT_DIM
        elif status == "active":
            secs = r.ticks_left / world.tick_rate
            text, color = f"ACTIVE {r.progress() * 100:3.0f}%  {secs:3.0f} S", D.COLOR_FLOW
        elif status == "available":
            text = f"{spec['cost']:4d} CR  {spec['time_s']:3d} S"
            color = D.COLOR_TEXT if world.credits >= spec["cost"] and r.current is None else D.COLOR_TEXT_DIM
        elif status == "waiting":
            text, color = f"AFTER MASS DRIVER PHASE {spec['phase']}", D.COLOR_TEXT_DIM
        else:
            need = ", ".join(RESEARCH[p]["name"].upper() for p in spec["requires"] if p not in r.done)
            text, color = f"NEEDS {need}", D.COLOR_TEXT_DIM
        c1, c2, c3 = D.RESEARCH_COLUMNS
        lines.append(([(c1, spec["name"].upper()), (c2, text), (c3, _effect_text(spec))], color))
    n = len(lines)
    lines.append(("", D.COLOR_TEXT_DIM))
    lines.append((f"CREDITS {world.credits}     UP/DOWN + ENTER OR CLICK: START   ESC: CLOSE", D.COLOR_TEXT_DIM))
    w = D.RESEARCH_WIDTH
    x = (surface.get_width() - w) // 2
    return _panel(surface, x, D.RESEARCH_TOP, w, lines, "RESEARCH", cursor, n)


def draw_production(surface, world):
    """Everything the colony makes: per minute now, made so far, and a bar
    graph of the rate over the whole run."""
    c1, c2, c3 = D.PRODUCTION_COLUMNS
    lines = [([(0, "GOOD"), (c1, "NOW / MIN"), (c2, "MADE"), (c3, "OVER THE RUN")], D.COLOR_TEXT_DIM)]
    items = stats.made_items(world)
    for k in items:
        color = D.COLOR_ALERT if ITEMS[k]["tier"] == "waste" else D.COLOR_TEXT
        lines.append(([(0, ITEMS[k]["name"].upper()), (c1, f"{stats.rate_now(world, k):5.1f}"),
                       (c2, str(stats.made(world).get(k, 0)))], color))
    if not items:
        lines.append(("NOTHING MADE YET", D.COLOR_TEXT_DIM))
    lines.append(("", D.COLOR_TEXT_DIM))
    lines.append((f"COLONY OUTPUT {stats.colony_output(world):.0f} ITEMS / MIN      L OR ESC: CLOSE", D.COLOR_FLOW))
    w = D.PRODUCTION_WIDTH
    rect, rows = _panel(surface, (surface.get_width() - w) // 2, D.RESEARCH_TOP, w, lines, "PRODUCTION",
                        None, len(items) + 1)
    for k, row in zip(items, rows[1:]):
        _sparkline(surface, stats.series(world, k), rect.x + 10 + c3, row.y + 1, w - c3 - 24, row.height - 3)
    return rect, []


def _sparkline(surface, values, x, y, w, h):
    """Bars for the rate in each interval, scaled to this good's best."""
    if not values:
        return
    n = min(len(values), max(1, w // 2))
    step = len(values) / n
    bars = [max(values[int(i * step):int((i + 1) * step)] or [0.0]) for i in range(n)]
    top = max(bars) or 1.0
    bw = max(1, w // n)
    for i, v in enumerate(bars):
        bh = int(h * v / top)
        if bh:
            color = D.COLOR_FLOW if i == n - 1 else D.COLOR_FLOW_DIM
            pygame.draw.rect(surface, color, (x + i * bw, y + h - bh, max(1, bw - 1), bh))


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


