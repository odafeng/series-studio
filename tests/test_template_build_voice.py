import os
import runpy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "claude" / "series-studio" / "template" / "tools" / "build_voice.py"


class TemplateBuildVoiceTests(unittest.TestCase):
    def load_tool(self, manifest=None):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        (root / "episodes/ep01/script").mkdir(parents=True)
        (root / "remotion/src").mkdir(parents=True)
        (root / "series.yaml").write_text(
            """voice:
  provider: minimax
  model: speech-2.8-hd
  voice_id: test_voice
  speed: 1.15
  emotion: happy
  vol: 1.0
  pitch: 0
  tts_replacements:
    現在進 RL 的核心: 現在進 R L 的核心
""",
            encoding="utf-8",
        )
        (root / "episodes/ep01/script/ep01-script.md").write_text(
            "## 00 開場\n\n**【旁白】**\n現在進 RL 的核心。\n",
            encoding="utf-8",
        )
        if manifest is not None:
            (root / "remotion/src/ep01Data.ts").write_text(manifest, encoding="utf-8")
        old_cwd, old_argv = Path.cwd(), sys.argv[:]
        try:
            os.chdir(root)
            sys.argv = [str(TOOL), "--ep", "1", "--dry"]
            module = runpy.run_path(str(TOOL))
        finally:
            os.chdir(old_cwd)
            sys.argv = old_argv
        self.addCleanup(tmp.cleanup)
        return module

    def test_model_replacement_and_hash_are_model_aware(self):
        module = self.load_tool()
        self.assertEqual(module["MODEL"], "speech-2.8-hd")
        self.assertEqual(module["audio_text"]("現在進 RL 的核心"), "現在進 R L 的核心")
        self.assertNotEqual(
            module["cue_hash"]("同一句", "speech-02-hd"),
            module["cue_hash"]("同一句", "speech-2.8-hd"),
        )

    def test_manifest_without_model_remains_legacy(self):
        module = self.load_tool('export const EP01 = {"fps": 30, "cues": []} as const;')
        self.assertEqual(module["MODEL"], "speech-02-hd")


if __name__ == "__main__":
    unittest.main()
