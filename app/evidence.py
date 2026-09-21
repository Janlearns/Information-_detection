"""Compare retrieved passages with the claim, not with category descriptions."""
import re
from urllib.parse import urlsplit
from app import classifier
from app.ordinal_facts import parse_claim, looks_like_ordinal, compare_ordinal, semantic_candidates
from app.text_units import split_statements

RELATIONS = ('Bukti membantah klaim', 'Bukti mendukung klaim', 'Bukti belum cukup / tidak relevan')


def summarize_decisive_evidence(counts):
    """Agreement is conditional on decisive evidence, separate from coverage."""
    decisive = counts['support'] + counts['contradict']
    total = decisive + counts['unknown']
    if not decisive:
        status = 'Belum cukup bukti'
    elif counts['support'] and counts['contradict']:
        status = 'Bukti saling bertentangan'
    elif counts['support']:
        status = 'Didukung bukti yang ditemukan'
    else:
        status = 'Dibantah bukti yang ditemukan'
    return {
        'status': status,
        'decisive_sources': decisive, 'total_sources': total,
        'unknown_sources': counts['unknown'],
        'scores': ({'Mendukung': counts['support'] / decisive,
                    'Membantah': counts['contradict'] / decisive} if decisive else None),
        'coverage': f"{decisive} dari {total} sumber unik memberi bukti tegas; {counts['unknown']} belum cukup/ambigu.",
        'note': 'Persentase kesepakatan hanya dihitung dari sumber yang mendukung atau membantah, bukan peluang kebenaran. Sumber belum cukup/ambigu tidak ikut pembagi. Target lima sumber terbaca bukan jaminan kepastian.',
    }


def token_windows(tokens, size, overlap=32):
    start = 0
    while start < len(tokens):
        yield tokens[start:start + size]
        if start + size >= len(tokens):
            break
        start += size - min(overlap, size - 1)


def aggregate_passages(rows):
    # Average complete distributions, never independent maxima from different
    # sentences. Low-relevance passages do not overwhelm explicit evidence.
    relevant = [row for row in rows if row[0] + row[1] >= .5]
    if not relevant:
        return [0., 0., 1.]
    weights = [row[0] + row[1] for row in relevant]
    return [sum(row[i] * weight for row, weight in zip(relevant, weights)) / sum(weights)
            for i in range(3)]


def compare_pair(premise, claim):
    import torch
    with classifier._lock:
        if classifier._pipeline is None:
            from transformers import pipeline
            classifier._pipeline = pipeline('zero-shot-classification', model=classifier.MODEL_ID,
                                             device=-1, trust_remote_code=False)
        engine = classifier._pipeline
        mapping = {str(k).lower(): v for k, v in engine.model.config.label2id.items()}
        ids = [next((v for k, v in mapping.items() if k.startswith(name)), None)
               for name in ('contradiction', 'entailment', 'neutral')]
        if None in ids:
            raise RuntimeError('Model tidak menyediakan label hubungan bukti yang dikenali.')
        tokenizer = engine.tokenizer
        premise_segments = [tokenizer.encode(part, add_special_tokens=False, verbose=False)
                            for part in re.split(r'(?<=[.!?])\s+|\n+', premise) if part.strip()]
        claim_tokens = tokenizer.encode(claim, add_special_tokens=False, verbose=False)
        if not premise_segments or not claim_tokens:
            raise ValueError('Teks bukti atau klaim kosong.')
        engine.model.eval()
        claim_results = []
        for claim_window in token_windows(claim_tokens, 160):
            room = 512 - len(claim_window) - tokenizer.num_special_tokens_to_add(pair=True)
            rows, batch = [], []
            def flush():
                encoded = tokenizer.pad(batch, padding=True, return_tensors='pt')
                with torch.inference_mode():
                    probabilities = engine.model(**encoded).logits.softmax(-1).tolist()
                rows.extend([row[i] for i in ids] for row in probabilities)
                batch.clear()
            for window in (window for segment in premise_segments for window in token_windows(segment, min(room, 160))):
                batch.append(tokenizer.prepare_for_model(window, pair_ids=claim_window,
                             truncation=False, return_attention_mask=True))
                if len(batch) == 8:
                    flush()
            if batch:
                flush()
            claim_results.append(aggregate_passages(rows))
        return [sum(row[i] for row in claim_results) / len(claim_results) for i in range(3)]


def classify_evidence(claim, sources):
    statements = split_statements(claim)
    if len(statements) <= 1:
        return classify_statement(statements[0] if statements else claim, sources)
    results = []
    for statement in statements:
        result = classify_statement(statement, sources)
        if result is None:
            return None
        results.append({'text': statement, **result})
    # Preserve each sentence's distribution. One supported sentence must not
    # silently certify the other statements in a long document.
    return {
        'label': 'Hubungan bukti per kalimat', 'method': 'statement_evidence',
        'scores': {label: sum(r['scores'][label] for r in results) / len(results) for label in RELATIONS},
        'statements': results,
        'comparisons': [],
        'summary': f'{len(results)} kalimat unik diperiksa satu per satu terhadap sumber terbaca.',
        'reason': 'Semua kalimat unik dianalisis, termasuk bagian akhir teks. Lihat hasil per kalimat; rata-rata dokumen bukan putusan kebenaran seluruh teks.',
        'warning': 'Skor dirata-ratakan per kalimat, bukan probabilitas hoaks. Pemisahan kalimat belum menyelesaikan rujukan kata ganti atau memecah semua klaim majemuk. Bukti yang tidak tersedia tetap belum cukup.',
        'truncated': False,
    }


