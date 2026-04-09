"""检索准确率评估"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.base import BaseEval, EvalReport, EvalResult
from scripts.config import WIKI_DIR
from scripts.query import search_wiki


class RetrievalEval(BaseEval):
    name = "retrieval_precision"
    eval_type = "deterministic"
    description = "Precision@K, MRR, 分类召回率"

    def run(self, verbose: bool = False) -> EvalReport:
        report = EvalReport(eval_name=self.name, eval_type=self.eval_type)
        cases = self.load_data("retrieval.yaml")

        mrr_sum = 0.0
        category_stats: dict[str, dict] = {}

        for case in cases:
            question = case["q"]
            expected = set(case["expect"])
            category = case.get("category", "unknown")

            results = search_wiki(question, top_k=5)
            result_stems = [r[0].stem for r in results]

            # Hit@K
            hit_1 = bool(expected & set(result_stems[:1]))
            hit_3 = bool(expected & set(result_stems[:3]))
            hit_5 = bool(expected & set(result_stems[:5]))

            # MRR
            rr = 0.0
            for i, stem in enumerate(result_stems):
                if stem in expected:
                    rr = 1.0 / (i + 1)
                    break
            mrr_sum += rr

            # 分类统计
            if category not in category_stats:
                category_stats[category] = {"total": 0, "hit3": 0}
            category_stats[category]["total"] += 1
            if hit_3:
                category_stats[category]["hit3"] += 1

            passed = hit_3
            report.add(EvalResult(
                case_id=question[:30],
                passed=passed,
                score=1.0 if hit_1 else (0.7 if hit_3 else (0.3 if hit_5 else 0.0)),
                details={
                    "question": question,
                    "expected": list(expected),
                    "got_top5": result_stems,
                    "hit@1": hit_1,
                    "hit@3": hit_3,
                    "hit@5": hit_5,
                    "mrr": round(rr, 3),
                },
            ))

            if verbose:
                status = "✓" if hit_3 else "✗"
                print(f"  {status} {question}")
                if not hit_3:
                    print(f"    expect: {list(expected)}")
                    print(f"    got:    {result_stems[:5]}")

        report.finalize()
        report.metadata = {
            "mrr": round(mrr_sum / len(cases), 3) if cases else 0,
            "category_recall": {
                cat: round(s["hit3"] / s["total"] * 100, 1)
                for cat, s in category_stats.items()
            },
        }
        return report
