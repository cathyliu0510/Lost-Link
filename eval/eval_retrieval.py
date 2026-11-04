"""
Retrieval check: does the right found report appear in the top 3?

Compares our alias matcher with the HW5 baseline (exact category + keyword
overlap) on the SAME 20 visible found reports (10 true + 10 distractors) and
the SAME queries. private_detail is stripped before either ranker sees data.

    python -m eval.eval_retrieval            # held-out queries (the real test)
    python -m eval.eval_retrieval --tuning   # the 10 lost reports used while building
"""
import argparse
import json
from pathlib import Path

from lostlink.matching import PUBLIC_FIELDS, rank_alias, rank_baseline

DATA = Path(__file__).resolve().parent.parent / "data"


def public(r: dict) -> dict:
    """Keep only fields the service would expose to a ranker."""
    return {k: r.get(k) for k in PUBLIC_FIELDS}


def evaluate(ranker, queries, pool, k=3):
    """Return per-query rows and summary metrics for one ranker."""
    rows = []
    for q in queries:
        top = [c["report_id"] for c in ranker(public(q), pool, limit=k)]
        hit = q["answer"] in top
        rows.append({"query": q["report_id"], "answer": q["answer"], "top3": top,
                     "hit": hit,
                     # wrong candidates the calling agent would have to sift through
                     "wrong_in_top3": sum(1 for t in top if t != q["answer"])})
    n = len(rows)
    return rows, {"hit@3": f"{sum(r['hit'] for r in rows)}/{n}",
                  "mean_wrong_in_top3": round(sum(r["wrong_in_top3"] for r in rows) / n, 2),
                  "no_candidate": sum(1 for r in rows if not r["top3"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuning", action="store_true", help="evaluate on tuning set")
    args = ap.parse_args()

    data = json.loads((DATA / "synthetic_reports.json").read_text())
    pool = [public(r) for r in data["found"] + data["distractors"]]
    queries = (data["lost_tuning"] if args.tuning
               else json.loads((DATA / "heldout_queries.json").read_text())["queries"])

    results = {}
    for name, ranker in (("alias_matcher", rank_alias), ("baseline", rank_baseline)):
        rows, summary = evaluate(ranker, queries, pool)
        results[name] = {"summary": summary, "rows": rows}

    # Per-query table, then summaries
    print(f"{'query':<6}{'answer':<8}{'alias top3':<22}{'baseline top3':<22}")
    for a, b in zip(results["alias_matcher"]["rows"], results["baseline"]["rows"]):
        mark = lambda r: ("✓ " if r["hit"] else "✗ ") + ",".join(r["top3"] or ["-"])
        print(f"{a['query']:<6}{a['answer']:<8}{mark(a):<22}{mark(b):<22}")
    print()
    for name in results:
        print(f"{name:<14}", results[name]["summary"])

    out = DATA.parent / "eval" / ("results_tuning.json" if args.tuning else "results_heldout.json")
    out.write_text(json.dumps(results, indent=2))
    print(f"\nsaved {out.relative_to(DATA.parent)}")


if __name__ == "__main__":
    main()
