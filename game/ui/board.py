"""Contracts board, orbital pass timer, the orbit (supply and scan) menu and
the end-of-site screen."""

import math

import pygame

from game.content import contracts as C
from game.content import display as D
from game.content.items import ITEMS
from game.render.hershey import draw_text, line_height
from game.sim.orbit import Orbit
from game.ui.menus import _panel

M = D.HUD_MARGIN


def clock(seconds):
    s = max(0, int(math.ceil(seconds)))
    return f"{s // 60}:{s % 60:02d}"


def _bar(surface, x, y, w, h, frac, color):
    pygame.draw.rect(surface, D.COLOR_FRAME, (x, y, w, h), 1)
    fill = int((w - 4) * max(0.0, min(1.0, frac)))
    if fill > 0:
        pygame.draw.rect(surface, color, (x + 2, y + 2, fill, h - 4))


def contract_urgent(world, c):
    now = world.time_s()
    return c.late or c.deadline_s - now <= C.WARN_S


def draw_board(surface, world, now_s):
    """Contracts (top right) and the pass timer under them. Returns the bottom y."""
    w = surface.get_width()
    lh = D.HUD_LINE_HEIGHT
    bw = D.BOARD_WIDTH
    x = w - M - 6 - bw
    y = M + 4
    t = world.time_s()
    cs = world.contracts
    draw_text(surface, "CONTRACTS", (x, y), 1, D.COLOR_TEXT)
    draw_text(surface, f"FILLED {cs.filled}  EXPIRED {cs.expired}", (x + bw, y), 1, D.COLOR_TEXT_DIM, "right")
    y += lh + 2
    if not cs.open:
        draw_text(surface, f"NO OPEN CONTRACTS - NEXT OFFER IN {clock(cs.next_offer_s - t)}", (x, y), 1,
                  D.COLOR_TEXT_DIM)
        y += lh
    for c in sorted(cs.open, key=lambda c: c.deadline_s):
        urgent = contract_urgent(world, c)
        blink = int(now_s * 2 * D.ALERT_BLINK_HZ) % 2 == 0
        color = D.COLOR_ALERT if urgent else D.COLOR_TEXT
        name = ITEMS[c.good]["name"].upper()
        label = ("STANDING: " if c.standing else "") + f"{c.delivered}/{c.qty} {name}"
        draw_text(surface, label, (x, y), 1, color)
        if c.late:
            right = f"LATE {clock(c.grace_end_s - t)}"
        else:
            right = f"{clock(c.deadline_s - t)}  {c.payout()} CR"
        draw_text(surface, right, (x + bw, y), 1, color if (not urgent or blink) else D.COLOR_TEXT_DIM, "right")
        y += lh + 1
        if c.late:
            frac = (c.grace_end_s - t) / max(1.0, c.grace_end_s - c.deadline_s)
        else:
            frac = (c.deadline_s - t) / max(1.0, c.deadline_s - c.issued_s)
        bar_color = D.COLOR_ALERT if urgent else D.COLOR_FLOW
        _bar(surface, x, y, bw, 6, frac, bar_color)
        if c.qty:
            # A tick on the bar for how much is delivered.
            dx = x + 2 + int((bw - 4) * c.delivered / c.qty)
            pygame.draw.line(surface, D.COLOR_TEXT, (dx, y - 2), (dx, y + 7))
        y += 11
    if cs.standing_streak and any(c.standing for c in cs.open):
        draw_text(surface, f"STANDING STREAK {cs.standing_streak}/{C.STANDING_WINS} - NO SUPPLY DROPS",
                  (x, y), 1, D.COLOR_FLOW)
        y += lh
    y += 4
    return draw_pass_timer(surface, world, x, y, bw)


def draw_pass_timer(surface, world, x, y, bw):
    """A sweeping arc: how far through the pass (or the wait for one) we are."""
    t = world.time_s()
    orbit = world.orbit
    over = Orbit.overhead(t)
    left = Orbit.seconds_to_change(t)
    span = C.PASS_DURATION_S if over else (C.PASS_PERIOD_S - C.PASS_DURATION_S if t >= C.FIRST_PASS_S
                                           else C.FIRST_PASS_S)
    frac = 1.0 - left / span
    r = D.PASS_ARC_RADIUS
    cx, cy = x + r, y + r
    color = D.COLOR_POWER if over else D.COLOR_TEXT_DIM
    pts = [(cx + r * math.cos(-math.pi / 2 + 2 * math.pi * k / 32), cy + r * math.sin(-math.pi / 2 + 2 * math.pi * k / 32))
           for k in range(33)]
    pygame.draw.aalines(surface, D.COLOR_FRAME, False, pts)
    n = max(2, int(32 * frac) + 1)
    arc = [(cx + r * math.cos(-math.pi / 2 + 2 * math.pi * frac * k / (n - 1)),
            cy + r * math.sin(-math.pi / 2 + 2 * math.pi * frac * k / (n - 1))) for k in range(n)]
    if frac > 0:
        pygame.draw.aalines(surface, color, False, arc)
    a = -math.pi / 2 + 2 * math.pi * frac
    pygame.draw.aaline(surface, color, (cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a)))
    tx = x + 2 * r + 8
    if over:
        draw_text(surface, f"SHIP OVERHEAD - {clock(left)} LEFT", (tx, y), 1, D.COLOR_POWER)
        scan = "SCAN USED" if orbit.scan_used else "SCAN READY"
        draw_text(surface, f"DROPS LANDING   {scan}   O: ORBIT", (tx, y + D.HUD_LINE_HEIGHT), 1, D.COLOR_TEXT_DIM)
    else:
        draw_text(surface, f"NEXT ORBITAL PASS IN {clock(left)}", (tx, y), 1, D.COLOR_TEXT_DIM)
        waiting = len(orbit.pending)
        note = f"{waiting} DROP{'S' if waiting != 1 else ''} WAITING" if waiting else "NO DROPS ORDERED"
        draw_text(surface, f"{note}   O: ORBIT", (tx, y + D.HUD_LINE_HEIGHT), 1, D.COLOR_TEXT_DIM)
    return y + max(2 * r, 2 * D.HUD_LINE_HEIGHT) + 6


