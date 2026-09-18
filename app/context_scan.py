"""Explicit browser selections only; no screen monitoring."""
import base64
import io
import re
import http.client
from concurrent.futures import ThreadPoolExecutor
from app.crawler import crawl
from app.evidence import classify_evidence
from app.relevance import rank_candidates
from app.ordinal_facts import parse_claim

TERMS = {
    'fomo': 'Fear of missing out: takut tertinggal tren atau pengalaman orang lain.',
    'gaslighting': 'Manipulasi yang membuat seseorang meragukan ingatan atau penilaiannya sendiri.',
    'red flag': 'Tanda peringatan adanya potensi masalah; maknanya bergantung konteks.',
    'clickbait': 'Judul atau tampilan yang memancing klik, sering dengan cara berlebihan.',
    'spill': 'Dalam slang: membagikan cerita atau mengungkap informasi.',
    'literally': 'Secara harfiah; dalam percakapan juga dipakai sebagai penekanan.',
    'hoax': 'Hoaks: informasi palsu yang disajikan seolah benar.',
    'fr': 'Dalam slang: for real, berarti sungguh atau serius.',
    'btw': 'By the way: ngomong-ngomong.',
    'cmiiw': 'Correct me if I am wrong: koreksi jika saya salah.',
}
_reader = None

# Seed vocabulary identifies terms, not their definitions or truth value.
SPECIALIST_TERMS = ('ledakan Kambrium', 'notokorda', 'Haikouichthys',
                    'placodermi', 'conodonta', 'Chondrichthyes', 'Osteichthyes')


def term_candidates(text, linked_terms=()):
    linked = re.findall(r'\[([^\]\n]+)\]\(https?://[^\s)]+\)', text)
    candidates = [*linked_terms, *linked, *SPECIALIST_TERMS]
    if len(text.split()) <= 3 and not re.search(r'\b(adalah|merupakan|presiden|ke\s*\d+)\b', text, re.I):
        candidates.append(text)
    found = []
    for value in candidates:
        term = value.strip(' *_')
        if (3 <= len(term) <= 80 and not term.isdigit() and
                re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I) and
                term.lower() not in TERMS and term.lower() not in {t.lower() for t in found}):
            found.append(term)
    return found[:4]


def read_source(url):
    """Retry transient failures only; never bypass a site's access rules."""
    for attempt in range(2):
        try:
            articles, failures = crawl(url, 1)
            if not articles and attempt == 0 and any('timed out' in f['error'].lower() for f in failures):
                continue
            return articles, failures
        except (OSError, http.client.HTTPException) as exc:
            if attempt:
                return [], [{'url': url, 'error': str(exc)}]
        except ValueError as exc:
            return [], [{'url': url, 'error': str(exc)}]


def related_excerpt(body, text):
    # Keep a complete paragraph, including surrounding sentences, without slicing.
    paragraphs = [p.strip() for p in body.splitlines() if p.strip()]
    words = set(re.findall(r'\w{4,}', text.lower()))
    return max(paragraphs, key=lambda p: (bool(re.search(r'presiden', text, re.I) and re.search(r'presiden.{0,45}ke[ -]*\d+', p, re.I)), len(words & set(re.findall(r'\w{4,}', p.lower())))), default='')


def explain_terms(candidates, sources):
    terms = []
    for term in candidates:
        meaning = 'Penjelasan istilah belum ditemukan dalam lima website yang dipilih.'
        for source in sources:
            sentences = re.split(r'(?<=[.!?])\s+|\n+', source.get('text', source['excerpt']))
            definition = next((sentence for sentence in sentences if term.lower() in sentence.lower()
                and re.search(r'\b(adalah|merupakan|berarti|disebut|is|are|was|were|refers to)\b', sentence, re.I)), None)
            if definition:
                meaning = 'Penjelasan dari sumber (belum divalidasi): ' + definition
                break
        terms.append({'term': term, 'meaning': meaning})
    return terms


def read_frame(data):
    global _reader
    if not data:
        return ''
    from PIL import Image
    import numpy as np
    import easyocr
    prefix, encoded = data.split(',', 1)
    if prefix not in {'data:image/jpeg;base64', 'data:image/png;base64'}:
        raise ValueError('Format gambar tidak didukung.')
    raw = base64.b64decode(encoded, validate=True)
    if len(raw) > 2_000_000:
        raise ValueError('Gambar terlalu besar.')
    with Image.open(io.BytesIO(raw)) as img:
        if img.width * img.height > 4_000_000:
            raise ValueError('Resolusi gambar terlalu besar.')
        pixels = np.array(img.convert('RGB'))
    if _reader is None:
        _reader = easyocr.Reader(['id', 'en'], gpu=False)
    return ' '.join(_reader.readtext(pixels, detail=0, paragraph=True))

