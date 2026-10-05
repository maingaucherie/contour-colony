"""Audio playback: sound effects, CRT hum and generative ambient music.

If the mixer can't start (no audio device), everything here quietly does
nothing, so the game runs the same without sound.
"""

import pygame

from game.content import audio as A
from game.audio.synth import MusicPlan, build_bank


class Audio:
    def __init__(self):
        self.ok = False
        self.rate, self.channels = A.SAMPLE_RATE, 1
        self.sounds = {}
        self.mode = A.MODES[0]
        self.plan = MusicPlan()
        self.pad_channels = []
        self.hum_channel = None
        self.ambient_channels = {}
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(A.SAMPLE_RATE, -16, 1, 512)
            freq, _, channels = pygame.mixer.get_init()
            self.rate, self.channels = freq, channels
            pygame.mixer.set_num_channels(A.CHANNELS)
            pygame.mixer.set_reserved(1 + len(A.AMBIENT_LOOPS))  # channel 0: the hum; then close-up loops
            self.ok = True
        except Exception as exc:  # no device, or a browser without audio
            print("audio disabled:", exc)

    def build(self):
        """Generator for the loader: synthesize every sound, then wrap them."""
        if not self.ok:
            return
        bank = yield from build_bank(self.rate, self.channels)
        try:
            self.sounds = {name: pygame.mixer.Sound(buffer=data) for name, data in bank.items()}
        except Exception as exc:
            print("audio disabled:", exc)
            self.ok = False
            return
        self.hum_channel = pygame.mixer.Channel(0)
        self.hum_channel.play(self.sounds["hum"], loops=-1)
        self.hum_channel.set_volume(0.0)
        for i, kind in enumerate(A.AMBIENT_LOOPS):
            ch = pygame.mixer.Channel(1 + i)
            ch.play(self.sounds[f"ambient:{kind}"], loops=-1)
            ch.set_volume(0.0)
            self.ambient_channels[kind] = ch

    # Controls ----------------------------------------------------------------

    def cycle_mode(self):
        modes = A.MODES
        self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]
        if self.mode != "all":
            for ch in self.pad_channels:
                ch.fadeout(500)
            self.pad_channels = []
            self.plan = MusicPlan()
        return self.mode

    def play(self, name):
        if not self.ok or self.mode == "off":
            return
        sound = self.sounds.get("sfx:" + name)
        if sound is not None:
            ch = pygame.mixer.find_channel()
            if ch is not None:
                ch.set_volume(A.MASTER)
                ch.play(sound)

    # Per frame ------------------------------------------------------------------

    def update(self, now, load, ambient=None):
        """now: seconds; load: power demand / supply (0..1+) for the hum;
        ambient: {category: loudness 0..1} for the close-up sounds."""
        if not self.ok or not self.sounds:
            return
        lo, hi = A.HUM_VOLUME
        hum = 0.0 if self.mode == "off" else (lo + (hi - lo) * max(0.0, min(1.0, load))) * A.MASTER
        self.hum_channel.set_volume(hum)
        for kind, ch in self.ambient_channels.items():
            level = 0.0 if self.mode == "off" or not ambient else ambient.get(kind, 0.0)
            ch.set_volume(level * A.AMBIENT_VOLUME[kind] * A.MASTER)
        if self.mode != "all":
            return
        for action in self.plan.update(now):
            if action[0] == "chord":
                for ch in self.pad_channels:
                    ch.fadeout(A.PAD_FADE_MS)
                self.pad_channels = []
                for f in action[1]:
                    ch = pygame.mixer.find_channel()
                    if ch is None:
                        break
                    ch.set_volume(A.PAD_VOLUME * A.MUSIC_VOLUME * A.MASTER)
                    ch.play(self.sounds[f"pad:{f}"], loops=-1, fade_ms=A.PAD_FADE_MS)
                    self.pad_channels.append(ch)
            else:
                _, note, volume = action
                ch = pygame.mixer.find_channel()
                if ch is not None:
                    ch.set_volume(volume * A.MUSIC_VOLUME * A.MASTER)
                    ch.play(self.sounds[f"pluck:{note}"])
