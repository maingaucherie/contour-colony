"""Console HUD: terminal frame, loading screen, readouts, stats."""

import pygame

from game.content import display as D
from game.content import world as W
from game.render.hershey import draw_text, line_height, text_width

M = D.HUD_MARGIN


def draw_frame(surface):
    """Corner brackets framing the console."""
    w, h = surface.get_size()
    n = D.HUD_CORNER_LENGTH
    for x, y, sx, sy in ((M // 2, M // 2, 1, 1), (w - M // 2, M // 2, -1, 1),
                         (M // 2, h - M // 2, 1, -1), (w - M // 2, h - M // 2, -1, -1)):
        pygame.draw.lines(surface, D.COLOR_FRAME, False,
                          [(x + sx * n, y), (x, y), (x, y + sy * n)])


def draw_loading(surface, seed, stage_index, stage_count, stage, progress):
    w, h = surface.get_size()
    draw_text(surface, "CONTOUR COLONY", (w // 2, h // 2 - 70), 2, align="center")
    draw_text(surface, f"SITE SEED {seed}", (w // 2, h // 2 - 34), 1, D.COLOR_TEXT_DIM, "center")
    bw, bh = D.PROGRESS_BAR_SIZE
    x, y = (w - bw) // 2, h // 2
    pygame.draw.rect(surface, D.COLOR_FRAME, (x, y, bw, bh), 1)
    fill = int((bw - 4) * min(max(progress, 0.0), 1.0))
    if fill > 0:
        pygame.draw.rect(surface, D.COLOR_PROGRESS, (x + 2, y + 2, fill, bh - 4))
    label = f"{stage_index}/{stage_count}  {stage}  {int(progress * 100):3d}%"
    draw_text(surface, label, (w // 2, y + bh + 10), 1, D.COLOR_TEXT_DIM, "center")


def draw_continue(surface, info, mouse=None):
    """Start-up offer to continue last time's site. Returns [continue rect, new site rect]."""
    w, h = surface.get_size()
    draw_text(surface, "CONTOUR COLONY", (w // 2, h // 2 - 90), 2, align="center")
    t = int(info["time_s"])
    state = "COMPLETE, KEPT RUNNING" if info["outcome"] == "won" else f"{info['mode'].upper()} PACE"
    draw_text(surface, f"SITE {info['seed']}   T+{t // 3600:02d}:{t // 60 % 60:02d}   {info['credits']} CR   {state}",
              (w // 2, h // 2 - 46), 1, D.COLOR_TEXT_DIM, "center")
    rects = []
    for i, label in enumerate(("CONTINUE  (ENTER)", "NEW SITE  (N)")):
        r = pygame.Rect(w // 2 - 120, h // 2 - 10 + i * 36, 240, 26)
        hover = mouse is not None and r.collidepoint(mouse)
        if hover:
            pygame.draw.rect(surface, D.COLOR_MENU_CURSOR, r)
        pygame.draw.rect(surface, D.COLOR_FLOW if i == 0 else D.COLOR_FRAME, r, 1)
        draw_text(surface, label, r.center, 1, D.COLOR_TEXT if i == 0 else D.COLOR_TEXT_DIM, "center", additive=True)
        rects.append(r)
    return rects


def _scale_bar_km(km_per_px):
    target = D.SCALE_BAR_TARGET_PX * km_per_px
    return min(D.SCALE_BAR_NICE_KM, key=lambda km: abs(km - target))


def draw_running(surface, info):
    """info: dict of readouts prepared by the app."""
    w, h = surface.get_size()
    lh = D.HUD_LINE_HEIGHT

    # Top left: site, economy, power, clock, research and view.
    draw_text(surface, f"SITE {info['seed']}", (M + 6, M + 4), 2)
    if info.get("complete"):
        draw_text(surface, f"COMPLETE - SCORE {info['complete']}", (M + 6 + 190, M + 10), 1, D.COLOR_FIELD)
    y = M + 4 + line_height(2) + 4
    rep = info["reputation"]
    credits = f"CREDITS {info['credits']}"
    draw_text(surface, credits, (M + 6, y), 1)
    rep_color = D.COLOR_ALERT if rep < D.REPUTATION_WARN else D.COLOR_TEXT
    rep_text = f"REPUTATION {rep:.0f}"
    rx = M + 6 + max(110, text_width(credits) + 18)
    draw_text(surface, rep_text, (rx, y), 1, rep_color)
    bx, bw = rx + text_width(rep_text) + 8, 90
    pygame.draw.rect(surface, D.COLOR_FRAME, (bx, y + 1, bw, 9), 1)
    fill = int((bw - 4) * max(0.0, min(1.0, rep / 100.0)))
    if fill:
        pygame.draw.rect(surface, rep_color if rep < D.REPUTATION_WARN else D.COLOR_FIELD, (bx + 2, y + 3, fill, 5))
    y += lh
    stored, cap = info["storage"]
    stock = f"STORAGE {stored}/{cap}   SCRAP {info['scrap']}   PARTS {info['parts']}   SINTER {info['sinter']}"
    draw_text(surface, stock, (M + 6, y), 1, D.COLOR_TEXT_DIM)

    t = int(info["time_s"])
    clock = f"T+{t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"
    rate = "PAUSED" if info["paused"] else f"SPEED {info['speed']}X"
    if not info["paused"] and info["speed"] > 1 and info.get("actual_speed", info["speed"]) < info["speed"] * 0.85:
        rate += f" (MANAGING {info['actual_speed']:.0f}X)"
    if info.get("saved"):
        rate += "   SAVED"
    draw_text(surface, f"{clock}   {rate}", (M + 6, y + lh), 1,
              D.COLOR_ALERT if info["paused"] else D.COLOR_TEXT_DIM)
    supply, demand = info["power"]
    spare = supply - demand
    text = f"POWER {spare:.0f} KW FREE OF {supply:.0f}" if spare >= 0 else f"POWER {-spare:.0f} KW SHORT"
    px = M + 6 + max(text_width(f"{clock}   {rate}") + 18, 200)
    draw_text(surface, text, (px, y + lh), 1, D.COLOR_ALERT if spare < 0 else D.COLOR_POWER)
    research = info.get("research")
    rtext = f"RESEARCH {research[0].upper()} {research[1] * 100:3.0f}%" if research else "RESEARCH IDLE (R)"
    view = "SURVEY VIEW" if info["view"] == "survey" else "OPERATIONS VIEW"
    draw_text(surface, f"{rtext}   {view}", (M + 6, y + 2 * lh), 1, D.COLOR_TEXT_DIM)
    haulers, idle, waiting = info["haulers"]
    if haulers or waiting:
        busy = waiting > idle and waiting >= D.HAULERS_SHORT_LOADS
        text = f"HAULERS {haulers} ({idle} FREE)   LOADS WAITING {waiting}" + ("   BUILD MORE HAULERS" if busy else "")
        draw_text(surface, text, (M + 6, y + 3 * lh), 1, D.COLOR_ALERT if busy else D.COLOR_TEXT_DIM)

    # Event log, newest at the bottom, fading out.
    ey = h - M - 7 - 3 * lh
    for age_s, text, kind in reversed(info.get("events", [])):
        if age_s > D.EVENT_SHOW_S:
            continue
        fade = 1.0 - age_s / D.EVENT_SHOW_S
        base = {"alert": D.COLOR_ALERT, "field": D.COLOR_FIELD, "contract": D.COLOR_FLOW,
                "won": D.COLOR_FIELD, "orbit": D.COLOR_POWER}.get(kind, D.COLOR_TEXT)
        color = tuple(int(c * (0.35 + 0.65 * fade)) for c in base)
        draw_text(surface, "> " + text, (M + 6, ey), 1, color)
        ey -= lh

    # Bottom left: cursor readout and controls.
    y = h - M - 7 - 2 * lh
    cursor = info.get("cursor")
    if cursor:
        x_km, y_km, elev, slope = cursor
        if slope <= W.SLOPE_BUILDABLE_DEG:
            kind, color = "BUILDABLE", D.COLOR_BUILDABLE
        elif slope <= W.SLOPE_ROAD_ONLY_DEG:
            kind, color = "TOO STEEP TO BUILD", D.COLOR_TEXT
        elif slope <= W.SLOPE_IMPASSABLE_DEG:
            kind, color = "TOO STEEP TO BUILD, HARD GOING", D.COLOR_TEXT
        else:
            kind, color = "CLIFF - IMPASSABLE", D.COLOR_ALERT
        draw_text(surface, f"X {x_km:5.1f} KM   Y {y_km:5.1f} KM   ELEV {elev:+6.0f} M   SLOPE {slope:4.1f} DEG  {kind}",
                  (M + 6, y), 1, color)
    draw_text(surface, info.get("hint") or "B BUILD  R RESEARCH  K CONTRACTS  O ORBIT  RIGHT CLICK ORDER"
              "  SPACE PAUSE  ,/. SPEED  TAB VIEW  M SOUND  I ICONS", (M + 6, y + lh + 4), 1, D.COLOR_TEXT_DIM)

    # Bottom right: scale bar.
    km_per_px = info["cell_m"] / 1000.0 / info["zoom"]
    km = _scale_bar_km(km_per_px)
    px = int(km / km_per_px)
    bx1, by = w - M - 6, h - M - 8 - lh
    bx0 = bx1 - px
    pygame.draw.lines(surface, D.COLOR_TEXT, False, [(bx0, by - 5), (bx0, by), (bx1, by), (bx1, by - 5)])
    draw_text(surface, f"{km} KM", (bx1, by - 5 - lh), 1, align="right")

    # Bottom right, above the scale bar: performance stats (F to hide).
    if info["show_stats"]:
        text = (f"FPS {info['fps']:4.1f}  FRAME {info['frame_ms']:4.1f} MS  SEGMENTS {info['segments']}"
                f"  TIER {info['tier']}  ZOOM {info['zoom']:4.1f}  GLOW {'ON' if info['glow'] else 'OFF'}")
        draw_text(surface, text, (w - M - 6, by - 5 - 2 * lh), 1, D.COLOR_TEXT_DIM, "right")
