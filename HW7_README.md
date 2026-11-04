# Lost Link - HW7 benchmark

Team: Kemeng Zhang, Yicheng Liu. MIT MAS.665, November 4, 2026.

## Team contributions

- **Kemeng Zhang**: defined the claim, primary metric and pre-set success checks; designed the baseline and three-arm comparison; wrote the tuning and fresh test cases; diagnosed the original ranker’s false suggestions on absent items and designed the category-eligibility change; analyzed results and limitations; wrote the report.
- **Yicheng Liu**: implemented the benchmark harness and verifier; ran the discovery and retest experiments; packaged the evidence bundle and reproducibility materials.

The submission is `Lost_Link_HW7.pdf`. The PDF includes an embedded copy of
`Lost_Link_HW7_reproducibility.zip` for offline inspection. The repository and
supporting evidence are public and accessible without signing in:

- [Readable execution evidence](https://github.com/cathyliu0510/Lost-Link/blob/main/HW7_execution_evidence.json)
- [Source and reproducibility bundle](https://github.com/cathyliu0510/Lost-Link/blob/main/Lost_Link_HW7_reproducibility.zip)

Extract the PDF attachment
with a PDF reader's Attachments panel, or with Python:

```python
from pypdf import PdfReader
from pathlib import Path
reader = PdfReader("Lost_Link_HW7.pdf")
for name, contents in reader.attachments.items():
    Path(name).write_bytes(contents[0])
```

## Result and scope

This benchmarks the service's retrieval contribution using two authenticated,
deterministic clients and real FastAPI/SQLite requests. It does not benchmark
an autonomous LLM's reasoning or prove real-world ownership/recovery success.

| Cases | Baseline | Original alias | Revised alias |
|---|---:|---:|---:|
| Existing regression positives: hit@3 | 3/10 | 10/10 | 10/10 |
| Tuning: correct retrieval or abstention | 4/4 | 1/4 | 4/4 |
| Fresh positives: hit@3 | 4/6 | 6/6 | 5/6 |
| Fresh absent items: false suggestions | 0/6 | 5/6 | 0/6 |
| Fresh overall success | 10/12 | 7/12 | 11/12 |

The one change requires positive evidence of a shared normalized category
before scoring. It removes suggestions caused only by unknown-field credit.
The fresh unsupported `watch` case H06 exposes the cost: original and baseline
retrieve the target, but the revised matcher abstains. No fresh-result tuning
was performed. Both snapshots and every case, including failures, are included.

## Check execution evidence without rerunning

Unzip the reproducibility bundle, then run these commands from `Lost-Link-HW7/`.
The recorded environment was macOS arm64, Python 3.13.7; all dependency versions
are pinned in the lock file. Python 3.13 is recommended for exact environment
reproduction. The optional LLM demo dependencies are not needed.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r eval/hw7_requirements.lock
.venv/bin/python -m eval.verify_hw7
.venv/bin/python -m pytest -q
```

The verifier independently re-scores all 258 saved search responses against
the fixture answer labels, reconciles 330 audit rows, and checks frozen hashes.
There were 24 discovery searches and 234 retest searches, plus 72 setup POSTs.
All search responses were HTTP 200; no stored private detail appeared in them.
Model calls, model tokens and model API charges were zero. Three repetitions
measure timing only; accuracy denominators count unique cases, not repeated rows.

## Rerun the comparison

Make a copy of the bundle first if you want to preserve the supplied evidence.
These commands recreate discovery with the original production source, restore
the fixed source, and then retest all three arms. Output replaces the local
`eval/hw7_evidence/` records. Timings will vary with hardware and system load.

```bash
cp lostlink/matching.py matching.revised.py
cp eval/hw7_original_matching.py lostlink/matching.py
.venv/bin/python -m eval.hw7_benchmark --phase discovery
mv matching.revised.py lostlink/matching.py
.venv/bin/python -m eval.hw7_benchmark --phase retest
.venv/bin/python -m eval.verify_hw7
```

The plan was saved before discovery. Fresh fixtures were saved before any
result inspection and their hashes are identical in discovery and retest.
Only T01-T04 informed the change. Q01-Q10 are an existing regression set,
not fresh held-out evidence. H01-H12 were not executed until after the change.
The same evaluator authored synthetic cases and the change, so holdout
execution is separated but case authorship is not independent.

## Evidence index

- `eval/hw7_plan.json`: measurable claim, pre-set checks, controls and budget.
- `eval/hw7_change_record.json`: tuning failure, causal explanation and one change.
- `eval/hw7_original_matching.py`: byte-identical base-commit matcher.
- `eval/hw7_benchmark.py`: API harness and measured latency/byte collection.
- `eval/hw7_evidence/discovery_*`: manifests, raw responses, audit and summary.
- `eval/hw7_evidence/retest_*`: three-arm retest, including all fresh failures.
- `eval/verify_hw7.py` and `eval/hw7_evidence/verification.txt`: independent checks.
- `data/hw7_tuning.json`, `data/hw7_fresh.json`: explicit answers, withheld from rankers.
- `data/hw7_extra_found.json`: the unsupported-type positive control.
- `tests/test_hw7_matching.py`: two tuning-motivated regression tests.
- `HW7_execution_evidence.json`: consolidated readable evidence for GitHub browsing.

Small synthetic samples do not establish statistical superiority. The fresh
gain over baseline is one case, and the mix of present/absent items affects
overall success. Known-category absence, stale reports, close duplicates,
multilingual inputs, concurrent load, real LLM tool use and human decisions
need further evaluation. This is a bounded service retrieval experiment.