# Orbit menu ---------------------------------------------------------------------

def orbit_entries():
    """Rows of the orbit menu: every supply crate or unit, then the scan."""
    return [("supply", i) for i in range(len(C.SUPPLY))] + [("scan", None)]


def draw_orbit_menu(surface, world, cursor=None):
    t = world.time_s()
    over = Orbit.overhead(t)
    lines = []
    c1, c2 = D.ORBIT_COLUMNS
    for kind, i in orbit_entries():
        if kind == "supply":
            e = C.SUPPLY[i]
            what = ", ".join(f"{n} {k.upper()}" for k, n in e.get("items", {}).items()) or "ONE UNIT, READY TO WORK"
            color = D.COLOR_TEXT if world.credits >= e["cost"] else D.COLOR_TEXT_DIM
            lines.append(([(0, e["name"].upper()), (c1, f"{e['cost']} CR"), (c2, what)], color))
        else:
            if not over:
                status, color = f"SHIP NOT OVERHEAD - NEXT PASS IN {clock(Orbit.seconds_to_change(t))}", D.COLOR_TEXT_DIM
            elif world.orbit.scan_used:
                status, color = "ALREADY USED THIS PASS", D.COLOR_TEXT_DIM
            else:
                status, color = "READY - CHOOSE, THEN CLICK THE MAP", D.COLOR_TEXT
            lines.append(([(0, "ORBITAL SCAN"), (c1, "FREE"), (c2, status)], color))
    n = len(lines)
    lines.append(("", D.COLOR_TEXT_DIM))
    lines.append((f"CREDITS {world.credits}.  DROPS LAND NEAR THE LANDER DURING THE NEXT PASS.", D.COLOR_TEXT_DIM))
    lines.append(("ORDERING A DROP RESETS THE STANDING CONTRACT STREAK.   ESC: CLOSE", D.COLOR_TEXT_DIM))
    w = D.ORBIT_MENU_WIDTH
    return _panel(surface, (surface.get_width() - w) // 2, D.RESEARCH_TOP, w, lines, "ORBIT", cursor, n)


# End of site ------------------------------------------------------------------------

def draw_end(surface, world):
    w, h = surface.get_size()
    won = world.outcome == "won"
    cs = world.contracts
    minutes = (world.end_s or world.time_s()) / 60.0
    lines = [
        world.outcome_text,
        "",
        f"TIME ON SITE        {int(minutes)} MIN {int(minutes * 60) % 60:02d} S",
        f"CONTRACTS FILLED    {cs.filled}",
        f"CONTRACTS EXPIRED   {cs.expired}",
        f"CREDITS EARNED      {cs.credits_earned}",
        f"REPUTATION          {cs.reputation:.0f}",
        "",
        f"SCORE               {world.score()}",
        "",
        "N: NEXT SITE" if won else "N: TRY A NEW SITE",
    ]
    lh = D.HUD_LINE_HEIGHT + 2
    bw, bh = D.END_PANEL_SIZE
    x, y = (w - bw) // 2, (h - bh) // 2
    rect = pygame.Rect(x, y, bw, bh)
    surface.fill(D.COLOR_BACKGROUND, rect)
    color = D.COLOR_FIELD if won else D.COLOR_ALERT
    pygame.draw.rect(surface, color, rect, 1)
    pygame.draw.rect(surface, color, rect.inflate(-6, -6), 1)
    draw_text(surface, "SITE COMPLETE" if won else "SITE LOST", (w // 2, y + 14), 2, color, "center")
    ty = y + 14 + line_height(2) + 12
    for i, text in enumerate(lines):
        col = D.COLOR_TEXT if i == 0 or text.startswith("SCORE") else D.COLOR_TEXT_DIM
        if text.startswith("N:"):
            col = D.COLOR_FLOW
        draw_text(surface, text, (x + 24, ty), 1, col)
        ty += lh
