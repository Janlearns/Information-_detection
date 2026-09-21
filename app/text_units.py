"""Topic-independent sentence units shared by retrieval and evidence analysis.

These are sentences, not guaranteed atomic claims. Preserve pronouns and
negation rather than inventing a subject or rewriting a compound statement.
"""
import re


def split_statements(text):
    units, seen = [], set()
    # Keep common title abbreviations and decimal points inside a sentence.
    boundary = re.compile(r'(?<=[.!?])\s+|\n+')
    pending = ''
    for part in boundary.split(text.strip()):
        part = re.sub(r'^\s*[-*\u2022]\s+', '', part).strip()
        if not part:
            continue
        pending = (pending + ' ' + part).strip()
        if re.search(r'\b(?:dr|prof|ir|mr|mrs|sdr|no)\.$', pending, re.I):
            continue
        key = ' '.join(pending.casefold().split())
        if key not in seen:
            units.append(pending)
            seen.add(key)
        pending = ''
    if pending and pending.casefold() not in seen:
        units.append(pending)
    return units


def search_units(text, limit=12):
    """Spread a bounded search budget across the entire text, including its end."""
    units = split_statements(text)
    chunks = []
    for unit in units:
        words = unit.split()
        chunks.extend(' '.join(words[i:i + 35]) for i in range(0, len(words), 35))
    if len(chunks) <= limit:
        return chunks, len(chunks)
    indices = [round(i * (len(chunks) - 1) / (limit - 1)) for i in range(limit)]
    return [chunks[i] for i in indices], len(chunks)