def scan(request):
    from ddgs import DDGS
    errors, sources = [], []
    selection = {'selected': [], 'candidates': [], 'status': 'not_run'}
    text = request.text.strip()
    if request.kind != 'text':
        try:
            text = ' '.join(filter(None, [read_frame(request.frame), text]))
        except Exception:
            errors.append('Teks visual belum dapat dibaca. Periksa instalasi OCR dan akses media.')
        if request.media_note:
            errors.append(request.media_note)
    terms = [{'term': term, 'meaning': meaning} for term, meaning in TERMS.items()
             if re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', text, re.I)]
    query = ' '.join(text.split()[:35])
    if query:
        try:
            search = DDGS(timeout=10)
            queries = [query + ' cek fakta', query]
            ordinal = parse_claim(text)
            if ordinal:
                # Do not force the user's disputed number into every search.
                queries = [f"{ordinal['subject']} urutan {ordinal['role']} {ordinal['country']}".strip(), query + ' cek fakta']
            hits = []
            for q in queries:
                try:
                    hits.extend(list(search.text(q, max_results=12)))
                except Exception:
                    errors.append('Pencarian sumber gagal untuk salah satu kueri.')
            try:
                selection = rank_candidates(text, hits)
                selection['status'] = 'done'
            except Exception:
                selection['status'] = 'failed'
                errors.append('Penyaringan relevansi transformer gagal. Website belum dibuka; coba lagi setelah model siap.')
            selected = selection['selected']
            with ThreadPoolExecutor(max_workers=3) as pool:
                results = pool.map(read_source, [item['url'] for item in selected])
                for candidate, (articles, failures) in zip(selected, results):
                    errors.extend(f['error'] for f in failures)
                    for article in articles:
                        excerpt = related_excerpt(article['text'], text)
                        sources.append({'title': article['title'], 'url': article['url'],
                                        'excerpt': excerpt, 'text': article['text'],
                                        'relevance': candidate['relevance'],
                                        'characters_read': len(article['text']), 'purpose': 'Pemeriksaan fakta'})
            terms.extend(explain_terms(term_candidates(text, getattr(request, 'linked_terms', ())), sources))
        except Exception:
            errors.append('Pencarian sumber gagal. Periksa koneksi internet lalu coba scan lagi.')
    else:
        errors.append('Tidak ada teks, caption, atau subtitle yang dapat dipakai untuk mencari bukti.')
    analysis, analysis_error = None, ''
    try:
        analysis = classify_evidence(text, sources) if text else None
        if analysis is None:
            analysis_error = 'Belum ada bukti yang dapat dibandingkan; persentase berbasis bukti belum tersedia.'
    except Exception:
        analysis_error = 'Perbandingan bukti gagal dijalankan. Periksa model lalu coba lagi; kutipan sumber tetap tersedia.'
    limitation = ''
    if request.kind != 'text':
        limitation = 'Analisis memakai teks pada foto/frame video, caption, dan subtitle yang tersedia. Belum mendeteksi manipulasi visual, deepfake, atau audio; video hanya memakai frame saat diklik.'
    evidence_count = sum(s['purpose'] == 'Pemeriksaan fakta' for s in sources)
    reason = (f'{evidence_count} sumber terkait berhasil dibaca. ' if evidence_count else
              'Belum ada sumber pemeriksaan fakta yang berhasil dibaca. ')
    if selection['status'] == 'done':
        reason += f"{len(selection['selected'])} dari {len(selection['candidates'])} kandidat dipilih sebelum website dibuka berdasarkan relevansi judul/ringkasan. "
    reason += analysis['reason'] if analysis else analysis_error
    return {'label': 'Sumber terkait ditemukan' if evidence_count else 'Bukti belum tersedia',
            'verification_status': 'evidence_compared' if analysis else 'not_assessed', 'text': text, 'terms': terms,
            'analysis': analysis, 'analysis_error': analysis_error, 'selection': selection,
            'sources': sources, 'errors': list(dict.fromkeys(errors)), 'limitation': limitation,
            'reason': reason}
