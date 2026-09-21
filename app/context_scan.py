"""Explicit browser selections only; no screen monitoring."""
import base64
import io
import re
import http.client
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from app.crawler import crawl, is_retryable_error
from app.evidence import classify_evidence
from app.relevance import rank_candidates, MIN_RELEVANCE
from app.ordinal_facts import parse_claim, compare_ordinal
from app.text_units import search_units
from app.search_status import error_kind, summarize_search
from app.search_session import SearchSession, SearchPaused

search_session = SearchSession()

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
            if not articles and attempt == 0 and any(f.get('retryable') or 'timed out' in f['error'].lower() for f in failures):
                continue
            return articles, failures
        except (ValueError, OSError, http.client.HTTPException) as exc:
            retryable = is_retryable_error(exc)
            if attempt or not retryable:
                return [], [{'url': url, 'error': str(exc), 'retryable': retryable}]


def related_excerpt(body, text):
    # Keep a complete paragraph, including surrounding sentences, without slicing.
    paragraphs = [p.strip() for p in body.splitlines() if p.strip()]
    words = set(re.findall(r'\w{4,}', text.lower()))
    ordinal = parse_claim(text)
    return max(paragraphs, key=lambda p: (bool(ordinal and compare_ordinal(p, ordinal)['facts']),
               len(words & set(re.findall(r'\w{4,}', p.lower())))), default='')


