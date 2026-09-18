"""Local OCR with bounded discovery of public evidence pages."""
import re
from difflib import SequenceMatcher
from app.crawler import crawl
from app.classifier import classify


def normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def changed(previous, current):
    return len(current) >= 100 and SequenceMatcher(None, previous, current).ratio() < .9


def check_text(text, cancelled=lambda: False):
    from ddgs import DDGS
    if cancelled():
        return None
    # Search snippets are discovery aids, never proof of a verdict.
    query = " ".join(text.split()[:35])
    sources, errors = [], []
    try:
        hits = DDGS(timeout=10).text(query + " cek fakta", max_results=3)
        for hit in hits:
            if cancelled():
                return None
            try:
                articles, failures = crawl(hit.get("href", ""), 1)
                sources.extend({"title": a["title"], "url": a["url"]} for a in articles)
                errors.extend(f["error"] for f in failures)
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
    except Exception as exc:
        errors.append("Pencarian sumber gagal: " + str(exc))
    if cancelled():
        return None
    analysis = classify(text[:30000])
    return {"label": "Belum terverifikasi", "indication": analysis["label"],
            "text": text[:500], "sources": sources[:3], "errors": errors,
            "reason": "Sumber terkait belum dibandingkan dengan klaim. Indikasi model bukan keputusan fakta."}
