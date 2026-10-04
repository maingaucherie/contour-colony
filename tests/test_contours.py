import math
import unittest
from array import array

from game.render.contours import (
    _segment_dist2, build_chunk, build_contours, level_range, march_chunk, nice_interval,
    simplify, stitch, tier_for_zoom,
)
from game.sim.terrain import Heightmap, generate_terrain, run_to_completion

SIZE = 65
CHUNK = 16
TIERS = (
    {"level_step": 4, "tolerance_cells": 0.75, "min_zoom": 0.0},
    {"level_step": 2, "tolerance_cells": 0.5, "min_zoom": 5.0},
    {"level_step": 1, "tolerance_cells": 0.25, "min_zoom": 10.0},
)


def cone(size=SIZE, cx=32.3, cy=31.7):
    """Height = minus distance from (cx, cy): every contour is a circle."""
    h = array("f", (-math.hypot(x - cx, y - cy) for y in range(size) for x in range(size)))
    return Heightmap(size, 400.0, h, min(h), max(h))


def all_polylines(contours, tier, k):
    out = []
    for chunk in contours.chunks:
        for level, lines in chunk.tiers[tier]:
            if level == k:
                out.extend(pl.points for pl in lines)
    return out


class IntervalTests(unittest.TestCase):
    def test_nice_interval_is_nice_and_near_target(self):
        for height_range in (37.0, 410.0, 3068.0, 4122.0, 25000.0):
            interval = nice_interval(height_range, 40, (1.0, 2.0, 2.5, 5.0))
            mantissa = interval / 10 ** math.floor(math.log10(interval))
            self.assertTrue(any(math.isclose(mantissa, s) for s in (1.0, 2.0, 2.5, 5.0)), interval)
            self.assertTrue(16 <= height_range / interval <= 100, (height_range, interval))

    def test_level_range_is_strict_at_top(self):
        self.assertEqual(level_range(-10.0, 30.0, 10.0), (-1, 2))
        self.assertEqual(level_range(-9.0, 31.0, 10.0), (0, 3))

    def test_tier_for_zoom(self):
        self.assertEqual(tier_for_zoom(1.0, TIERS), 0)
        self.assertEqual(tier_for_zoom(5.0, TIERS), 1)
        self.assertEqual(tier_for_zoom(30.0, TIERS), 2)


class MarchingSquaresTests(unittest.TestCase):
    def test_cone_level_is_one_closed_circle(self):
        hm = cone()
        levels = march_chunk(hm.heights, hm.size, 0, 0, hm.size - 1, hm.size - 1, 1.0)
        segs, points = levels[-10]
        lines = stitch(segs, points)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertEqual(line[0], line[-1])
        for x, y in line:
            self.assertAlmostEqual(math.hypot(x - 32.3, y - 31.7), 10.0, delta=0.1)

    def test_saddle_cells_stitch_into_two_lines(self):
        # Checkerboard 2x2 cell block: one saddle cell, high corners top-left and bottom-right.
        size = 2
        h = array("f", [1.0, 0.0, 0.0, 1.0])
        levels = march_chunk(h, size, 0, 0, 1, 1, 0.5)
        segs, points = levels[1]
        self.assertEqual(len(segs), 2)
        self.assertEqual(len(stitch(segs, points)), 2)

    def test_chunk_seams_meet_exactly_and_lines_close_globally(self):
        hm = cone()
        contours = run_to_completion(build_contours(hm, TIERS, CHUNK))
        self.assertGreater(contours.chunks_per_side, 1)
        tier = 2
        for k in range(contours.k_min, contours.k_max + 1):
            # Count open-line endpoints: across all chunks each must be matched by
            # another chunk's endpoint at exactly the same position.
            ends = {}
            for pts in all_polylines(contours, tier, k):
                if pts[0] != pts[-1]:
                    for p in (pts[0], pts[-1]):
                        ends[p] = ends.get(p, 0) + 1
            for p, n in ends.items():
                on_border = p[0] in (0, SIZE - 1) or p[1] in (0, SIZE - 1)
                if not on_border:
                    self.assertEqual(n, 2, (k, p))

    def test_tiers_hold_the_right_levels(self):
        hm = cone()
        contours = run_to_completion(build_contours(hm, TIERS, CHUNK))
        for chunk in contours.chunks:
            for spec, levels in zip(TIERS, chunk.tiers):
                for k, _ in levels:
                    self.assertEqual(k % spec["level_step"], 0)
        full = {k for c in contours.chunks for k, _ in c.tiers[2]}
        lo, hi = level_range(hm.min_h, hm.max_h, contours.interval)
        self.assertTrue(full <= set(range(lo, hi + 1)))


class SimplifyTests(unittest.TestCase):
    def test_open_line_keeps_endpoints_and_stays_within_tolerance(self):
        pts = [(x * 0.1, math.sin(x * 0.1)) for x in range(100)]
        out = simplify(pts, 0.05)
        self.assertEqual(out[0], pts[0])
        self.assertEqual(out[-1], pts[-1])
        self.assertLess(len(out), len(pts))
        # Every original point lies within tolerance of the simplified line.
        for p in pts:
            d = min(_segment_dist2(p, a, b) for a, b in zip(out, out[1:]))
            self.assertLessEqual(math.sqrt(d), 0.05 + 1e-9)

    def test_closed_loop_stays_closed(self):
        pts = [(10 * math.cos(a / 50 * 2 * math.pi), 10 * math.sin(a / 50 * 2 * math.pi)) for a in range(50)]
        pts.append(pts[0])
        out = simplify(pts, 0.25)
        self.assertEqual(out[0], out[-1])
        self.assertGreaterEqual(len(out), 4)

    def test_tiny_loop_is_dropped(self):
        pts = [(0.0, 0.0), (0.1, 0.0), (0.1, 0.1), (0.0, 0.1), (0.0, 0.0)]
        self.assertIsNone(simplify(pts, 0.5))


class GeneratedSiteTests(unittest.TestCase):
    def test_real_terrain_builds_and_is_deterministic(self):
        hm = run_to_completion(generate_terrain(11, 96))
        a = run_to_completion(build_contours(hm, TIERS, 32))
        b = run_to_completion(build_contours(hm, TIERS, 32))
        flat = lambda cs: [(k, [pl.points for pl in lines]) for c in cs.chunks for t in c.tiers for k, lines in t]
        self.assertEqual(flat(a), flat(b))
        self.assertGreater(sum(len(lines) for _, lines in flat(a)), 0)


if __name__ == "__main__":
    unittest.main()