def read_candidates(selection, text, target=5, max_attempts=10):
    """Fill readable-source slots from ranked candidates, with a bounded budget.

    Rank all metadata first. Failure to fetch a page never lowers the relevance
    threshold or turns a search snippet into evidence.
    """
    sources, errors, attempted, queued_hosts, successful_hosts = [], [], [], set(), set()
    ordered = list(selection['selected'])
    ordered.extend(item for item in selection['candidates'] if item not in ordered)
    queue = []
    for item in ordered:
        if item.get('relevance') is None or item['relevance'] < MIN_RELEVANCE:
            continue
        host = (urlsplit(item['url']).hostname or '').lower().removeprefix('www.')
        if not host or host in queued_hosts:
            continue
        queued_hosts.add(host)
        queue.append(item)
    with ThreadPoolExecutor(max_workers=3) as pool:
        while queue and len(sources) < target and len(attempted) < max_attempts:
            count = min(target - len(sources), max_attempts - len(attempted), len(queue))
            batch, queue = queue[:count], queue[count:]
            # Do not start a full extra batch if only one readable slot remains.
            for candidate, (articles, failures) in zip(batch, pool.map(read_source, [item['url'] for item in batch])):
                attempted.append(candidate)
                candidate.update(selected=True, read_status='failed')
                candidate['read_errors'] = [failure['error'] for failure in failures]
                errors.extend(f"{failure.get('url', candidate['url'])}: {failure['error']}" for failure in failures)
                for article in articles:
                    host = (urlsplit(article['url']).hostname or '').lower().removeprefix('www.')
                    body = article.get('text', '').strip()
                    if not body or not host or host in successful_hosts:
                        continue
                    successful_hosts.add(host)
                    sources.append({'title': article['title'], 'url': article['url'],
                                    'excerpt': related_excerpt(body, text), 'text': body,
                                    'relevance': candidate['relevance'], 'characters_read': len(body),
                                    'purpose': 'Pemeriksaan fakta'})
                    candidate['read_status'] = 'read'
                    break
                candidate['reason'] = ('Artikel berhasil dibaca.' if candidate['read_status'] == 'read' else
                                       'Artikel gagal dibaca; kandidat relevan berikutnya dicoba jika anggaran akses masih tersedia.')
    selection['selected'] = attempted
    selection['reading'] = {'attempted_hosts': len(attempted), 'read_hosts': len(sources),
                            'target': target, 'max_attempts': max_attempts,
                            'limit_reached': bool(queue and len(attempted) >= max_attempts and len(sources) < target)}
    return sources, errors


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
    search_status = {'status': 'not_run', 'attempts': [], 'candidate_count': 0, 'message': ''}
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
    query_units, total_query_units = search_units(text)
    search_coverage = {'total_units': total_query_units, 'searched_units': len(query_units),
                       'limited': total_query_units > len(query_units)}
    if query_units:
        try:
            search = DDGS(timeout=10)
            queries = []
            for query in query_units:
                ordinal = parse_claim(query)
                if ordinal:
                    queries.extend([f"{ordinal['subject']} urutan {ordinal['role']} {ordinal['country']}".strip(), query + ' cek fakta'])
                else:
                    queries.extend([query + ' cek fakta', query])
            queries = list(dict.fromkeys(queries))
            hits, attempts = [], []
            for q in queries:
                try:
                    found, cached = search_session.query(search, q)
                    hits.extend(found)
                    attempts.append({'query': q, 'status': 'success' if found else 'empty', 'results': len(found), 'cached': cached})
                except SearchPaused as exc:
                    attempts.append({'query': q, 'status': exc.kind, 'results': 0, 'deferred': True,
                                     'retry_after_seconds': exc.retry_after})
                except Exception as exc:
                    attempts.append({'query': q, 'status': error_kind(exc), 'results': 0})
            search_status = summarize_search(attempts, len(hits))
            search_status['retry_after_seconds'] = search_session.retry_after()
            search_status['cached_queries'] = sum(bool(item.get('cached')) for item in attempts)
            if search_status['retry_after_seconds']:
                search_status['message'] += f" Tunggu sekitar {search_status['retry_after_seconds']} detik sebelum mencoba kueri baru. Kueri yang masih ada di cache dapat dipakai; aplikasi tidak membatasi jumlah scan."
            if search_status['cached_queries']:
                search_status['message'] += f" {search_status['cached_queries']} kueri memakai cache pencarian lokal (maksimal 5 menit); artikel tetap dibaca ulang."
            if search_status['message']:
                errors.append(search_status['message'])
            try:
                if hits:
                    selection = rank_candidates(text, hits)
                    selection['status'] = 'done'
                else:
                    selection['status'] = 'search_' + search_status['status']
            except Exception:
                selection['status'] = 'failed'
                errors.append('Penyaringan relevansi transformer gagal. Website belum dibuka; coba lagi setelah model siap.')
            if selection['status'] == 'done':
                sources, failures = read_candidates(selection, text)
                errors.extend(failures)
            terms.extend(explain_terms(term_candidates(text, getattr(request, 'linked_terms', ())), sources))
        except Exception as exc:
            if search_status['status'] == 'not_run':
                search_status = summarize_search([{'query': '', 'status': error_kind(exc), 'results': 0}], 0)
                errors.append(search_status['message'])
            else:
                errors.append('Pemrosesan hasil pencarian gagal. Periksa sumber yang berhasil dibaca.')
    else:
        errors.append('Tidak ada teks, caption, atau subtitle yang dapat dipakai untuk mencari bukti.')
    analysis, analysis_error = None, ''
    try:
        analysis = classify_evidence(text, sources) if text else None
        if analysis is None:
            if search_status['status'] in {'failed', 'empty'}:
                analysis_error = search_status['message']
            elif selection['status'] == 'failed':
                analysis_error = 'Kandidat ditemukan, tetapi penyaringan relevansi gagal dijalankan.'
            elif selection['candidates'] and not selection['selected']:
                analysis_error = 'Kandidat ditemukan, tetapi belum ada yang lolos seleksi relevansi.'
            elif selection['selected'] and not sources:
                analysis_error = 'Sumber terpilih, tetapi teks artikelnya belum berhasil dibaca. Lihat catatan akses.'
            else:
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
        reason += f"{len(selection['selected'])} dari {len(selection['candidates'])} kandidat dicoba setelah seleksi relevansi; target maksimal 5 sumber terbaca dengan batas 10 percobaan website. "
        if selection.get('reading', {}).get('limit_reached'):
            reason += 'Batas percobaan tercapai; sebagian kandidat belum dibuka. '
    reason += analysis['reason'] if analysis else analysis_error
    if search_coverage['limited']:
        reason += f' Pencarian dibatasi pada {len(query_units)} dari {total_query_units} bagian yang tersebar dari awal sampai akhir; sumber belum tentu mencakup semua kalimat.'
    return {'label': 'Sumber terkait ditemukan' if evidence_count else 'Bukti belum tersedia',
            'verification_status': 'evidence_compared' if analysis else 'not_assessed', 'text': text, 'terms': terms,
            'analysis': analysis, 'analysis_error': analysis_error, 'selection': selection,
            'search_coverage': search_coverage,
            'search': search_status,
            'sources': sources, 'errors': list(dict.fromkeys(errors)), 'limitation': limitation,
            'reason': reason}
