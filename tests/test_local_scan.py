import base64
import io
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from app.local_scan import prepare_file


class LocalScanTests(unittest.TestCase):
    def test_text_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'claim.txt'
            path.write_text('FOMO', encoding='utf-16')
            self.assertEqual(prepare_file(path).text, 'FOMO')
            path.write_text('x' * 30001, encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare_file(path)

    def test_image_is_resized_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'photo.png'
            Image.new('RGB', (2000, 1000), 'white').save(path)
            original = path.read_bytes()
            result = prepare_file(path)
            self.assertEqual(result.kind, 'image')
            with Image.open(io.BytesIO(base64.b64decode(result.frame.split(',')[1]))) as img:
                self.assertEqual(img.size, (1400, 700))
            self.assertEqual(path.read_bytes(), original)

    def test_unsupported_and_folder_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'program.exe'
            path.write_bytes(b'not media')
            for target in [directory, path]:
                with self.assertRaises(ValueError):
                    prepare_file(target)
