"""结构健康度评估"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals.base import BaseEval, EvalReport, EvalResult
from scripts.config import WIKI_DIR
from scripts.lib.schema import find_broken_links, find_orphan_pages, validate_page
from scripts.lib.wiki_io import extract_wiki_links, list_wiki_pages, read_wiki_page


class StructureEval(BaseEval):
    name = "structure"
    eval_type = "deterministic"
    description = "Schema 合规性、链接完整性、索引覆盖率"

    def run(self, verbose: bool = False) -> EvalReport:
        report = EvalReport(eval_name=self.name, eval_type=self.eval_type)
        pages = list_wiki_pages()

        # Case 1: Schema 合规
        schema_errors = 0
        for p in pages:
            errors = validate_page(p)
            schema_errors += len(errors)
            if verbose and errors:
                print(f"  Schema: {p.relative_to(WIKI_DIR)}: {errors}")

        compliance = 1.0 - (schema_errors / max(len(pages) * 6, 1))
        report.add(EvalResult(
            case_id="schema_compliance",
            passed=schema_errors == 0,
            score=max(0, compliance),
            details={"errors": schema_errors, "pages": len(pages)},
        ))

        # Case 2: 断链
        broken = find_broken_links()
        report.add(EvalResult(
            case_id="broken_links",
            passed=len(broken) == 0,
            score=1.0 if not broken else max(0, 1 - len(broken) / max(len(pages), 1)),
            details={"count": len(broken)},
        ))

        # Case 3: 孤立页面
        orphans = find_orphan_pages()
        report.add(EvalResult(
            case_id="orphan_pages",
            passed=len(orphans) == 0,
            score=1.0 if not orphans else max(0, 1 - len(orphans) / max(len(pages), 1)),
            details={"count": len(orphans)},
        ))

        # Case 4: 交叉引用密度
        total_links = sum(
            len(extract_wiki_links(p.read_text(encoding="utf-8")))
            for p in pages
        )
        avg_links = total_links / len(pages) if pages else 0
        # 期望每页至少 3 个引用
        density_score = min(1.0, avg_links / 3.0)
        report.add(EvalResult(
            case_id="cross_ref_density",
            passed=avg_links >= 3.0,
            score=density_score,
            details={"total_links": total_links, "avg_per_page": round(avg_links, 1)},
        ))

        report.finalize()
        return report
