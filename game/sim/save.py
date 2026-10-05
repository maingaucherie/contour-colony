"""Saving and loading a site. Never imports pygame.

A save is the site's seed plus a snapshot of everything that changes while
playing. Terrain, contours, the path grid and other things derived from the
seed are rebuilt on load (build_world), then the snapshot is laid over them.
Loading then continuing runs exactly as if the game had never stopped.

Saves carry SAVE_VERSION; a save from another version is refused (no
conversion yet: the format will change freely until the game is finished).
"""

import base64
import dataclasses
import json
from collections import deque

from game.content import contracts as CT
from game.content import world as W
from game.sim import power
from game.sim.contracts import Contract
from game.sim.debris import Debris
from game.sim.fields import Field
from game.sim.orbit import Pod
from game.sim.structures import Structure
from game.sim.units import Unit

SKIP_FIELDS = {"trail"}   # cosmetic: rebuilt as units drive


class SaveError(Exception):
    pass


# Encoding -------------------------------------------------------------------

def _value(v):
    if isinstance(v, (deque, tuple, list)):
        return [_value(x) for x in v]
    if isinstance(v, set):
        return sorted(v)
    if isinstance(v, dict):
        return {str(k): _value(x) for k, x in v.items()}
    if isinstance(v, (bytes, bytearray)):
        return base64.b64encode(bytes(v)).decode("ascii")
    return v


def _record(obj):
    """A dataclass instance as a plain dict."""
    return {f.name: _value(getattr(obj, f.name)) for f in dataclasses.fields(obj) if f.name not in SKIP_FIELDS}


def _rng(r):
    return _value(r.getstate())


def snapshot(world):
    """Everything about the world that changes while playing, as JSON-ready data."""
    c, o, r = world.contracts, world.orbit, world.research
    return {
        "version": W.SAVE_VERSION,
        "seed": world.seed,
        "mode": c.mode["name"],
        "world": {
            "tick_count": world.tick_count, "next_id": world.next_id, "credits": world.credits,
            "scrap_spawned": world.scrap_spawned, "scrap_sold": world.scrap_sold,
            "consumed": world.consumed, "produced": world.produced,
            "outcome": world.outcome, "outcome_text": world.outcome_text, "end_s": world.end_s,
            "endless": world.endless, "final_score": world.final_score, "debris_timer": world.debris_timer,
            "storage_full": world.storage_full, "autosold": world.autosold,
            "event_count": world.event_count, "events": _value(world.events),
            "rng": _rng(world.rng), "lander": world.lander.id,
        },
        "structures": [_record(s) for s in world.structures.values()],
        "units": [_record(u) for u in world.units.values()],
        "debris": [_record(d) for d in world.debris.values()],
        "fields": [_record(f) for f in world.fields],
        "survey": _value(world.survey.levels),
        "tracks": _value(world.tracks.cells),
        "research": {"done": _value(r.done), "current": r.current, "ticks_left": r.ticks_left},
        "contracts": {
            "rng": _rng(c.rng), "offers": [_record(x) for x in c.offers], "open": [_record(x) for x in c.open],
            "next_id": c.next_id, "filled": c.filled, "expired": c.expired, "next_offer_s": c.next_offer_s,
            "reputation": c.reputation, "credits_earned": c.credits_earned,
            "standing_streak": c.standing_streak, "drops_since_standing": c.drops_since_standing,
            "log": _value(c.log),
        },
        "orbit": {
            "pending": [e["name"] for e in o.pending],
            "falling": [{"item": p.item["name"], "land_s": p.land_s, "x": p.x, "y": p.y} for p in o.falling],
            "was_overhead": o.was_overhead, "scan_used": o.scan_used, "orders": o.orders,
            "landed": _value(o.landed),
        },
    }


def dumps(world):
    return json.dumps(snapshot(world), separators=(",", ":"))


