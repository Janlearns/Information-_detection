"""Describe existing search failures without hiding them as empty evidence."""


def error_kind(exc):
    message = str(exc).lower()
    if 'no results' in message:
        return 'empty'
    if 'timeout' in type(exc).__name__.lower() or 'timed out' in message:
        return 'timeout'
    if any(word in message for word in ('429', 'ratelimit', 'rate limit', 'captcha')):
        return 'rate_limit'
    if any(word in message for word in ('certificate', 'ssl', 'tls')):
        return 'certificate'
    return 'connection'


def summarize_search(attempts, hit_count):
    counts = {}
    for attempt in attempts:
        status = attempt['status']
        counts[status] = counts.get(status, 0) + 1
    failures = sum(value for key, value in counts.items() if key not in {'success', 'empty'})
    status = ('partial' if failures else 'success') if hit_count else ('failed' if failures else 'empty')
    labels = {'timeout': 'melewati batas waktu', 'rate_limit': 'dibatasi layanan pencarian',
              'certificate': 'gagal memverifikasi sertifikat koneksi', 'connection': 'gagal terhubung',
              'empty': 'tanpa hasil'}
    sent_counts = {}
    deferred = 0
    for attempt in attempts:
        if attempt.get('deferred'):
            deferred += 1
        else:
            key = attempt['status']
            sent_counts[key] = sent_counts.get(key, 0) + 1
    detail = ', '.join(f'{sent_counts[key]} percobaan {label}' for key, label in labels.items() if sent_counts.get(key))
    if deferred:
        detail = ', '.join(filter(None, [detail, f'{deferred} kueri ditunda tanpa permintaan baru']))
    if status == 'failed':
        message = 'Pencarian sumber gagal: ' + detail + '. Kegagalan akses bukan bukti bahwa klaim salah atau informasinya tidak ada.'
    elif status == 'empty':
        message = 'Layanan pencarian tidak mengembalikan kandidat untuk kueri yang dicoba.'
    elif status == 'partial':
        message = 'Sebagian pencarian berhasil; ' + detail + '.'
    else:
        message = ''
    return {'status': status, 'attempts': attempts, 'candidate_count': hit_count, 'message': message}
