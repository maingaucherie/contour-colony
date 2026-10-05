"""Contracts, reputation and credits: the run's clock. Never imports pygame.

Goods count as delivered when a hauler brings them to the lander's export bay
(they go straight to the open contracts, oldest first); goods already in the
lander's hold ship too, except building materials (scrap, parts, sinter). Filled on time pays credits and reputation; filled late (within the
grace period) pays credits only; past that the contract expires and costs
reputation. Reputation also drains slowly. At zero the run is lost.
"""

import random
from dataclasses import dataclass

from game.content import contracts as C
from game.content import world as W
from game.content.items import ITEMS
from game.content.structures import STRUCTURES
from game.content.units import UNITS

BUILD_MATERIALS = frozenset(k for spec in list(STRUCTURES.values()) + list(UNITS.values())
                            for k in {**spec.get("build_cost", {}), **spec.get("bay_cost", {})})


@dataclass(slots=True)
class Contract:
    id: int
    good: str
    qty: int
    issued_s: float
    deadline_s: float
    grace_end_s: float
    standing: bool = False
    delivered: int = 0
    late: bool = False

    def remaining(self):
        return self.qty - self.delivered

    def payout(self):
        return int(self.qty * ITEMS[self.good]["value"] * C.PAY_MULTIPLIER)


class Contracts:
    def __init__(self, seed):
        self.rng = random.Random(f"{seed}/contracts")
        self.open = []
        self.next_id = 1
        self.filled = 0
        self.expired = 0
        self.next_offer_s = C.FIRST_CONTRACT_S
        self.reputation = float(C.REPUTATION_START)
        self.credits_earned = 0
        self.standing_streak = 0
        self.drops_since_standing = 0
        self.log = []                  # (time_s, text) of finished contracts

    def needs(self):
        """Goods still wanted at the export bay: {item: amount}."""
        out = {}
        for c in self.open:
            out[c.good] = out.get(c.good, 0) + c.remaining()
        return out

    def tier(self):
        return min(len(C.TEMPLATES) - 1, self.filled // C.TIER_EVERY)

    def _issue(self, now, template, standing=False):
        lo, hi = (template["qty"], template["qty"]) if standing else template["qty"]
        qty = self.rng.randint(lo, hi)
        span = template["minutes"] * 60.0
        c = Contract(self.next_id, template["good"], qty, now, now + span, now + span * (1 + C.LATE_GRACE_FRACTION),
                     standing=standing)
        self.next_id += 1
        self.open.append(c)
        return c

    def note_drop(self):
        self.drops_since_standing += 1

    def update(self, world):
        now = world.time_s()
        # New offers.
        if now >= self.next_offer_s and sum(1 for c in self.open if not c.standing) < C.MAX_OPEN:
            pool = [t for tier in C.TEMPLATES[: self.tier() + 1] for t in tier]
            open_goods = {c.good for c in self.open}
            choices = [t for t in pool if t["good"] not in open_goods] or pool
            c = self._issue(now, self.rng.choice(choices))
            world.event(f"NEW CONTRACT: {c.qty} {ITEMS[c.good]['name'].upper()} IN {C_minutes(c)} MIN", "contract")
            self.next_offer_s = now + C.NEW_CONTRACT_EVERY_S
        if (self.filled >= C.STANDING_AFTER and not any(c.standing for c in self.open)
                and any(s.kind == C.STANDING_REQUIRES and s.built for s in world.structures.values())):
            c = self._issue(now, C.STANDING, standing=True)
            world.event(f"STANDING CONTRACT: {c.qty} {ITEMS[c.good]['name'].upper()} EVERY "
                        f"{C.STANDING['minutes']} MIN - FILL IT {C.STANDING_WINS}X WITHOUT SUPPLY DROPS", "contract")

        # Goods already sitting in the lander's hold ship too, except building
        # materials (those stay for construction; haulers bring contract parts
        # and sinter straight from production).
        hold = world.lander.storage
        for item in [k for k in hold if k not in BUILD_MATERIALS]:
            n = self.receive(world, item, hold[item] - world.lander.reserved_out.get(item, 0))
            if n:
                hold[item] -= n
                if not hold[item]:
                    del hold[item]

        for c in list(self.open):
            if c.remaining() <= 0:
                self._fill(world, c, now)
            elif now > c.grace_end_s:
                self._expire(world, c)
            elif now > c.deadline_s and not c.late:
                c.late = True
                world.event(f"CONTRACT LATE: {ITEMS[c.good]['name'].upper()} - CREDITS ONLY NOW", "alert")

        # Slow reputation drain once the site has had time to get going.
        if now > C.REPUTATION_DRAIN_GRACE_S:
            self.reputation -= C.REPUTATION_DRAIN_PER_MIN / 60.0 / W.TICK_RATE
        self.reputation = min(self.reputation, C.REPUTATION_MAX)
        if self.reputation <= 0 and world.outcome is None:
            self.reputation = 0.0
            world.finish("lost", "REPUTATION GONE: THE CONSORTIUM HAS PULLED THE PLUG")

    def receive(self, world, item, amount):
        """Goods arriving at the export bay: credit open contracts, oldest first.
        Returns how many were taken."""
        taken = 0
        for c in sorted(self.open, key=lambda c: c.issued_s):
            if c.good == item and taken < amount:
                n = min(c.remaining(), amount - taken)
                c.delivered += n
                taken += n
        if taken:
            world.consumed[item] = world.consumed.get(item, 0) + taken
        return taken

    def _fill(self, world, c, now):
        self.open.remove(c)
        pay = c.payout()
        world.credits += pay
        self.credits_earned += pay
        self.filled += 1
        on_time = now <= c.deadline_s
        if on_time:
            self.reputation += C.REPUTATION_ON_TIME
        name = ITEMS[c.good]["name"].upper()
        world.event(f"CONTRACT FILLED{'' if on_time else ' LATE'}: {c.qty} {name} +{pay} CR"
                    + (f" +{C.REPUTATION_ON_TIME} REP" if on_time else ""), "contract")
        self.log.append((now, f"{'filled' if on_time else 'late'} {c.qty} {c.good}"))
        if c.standing:
            self.standing_streak = self.standing_streak + 1 if self.drops_since_standing == 0 else 1
            self.drops_since_standing = 0
            if self.standing_streak >= C.STANDING_WINS:
                world.finish("won", "SITE SELF-SUFFICIENT: HANDED OFF TO THE CONSORTIUM")

    def _expire(self, world, c):
        self.open.remove(c)
        self.expired += 1
        self.reputation += C.REPUTATION_EXPIRED
        if c.standing:
            self.standing_streak = 0
        world.event(f"CONTRACT EXPIRED: {ITEMS[c.good]['name'].upper()} {C.REPUTATION_EXPIRED} REP", "alert")
        self.log.append((world.time_s(), f"expired {c.qty} {c.good}"))


def C_minutes(c):
    return int(round((c.deadline_s - c.issued_s) / 60))
