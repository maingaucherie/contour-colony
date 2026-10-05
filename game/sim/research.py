"""Research: one node at a time, paid in credits up front. Never imports pygame."""

from game.content import world as W
from game.content.research import RESEARCH


class Research:
    def __init__(self):
        self.done = set()
        self.current = None
        self.ticks_left = 0

    def status(self, node):
        if node in self.done:
            return "done"
        if node == self.current:
            return "active"
        if all(r in self.done for r in RESEARCH[node]["requires"]):
            return "available"
        return "locked"

    def can_start(self, node, credits):
        st = self.status(node)
        if st != "available":
            return False, {"done": "ALREADY DONE", "active": "IN PROGRESS", "locked": "PREREQUISITES MISSING"}[st]
        if self.current is not None:
            return False, "ANOTHER PROJECT IS RUNNING"
        if credits < RESEARCH[node]["cost"]:
            return False, "NOT ENOUGH CREDITS"
        return True, ""

    def start(self, node):
        self.current = node
        self.ticks_left = round(RESEARCH[node]["time_s"] * W.TICK_RATE)

    def tick(self):
        """Advance; returns the node that just completed, or None."""
        if self.current is None:
            return None
        self.ticks_left -= 1
        if self.ticks_left > 0:
            return None
        node, self.current = self.current, None
        self.done.add(node)
        return node

    def progress(self):
        if self.current is None:
            return 0.0
        total = RESEARCH[self.current]["time_s"] * W.TICK_RATE
        return 1.0 - self.ticks_left / total

    def unlocked(self, unlocked_by):
        return unlocked_by is None or unlocked_by in self.done

    def effect(self, name, default):
        """Combined effect: multipliers multiply, flags OR together."""
        value = default
        for node in self.done:
            eff = RESEARCH[node].get("effects", {})
            if name in eff:
                v = eff[name]
                value = (value or v) if isinstance(v, bool) else value * v
        return value
