"""Configuration checks use isolated processes and synthetic tokens."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class ConfigTests(unittest.TestCase):
    def check_config(self, content, overrides, assertion):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            package = folder / 'app'
            package.mkdir()
            for name in ('__init__.py', 'config.py'):
                (package / name).write_bytes((root / 'app' / name).read_bytes())
            if content is not None:
                (folder / '.env').write_text(content, encoding='utf-8-sig')
            env = {key: value for key, value in os.environ.items()
                   if key not in {'MODEL_ID', 'HF_TOKEN', 'PYTHON_DOTENV_DISABLED'}}
            env.update(PYTHONPATH=str(folder), **overrides)
            result = subprocess.run([sys.executable, '-c', 'from app.config import MODEL_ID, MODEL_TOKEN; ' + assertion],
                                    cwd=package, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_file_uses_public_model_without_token(self):
        self.check_config(None, {}, "assert MODEL_ID == 'MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli'; assert MODEL_TOKEN is False")

    def test_loads_project_file_from_other_directory(self):
        self.check_config('MODEL_ID=test/model\nHF_TOKEN=fake-test-token\n', {},
                          "assert MODEL_ID == 'test/model'; assert MODEL_TOKEN == 'fake-test-token'")

    def test_process_environment_wins(self):
        self.check_config('MODEL_ID=file/model\nHF_TOKEN=fake-file-token\n',
                          {'MODEL_ID': 'process/model', 'HF_TOKEN': 'fake-process-token'},
                          "assert MODEL_ID == 'process/model'; assert MODEL_TOKEN == 'fake-process-token'")

    def test_empty_values_keep_safe_defaults(self):
        self.check_config('MODEL_ID=\nHF_TOKEN=\n', {},
                          "assert MODEL_ID; assert MODEL_TOKEN is False")
