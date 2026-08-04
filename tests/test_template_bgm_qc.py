import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "claude/series-studio/template/tools/bgm_qc.py"
SPEC = importlib.util.spec_from_file_location("template_bgm_qc", MODULE_PATH)
assert SPEC and SPEC.loader
bgm_qc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bgm_qc)


class TemplateBgmVocalQcTests(unittest.TestCase):
    def test_detection_resets_whisper_context_between_segments(self):
        segment = SimpleNamespace(start=1, end=2, text="clear voice", no_speech_prob=0.1, avg_logprob=-0.2)

        class Model:
            def transcribe(self, path, **kwargs):
                self.path = path
                self.kwargs = kwargs
                return iter([segment]), None

        model = Model()
        vocals = bgm_qc.detect_vocals("music.mp3", model)

        self.assertEqual(model.path, "music.mp3")
        self.assertFalse(model.kwargs["condition_on_previous_text"])
        self.assertFalse(model.kwargs["vad_filter"])
        self.assertEqual(model.kwargs["beam_size"], 5)
        self.assertEqual([item["text"] for item in vocals], ["clear voice"])

    def test_rejects_speech_and_sung_phrases_but_ignores_low_confidence_music(self):
        segments = [
            SimpleNamespace(start=0, end=2, text="a clear voice", no_speech_prob=0.1, avg_logprob=-0.2),
            SimpleNamespace(start=2, end=5, text="see you in the next one", no_speech_prob=0.77, avg_logprob=-0.5),
            SimpleNamespace(start=5, end=7, text="Music", no_speech_prob=0.5, avg_logprob=-1.2),
        ]

        vocals = bgm_qc.filter_confident_vocal_segments(segments)

        self.assertEqual([item["text"] for item in vocals], ["a clear voice", "see you in the next one"])


if __name__ == "__main__":
    unittest.main()
