"""Tone generation into int16 sample arrays. Pure Python: no pygame.

Sustained notes use whole-Hz frequencies and a one-second wavetable indexed by
(n * f) % rate, so a one-second buffer loops seamlessly.
"""

import math
import random
from array import array

from game.content import audio as A


def _clip16(v):
    return max(-32767, min(32767, int(v * 32767)))


def _wave(kind, phase):
    """phase in cycles."""
    p = phase % 1.0
    if kind == "square":
        return 0.6 if p < 0.5 else -0.6   # squares are loud; tame them
    if kind == "triangle":
        return 4 * p - 1 if p < 0.5 else 3 - 4 * p
    return math.sin(2 * math.pi * p)


def _edge(i, n, rate):
    e = max(1, int(A.ENVELOPE_EDGE_S * rate))
    return min(1.0, i / e, (n - 1 - i) / e) if n > 1 else 0.0


def tone(freq, dur, wave, volume, rate):
    n = max(1, int(dur * rate))
    return [_wave(wave, freq * i / rate) * volume * _edge(i, n, rate) for i in range(n)]


def sweep(f0, f1, dur, wave, volume, rate):
    n = max(1, int(dur * rate))
    out, phase = [], 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * i / n
        phase += f / rate
        out.append(_wave(wave, phase) * volume * _edge(i, n, rate))
    return out


def ping(freq, dur, volume, rate):
    n = max(1, int(dur * rate))
    k = 5.0 / n
    return [math.sin(2 * math.pi * freq * i / rate) * volume * math.exp(-k * i) * _edge(i, n, rate)
            for i in range(n)]


def mix(parts, rate):
    """parts: [(start_s, samples)] -> one float list."""
    length = max(int(s * rate) + len(p) for s, p in parts)
    out = [0.0] * length
    for start, samples in parts:
        o = int(start * rate)
        for i, v in enumerate(samples):
            out[o + i] += v
    return out


def sfx(spec, rate):
    parts = []
    for start, kind, params in spec:
        if kind == "tone":
            parts.append((start, tone(*params, rate)))
        elif kind == "sweep":
            parts.append((start, sweep(*params, rate)))
        elif kind == "ping":
            parts.append((start, ping(*params, rate)))
    return mix(parts, rate)


def sine_table(rate, second_harmonic=0.0):
    return [math.sin(2 * math.pi * i / rate) + second_harmonic * math.sin(4 * math.pi * i / rate)
            for i in range(rate)]


def loop_note(freq, table, detune, volume, rate):
    """One second of a whole-Hz note (plus a detuned twin): loops seamlessly."""
    f2 = freq + detune
    return [(table[(i * freq) % rate] + table[(i * f2) % rate]) * 0.5 * volume for i in range(rate)]


def hum(rate):
    table = sine_table(rate)
    total = sum(a for _, a in A.HUM_HARMONICS)
    return [sum(table[(i * f) % rate] * a for f, a in A.HUM_HARMONICS) / total for i in range(rate)]


def pluck(freq, rate, table):
    n = int(A.PLUCK_DECAY_S * rate)
    k = 6.0 / n
    return [table[(i * freq) % rate] * math.exp(-k * i) * _edge(i, n, rate) for i in range(n)]


def to_int16(samples, channels):
    if channels == 1:
        return array("h", (_clip16(v) for v in samples))
    out = array("h", bytes(2 * len(samples) * channels))
    for i, v in enumerate(samples):
        c = _clip16(v)
        for ch in range(channels):
            out[i * channels + ch] = c
    return out


def build_bank(rate, channels):
    """Generator: yields progress, returns {name: int16 array}. Spread over frames
    by the loader so the browser build doesn't stall."""
    bank = {}
    jobs = [("sfx:" + name, spec) for name, spec in A.SFX.items()]
    jobs.append(("hum", None))
    pad_notes = sorted({f for chord in A.PAD_CHORDS for f in chord})
    jobs += [(f"pad:{f}", f) for f in pad_notes]
    jobs += [(f"pluck:{f}", f) for f in A.PLUCK_SCALE]
    table = sine_table(rate, A.PAD_SECOND_HARMONIC)
    plain = sine_table(rate)
    for i, (name, arg) in enumerate(jobs):
        if name.startswith("sfx:"):
            samples = sfx(arg, rate)
        elif name == "hum":
            samples = hum(rate)
        elif name.startswith("pad:"):
            samples = loop_note(arg, table, A.PAD_DETUNE_HZ, 1.0, rate)
        else:
            samples = pluck(arg, rate, plain)
        bank[name] = to_int16(samples, channels)
        yield (i + 1) / len(jobs)
    return bank


class MusicPlan:
    """Decides what the ambient music does next. Pure: the player turns the
    returned actions into mixer calls."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.chord = -1
        self.next_chord = 0.0
        self.next_pluck = 2.0
        self.pending = []   # (time, note, volume) echoes

    def update(self, now):
        actions = []
        if now >= self.next_chord:
            self.chord = (self.chord + 1) % len(A.PAD_CHORDS)
            self.next_chord = now + A.PAD_CHORD_S
            actions.append(("chord", A.PAD_CHORDS[self.chord]))
        if now >= self.next_pluck:
            note = self.rng.choice(A.PLUCK_SCALE)
            self.next_pluck = now + self.rng.uniform(*A.PLUCK_GAP_S)
            actions.append(("pluck", note, A.PLUCK_VOLUME))
            for delay, rel in A.PLUCK_ECHOES:
                self.pending.append((now + delay, note, A.PLUCK_VOLUME * rel))
        due = [p for p in self.pending if p[0] <= now]
        self.pending = [p for p in self.pending if p[0] > now]
        actions += [("pluck", note, vol) for _, note, vol in due]
        return actions
