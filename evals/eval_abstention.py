"""拒答能力评估 (Abstention)

测试系统在知识库没有答案时，是否能正确拒答而非编造。
使用 confidence level（基于 score + coverage）判断。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.base import BaseEval, EvalReport, EvalResult
from scripts.query import search_wiki, get_confidence


class AbstentionEval(BaseEval):
    name = "abstention"
    eval_type = "deterministic"
    description = "超纲问题拒答能力 + 有答问题响应能力"

    def run(self, verbose: bool = False) -> EvalReport:
        report = EvalReport(eval_name=self.name, eval_type=self.eval_type)
        cases = self.load_data("abstention.yaml")

        for case in cases:
            case_id = case["id"]
            question = case["question"]
            has_answer = case["has_answer"]

            results = search_wiki(question, top_k=3)
            top_score = results[0][1] if results else 0.0
            top_coverage = results[0][2].get("_coverage", 0) if results else 0.0
            confidence = get_confidence(top_score, top_coverage)

            # 系统认为有答案：confidence >= MEDIUM
            system_says_has_answer = confidence in ("HIGH", "MEDIUM")

            if has_answer:
                passed = system_says_has_answer
                score = 1.0 if passed else 0.0
            else:
                passed = not system_says_has_answer
                score = 1.0 if passed else 0.0

            report.add(EvalResult(
                case_id=case_id,
                passed=passed,
                score=score,
                details={
                    "question": question,
                    "has_answer": has_answer,
                    "top_score": round(top_score, 1),
                    "top_coverage": round(top_coverage, 2),
                    "confidence": confidence,
                    "system_says_has_answer": system_says_has_answer,
                    "result_stems": [r[0].stem for r in results[:3]],
                },
            ))

            if verbose:
                status = "✓" if passed else "✗"
                label = "应答" if has_answer else "拒答"
                print(f"  {status} {case_id} (期望{label}, conf={confidence}, "
                      f"score={top_score:.1f}, cov={top_coverage:.0%})")

        report.finalize()
        return report
