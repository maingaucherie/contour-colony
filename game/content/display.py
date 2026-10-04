"""Display, camera, input and loading tables. Plain data: no logic."""

SCREEN_SIZE = (960, 540)
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
    "quit": ("escape",),
}
# Mouse button used to drag-pan (1 left, 2 middle, 3 right).
PAN_DRAG_BUTTONS = (1, 2)
