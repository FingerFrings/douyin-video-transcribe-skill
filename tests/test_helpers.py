import importlib.util
import sys
import unittest
from pathlib import Path


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load module from {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class HelperTests(unittest.TestCase):
    def test_installer_helpers_use_requested_venv_path(self):
        module = load_module(Path('scripts/install_faster_whisper.py'), 'install_faster_whisper')
        venv = Path('/tmp/example-venv')
        python = module.python_in_venv(venv)
        self.assertTrue(str(python).endswith('bin/python') or str(python).endswith('Scripts/python.exe'))
        mirror = module.PyPIMirror('test', 'https://example.invalid/simple', 'example.invalid')
        cmd = module.build_install_command(python, mirror)
        self.assertEqual(str(python), cmd[0])
        self.assertIn('faster-whisper', cmd)
        self.assertIn('--trusted-host', cmd)

    def test_transcriber_writes_srt_and_text_from_segments(self):
        import tempfile
        module = load_module(Path('scripts/transcribe_faster_whisper.py'), 'transcribe_faster_whisper')

        class Segment:
            def __init__(self, start, end, text):
                self.start = start
                self.end = end
                self.text = text

        with tempfile.TemporaryDirectory() as tmp:
            out = module.write_outputs([
                Segment(0, 1.25, ' hello   world '),
                Segment(1.25, 2.5, 'second line'),
            ], Path(tmp))

            self.assertTrue(out.srt_path.read_text(encoding='utf-8').startswith('1\n00:00:00,000 --> 00:00:01,250\nhello world'))
            self.assertEqual(out.text_path.read_text(encoding='utf-8'), 'hello world second line\n')

    def test_repository_skill_is_self_contained(self):
        skill = Path('SKILL.md').read_text(encoding='utf-8')
        self.assertIn('scripts/install_faster_whisper.py', skill)
        self.assertIn('scripts/transcribe_faster_whisper.py', skill)
        self.assertNotIn('video-to-subtitle-summary', skill)
        self.assertGreaterEqual(len(list(Path('scripts').glob('*.py'))), 2)


if __name__ == '__main__':
    unittest.main()
