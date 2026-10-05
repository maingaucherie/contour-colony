"""Console HUD: terminal frame, loading screen, readouts, stats."""

import pygame

from game.content import display as D
from game.render.hershey import draw_text, line_height

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


def _scale_bar_km(km_per_px):
    target = D.SCALE_BAR_TARGET_PX * km_per_px
    return min(D.SCALE_BAR_NICE_KM, key=lambda km: abs(km - target))


def draw_running(surface, info):
    """info: dict of readouts prepared by the app."""
    w, h = surface.get_size()
    lh = D.HUD_LINE_HEIGHT

    # Top left: site, economy, power, clock, research and view.
    draw_text(surface, f"SITE {info['seed']}", (M + 6, M + 4), 2)
    y = M + 4 + line_height(2) + 4
    draw_text(surface, f"CREDITS {info['credits']}   SCRAP {info['scrap']}   PARTS {info['parts']}", (M + 6, y), 1)
    supply, demand = info["power"]
    spare = supply - demand
    text = f"POWER {spare:.0f} KW FREE OF {supply:.0f}" if spare >= 0 else f"POWER {-spare:.0f} KW SHORT"
    draw_text(surface, text, (M + 6 + 330, y), 1, D.COLOR_ALERT if spare < 0 else D.COLOR_POWER)
    y += lh
    t = int(info["time_s"])
    clock = f"T+{t // 3600:02d}:{t // 60 % 60:02d}:{t % 60:02d}"
    rate = "PAUSED" if info["paused"] else f"SPEED {info['speed']}X"
    draw_text(surface, f"{clock}   {rate}", (M + 6, y + lh), 1,
              D.COLOR_ALERT if info["paused"] else D.COLOR_TEXT_DIM)
    research = info.get("research")
    rtext = f"RESEARCH {research[0].upper()} {research[1] * 100:3.0f}%" if research else "RESEARCH IDLE (R)"
    view = "SURVEY VIEW" if info["view"] == "survey" else "OPERATIONS VIEW"
    draw_text(surface, f"{rtext}   {view}", (M + 6, y + 2 * lh), 1, D.COLOR_TEXT_DIM)

    # Event log, newest at the bottom, fading out.
    ey = h - M - 4 - 3 * lh
    for age_s, text, kind in reversed(info.get("events", [])):
        if age_s > D.EVENT_SHOW_S:
            continue
        fade = 1.0 - age_s / D.EVENT_SHOW_S
        base = {"alert": D.COLOR_ALERT, "field": D.COLOR_FIELD}.get(kind, D.COLOR_TEXT)
        color = tuple(int(c * (0.35 + 0.65 * fade)) for c in base)
        draw_text(surface, "> " + text, (M + 6, ey), 1, color)
        ey -= lh

    # Bottom left: cursor readout and controls.
    y = h - M - 4 - 2 * lh
    cursor = info.get("cursor")
    if cursor:
        x_km, y_km, elev, slope = cursor
        draw_text(surface, f"X {x_km:5.1f} KM   Y {y_km:5.1f} KM   ELEV {elev:+6.0f} M   SLOPE {slope:4.1f} DEG",
                  (M + 6, y), 1)
    draw_text(surface, info.get("hint") or "B BUILD  R RESEARCH  CLICK SELECT  RIGHT CLICK ORDER  SPACE PAUSE"
              "  ,/. SPEED  TAB VIEW  M SOUND  I ICONS", (M + 6, y + lh), 1, D.COLOR_TEXT_DIM)

    # Bottom right: scale bar.
    km_per_px = info["cell_m"] / 1000.0 / info["zoom"]
    km = _scale_bar_km(km_per_px)
    px = int(km / km_per_px)
    bx1, by = w - M - 6, h - M - 8 - lh
    bx0 = bx1 - px
    pygame.draw.lines(surface, D.COLOR_TEXT, False, [(bx0, by - 5), (bx0, by), (bx1, by), (bx1, by - 5)])
    draw_text(surface, f"{km} KM", (bx1, by - 5 - lh), 1, align="right")

    # Top right: performance stats.
    if info["show_stats"]:
        lines = (
            f"FPS {info['fps']:5.1f}",
            f"FRAME {info['frame_ms']:5.1f} MS",
            f"SEGMENTS {info['segments']:5d}",
            f"TIER {info['tier']}  ZOOM {info['zoom']:5.1f}",
            f"GLOW {'ON' if info['glow'] else 'OFF'}",
        )
        for i, text in enumerate(lines):
            draw_text(surface, text, (w - M - 6, M + 4 + i * lh), 1, D.COLOR_TEXT_DIM, "right")
