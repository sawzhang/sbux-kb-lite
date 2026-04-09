"""内容丰富度评估"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.base import BaseEval, EvalReport, EvalResult
from scripts.lib.wiki_io import list_wiki_pages, read_wiki_page


class ContentRichnessEval(BaseEval):
    name = "content_richness"
    eval_type = "deterministic"
    description = "字数、章节数、核心要点覆盖率、标签丰富度"

    # 阈值
    MIN_WORDS = 200
    MIN_SECTIONS = 2
    MIN_TAGS = 1

    def run(self, verbose: bool = False) -> EvalReport:
        report = EvalReport(eval_name=self.name, eval_type=self.eval_type)
        pages = list_wiki_pages()

        for p in pages:
            meta, body = read_wiki_page(p)
            stem = p.stem

            # 字数
            cn = len(re.findall(r'[\u4e00-\u9fff]', body))
            en = len(re.findall(r'[a-zA-Z]+', body))
            word_count = cn + en

            # 章节
            sections = len(re.findall(r'^##\s', body, re.MULTILINE))

            # 核心要点
            has_key_points = "## 核心要点" in body

            # 相关页面
            has_related = "## 相关页面" in body

            # 标签
            tags = meta.get("tags", [])

            # 综合打分
            score = 0.0
            issues = []

            if word_count >= self.MIN_WORDS:
                score += 0.3
            else:
                issues.append(f"字数不足: {word_count} < {self.MIN_WORDS}")

            if sections >= self.MIN_SECTIONS:
                score += 0.2
            else:
                issues.append(f"章节不足: {sections} < {self.MIN_SECTIONS}")

            if has_key_points:
                score += 0.2
            else:
                issues.append("缺少核心要点")

            if has_related:
                score += 0.15
            else:
                issues.append("缺少相关页面")

            if len(tags) >= self.MIN_TAGS:
                score += 0.15
            else:
                issues.append("缺少标签")

            report.add(EvalResult(
                case_id=stem,
                passed=score >= 0.8,
                score=score,
                details={
                    "word_count": word_count,
                    "sections": sections,
                    "has_key_points": has_key_points,
                    "has_related": has_related,
                    "tags": len(tags),
                    "issues": issues,
                },
            ))

            if verbose and issues:
                print(f"  {stem}: {', '.join(issues)}")

        report.finalize()
        return report
