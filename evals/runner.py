#!/usr/bin/env python3
"""
知识库 Evals 运行器

用法：
  python3 -m evals.runner                          # 运行所有确定性 eval
  python3 -m evals.runner --suite all               # 运行所有 eval
  python3 -m evals.runner --suite deterministic     # 仅确定性 eval
  python3 -m evals.runner --eval retrieval_precision # 运行单个 eval
  python3 -m evals.runner --eval faithfulness --mode claude-code
  python3 -m evals.runner -v                        # 详细输出
  python3 -m evals.runner --save                    # 保存结果到 evals/results/
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.base import EvalReport
from evals.eval_structure import StructureEval
from evals.eval_retrieval import RetrievalEval
from evals.eval_content import ContentRichnessEval
from evals.eval_faithfulness import FaithfulnessEval
from evals.eval_consistency import ConsistencyEval
from evals.eval_abstention import AbstentionEval

# 注册所有 eval
EVAL_REGISTRY = {
    "structure": StructureEval,
    "retrieval_precision": RetrievalEval,
    "content_richness": ContentRichnessEval,
    "faithfulness": FaithfulnessEval,
    "consistency": ConsistencyEval,
    "abstention": AbstentionEval,
}

DETERMINISTIC_EVALS = ["structure", "content_richness", "retrieval_precision", "consistency", "abstention"]
LLM_JUDGE_EVALS = ["faithfulness"]


def run_eval(name: str, verbose: bool = False, mode: str = "claude-code") -> EvalReport:
    """运行单个 eval"""
    if name not in EVAL_REGISTRY:
        print(f"未知 eval: {name}")
        print(f"可用: {list(EVAL_REGISTRY.keys())}")
        sys.exit(1)

    eval_cls = EVAL_REGISTRY[name]
    eval_inst = eval_cls()

    if eval_inst.eval_type == "llm-judge":
        return eval_inst.run(verbose=verbose, mode=mode)
    else:
        return eval_inst.run(verbose=verbose)


def print_summary(reports: list[EvalReport]):
    """打印汇总报告"""
    print()
    print("=" * 60)
    print("知识库 Evals 评估报告")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    print(f"{'Eval':<25} {'Type':<15} {'Score':>8} {'Pass':>10}")
    print("-" * 60)

    total_score = 0
    total_weight = 0
    weights = {
        "structure": 15,
        "content_richness": 15,
        "retrieval_precision": 30,
        "consistency": 15,
        "abstention": 10,
        "faithfulness": 15,
    }

    for r in reports:
        w = weights.get(r.eval_name, 10)
        total_score += r.score * w
        total_weight += w
        print(f"{r.eval_name:<25} {r.eval_type:<15} {r.score:>7.1f} {r.passed_cases:>4}/{r.total_cases}")

        # 打印额外 metadata
        if r.metadata:
            for k, v in r.metadata.items():
                if isinstance(v, dict):
                    print(f"  └ {k}: {json.dumps(v, ensure_ascii=False)}")
                else:
                    print(f"  └ {k}: {v}")

    print("-" * 60)
    overall = round(total_score / total_weight, 1) if total_weight else 0
    print(f"{'综合加权得分':<25} {'':15} {overall:>7.1f}")
    print("=" * 60)

    # 失败项摘要
    failures = []
    for r in reports:
        for result in r.results:
            if not result.passed:
                failures.append((r.eval_name, result.case_id, result.details))

    if failures:
        print(f"\n失败项 ({len(failures)} 个):")
        for eval_name, case_id, details in failures[:10]:
            print(f"  [{eval_name}] {case_id}")
            if "question" in details:
                print(f"    Q: {details['question']}")
            if "expected" in details:
                print(f"    期望: {details['expected']}")
            if "got_top5" in details:
                print(f"    实际: {details['got_top5'][:3]}")
        if len(failures) > 10:
            print(f"  ... 及其他 {len(failures) - 10} 个")

    return overall


def main():
    parser = argparse.ArgumentParser(description="知识库 Evals 运行器")
    parser.add_argument("--suite", choices=["all", "deterministic", "llm-judge"],
                        default="deterministic", help="运行的 eval 套件")
    parser.add_argument("--eval", type=str, help="运行单个 eval（覆盖 --suite）")
    parser.add_argument("--mode", choices=["claude-code", "api"],
                        default="claude-code", help="LLM judge 模式")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--save", action="store_true", help="保存结果到 evals/results/")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    # 确定要运行的 eval 列表
    if args.eval:
        eval_names = [args.eval]
    elif args.suite == "all":
        eval_names = DETERMINISTIC_EVALS + LLM_JUDGE_EVALS
    elif args.suite == "llm-judge":
        eval_names = LLM_JUDGE_EVALS
    else:
        eval_names = DETERMINISTIC_EVALS

    reports = []
    for name in eval_names:
        if args.verbose:
            print(f"\n--- {name} ---")
        report = run_eval(name, verbose=args.verbose, mode=args.mode)
        reports.append(report)

        if args.save:
            eval_inst = EVAL_REGISTRY[name]()
            path = eval_inst.save_report(report)
            if args.verbose:
                print(f"  保存到: {path}")

    if args.json:
        output = {
            "timestamp": datetime.now().isoformat(),
            "evals": [r.to_dict() for r in reports],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print_summary(reports)


if __name__ == "__main__":
    main()
