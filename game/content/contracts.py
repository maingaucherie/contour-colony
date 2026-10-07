"""Contracts, reputation, orbital passes and supply drops. Plain data: no logic."""

# Pace. Calm (the default) offers contracts you choose to accept: the clock
# starts when you accept, unaccepted offers are withdrawn without penalty,
# reputation never drains, and the site can't be lost. Pressure assigns every contract at once and drains
# reputation, as the original brief had it.
MODES = {
    "calm": {"name": "calm", "accept_offers": True, "drain_per_min": 0.0, "wear_breaks": False,
             "can_lose": False, "first_contract_s": 120, "offer_every_s": 150},
    "pressure": {"name": "pressure", "accept_offers": False, "drain_per_min": 1.0, "wear_breaks": True,
                 "can_lose": True, "first_contract_s": 300, "offer_every_s": 300},
}
DEFAULT_MODE = "calm"
MAX_OFFERS = 2                       # offers waiting for an answer at once (calm)
OFFER_WINDOW_S = 600                 # an offer nobody accepts is withdrawn after this

# Reputation: contract standing (and, under pressure, the fail state).
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

# Templates by tier. Contracts are side income: the site is won by firing the
# mass driver (see structures.py). The tier offered rises with contracts
# filled (one tier per TIER_EVERY filled). minutes is the time allowed.
TIER_EVERY = 2
TEMPLATES = (
    # tier 0: what the scramble makes
    ({"good": "regolith", "qty": (30, 40), "minutes": 15},
     {"good": "sinter", "qty": (8, 12), "minutes": 15},
     {"good": "iron", "qty": (6, 10), "minutes": 15}),
    # tier 1: minerals and parts
    ({"good": "ilmenite", "qty": (20, 30), "minutes": 14},
     {"good": "anorthite", "qty": (20, 30), "minutes": 14},
     {"good": "parts", "qty": (5, 8), "minutes": 14}),
    # tier 2: processing
    ({"good": "concentrate", "qty": (10, 16), "minutes": 12},
     {"good": "water", "qty": (12, 20), "minutes": 12},
     {"good": "oxygen", "qty": (12, 20), "minutes": 12}),
    # tier 3: volume
    ({"good": "parts", "qty": (12, 20), "minutes": 12},
     {"good": "iron", "qty": (20, 30), "minutes": 12}),
)

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