def classify_statement(claim, sources):
    comparisons, seen = [], set()
    ordinal = parse_claim(claim)
    numerical = ordinal is not None
    # Use only fetched fact-check passages. Identical copies and same-host pages
    # must not multiply their influence in the aggregate.
    for source in sources:
        if source.get('purpose') != 'Pemeriksaan fakta':
            continue
        excerpt = source.get('text', source.get('excerpt', '')).strip()
        host = (urlsplit(source['url']).hostname or '').lower().removeprefix('www.')
        fingerprint = re.sub(r'\W+', '', excerpt.lower())
        if not excerpt or host in seen or fingerprint in seen:
            continue
        seen.update((host, fingerprint))
        detail = compare_ordinal(excerpt, ordinal) if numerical else None
        semantic_checks = []
        if numerical:
            accepted = []
            for candidate in semantic_candidates(excerpt, ordinal):
                # Ask NLI about the entity-role relation, never ask it to
                # decide whether two different numerical values are equal.
                scope = candidate['country']
                hypothesis = f"{ordinal['subject']} menjabat sebagai {ordinal['role']} {scope}.".replace(' .', '.')
                values = compare_pair(candidate['quote'], hypothesis)
                approved = values[1] >= .90 and values[0] <= .05
                semantic_checks.append({**candidate, 'hypothesis': hypothesis,
                                        'scores': dict(zip(RELATIONS, values)), 'accepted': approved})
                if approved:
                    accepted.append({**candidate, 'method': 'semantic_role_match'})
            if accepted:
                detail = compare_ordinal(excerpt, ordinal, accepted)
        if detail:
            values = [float(detail['relation'] == relation) for relation in ('contradict', 'support', 'unknown')]
        else:
            values = compare_pair(excerpt, claim)
        comparisons.append({'url': source['url'], 'excerpt': source.get('excerpt', excerpt),
                            'characters_analyzed': len(excerpt), 'reading_complete': True,
                            'scores': dict(zip(RELATIONS, values)),
                            'method': 'ordinal_comparison' if numerical else 'nli',
                            'semantic_checks': semantic_checks,
                            **(detail or {})})
    if not comparisons:
        return None
    scores = {label: sum(c['scores'][label] for c in comparisons) / len(comparisons)
              for label in RELATIONS}
    if numerical:
        counts = {relation: sum(c['relation'] == relation for c in comparisons)
                  for relation in ('contradict', 'support', 'unknown')}
        observed = sorted({number for c in comparisons for number in c['observed_numbers']})
        summary = (f"Klaim menyebut {ordinal['role']} ke-{ordinal['number']}. " if ordinal else
                   'Susunan klaim angka belum dapat diuraikan dengan aman. ')
        summary += ('Nomor urut yang ditemukan dalam bukti eksplisit: ' + ', '.join(map(str, observed)) + '. '
                    if observed else 'Belum ditemukan bukti nomor urut yang dapat dicocokkan. ')
        summary += f"{counts['contradict']} sumber membantah, {counts['support']} mendukung, {counts['unknown']} belum cukup/ambigu."
        consensus = summarize_decisive_evidence(counts)
        return {'label': 'Kesepakatan bukti nomor urut', 'scores': scores, 'comparisons': comparisons,
                'consensus': consensus,
                'method': 'ordinal_comparison', 'counts': counts, 'claim_fact': ordinal,
                'observed_numbers': observed, 'summary': summary,
                'warning': 'Persentase adalah proporsi sumber terbaca setelah deduplikasi, bukan keyakinan AI atau peluang hoaks. Sumber yang berisi angka bertentangan atau hubungan orang-jabatan yang ambigu dihitung belum cukup. Sumber bisa keliru atau saling menyalin.',
                'reason': 'Seluruh teks dipindai untuk mencocokkan orang, jabatan, lingkup, dan nomor urut. Kalimat yang tidak cocok dengan pola langsung diperiksa secara semantik untuk hubungan orang-jabatan; angka tetap diambil dari pasangan jabatan-nomor dalam sumber. Pencocokan semantik dapat keliru; periksa kutipannya.',
                'truncated': False}
    return {'label': 'Persentase hubungan bukti', 'scores': scores,
            'comparisons': comparisons, 'model': classifier.MODEL_ID,
            'method': 'nli',
            'numeric_caution': looks_like_ordinal(claim),
            'warning': 'Persentase adalah skor hubungan kutipan dengan klaim, bukan probabilitas hoaks. Distribusi skor kalimat yang dinilai relevan dirata-ratakan dengan bobot relevansi, kemudian antarwebsite. Angka belum dikalibrasi; sumber bisa keliru atau saling menyalin. NLI dapat keliru pada angka, negasi, dan rujukan kata ganti; hasil semantik bukan verifikasi numerik eksak.',
            'reason': f'Seluruh teks dari {len(comparisons)} website dibandingkan dengan klaim sampai bagian akhir. Persentase antarwebsite dirata-ratakan tanpa putusan mutlak.',
            'truncated': False}
