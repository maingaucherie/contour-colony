"""Display, camera, input and loading tables. Plain data: no logic."""

SCREEN_SIZE = (960, 540)
SURFACE_DEPTH = 32                # bits per pixel of every offscreen surface
SCALED_WINDOW = True              # scale the 960x540 frame to the window (off: --no-scale)
WINDOW_TITLE = "Contour Colony"
FRAME_RATE_CAP = 60

# Heavy setup jobs (terrain, contours) run for at most this long per frame.
LOAD_BUDGET_MS = 30

# Camera. Zoom is screen pixels per terrain cell.
ZOOM_FIT_MARGIN = 0.92            # min zoom shows the whole site with this fill fraction
ZOOM_MAX = 32.0
ZOOM_WHEEL_FACTOR = 1.15
ZOOM_KEY_FACTOR_PER_S = 2.5
PAN_KEY_SPEED_PX_PER_S = 480.0

# Glow (bloom): lines are downscaled by GLOW_DOWNSCALE, scaled back up and
# added GLOW_GAIN times on top of the frame.
GLOW_ENABLED = True
GLOW_DOWNSCALE = 4
GLOW_GAIN = 2

# Colours (RGB). Terrain in operations view sits at 25-35% brightness.
COLOR_BACKGROUND = (0, 0, 0)
COLOR_CONTOUR_OPS = (52, 78, 62)
COLOR_CONTOUR_OPS_INDEX = (72, 104, 84)
COLOR_SITE_BORDER = (60, 90, 70)
COLOR_TEXT = (230, 240, 230)
COLOR_TEXT_DIM = (120, 150, 130)
COLOR_FRAME = (90, 130, 105)
COLOR_PROGRESS = (110, 230, 240)

# Survey view height palette: (height fraction, RGB) stops, low to high.
# Cool hues only: red, amber and cyan-as-flow are reserved for gameplay meaning.
SURVEY_PALETTE = (
    (0.0, (70, 50, 200)),
    (0.25, (60, 110, 235)),
    (0.5, (60, 190, 200)),
    (0.75, (130, 230, 140)),
    (1.0, (235, 255, 235)),
)
CONTOUR_FADE_STEPS = 12           # brightness steps used when contours fade in and out
SURVEY_INDEX_BRIGHTNESS = 1.0
SURVEY_NORMAL_BRIGHTNESS = 0.7

# Text sizes: font units to pixels for the 1x and 2x sizes.
TEXT_SCALES = {1: 0.42, 2: 0.84}
TEXT_LETTER_SPACING_UNITS = 1
TEXT_CACHE_MAX = 256

# HUD layout.
HUD_MARGIN = 10
HUD_LINE_HEIGHT = 14
HUD_CORNER_LENGTH = 18
SCALE_BAR_TARGET_PX = 120
SCALE_BAR_NICE_KM = (1, 2, 5, 10, 20, 50)
PROGRESS_BAR_SIZE = (360, 14)

# Key bindings: action -> pygame key names (pygame.key.key_code).
KEY_BINDINGS = {
    "pan_left": ("a", "left"),
    "pan_right": ("d", "right"),
    "pan_up": ("w", "up"),
    "pan_down": ("s", "down"),
    "zoom_in": ("=", "e"),
    "zoom_out": ("-", "q"),
    "toggle_view": ("tab", "v"),
    "toggle_glow": ("g",),
    "toggle_stats": ("f3", "f"),
    "new_site": ("n",),
    "pause": ("space",),
    "speed_up": (".",),
    "speed_down": (",",),
    "sell": ("x",),
    "centre": ("c",),
    "build": ("b",),
    "icons": ("i",),
    "sound": ("m",),
    "research": ("r",),
    "priority": ("p",),
    "orbit": ("o",),
    "contracts": ("k",),
    "cancel_site": ("delete", "backspace"),
    "quit": ("escape",),
}
# Mouse button used to drag-pan (1 left, 2 middle, 3 right).
PAN_DRAG_BUTTONS = (1, 2)

# Entities. Sizes are in cells, with a minimum on-screen size in pixels.
START_ZOOM = 9.0                  # opening camera, centred on the lander
STRUCTURE_SCALE = 1.25            # glyph half-size = footprint radius x this
STRUCTURE_MIN_PX = 13
LANDER_MIN_PX = 26
ROVER_SIZE_CELLS = 1.0            # glyph half-size
ROVER_MIN_PX = 13
ROVER_BOB = 0.06                  # body bounce, in glyph units
ROVER_BOB_WAVELENGTH_CELLS = 0.45
ROVER_FACING_DEADBAND = 0.3       # |cos(heading)| needed before a rover turns around
DEBRIS_SIZE_CELLS = 0.8
DEBRIS_MIN_PX = 6
BEACON_BLINK_HZ = 0.7

# Icon style: "symbols" (top-down console marks, default) or "pictorial" (the
# side-view rovers and oblique structures). I toggles between them.
ICON_STYLES = ("symbols", "pictorial")
SYMBOL_STRUCTURE_SCALE = 1.0      # symbol radius = footprint radius x this
SYMBOL_STRUCTURE_MIN_PX = 4
UNIT_SYMBOL_CELLS = 0.55          # unit marker radius in cells ...
UNIT_SYMBOL_PX = (6, 10)          # ... clamped to this pixel range
CARGO_DOT_PX = 2
SELECT_PICK_RADIUS_PX = 14
CLICK_MAX_DRAG_PX = 5

