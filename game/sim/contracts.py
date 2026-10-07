"""Contracts, reputation and credits: the run's clock. Never imports pygame.

Goods count as delivered when a hauler brings them to the lander's export bay
(they go straight to the open contracts, oldest first); goods already in the
lander's hold ship too, except building materials (scrap, parts, sinter).
In calm mode contracts arrive as offers and their clock starts when accepted;
in pressure mode they start at once and reputation also drains. Filled on time
pays credits and reputation; filled late (within the grace period) pays
credits only; past that the contract expires and costs reputation. At zero
reputation the run is lost.
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
    minutes: float
    offered_s: float
    issued_s: float = 0.0          # accepted at
    deadline_s: float = 0.0
    grace_end_s: float = 0.0
    standing: bool = False
    delivered: int = 0
    late: bool = False

    def remaining(self):
        return self.qty - self.delivered

    def payout(self):
        return int(self.qty * ITEMS[self.good]["value"] * C.PAY_MULTIPLIER)

    def start(self, now):
        span = self.minutes * 60.0
        self.issued_s, self.deadline_s = now, now + span
        self.grace_end_s = now + span * (1 + C.LATE_GRACE_FRACTION)


class Contracts:
    def __init__(self, seed, mode=C.DEFAULT_MODE):
        self.rng = random.Random(f"{seed}/contracts")
        self.mode = C.MODES[mode]
        self.offers = []               # waiting to be accepted (calm mode)
        self.open = []                 # accepted, with a clock running
        self.next_id = 1
        self.filled = 0
        self.expired = 0
        self.next_offer_s = self.mode["first_contract_s"]
        self.reputation = float(C.REPUTATION_START)
        self.credits_earned = 0
        self.log = []                  # (time_s, text) of finished contracts

    def set_mode(self, mode):
        """Switch pace (the landing briefing allows it before the first offer)."""
        first = self.next_offer_s == self.mode["first_contract_s"] and not self.offers and not self.open
        self.mode = C.MODES[mode]
        if first:
            self.next_offer_s = self.mode["first_contract_s"]

    def needs(self):
        """Goods still wanted at the export bay: {item: amount}."""
        out = {}
        for c in self.open:
            out[c.good] = out.get(c.good, 0) + c.remaining()
        return out

    def tier(self):
        return min(len(C.TEMPLATES) - 1, self.filled // C.TIER_EVERY)

    def _make(self, now, template, standing=False):
        lo, hi = (template["qty"], template["qty"]) if standing else template["qty"]
        c = Contract(self.next_id, template["good"], self.rng.randint(lo, hi), template["minutes"], now,
                     standing=standing)
        self.next_id += 1
        return c

    def _issue(self, now, template, standing=False):
        """A contract that starts at once (pressure mode, standing contracts, tests)."""
        c = self._make(now, template, standing)
        c.start(now)
        self.open.append(c)
        return c

    def accept(self, world, contract_id):
        """Command: accept an offer. Returns (ok, reason)."""
        c = next((o for o in self.offers if o.id == contract_id), None)
        if c is None:
            return False, "NO SUCH OFFER"
        if sum(1 for o in self.open if not o.standing) >= C.MAX_OPEN:
            return False, f"ALREADY {C.MAX_OPEN} CONTRACTS UNDER WAY"
        self.offers.remove(c)
        c.start(world.time_s())
        self.open.append(c)
        world.event(f"CONTRACT ACCEPTED: {c.qty} {ITEMS[c.good]['name'].upper()} IN {int(c.minutes)} MIN", "contract")
        return True, ""

    def update(self, world):
        now = world.time_s()
        mode = self.mode
        # New offers (or, under pressure, new contracts outright).
        waiting = len(self.offers) if mode["accept_offers"] else sum(1 for c in self.open if not c.standing)
        room = C.MAX_OFFERS if mode["accept_offers"] else C.MAX_OPEN
        if now >= self.next_offer_s and waiting < room:
            pool = [t for tier in C.TEMPLATES[: self.tier() + 1] for t in tier]
            taken = {c.good for c in self.open + self.offers}
            choices = [t for t in pool if t["good"] not in taken] or pool
            template = self.rng.choice(choices)
            name = ITEMS[template["good"]]["name"].upper()
            if mode["accept_offers"]:
                c = self._make(now, template)
                self.offers.append(c)
                world.event(f"CONTRACT OFFERED: {c.qty} {name} IN {int(c.minutes)} MIN - CLICK IT TO ACCEPT", "contract")
            else:
                c = self._issue(now, template)
                world.event(f"NEW CONTRACT: {c.qty} {name} IN {int(c.minutes)} MIN", "contract")
            self.next_offer_s = now + mode["offer_every_s"]
        for c in list(self.offers):
            if now - c.offered_s > C.OFFER_WINDOW_S:
                self.offers.remove(c)
                world.event(f"OFFER WITHDRAWN: {ITEMS[c.good]['name'].upper()}")

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

        # Under pressure, reputation drains slowly once the site has had time to get going.
        if mode["drain_per_min"] and now > C.REPUTATION_DRAIN_GRACE_S:
            self.reputation -= mode["drain_per_min"] / 60.0 / W.TICK_RATE
        self.reputation = min(self.reputation, C.REPUTATION_MAX)
        if self.reputation <= 0:
            self.reputation = 0.0
            if mode["can_lose"] and world.outcome is None:
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

    def _expire(self, world, c):
        self.open.remove(c)
        self.expired += 1
        self.reputation += C.REPUTATION_EXPIRED
        world.event(f"CONTRACT EXPIRED: {ITEMS[c.good]['name'].upper()} {C.REPUTATION_EXPIRED} REP", "alert")
        self.log.append((world.time_s(), f"expired {c.qty} {c.good}"))


