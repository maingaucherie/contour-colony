"""Generate the body a site sits on, for the landing briefing. Never imports
pygame. Deterministic per seed."""

import random

from game.content import body as B


def _name(rng):
    return rng.choice(B.NAME_STARTS) + rng.choice(B.NAME_MIDDLES) + rng.choice(B.NAME_ENDS)


def generate(seed):
    rng = random.Random(f"{seed}/body")
    spec = rng.choices(B.KINDS, weights=[k["weight"] for k in B.KINDS])[0]
    star = _name(rng)
    if spec["parent"]:
        parent = f"{star} {rng.choice(B.ROMAN)}"
        name = f"{parent}-{'ABCDEF'[rng.randrange(6)]}"
    else:
        parent = None
        name = f"{_name(rng)} ({star} SYSTEM)"
    (lo_min, lo_max), (hi_min, hi_max) = spec["temp"]
    return {
        "name": name,
        "kind": spec["kind"],
        "description": rng.choice(spec["describe"]),
        "parent": parent,
        "gravity_g": round(rng.uniform(*spec["gravity"]), 3),
        "day_h": rng.randint(*spec["day_h"]),
        "temp_c": (rng.randint(lo_min, lo_max), rng.randint(hi_min, hi_max)),
        "orders": rng.choice(B.ORDERS),
    }


def briefing_lines(seed, body):
    """The teletype lines of the landing briefing."""
    what = body["description"] + (f" OF {body['parent']}" if body["parent"] else "")
    lo, hi = body["temp_c"]
    return [
        f"ORBITAL SURVEY COMPLETE - SITE {seed}",
        "",
        f"BODY      {body['name']}",
        f"          {what}",
        f"GRAVITY   {body['gravity_g']:.3f} G      DAY {body['day_h']} H",
        f"SURFACE   {lo} TO {hi} C, NO ATMOSPHERE",
        f"ORDERS    {body['orders']}",
    ]
