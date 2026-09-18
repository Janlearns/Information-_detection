"""Rank search metadata before fetching any destination website."""
from urllib.parse import urlsplit, urlunsplit
from app.evidence import compare_pair
from app.ordinal_facts import parse_claim, compare_ordinal

# Experimental retrieval threshold, not a fact-verification confidence level.
MIN_RELEVANCE = 0.5


def rank_candidates(claim, hits, limit=5):
    candidates, seen = [], set()
    ordinal = parse_claim(claim)
    for hit in hits:
        raw_url = hit.get('href', '')
        try:
            parsed = urlsplit(raw_url)
            if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
                continue
        except ValueError:
            continue
        url = urlunsplit(parsed._replace(fragment=''))
        if url in seen:
            continue
        seen.add(url)
        title = (hit.get('title') or '').strip()
        snippet = (hit.get('body') or hit.get('snippet') or '').strip()
        description = '\n'.join(part for part in (title, snippet) if part)
        if not description:
            candidates.append({'url': url, 'title': title, 'relevance': None,
                               'selected': False, 'reason': 'Judul dan ringkasan tidak tersedia.'})
            continue
        direct = compare_ordinal(description, ordinal) if ordinal else None
        if direct and direct['facts']:
            score = 1.0  # Exact retrieval match, not truth confidence.
        else:
            contradiction, support, neutral = compare_pair(description, claim)
            score = contradiction + support
        # Contradictory evidence is just as relevant as supporting evidence.
        candidates.append({'url': url, 'title': title, 'relevance': score,
                           'explicit_ordinal': bool(direct and direct['facts']),
                           'selected': False, 'reason': 'Hubungan dengan klaim belum cukup kuat.'})
    candidates.sort(key=lambda item: item['relevance'] if item['relevance'] is not None else -1, reverse=True)
    selected, hosts = [], set()
    for item in candidates:
        if item['relevance'] is None or item['relevance'] < MIN_RELEVANCE:
            continue
        host = urlsplit(item['url']).hostname.lower().removeprefix('www.')
        if host in hosts:
            item['reason'] = 'Website yang sama sudah diwakili hasil lebih relevan.'
        elif len(selected) >= limit:
            item['reason'] = 'Di luar lima website paling relevan.'
        else:
            hosts.add(host)
            item.update(selected=True, reason='Dipilih berdasarkan hubungan makna judul/ringkasan dengan klaim.')
            selected.append(item)
    return {'selected': selected, 'candidates': candidates, 'threshold': MIN_RELEVANCE,
            'method': 'Transformer NLI: skor mendukung + membantah; ringkasan hanya untuk seleksi, bukan bukti.'}