def summary(text):
    """Small description of a save for the continue prompt, or None if unusable."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return None
    if data.get("version") != W.SAVE_VERSION:
        return None
    wd = data["world"]
    return {"seed": data["seed"], "time_s": wd["tick_count"] / W.TICK_RATE, "credits": wd["credits"],
            "mode": data["mode"], "outcome": wd["outcome"]}


# Decoding -------------------------------------------------------------------

def _state(s):
    """random.getstate() from its JSON form."""
    version, internal, gauss = s
    return version, tuple(internal), gauss


def _make(cls, d, **fix):
    names = {f.name for f in dataclasses.fields(cls)}
    kwargs = {k: v for k, v in d.items() if k in names}
    kwargs.update(fix)
    return cls(**kwargs)


def _int_keys(d):
    return {int(k): v for k, v in d.items()}


def read(text):
    """Parse and check a save. Returns its data, or raises SaveError."""
    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise SaveError("SAVE IS DAMAGED") from exc
    if data.get("version") != W.SAVE_VERSION:
        raise SaveError("SAVE IS FROM ANOTHER VERSION OF THE GAME")
    return data


def apply(world, data):
    """Lay a snapshot over a freshly built world for the same seed and mode."""
    wd = data["world"]
    for key in ("tick_count", "next_id", "credits", "scrap_spawned", "scrap_sold", "consumed", "produced",
                "outcome", "outcome_text", "end_s", "endless", "final_score", "debris_timer", "storage_full", "autosold",
                "event_count"):
        setattr(world, key, wd[key])
    world.events = deque((tuple(e) for e in wd["events"]), maxlen=W.EVENT_LOG_LENGTH)
    world.rng.setstate(_state(wd["rng"]))

    world.structures = {}
    for d in data["structures"]:
        s = _make(Structure, d, docks=[tuple(p) for p in d["docks"]])
        world.structures[s.id] = s
    world.lander = world.structures[wd["lander"]]
    world.units = {}
    for d in data["units"]:
        u = _make(Unit, d, path=[tuple(p) for p in d["path"]],
                  haul=tuple(d["haul"]) if d["haul"] is not None else None,
                  order=tuple(d["order"]) if d["order"] is not None else None,
                  survey_at=tuple(d["survey_at"]) if d["survey_at"] is not None else None)
        world.units[u.id] = u
    world.debris = {d["id"]: _make(Debris, d) for d in data["debris"]}
    world.fields = [_make(Field, d, phases=tuple(d["phases"]), boundary=[tuple(p) for p in d["boundary"]])
                    for d in data["fields"]]

    world.survey.levels = bytearray(base64.b64decode(data["survey"]))
    world.survey.version += 1
    world.survey.changes = []
    world.tracks.cells = _int_keys(data["tracks"])
    world.tracks.version += 1

    rd = data["research"]
    world.research.done = set(rd["done"])
    world.research.current = rd["current"]
    world.research.ticks_left = rd["ticks_left"]

    cd, c = data["contracts"], world.contracts
    c.mode = CT.MODES[data["mode"]]
    c.rng.setstate(_state(cd["rng"]))
    c.offers = [_make(Contract, d) for d in cd["offers"]]
    c.open = [_make(Contract, d) for d in cd["open"]]
    for key in ("next_id", "filled", "expired", "next_offer_s", "reputation", "credits_earned",
                "standing_streak", "drops_since_standing"):
        setattr(c, key, cd[key])
    c.log = [tuple(x) for x in cd["log"]]

    od, o = data["orbit"], world.orbit
    catalogue = {e["name"]: e for e in CT.SUPPLY}
    o.pending = [catalogue[n] for n in od["pending"]]
    o.falling = [Pod(catalogue[p["item"]], p["land_s"], p["x"], p["y"]) for p in od["falling"]]
    o.was_overhead, o.scan_used, o.orders = od["was_overhead"], od["scan_used"], od["orders"]
    o.landed = [tuple(x) for x in od["landed"]]

    # Derived state, recomputed as the tick would.
    world.structures_changed()
    world.power_grids = power.compute(list(world.structures.values()))
    world.dirty_power = False
    world.charger_key = None
    world._refresh_chargers()
    return world


def load(text, heightmap, build_world, run_to_completion):
    """Rebuild a saved site: the world for its seed, then its snapshot."""
    data = read(text)
    world = run_to_completion(build_world(data["seed"], heightmap, data["mode"]))
    return apply(world, data)

