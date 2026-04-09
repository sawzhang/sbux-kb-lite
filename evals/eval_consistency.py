"""一致性评估 (Consistency)

测试同一个问题的不同问法，检索系统是否返回一致的 wiki 页面。
纯确定性评估，不需要 LLM。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.base import BaseEval, EvalReport, EvalResult
from scripts.query import search_wiki


class ConsistencyEval(BaseEval):
    name = "consistency"
    eval_type = "deterministic"
    description = "同义改写问题的检索一致性"

    def run(self, verbose: bool = False) -> EvalReport:
        report = EvalReport(eval_name=self.name, eval_type=self.eval_type)
        cases = self.load_data("consistency.yaml")

        for case in cases:
            case_id = case["id"]
            variants = case["variants"]
            expected = set(case.get("expect", []))

            # 对每个变体做检索
            all_results = []
            variant_hits = []
            for variant in variants:
                results = search_wiki(variant, top_k=5)
                stems = [r[0].stem for r in results[:3]]
                all_results.append(stems)
                hit = bool(expected & set(stems)) if expected else True
                variant_hits.append(hit)

            # 一致性：所有变体是否命中相同的期望页面
            all_hit = all(variant_hits)

            # 结果集重叠度：取所有变体 top-3 结果的交集占比
            if len(all_results) >= 2:
                sets = [set(r) for r in all_results]
                intersection = sets[0]
                union = sets[0]
                for s in sets[1:]:
                    intersection &= s
                    union |= s
                overlap = len(intersection) / len(union) if union else 0
            else:
                overlap = 1.0

            score = 0.0
            if all_hit:
                score += 0.6
            elif any(variant_hits):
                score += 0.3
            score += overlap * 0.4

            report.add(EvalResult(
                case_id=case_id,
                passed=all_hit and overlap >= 0.3,
                score=score,
                details={
                    "variants": variants,
                    "expected": list(expected),
                    "variant_results": {v: r for v, r in zip(variants, all_results)},
                    "all_hit_expected": all_hit,
                    "result_overlap": round(overlap, 2),
                },
            ))

            if verbose:
                status = "✓" if all_hit else "✗"
                print(f"  {status} {case_id} (overlap={overlap:.0%})")
                if not all_hit:
                    for v, r, h in zip(variants, all_results, variant_hits):
                        mark = "✓" if h else "✗"
                        print(f"    {mark} \"{v}\" → {r}")

        report.finalize()
        return report
