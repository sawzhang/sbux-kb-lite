"""Eval 基类和通用工具"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

EVALS_DIR = Path(__file__).resolve().parent
DATA_DIR = EVALS_DIR / "data"
RESULTS_DIR = EVALS_DIR / "results"


@dataclass
class EvalResult:
    """单个 eval case 的结果"""
    case_id: str
    passed: bool
    score: float  # 0.0 ~ 1.0
    details: dict = field(default_factory=dict)


@dataclass
class EvalReport:
    """一个 eval 的完整报告"""
    eval_name: str
    eval_type: str  # "deterministic" | "llm-judge"
    total_cases: int = 0
    passed_cases: int = 0
    score: float = 0.0  # 平均分 0~100
    results: list[EvalResult] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def add(self, result: EvalResult):
        self.results.append(result)
        self.total_cases += 1
        if result.passed:
            self.passed_cases += 1

    def finalize(self):
        if self.total_cases > 0:
            self.score = round(
                sum(r.score for r in self.results) / self.total_cases * 100, 1
            )

    def summary(self) -> str:
        return (
            f"{self.eval_name}: {self.score}/100 "
            f"({self.passed_cases}/{self.total_cases} passed)"
        )

    def to_dict(self) -> dict:
        return {
            "eval_name": self.eval_name,
            "eval_type": self.eval_type,
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "score": self.score,
            "metadata": self.metadata,
            "results": [
                {
                    "case_id": r.case_id,
                    "passed": r.passed,
                    "score": r.score,
                    "details": r.details,
                }
                for r in self.results
            ],
        }


class BaseEval(ABC):
    """所有 Eval 的基类"""

    name: str = "base"
    eval_type: str = "deterministic"  # "deterministic" | "llm-judge"
    description: str = ""

    def load_data(self, filename: str) -> list[dict]:
        """加载 YAML 测试数据"""
        path = DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Eval data not found: {path}")
        return yaml.safe_load(path.read_text(encoding="utf-8"))

    @abstractmethod
    def run(self, verbose: bool = False) -> EvalReport:
        """执行评估，返回报告"""
        ...

    def save_report(self, report: EvalReport) -> Path:
        """保存报告到 results/"""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = RESULTS_DIR / f"{report.eval_name}_{ts}.json"
        path.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
