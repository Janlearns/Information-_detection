"""Conservative extraction of Indonesian office ordinals, without a fact database.

Unknown wording, negation, reported false claims and ambiguous attachments abstain.
This parser does not resolve pronouns, aliases, compound claims or office terms.
"""
import re
import unicodedata

UNITS = ('', 'satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan', 'sembilan')


def number_words(number):
    if number < 10:
        return UNITS[number]
    if number == 10:
        return 'sepuluh'
    if number == 11:
        return 'sebelas'
    if number < 20:
        return UNITS[number - 10] + ' belas'
    return UNITS[number // 10] + ' puluh' + (' ' + UNITS[number % 10] if number % 10 else '')


WORDS = {number_words(i): i for i in range(1, 100)}
NUMBER = r'(?:\d{1,4}|' + '|'.join(re.escape(w) for w in sorted(WORDS, key=len, reverse=True)) + r')'
ROLE = r'(?:wakil presiden|perdana menteri|presiden)'
COUNTRY = r'(?:republik indonesia|indonesia|ri|amerika serikat|as)'
OFFICE = (rf'(?P<role>{ROLE})(?:\s+(?P<country_before>{COUNTRY}))?\s+'
          rf'ke[\s-]*(?P<number>{NUMBER})(?![\w])(?:\s+(?P<country_after>{COUNTRY}))?')
UNSAFE = re.compile(r'\b(?:bukan|tidak|belum|hoaks|hoax|palsu|klaim|katanya|benarkah|'
                    r'jika|seandainya|andai|akan|calon|diduga|mungkin|konon|apakah)\b|[?"“”]', re.I)
LINK = r'(?:(?:adalah|merupakan|ialah|sebagai)\s+|(?:resmi\s+)?(?:menjabat(?:\s+sebagai)?|menjadi|dilantik(?:\s+sebagai)?|terpilih\s+sebagai)\s+)?'
CLAIM = re.compile(rf'^(?P<subject>[\w]+(?:[ -][\w]+){{0,3}}?)\s+{LINK}{OFFICE}\s*[.!]?$', re.I)
REVERSE_CLAIM = re.compile(rf'^{OFFICE}\s+(?:adalah|ialah|merupakan)\s+(?P<subject>[\w]+(?:[ -][\w]+){{0,3}}?)\s*[.!]?$', re.I)


def normalize_text(text):
    """Normalize typography, not negation, entities or numerical values."""
    text = unicodedata.normalize('NFKC', text)
    text = text.translate(str.maketrans({char: '-' for char in '\u2010\u2011\u2012\u2013\u2014\u2212'}))
    return ' '.join(text.split())


def normalize_claim(text):
    text = normalize_text(text)
    text = re.sub(r'^(?:[-*•]\s+)', '', text)
    return re.sub(r'^(?:pa|pak|bapak|ibu|bu)\.?\s+', '', text, flags=re.I)


def country(value):
    value = (value or '').lower()
    return {'ri': 'indonesia', 'republik indonesia': 'indonesia', 'as': 'amerika serikat'}.get(value, value)


def parse_claim(text):
    text = normalize_claim(text)
    if UNSAFE.search(text):
        return None
    match = CLAIM.fullmatch(text) or REVERSE_CLAIM.fullmatch(text)
    if not match:
        return None
    subject = normalize_claim(match['subject'])
    if re.search(r'\b(?:dan|atau|menurut|kata|bahwa|bapak|pak|presiden)\b', subject, re.I):
        return None
    value = match['number'].lower()
    return {'subject': subject, 'role': match['role'].lower(),
            'number': int(value) if value.isdigit() else WORDS[value],
            'country': country(match['country_before'] or match['country_after'])}


def looks_like_ordinal(text):
    return bool(re.search(rf'{ROLE}.{{0,45}}\bke[\s-]*{NUMBER}\b', normalize_text(text), re.I))


def extract_ordinals(body, claim):
    # A short input name can match a full name, but arbitrary intervening prose
    # cannot join a person to a different person's office.
    subject = r'(?i:' + re.escape(claim['subject']) + r')(?:\s+[A-Z][a-z]+){0,2}'
    office = r'(?i:' + OFFICE + ')'
    forward = re.compile(rf'(?<!\w){subject}\s+(?i:{LINK}){office}')
    reverse = re.compile(rf'{office}\s*[,":-]?\s*(?:(?i:adalah|ialah|merupakan)\s+)?(?:(?i:jenderal\s+tni\s*\(purn\)\s*))?{subject}(?!\w)')
    found = []
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', body):
        sentence = normalize_text(sentence)
        if not sentence or UNSAFE.search(sentence) or re.search(r'\b(?:dan|atau)\b', sentence, re.I):
            continue
        for pattern in (forward, reverse):
            for match in pattern.finditer(sentence):
                # Do not read "Angga Raka Prabowo" as the input entity "Prabowo",
                # nor "wakil presiden" as "presiden".
                prefix = sentence[:match.start()].strip()
                previous = prefix.split()[-1].strip(',:') if prefix else ''
                if previous.lower() in {'wakil', 'mantan'}:
                    continue
                if previous and previous[0].isupper() and previous.lower() not in {'bapak', 'pak', 'presiden', 'ri', 'purn)'}:
                    continue
                role = match['role'].lower()
                scope = country(match['country_before'] or match['country_after'])
                if role != claim['role'] or (claim['country'] and scope != claim['country']):
                    continue
                value = match['number'].lower()
                number = int(value) if value.isdigit() else WORDS[value]
                record = {'number': number, 'country': scope, 'quote': sentence}
                if record not in found:
                    found.append(record)
    return found


def semantic_candidates(body, claim):
    """Candidate facts, not verdicts: keep observed role-number pairs intact.

    Only one distinct number for the requested role is allowed per sentence.
    Multiple people/roles still need semantic relation checking by the caller.
    """
    if not claim:
        return []
    subject = re.compile(r'(?<!\w)' + re.escape(claim['subject']) + r'(?!\w)', re.I)
    candidates = []
    for raw in re.split(r'(?<=[.!?])\s+|\n+', body):
        sentence = normalize_text(raw)
        person = subject.search(sentence)
        if not person or UNSAFE.search(sentence) or extract_ordinals(sentence, claim):
            continue
        # Do not shorten a different person's name to the query's name.
        prefix = sentence[:person.start()].strip()
        previous = prefix.split()[-1].strip(',:') if prefix else ''
        if previous and previous[0].isupper() and previous.lower() not in {'bapak', 'pak', 'presiden', 'ri', 'purn)'}:
            continue
        offices = list(re.finditer(OFFICE, sentence, re.I))
        if not offices:
            continue
        # Require an actual office predicate, not merely visiting/meeting an
        # office holder. NLI alone misclassifies these on the bundled model.
        predicate = re.search(
            r'\b(?:(?:resmi|telah|sudah)\s+)*(?:adalah|merupakan|ialah|menjadi|'
            r'menjabat(?:\s+sebagai)?|dilantik(?:\s+sebagai)?|terpilih\s+sebagai)\s*$',
            sentence[:offices[0].start()], re.I)
        if not predicate:
            continue
        head = sentence[:predicate.start()].strip()
        # Preserve the original sentence for NLI; only remove a delimited
        # apposition when checking who the predicate is attached to.
        head = re.sub(r',[^,]+,', '', head).strip()
        people = re.split(r'\s+dan\s+', head, flags=re.I)
        if len(people) != len(offices):
            continue
        if any(sentence[left.end():right.start()].strip().lower() != 'dan'
               for left, right in zip(offices, offices[1:])):
            continue
        owner = re.compile(re.escape(claim['subject']) + r'(?:\s+[A-Z][a-z]+){0,2}', re.I)
        eligible = []
        for name, office in zip(people, offices):
            if not owner.fullmatch(normalize_claim(name)):
                continue
            if office['role'].lower() != claim['role']:
                continue
            scope = country(office['country_before'] or office['country_after'])
            if claim['country'] and scope != claim['country']:
                continue
            value = office['number'].lower()
            number = int(value) if value.isdigit() else WORDS[value]
            eligible.append({'number': number, 'country': scope, 'quote': sentence})
        if len({(fact['number'], fact['country']) for fact in eligible}) != 1:
            continue
        if eligible and eligible[0] not in candidates:
            candidates.append(eligible[0])
    return candidates


def compare_ordinal(body, claim, additional_facts=()):
    facts = extract_ordinals(body, claim) if claim else []
    facts.extend(fact for fact in additional_facts if fact not in facts)
    values = sorted({fact['number'] for fact in facts})
    scopes = {fact['country'] for fact in facts if fact['country']}
    if not values:
        relation = 'unknown'
        explanation = 'Sistem belum berhasil mengaitkan nama, jabatan, dan nomor urut dalam sumber. Ini bisa berarti bukti tidak tersedia atau susunan kalimat belum dikenali; periksa teks sumber.'
    elif len(values) != 1 or len(scopes) > 1:
        relation = 'unknown'
        explanation = 'Sumber memuat nomor urut atau lingkup jabatan yang berbeda; perlu pemeriksaan lebih lanjut.'
    else:
        relation = 'support' if values[0] == claim['number'] else 'contradict'
        explanation = (f"Klaim: {claim['subject']}, {claim['role']} ke-{claim['number']}. "
                       f"Sumber menyebut ke-{values[0]}; " + ('angkanya sama.' if relation == 'support' else 'angkanya berbeda.'))
    if any(fact.get('method') == 'semantic_role_match' for fact in facts):
        explanation += ' Hubungan orang-jabatan diperiksa dengan bantuan model semantik; nomor dibandingkan langsung dari kutipan.'
    return {'relation': relation, 'facts': facts, 'observed_numbers': values, 'explanation': explanation}