COLOR_STRUCTURE = (235, 245, 235)
COLOR_UNIT = (240, 250, 240)
COLOR_DEBRIS = (150, 140, 120)
COLOR_POWER = (255, 176, 40)      # amber: power links, charging
COLOR_FLOW = (70, 220, 235)       # cyan: item flow, routes, buffer gauges
COLOR_ALERT = (255, 70, 60)       # red: broken, stranded, deadlines
COLOR_SELECT = (255, 255, 255)
COLOR_FIELD = (90, 235, 120)      # green: resource fields and survey data
COLOR_FIELD_ICE = (120, 235, 205)
COLOR_SITE = (150, 160, 150)      # construction sites
COLOR_GHOST_OK = (200, 255, 210)
COLOR_GRID_LINK = (170, 115, 30)  # dim amber
UNPOWERED_FLICKER = (0.25, 0.55)  # brightness range of an unpowered structure
FIELD_HINT_FLICKER_HZ = 3.0
SCAN_BEAM_TRAIL = 3               # faint copies of the radar beam behind it
SCAN_BEAM_TRAIL_STEP = 0.02       # radians between them
COLOR_TRACK = (72, 66, 54)        # worn tracks: dusty, below everything else
TRACK_MIN_BRIGHTNESS = 0.3
TRACK_REFRESH_TICKS = 50          # rebuild the visible track list this often (sim ticks)
TRACK_TWIN_ZOOM = 10.0            # from this zoom, tracks show as two tread lines
TRACK_TWIN_GAP_CELLS = 0.18
COLOR_SCAN = (22, 64, 36)         # very dim green: a quiet sweep across the whole map
FIELD_LONG_DASH_PX = 10
FIELD_GAP_PX = 4

# Unit state cues.
IDLE_BLINK_HZ = 1.0
PICKUP_BLINK_HZ = 6.0
LOW_BATTERY_FLICKER_BELOW = 0.3   # battery fraction
LOW_BATTERY_FLICKER_RATE = 53.0   # radians per second of the brightness wobble
LOW_BATTERY_FLICKER_MIN = 0.45    # dimmest brightness during the flicker
CARGO_PIP_PX = 2

# Phosphor trails: colour by age from fresh to old, fading out.
TRAIL_COLOR_FRESH = (200, 255, 210)
TRAIL_COLOR_OLD = (20, 70, 35)

# Buildable-ground marks: in placement mode around the cursor, and across the
# screen in survey view.
SLOPE_MARK_RADIUS_CELLS = 10      # placement mode
SLOPE_MARK_MAX = 1400             # survey view: marks per frame at most (sets the spacing)
COLOR_BUILDABLE = (70, 200, 100)
COLOR_TOO_STEEP = (170, 50, 45)

# Line styles that back up colour meaning.
DASH_PX = 6
GAP_PX = 4
DOT_SPACING_PX = 5

# Contracts board (top right) and the orbital pass timer under it.
BOARD_WIDTH = 330
PASS_ARC_RADIUS = 12
ALERT_BLINK_HZ = 2.0
REPUTATION_WARN = 20              # reputation shown in red below this
ORBIT_MENU_WIDTH = 660
ORBIT_COLUMNS = (130, 200)        # x offsets: cost, contents
END_PANEL_SIZE = (440, 300)

# Production gauges beside structures: one thin bar per buffer, shown once
# the structure is at least GAUGE_MIN_HALF_PX on screen.
GAUGE_MIN_HALF_PX = 7
GAUGE_WIDTH_PX = 2
GAUGE_GAP_PX = 2
COLOR_STARVED = (255, 70, 60)     # status colours on the wireframe (red: starved or blocked)

# Supply pods falling to the surface.
POD_SIZE_PX = 5
POD_FALL_PX = 180                 # a pod starts this far above its landing spot on screen
POD_TRAIL_STEPS = 8
POD_TRAIL_STEP_PX = 12
POD_RETRO_FRACTION = 0.25         # retro-rockets fire for the last quarter of the fall
POD_FLARE_PX = 9
POD_DUST_RADIUS_PX = 40

# Landing intro (real seconds and screen pixels).
INTRO_DESCENT_S = 4.0
INTRO_LANDER_START_PX = 260       # the lander starts this far above its spot
INTRO_PLUME_PX = 26
INTRO_DUST_S = 2.0
INTRO_DUST_RADIUS_PX = 90
INTRO_TEXT_DELAY_S = 0.6
INTRO_CHARS_PER_S = 70
INTRO_PANEL_WIDTH = 520

# Panels.
PANEL_WIDTH = 340
PANEL_GAP = 8                     # inspect panel sits this far under the contracts board
MENU_WIDTH = 470                  # build menu, top left under the HUD
MENU_TOP = 126
MENU_COLUMNS = (22, 170)          # x offsets: name, cost
RESEARCH_WIDTH = 790
RESEARCH_COLUMNS = (6, 190, 415)  # x offsets: name, status, effect
COLOR_MENU_CURSOR = (5, 28, 32)   # highlighted menu row
RESEARCH_TOP = 90
NEW_SITE_CONFIRM_S = 3.0          # press N twice within this to abandon the site
SELL_BATCH = 10                   # scrap sold per press of the sell key
HAULERS_SHORT_LOADS = 3           # HUD asks for more haulers when this many loads wait and none are free
MARKET_BATCH = 10                 # goods sold per choice in the orbit menu's market
PANEL_BATTERY_BAR = (120, 8)

# Event log.
EVENT_SHOW_S = 14.0               # an event fades out over this long
