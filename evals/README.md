# 知识库评估框架 (KB Evals)

参考 OpenAI Evals / RAGAS / DeepEval 的方法论，为 LLM Wiki 知识库设计的评估体系。

## 评估维度

| Eval | 类型 | 说明 | 是否需要 LLM |
|------|------|------|-------------|
| `structure` | 确定性 | Schema 合规、断链、孤立页、索引完整性 | 否 |
| `content_richness` | 确定性 | 字数、章节数、要点覆盖率、交叉引用密度 | 否 |
| `retrieval_precision` | 确定性 | Precision@K、MRR、召回率 | 否 |
| `faithfulness` | LLM-as-Judge | 回答是否忠实于 wiki 内容（不幻觉） | 是 |
| `completeness` | LLM-as-Judge | 回答是否完整覆盖问题各方面 | 是 |
| `abstention` | LLM-as-Judge | 超纲问题是否能正确拒答 | 是 |
| `noise_robustness` | LLM-as-Judge | 混入无关 context 后是否仍正确 | 是 |
| `consistency` | LLM-as-Judge | 同义改写问题是否得到一致回答 | 是 |

## 使用方式

```bash
# 运行所有确定性 eval（不需要 LLM）
python3 -m evals.runner --suite deterministic

# 运行所有 eval（需要 Claude Code 或 ANTHROPIC_API_KEY）
python3 -m evals.runner --suite all

# 运行单个 eval
python3 -m evals.runner --eval retrieval_precision
python3 -m evals.runner --eval faithfulness

# Claude Code 模式：输出待判断的 cases，由 Claude Code 评分
python3 -m evals.runner --eval faithfulness --mode claude-code
```

## Eval Spec 格式

每个 eval 的测试用例定义在 `evals/data/` 目录下的 YAML 文件中。
