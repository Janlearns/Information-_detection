"""Conservative extraction of Indonesian office ordinals, without a fact database.

Unknown wording, negation, reported false claims and ambiguous attachments abstain.
This parser does not resolve pronouns, aliases, compound claims or office terms.
"""
import re

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
LINK = r'(?:(?:adalah|merupakan|sebagai)\s+|(?:resmi\s+)?(?:menjabat(?:\s+sebagai)?|menjadi|dilantik(?:\s+sebagai)?)\s+)?'
CLAIM = re.compile(rf'^(?P<subject>[\w]+(?:[ -][\w]+){{0,3}}?)\s+{LINK}{OFFICE}\s*[.!]?$', re.I)


def country(value):
    value = (value or '').lower()
    return {'ri': 'indonesia', 'republik indonesia': 'indonesia', 'as': 'amerika serikat'}.get(value, value)


def parse_claim(text):
    text = ' '.join(text.split())
    if UNSAFE.search(text):
        return None
    match = CLAIM.fullmatch(text)
    if not match:
        return None
    subject = match['subject']
    if re.search(r'\b(?:dan|atau|menurut|kata|bahwa|bapak|pak|presiden)\b', subject, re.I):
        return None
    value = match['number'].lower()
    return {'subject': subject, 'role': match['role'].lower(),
            'number': int(value) if value.isdigit() else WORDS[value],
            'country': country(match['country_before'] or match['country_after'])}


def looks_like_ordinal(text):
    return bool(re.search(rf'{ROLE}.{{0,45}}\bke[\s-]*{NUMBER}\b', text, re.I))


def extract_ordinals(body, claim):
    # A short input name can match a full name, but arbitrary intervening prose
    # cannot join a person to a different person's office.
    subject = r'(?i:' + re.escape(claim['subject']) + r')(?:\s+[A-Z][a-z]+){0,2}'
    office = r'(?i:' + OFFICE + ')'
    forward = re.compile(rf'(?<!\w){subject}\s+(?i:{LINK}){office}')
    reverse = re.compile(rf'{office}\s*[,":-]?\s*(?:(?i:jenderal\s+tni\s*\(purn\)\s*))?{subject}(?!\w)')
    found = []
    for sentence in re.split(r'(?<=[.!?])\s+|\n+', body):
        sentence = ' '.join(sentence.split())
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


def compare_ordinal(body, claim):
    facts = extract_ordinals(body, claim) if claim else []
    values = sorted({fact['number'] for fact in facts})
    scopes = {fact['country'] for fact in facts if fact['country']}
    if not values:
        relation = 'unknown'
        explanation = 'Tidak ada pernyataan nomor urut yang secara eksplisit terikat pada orang dan jabatan dalam klaim.'
    elif len(values) != 1 or len(scopes) > 1:
        relation = 'unknown'
        explanation = 'Sumber memuat nomor urut atau lingkup jabatan yang berbeda; perlu pemeriksaan lebih lanjut.'
    else:
        relation = 'support' if values[0] == claim['number'] else 'contradict'
        explanation = (f"Klaim: {claim['subject']}, {claim['role']} ke-{claim['number']}. "
                       f"Sumber menyebut ke-{values[0]}; " + ('angkanya sama.' if relation == 'support' else 'angkanya berbeda.'))
    return {'relation': relation, 'facts': facts, 'observed_numbers': values, 'explanation': explanation}
