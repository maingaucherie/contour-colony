"""Contracts, reputation, orbital passes and supply drops. Plain data: no logic."""

# Pace. Calm (the default) offers contracts you choose to accept: the clock
# starts when you accept, unaccepted offers are withdrawn without penalty, and
# reputation never drains. Pressure assigns every contract at once and drains
# reputation, as the original brief had it.
MODES = {
    "calm": {"name": "calm", "accept_offers": True, "drain_per_min": 0.0, "wear_breaks": False,
             "first_contract_s": 120, "offer_every_s": 150},
    "pressure": {"name": "pressure", "accept_offers": False, "drain_per_min": 1.0, "wear_breaks": True,
                 "first_contract_s": 300, "offer_every_s": 300},
}
DEFAULT_MODE = "calm"
MAX_OFFERS = 2                       # offers waiting for an answer at once (calm)
OFFER_WINDOW_S = 600                 # an offer nobody accepts is withdrawn after this

# Reputation: the run's clock and fail state.
REPUTATION_START = 50
REPUTATION_MAX = 100
REPUTATION_DRAIN_GRACE_S = 900       # pressure mode: no drain while the site is being set up
REPUTATION_ON_TIME = 10
REPUTATION_EXPIRED = -15

# Contracts. At most MAX_OPEN under way at once; a new one is offered every
# offer_every_s (see MODES) while there's room. Filled late (within the grace
# period after the deadline) pays credits only; past that it expires.
MAX_OPEN = 3
LATE_GRACE_FRACTION = 0.5            # of the contract's duration
PAY_MULTIPLIER = 1.8                 # credits = quantity x item value x this
WARN_S = 60                          # contracts this close to their deadline tick and turn red

# Templates by tier. The tier offered rises with contracts filled
# (one tier per TIER_EVERY filled). minutes is the time allowed.
TIER_EVERY = 2
TEMPLATES = (
    # tier 0: raw-ish goods from the first mines
    ({"good": "ilmenite", "qty": (20, 30), "minutes": 15},
     {"good": "ice", "qty": (12, 20), "minutes": 15},
     {"good": "regolith", "qty": (30, 40), "minutes": 15}),
    # tier 1: first processing
    ({"good": "concentrate", "qty": (10, 16), "minutes": 14},
     {"good": "water", "qty": (12, 20), "minutes": 14},
     {"good": "sinter", "qty": (8, 12), "minutes": 14}),
    # tier 2: refined
    ({"good": "oxygen", "qty": (12, 20), "minutes": 12},
     {"good": "iron", "qty": (8, 14), "minutes": 12},
     {"good": "hydrogen", "qty": (16, 24), "minutes": 12}),
    # tier 3: manufactured
    ({"good": "parts", "qty": (5, 8), "minutes": 12},
     {"good": "iron", "qty": (16, 24), "minutes": 12}),
)

# The standing contract: a repeating order that opens once STANDING_AFTER
# contracts have been filled. Filling it STANDING_WINS times in a row with no
# supply drop ordered in between hands the site off: the run is won.
STANDING_AFTER = 6
STANDING_REQUIRES = "machine_shop"   # ... and only once the site has one built
STANDING = {"good": "parts", "qty": 8, "minutes": 12}
STANDING_WINS = 2

# Score at the end.
SCORE_REPUTATION = 10                # points per reputation
SCORE_TIME_TARGET_MIN = 60           # bonus for every minute under this ...
SCORE_TIME_BONUS_PER_MIN = 25        # ... worth this much

# Orbital passes: the ship is overhead PASS_DURATION_S of every PASS_PERIOD_S.
PASS_PERIOD_S = 240
PASS_DURATION_S = 90
FIRST_PASS_S = 60                    # the first pass begins this far into the run

# Supply drops: ordered any time, land during the next pass near the lander.
SUPPLY = (
    {"name": "parts crate", "cost": 100, "items": {"parts": 10}},
    {"name": "scrap crate", "cost": 50, "items": {"scrap": 40}},
    {"name": "sinter crate", "cost": 120, "items": {"sinter": 20}},
    {"name": "hauler", "cost": 130, "unit": "hauler"},
    {"name": "constructor", "cost": 160, "unit": "constructor"},
    {"name": "survey rover", "cost": 130, "unit": "survey_rover"},
)
DROP_OFFSET_CELLS = 4.5              # drop pods land this far from the lander
DROP_FALL_S = 4.0                    # descent shown before a drop lands
DUST_S = 2.0                         # a landing's dust ring lasts this long

# Orbital scan: once per pass, flag fields and survey (level 1) in a radius.
SCAN_RADIUS_CELLS = 24.0
