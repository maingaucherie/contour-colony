"""The body each site sits on: names and physical ranges for the landing
briefing. Plain data: no logic. (Flavour for now; terrain may follow later.)"""

# Name parts: a catalogue star or planet name, then the body's designation.
NAME_STARTS = ("KES", "VOR", "AN", "TAL", "OR", "MIR", "SEL", "DRA", "HAL", "CY", "NE", "PRA", "ZE", "LU", "ITH")
NAME_MIDDLES = ("", "", "RA", "LO", "MA", "TI", "NE", "VE", "SA", "DO")
NAME_ENDS = ("SA", "RIS", "TH", "NE", "ON", "IA", "US", "EK", "AR", "OS", "IX")
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII")

# Kinds of body: weight (how often), gravity in g, day length in hours,
# surface temperature range in Celsius, and a short description.
KINDS = (
    {"kind": "moon", "weight": 5, "gravity": (0.08, 0.2), "day_h": (20, 700), "temp": ((-190, -120), (60, 130)),
     "parent": True, "describe": ("CRATERED MOON", "AIRLESS MOON", "TIDALLY LOCKED MOON", "DUSTY GREY MOON")},
    {"kind": "dwarf planet", "weight": 2, "gravity": (0.04, 0.09), "day_h": (6, 160), "temp": ((-230, -200), (-170, -120)),
     "parent": False, "describe": ("ICY DWARF PLANET", "DARK DWARF PLANET")},
    {"kind": "asteroid", "weight": 2, "gravity": (0.01, 0.04), "day_h": (3, 30), "temp": ((-150, -90), (-20, 40)),
     "parent": False, "describe": ("METAL-RICH ASTEROID", "RUBBLE-PILE ASTEROID", "CARBONACEOUS ASTEROID")},
)

# What the consortium says it wants.
ORDERS = (
    "SET UP A MINING SITE AND FILL CONSORTIUM CONTRACTS",
    "BUILD A SELF-SUFFICIENT SITE, THEN HAND IT OVER",
    "PROVE THE SITE: MAKE MACHINE PARTS WITHOUT RESUPPLY",
)
