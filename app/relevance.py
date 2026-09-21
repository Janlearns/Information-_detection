"""Rank search metadata before fetching any destination website."""
from urllib.parse import urlsplit, urlunsplit
from app.evidence import compare_pair
from app.ordinal_facts import parse_claim, compare_ordinal
from app.text_units import split_statements

# Experimental retrieval threshold, not a fact-verification confidence level.
MIN_RELEVANCE = 0.5


def rank_candidates(claim, hits, limit=5):
    candidates, seen = [], set()
    statements = split_statements(claim) or [claim]
    ordinals = [parse_claim(statement) for statement in statements]
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
        statement_scores, explicit = [], False
        for statement, ordinal in zip(statements, ordinals):
            direct = compare_ordinal(description, ordinal) if ordinal else None
            if direct and direct['facts']:
                statement_scores.append(1.0)
                explicit = True
            else:
                contradiction, support, neutral = compare_pair(description, statement)
                statement_scores.append(contradiction + support)
        score = max(statement_scores)
        # Contradictory evidence is just as relevant as supporting evidence.
        candidates.append({'url': url, 'title': title, 'relevance': score,
                           'explicit_ordinal': explicit, 'statement_scores': statement_scores,
                           'selected': False, 'reason': 'Hubungan dengan klaim belum cukup kuat.'})
    candidates.sort(key=lambda item: item['relevance'] if item['relevance'] is not None else -1, reverse=True)
    selected, hosts, covered = [], set(), set()
    pending = list(candidates)
    while pending:
        def priority(item):
            host = urlsplit(item['url']).hostname.lower().removeprefix('www.')
            fresh = sum(score >= MIN_RELEVANCE and i not in covered
                        for i, score in enumerate(item.get('statement_scores', [])))
            return host not in hosts, fresh, item['relevance'] if item['relevance'] is not None else -1
        item = max(pending, key=priority) if len(statements) > 1 else pending[0]
        pending.remove(item)
        if item['relevance'] is None or item['relevance'] < MIN_RELEVANCE:
            continue
        host = urlsplit(item['url']).hostname.lower().removeprefix('www.')
        if host in hosts:
            item['reason'] = 'Website yang sama sudah diwakili hasil lebih relevan.'
        elif len(selected) >= limit:
            item['reason'] = 'Kandidat cadangan jika sumber pilihan gagal dibaca.'
        else:
            hosts.add(host)
            item.update(selected=True, reason='Dipilih berdasarkan hubungan makna judul/ringkasan dengan klaim.')
            selected.append(item)
            covered.update(i for i, score in enumerate(item['statement_scores']) if score >= MIN_RELEVANCE)
    return {'selected': selected, 'candidates': candidates, 'threshold': MIN_RELEVANCE,
            'method': 'Transformer NLI: skor mendukung + membantah; ringkasan hanya untuk seleksi, bukan bukti.'}
