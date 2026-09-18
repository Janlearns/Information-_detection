"""Prepare explicitly selected local files for the shared scan engine."""
import base64
import io
from pathlib import Path
from types import SimpleNamespace

IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tif', '.tiff'}
VIDEO_TYPES = {'.mp4', '.mkv', '.webm', '.mov', '.avi', '.m4v'}
TEXT_TYPES = {'.txt', '.md', '.srt', '.vtt'}


def image_data(image):
    image = image.convert('RGB')
    image.thumbnail((1400, 1400))
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=85)
    return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode('ascii')


def prepare_file(filename, video_seconds=0):
    path = Path(filename).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError('Pilih satu file, bukan folder.')
    payload = SimpleNamespace(kind='text', text='', frame='', media_note='')
    suffix = path.suffix.lower()
    if suffix in TEXT_TYPES:
        if path.stat().st_size > 2_000_000:
            raise ValueError('File teks melebihi batas 2 MB.')
        data = path.read_bytes()
        encoding = 'utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
        try:
            payload.text = data.decode(encoding)
        except UnicodeError as exc:
            raise ValueError('Simpan file teks sebagai UTF-8 atau UTF-16 lalu coba lagi.') from exc
        if len(payload.text) > 30000:
            raise ValueError('Teks melebihi 30.000 karakter. Pilih potongan teks yang ingin diperiksa.')
        if not payload.text.strip():
            raise ValueError('File teks kosong.')
    elif suffix in IMAGE_TYPES:
        from PIL import Image, ImageOps
        if path.stat().st_size > 50_000_000:
            raise ValueError('Foto melebihi batas 50 MB.')
        with Image.open(path) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError('Foto melebihi batas 40 megapiksel.')
            payload.frame = image_data(ImageOps.exif_transpose(image))
        payload.kind = 'image'
        payload.media_note = 'Sumber: foto lokal yang dipilih.'
    elif suffix in VIDEO_TYPES:
        import cv2
        from PIL import Image
        if video_seconds < 0:
            raise ValueError('Posisi video tidak boleh negatif.')
        video = cv2.VideoCapture(str(path))
        try:
            if not video.isOpened():
                raise ValueError('Video tidak dapat dibuka. Format atau codec belum didukung.')
            video.set(cv2.CAP_PROP_POS_MSEC, video_seconds * 1000)
            ok, frame = video.read()
            if not ok:
                raise ValueError('Frame video tidak dapat dibaca pada posisi tersebut.')
            payload.frame = image_data(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        finally:
            video.release()
        payload.kind = 'video'
        payload.media_note = f'Sumber: satu frame video lokal pada detik {video_seconds:g}; audio tidak dianalisis.'
    else:
        raise ValueError('Format belum didukung. Pilih TXT, MD, SRT, VTT, foto, atau video.')
    return payload
