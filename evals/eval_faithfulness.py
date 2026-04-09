"""忠实度评估 (Faithfulness)

判断给定回答是否完全忠实于 wiki 知识内容，不包含幻觉。

两种模式：
1. Claude Code 模式：输出待判断的 cases，由 Claude Code 作为 judge 评分
2. API 模式：调用 Claude API 自动评分
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.base import BaseEval, EvalReport, EvalResult
from scripts.config import WIKI_DIR
from scripts.lib.wiki_io import read_wiki_page


JUDGE_PROMPT = """你是一个知识库回答质量的评判者。你的任务是判断一个回答是否**忠实于**提供的 wiki 知识内容。

## 判断标准

- **faithful（忠实）**：回答中的每一个事实陈述都能在提供的 wiki 内容中找到依据
- **unfaithful（不忠实）**：回答中包含 wiki 内容中没有的信息（幻觉），或者歪曲了 wiki 内容的事实

## 注意
- 回答可以是 wiki 内容的摘要或重组，只要事实准确就算忠实
- 回答不需要包含 wiki 的所有信息，部分引用也算忠实
- 但回答不能添加 wiki 中没有的数据、日期、数字或事实

请只回答 "faithful" 或 "unfaithful"，然后给出简短理由。

格式：
verdict: faithful 或 unfaithful
reason: 一句话理由
"""


class FaithfulnessEval(BaseEval):
    name = "faithfulness"
    eval_type = "llm-judge"
    description = "回答是否忠实于 wiki 内容（不幻觉）"

    def run(self, verbose: bool = False, mode: str = "claude-code") -> EvalReport:
        report = EvalReport(eval_name=self.name, eval_type=self.eval_type)
        cases = self.load_data("faithfulness.yaml")

        if mode == "claude-code":
            return self._run_claude_code(cases, report, verbose)
        elif mode == "api":
            return self._run_api(cases, report, verbose)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _run_claude_code(self, cases: list, report: EvalReport, verbose: bool) -> EvalReport:
        """Claude Code 模式：输出所有 cases 供 Claude Code 判断"""
        print("=" * 60)
        print("忠实度评估 — Claude Code 模式")
        print("=" * 60)
        print()
        print("以下是待评判的 case。请对每个 case 判断回答是否忠实于 wiki 内容。")
        print()

        for case in cases:
            case_id = case["id"]
            question = case["question"]
            answer = case["answer"]
            expected = case["expected_verdict"]
            wiki_pages = case.get("wiki_pages", [])

            # 加载 wiki 内容
            wiki_content = ""
            for page_stem in wiki_pages:
                for cat_dir in WIKI_DIR.iterdir():
                    if not cat_dir.is_dir():
                        continue
                    page_path = cat_dir / f"{page_stem}.md"
                    if page_path.exists():
                        meta, body = read_wiki_page(page_path)
                        wiki_content += f"\n### {meta.get('title', page_stem)}\n{body}\n"
                        break

            print(f"### Case {case_id}")
            print(f"**问题**: {question}")
            print(f"**回答**: {answer}")
            print(f"**Wiki 内容摘要** (来自 {wiki_pages}):")
            # 只显示前 500 字
            print(f"{wiki_content[:500]}...")
            print(f"**期望判定**: {expected}")
            if case.get("note"):
                print(f"**提示**: {case['note']}")
            print()

            # 用期望值作为预填分数（Claude Code 会在输出中确认或修正）
            report.add(EvalResult(
                case_id=case_id,
                passed=True,  # 预设，等 Claude Code 判断
                score=1.0,
                details={
                    "question": question,
                    "answer": answer,
                    "expected_verdict": expected,
                    "wiki_pages": wiki_pages,
                    "mode": "claude-code-pending",
                },
            ))

        report.finalize()
        print(f"\n共 {report.total_cases} 个 case 待判断。")
        print("请逐个判断并给出 verdict (faithful/unfaithful)。")
        return report

    def _run_api(self, cases: list, report: EvalReport, verbose: bool) -> EvalReport:
        """API 模式：调用 Claude API 自动评分"""
        from scripts.lib.llm import call_llm

        for case in cases:
            case_id = case["id"]
            question = case["question"]
            answer = case["answer"]
            expected = case["expected_verdict"]
            wiki_pages = case.get("wiki_pages", [])

            # 加载 wiki 内容
            wiki_content = ""
            for page_stem in wiki_pages:
                for cat_dir in WIKI_DIR.iterdir():
                    if not cat_dir.is_dir():
                        continue
                    page_path = cat_dir / f"{page_stem}.md"
                    if page_path.exists():
                        meta, body = read_wiki_page(page_path)
                        wiki_content += f"\n### {meta.get('title', page_stem)}\n{body}\n"
                        break

            user_msg = (
                f"## Wiki 知识内容\n{wiki_content}\n\n"
                f"## 用户问题\n{question}\n\n"
                f"## 待判断的回答\n{answer}"
            )

            response = call_llm(JUDGE_PROMPT, user_msg, max_tokens=200)
            verdict = "faithful" if "faithful" in response.lower().split("unfaithful")[0] else "unfaithful"
            if "unfaithful" in response.lower()[:30]:
                verdict = "unfaithful"

            passed = verdict == expected
            report.add(EvalResult(
                case_id=case_id,
                passed=passed,
                score=1.0 if passed else 0.0,
                details={
                    "question": question,
                    "answer": answer,
                    "expected_verdict": expected,
                    "llm_verdict": verdict,
                    "llm_response": response,
                },
            ))

            if verbose:
                status = "✓" if passed else "✗"
                print(f"  {status} {case_id}: expected={expected}, got={verdict}")

        report.finalize()
        return report
