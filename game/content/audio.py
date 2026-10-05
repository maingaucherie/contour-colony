"""Sound and music tables. Plain data: no logic.

Every sustained note uses a whole-number frequency in Hz, so one second of it
loops seamlessly; chords are layered loops faded in and out by the mixer.
"""

SAMPLE_RATE = 22050      # requested; the mixer's actual rate is used if it differs
CHANNELS = 32
MASTER = 0.8

# Sound effects: name -> list of (start_s, kind, params). Kinds:
#   tone  (freq_hz, dur_s, wave, volume)            wave: square, sine, triangle
#   sweep (freq_from, freq_to, dur_s, wave, volume)
#   ping  (freq_hz, dur_s, volume)                  sine with an exponential decay
#   noise (dur_s, volume)                           radio static
SFX = {
    "select":   [(0.00, "tone", (1320, 0.035, "square", 0.18))],
    "menu":     [(0.00, "tone", (880, 0.02, "square", 0.12))],
    "confirm":  [(0.00, "tone", (660, 0.05, "square", 0.16)), (0.055, "tone", (990, 0.07, "square", 0.16))],
    "error":    [(0.00, "tone", (140, 0.16, "square", 0.22))],
    "place":    [(0.00, "sweep", (240, 110, 0.10, "triangle", 0.4))],
    "order":    [(0.00, "tone", (990, 0.04, "square", 0.14)), (0.05, "tone", (1320, 0.04, "square", 0.14))],
    "sell":     [(0.00, "tone", (1568, 0.04, "square", 0.12)), (0.045, "tone", (2093, 0.08, "square", 0.12))],
    "complete": [(0.00, "ping", (523, 0.35, 0.3)), (0.09, "ping", (659, 0.35, 0.3)), (0.18, "ping", (784, 0.5, 0.3))],
    "research": [(0.00, "ping", (392, 0.4, 0.25)), (0.12, "ping", (523, 0.4, 0.25)), (0.24, "ping", (659, 0.4, 0.25)),
                 (0.36, "ping", (1046, 0.7, 0.25))],
    "field":    [(0.00, "ping", (1046, 0.9, 0.35)), (0.45, "ping", (1046, 0.7, 0.12))],
    "alert":    [(0.00, "tone", (440, 0.09, "square", 0.2)), (0.14, "tone", (440, 0.09, "square", 0.2))],
    "contract": [(0.00, "ping", (784, 0.5, 0.3)), (0.10, "ping", (988, 0.5, 0.3)), (0.20, "ping", (1175, 0.6, 0.3)),
                 (0.30, "ping", (1568, 0.9, 0.25))],
    "offer":    [(0.00, "tone", (1175, 0.05, "square", 0.12)), (0.08, "tone", (1175, 0.05, "square", 0.12))],
    "static":   [(0.00, "noise", (0.55, 0.35)), (0.05, "sweep", (2400, 900, 0.3, "sine", 0.06))],
    "tick":     [(0.00, "tone", (2093, 0.012, "square", 0.08))],
    "won":      [(0.00, "ping", (523, 0.6, 0.3)), (0.15, "ping", (659, 0.6, 0.3)), (0.30, "ping", (784, 0.6, 0.3)),
                 (0.45, "ping", (1046, 1.2, 0.3)), (0.45, "ping", (523, 1.2, 0.2))],
    "lost":     [(0.00, "sweep", (440, 110, 1.2, "triangle", 0.35))],
    "rolled":   [(0.00, "tone", (784, 0.04, "square", 0.14)), (0.06, "tone", (988, 0.04, "square", 0.14)),
                 (0.12, "tone", (1175, 0.06, "square", 0.14))],
}
ENVELOPE_EDGE_S = 0.004  # attack/release on every tone, to avoid clicks

# CRT hum: harmonics of 60 Hz (amplitude per harmonic); louder with power load.
HUM_HARMONICS = ((60, 1.0), (120, 0.5), (180, 0.25), (300, 0.08))
HUM_VOLUME = (0.035, 0.11)   # at no load .. full load

# Ambient music: slow pad chords (whole-Hz pitches) and sparse, echoing notes.
PAD_CHORDS = (               # D minor-ish progression: Dm9, Bbmaj7, Fmaj7, C(add9)
    (147, 220, 262, 330, 349),
    (117, 175, 220, 294, 349),
    (175, 262, 330, 440, 523),
    (131, 196, 247, 294, 392),
)
PAD_DETUNE_HZ = 1            # a second, detuned voice per note gives a slow 1 Hz shimmer
PAD_SECOND_HARMONIC = 0.12
PAD_CHORD_S = 14.0           # each chord lasts this long
PAD_FADE_MS = 5000
PAD_VOLUME = 0.07            # per note
PLUCK_SCALE = (587, 659, 698, 784, 880, 1047, 1175)  # D minor pentatonic-ish, upper octaves
PLUCK_GAP_S = (2.0, 6.0)
PLUCK_DECAY_S = 1.4
PLUCK_VOLUME = 0.12
PLUCK_ECHOES = ((0.42, 0.45), (0.84, 0.2))  # (delay s, relative volume)
MUSIC_VOLUME = 1.0

# Mute cycle (M): all on -> effects only -> silent.
MODES = ("all", "sfx", "off")
