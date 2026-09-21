"""Small real-model regression, not a representative accuracy benchmark.

Run: python tests/semantic_smoke.py. Requires an already cached model.
The deterministic suite is separate: python -m unittest discover -s tests.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from app.evidence import compare_pair, classify_evidence

CASES = [
    ('Tumbuhan memanfaatkan cahaya matahari untuk menghasilkan makanan.',
     'Tanaman membuat makanan dengan bantuan sinar matahari.', 1),
    ('Kereta ini digerakkan oleh listrik, bukan mesin diesel.',
     'Kereta ini menggunakan mesin diesel.', 0),
    ('Pabrik berhenti beroperasi akibat kekurangan bahan baku.',
     'Produksi dihentikan karena pasokan bahan baku tidak mencukupi.', 1),
    ('Perpustakaan buka setiap hari hingga pukul delapan malam.',
     'Baterai telepon dapat diisi tanpa kabel.', 2),
]

if __name__ == '__main__':
    results = []
    for premise, claim, expected in CASES:
        scores = compare_pair(premise, claim)
        results.append({'premise': premise, 'claim': claim, 'scores': scores,
                        'passed': max(range(3), key=scores.__getitem__) == expected})
    print(json.dumps(results, ensure_ascii=True, indent=2))
    joint = 'Prabowo Subianto dan Gibran Rakabuming Raka resmi menjabat sebagai Presiden ke-8 dan Wakil Presiden ke-14 Republik Indonesia.'
    ordinal_cases = [
        (joint, 'Prabowo Subianto presiden ke-8', 'support'),
        (joint, 'Prabowo Subianto presiden ke-10', 'contradict'),
        (joint, 'Gibran Rakabuming Raka presiden ke-8', 'unknown'),
        ('Prabowo Subianto bertemu Presiden ke-8 Republik Indonesia.', 'Prabowo Subianto presiden ke-8', 'unknown'),
        ('Prabowo Subianto menghadiri pelantikan Presiden ke-8 Republik Indonesia.', 'Prabowo Subianto presiden ke-8', 'unknown'),
        ('Prabowo Subianto, yang sebelumnya menjabat Menteri Pertahanan, dilantik sebagai Presiden ke-8 Republik Indonesia.', 'Prabowo Subianto presiden ke-8', 'support'),
    ]
    for premise, claim, expected in ordinal_cases:
        result = classify_evidence(claim, [{'url': 'https://example.org', 'text': premise, 'purpose': 'Pemeriksaan fakta'}])
        passed = result['counts'][expected] == 1
        results.append({'passed': passed})
        print(json.dumps({'claim': claim, 'expected': expected, 'counts': result['counts'], 'passed': passed}))
    if not all(row['passed'] for row in results):
        raise SystemExit('Real-model regression failed; inspect scores.')
