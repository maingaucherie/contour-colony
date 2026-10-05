import unittest
from array import array

from game.audio import synth
from game.content import audio as A
from game.sim.terrain import run_to_completion

RATE = 8000  # small, to keep the test fast


class SynthTests(unittest.TestCase):
    def test_loop_notes_are_seamless(self):
        table = synth.sine_table(RATE, A.PAD_SECOND_HARMONIC)
        note = synth.loop_note(220, table, A.PAD_DETUNE_HZ, 1.0, RATE)
        self.assertEqual(len(note), RATE)
        # The sample after the last one (index RATE) would equal sample 0.
        nxt = (table[(RATE * 220) % RATE] + table[(RATE * 221) % RATE]) * 0.5
        self.assertAlmostEqual(nxt, note[0])

    def test_bank_has_every_sound_as_int16(self):
        bank = run_to_completion(synth.build_bank(RATE, 2))
        for name in A.SFX:
            self.assertIn("sfx:" + name, bank)
        self.assertIn("hum", bank)
        for chord in A.PAD_CHORDS:
            for f in chord:
                self.assertEqual(len(bank[f"pad:{f}"]), RATE * 2)  # one second, stereo
        for data in bank.values():
            self.assertIsInstance(data, array)
            self.assertEqual(data.typecode, "h")
            self.assertEqual(len(data) % 2, 0)

    def test_sounds_stay_inside_16_bit(self):
        samples = synth.sfx(A.SFX["complete"], RATE)
        self.assertLessEqual(max(abs(v) for v in samples), 1.0)

    def test_music_plan_changes_chords_on_schedule_and_echoes_plucks(self):
        plan = synth.MusicPlan(seed=1)
        chords, plucks = [], 0
        t = 0.0
        while t < A.PAD_CHORD_S * 3 + 1:
            for action in plan.update(t):
                if action[0] == "chord":
                    chords.append(t)
                else:
                    plucks += 1
            t += 0.1
        self.assertEqual(len(chords), 4)
        self.assertAlmostEqual(chords[1] - chords[0], A.PAD_CHORD_S, delta=0.11)
        self.assertGreater(plucks, 3)


if __name__ == "__main__":
    unittest.main()
