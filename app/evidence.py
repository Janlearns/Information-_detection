"""Compare retrieved passages with the claim, not with category descriptions."""
import re
from urllib.parse import urlsplit
from app import classifier
from app.ordinal_facts import parse_claim, looks_like_ordinal, compare_ordinal

RELATIONS = ('Bukti membantah klaim', 'Bukti mendukung klaim', 'Bukti belum cukup / tidak relevan')


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
    comparisons, seen = [], set()
    ordinal = parse_claim(claim)
    numerical = ordinal is not None or looks_like_ordinal(claim)
    # Use only fetched fact-check passages. Identical copies and same-host pages
    # must not multiply their influence in the aggregate.
    for source in sources:
        if source.get('purpose') != 'Pemeriksaan fakta':
            continue
        excerpt = source.get('text', source.get('excerpt', '')).strip()
        host = urlsplit(source['url']).hostname
        fingerprint = re.sub(r'\W+', '', excerpt.lower())
        if not excerpt or host in seen or fingerprint in seen:
            continue
        seen.update((host, fingerprint))
        detail = compare_ordinal(excerpt, ordinal) if numerical else None
        if detail:
            values = [float(detail['relation'] == relation) for relation in ('contradict', 'support', 'unknown')]
        else:
            values = compare_pair(excerpt, claim)
        comparisons.append({'url': source['url'], 'excerpt': source.get('excerpt', excerpt),
                            'characters_analyzed': len(excerpt), 'reading_complete': True,
                            'scores': dict(zip(RELATIONS, values)),
                            'method': 'ordinal_comparison' if numerical else 'nli',
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
        return {'label': 'Komposisi bukti nomor urut', 'scores': scores, 'comparisons': comparisons,
                'method': 'ordinal_comparison', 'counts': counts, 'claim_fact': ordinal,
                'observed_numbers': observed, 'summary': summary,
                'warning': 'Persentase adalah proporsi sumber terbaca setelah deduplikasi, bukan keyakinan AI atau peluang hoaks. Sumber yang berisi angka bertentangan atau hubungan orang-jabatan yang ambigu dihitung belum cukup. Sumber bisa keliru atau saling menyalin.',
                'reason': 'Seluruh teks dipindai untuk mencocokkan orang, jabatan, lingkup, dan nomor urut. Tidak memakai tebakan NLI untuk menyamakan angka berbeda.',
                'truncated': False}
    return {'label': 'Persentase hubungan bukti', 'scores': scores,
            'comparisons': comparisons, 'model': classifier.MODEL_ID,
            'warning': 'Persentase adalah skor hubungan kutipan dengan klaim, bukan probabilitas hoaks. Distribusi skor kalimat yang dinilai relevan dirata-ratakan dengan bobot relevansi, kemudian antarwebsite. Angka belum dikalibrasi; sumber bisa keliru atau saling menyalin.',
            'reason': f'Seluruh teks dari {len(comparisons)} website dibandingkan dengan klaim sampai bagian akhir. Persentase antarwebsite dirata-ratakan tanpa putusan mutlak.',
            'truncated': False}
