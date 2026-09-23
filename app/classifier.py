import threading
from app.config import MODEL_ID, MODEL_TOKEN

LABELS = ["informasi hoaks atau klaim menyesatkan", "informasi faktual yang dapat diverifikasi", "opini atau informasi yang belum cukup bukti"]
_pipeline = None
_lock = threading.Lock()

def classify(text):
    global _pipeline
    if not text.strip():
        raise ValueError("Tidak ada teks untuk diklasifikasikan.")
    with _lock:
        if _pipeline is None:
            try:
                from transformers import pipeline
                _pipeline = pipeline("zero-shot-classification", model=MODEL_ID, token=MODEL_TOKEN, device=-1, trust_remote_code=False)
            except Exception as exc:
                raise RuntimeError("Model belum siap. Periksa dependensi, koneksi, dan konfigurasi model/token lokal.") from exc
        # Bound inference and make coverage explicit. Each chunk stays under model context.
        tokenizer = _pipeline.tokenizer
        tokens = tokenizer.encode(text, add_special_tokens=False)
        chunks = [tokenizer.decode(tokens[i:i+220], skip_special_tokens=True) for i in range(0, min(len(tokens), 1320), 220)]
        results = _pipeline(chunks, candidate_labels=LABELS, hypothesis_template="Teks ini berisi {}.", multi_label=False)
        scores = {label: sum(dict(zip(r["labels"], r["scores"]))[label] for r in results) / len(results) for label in LABELS}
    return {"label": "Persentase klasifikasi", "scores": scores, "model": MODEL_ID, "chunks": len(chunks), "tokens_analyzed": min(len(tokens), 1320), "tokens_total": len(tokens), "truncated": len(tokens) > 1320, "reason": "Persentase dihitung dari rata-rata skor model per potongan teks untuk semua kategori, tanpa ambang putusan hoaks atau bukan hoaks.", "warning": "Persentase adalah skor kecocokan kategori dari model, bukan probabilitas kebenaran. Model tidak memeriksa bukti eksternal."}
