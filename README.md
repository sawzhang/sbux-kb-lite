# sbux-kb-lite

星巴克 AI 点单场景的轻量知识库，基于 **LLM Wiki** 模式替代传统 RAG。

## 方案思路

用户在点单过程中会产生闲聊类意图（咨询星巴克文化、咖啡知识、品牌故事等），需要知识库支撑回答。传统 RAG 需要 chunk 分割、embedding 生成、向量数据库维护，对于这个场景太重了。

本项目采用 Karpathy 提出的 **LLM Wiki** 模式：

> LLM 预先将原始文章消化为结构化的 wiki markdown 页面，查询时直接读取页面作为 context，零 embedding、零向量数据库。

核心流程：**Ingest**（文章消化）→ **Query**（知识查询）→ **Lint**（健康检查）

## 方案参考

- [LLM Wiki by Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — 核心设计理念：让 LLM 维护一个持久化、交叉链接的 wiki，替代每次从原始文档重新检索的 RAG 模式
- [yologdev/karpathy-llm-wiki](https://github.com/yologdev/karpathy-llm-wiki) — 社区实现参考，验证了 ingest/query/lint 三件套的可行性
- [Graphify](https://github.com/safishamsi/graphify) — 知识图谱方案参考（本项目选择了更轻量的 wiki 路线）

## 架构

```
sources/        原始文章（不可变，人工或爬虫收集）
    ↓ ingest
wiki/           LLM 生成的结构化 wiki 页面（自动维护）
    ↓ query
回答            基于 wiki 页面的知识回答
```

三层结构：
- **Raw Sources** (`sources/`) — 原始文章，不可修改
- **The Wiki** (`wiki/`) — LLM 维护的结构化 markdown 页面
- **The Schema** (`schema/`) — wiki 规范和分类定义

## 快速开始

### 前置要求

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) 包管理器

### 1. 安装依赖

```bash
git clone https://github.com/sawzhang/sbux-kb-lite.git
cd sbux-kb-lite
uv sync                  # 安装核心依赖（pyyaml）
uv sync --extra api      # 可选：安装 Claude API 依赖（anthropic）
```

### 2. 抓取文章

在 Claude Code 中直接说：
```
帮我运行 crawl 抓取星巴克文章到 sources 目录
```
Claude Code 会用内置 WebSearch + WebFetch 搜索、抓取、保存文章。

### 3. 导入文章到 Wiki

```bash
# 本地模式（不依赖 LLM API，确定性转换）
uv run scripts/ingest_local.py

# API 模式（调用 Claude API，更智能的拆分和交叉引用）
export ANTHROPIC_API_KEY=your-key
uv run scripts/ingest.py sources/starbucks-brand-story.md
```

### 4. 查询知识库

**Claude Code 模式（推荐）** — 无需 API key，输出检索结果由 Claude Code 回答：

```bash
uv run scripts/query.py "星巴克的Logo有什么含义？"
uv run scripts/query.py "什么是第三空间？"
uv run scripts/query.py "浅烘和深烘有什么区别？"
```

在 Claude Code 中直接使用：
```
帮我查询知识库：星巴克的Logo有什么含义？
```
Claude Code 会运行 query.py → 读取检索结果 → 基于 wiki 知识回答。

**API 模式** — 调用 Claude API 直接生成回答：

```bash
uv run scripts/query.py --api "星巴克的Logo有什么含义？"
```

**JSON 模式** — 输出结构化检索结果：

```bash
uv run scripts/query.py --json "星巴克的Logo有什么含义？"
```

### 5. 健康检查

```bash
uv run scripts/lint.py
```

## 知识分类

| 分类 | 说明 | 示例 |
|------|------|------|
| `brand` | 品牌历史、创始人、Logo、使命 | 星巴克起源、Howard Schultz |
| `coffee` | 咖啡豆、产地、烘焙、冲煮 | 阿拉比卡、耶加雪菲 |
| `products` | 饮品、食品、周边 | 星冰乐、季节限定 |
| `culture` | 第三空间、门店、员工文化 | 门店设计、伙伴文化 |

## 质量评估 (Evals)

参考 OpenAI Evals / RAGAS 方法论，内置知识库质量评估框架：

```bash
# 运行所有确定性 eval
uv run -m evals.runner

# 详细输出
uv run -m evals.runner -v

# 运行单个 eval
uv run -m evals.runner --eval retrieval_precision
```

当前评估得分（94.6/100）：

| Eval | 得分 | 说明 |
|------|------|------|
| structure | 100.0 | Schema 合规、断链、孤立页、交叉引用密度 |
| content_richness | 100.0 | 字数、章节、核心要点、标签覆盖率 |
| retrieval_precision | 99.3 | 42 个测试问题的 Precision@K 和 MRR |
| consistency | 87.5 | 同义改写查询的检索一致性 |
| abstention | 75.0 | 超纲问题的拒答能力 |

## 项目结构

```
sbux-kb-lite/
├── README.md
├── DESIGN.md                  # 详细设计文档
├── CLAUDE.md                  # Claude Code 指引
├── requirements.txt
├── schema/
│   ├── wiki-rules.md          # 页面结构规范
│   └── categories.md          # 知识分类定义
├── sources/                   # 原始文章（100 篇）
├── wiki/                      # LLM 维护的 wiki 页面（100 页）
│   ├── index.md               # 自动维护的全局索引
│   └── log.md                 # 变更日志
├── scripts/
│   ├── config.py              # 配置
│   ├── crawl.py               # 文章抓取
│   ├── ingest.py              # 文章消化（API 模式）
│   ├── ingest_local.py        # 文章消化（本地模式）
│   ├── query.py               # 知识查询（3 种模式）
│   ├── lint.py                # 健康检查
│   └── lib/
│       ├── wiki_io.py         # wiki 读写工具
│       ├── llm.py             # Claude API 封装
│       ├── schema.py          # schema 校验
│       └── synonyms.py        # 同义词表
└── evals/                     # 知识库评估框架
    ├── runner.py              # 评估运行器
    ├── base.py                # Eval 基类
    ├── eval_*.py              # 各维度评估实现
    └── data/                  # YAML 测试数据集
```

## 与 RAG 对比

| 维度 | RAG | LLM Wiki |
|------|-----|----------|
| 基础设施 | 向量数据库 + embedding 服务 | 纯文件系统 |
| 数据处理 | chunk + embed + index | LLM 一次性 ingest |
| 查询方式 | 向量相似度搜索 | 索引查找 + 页面读取 |
| 可维护性 | pipeline 复杂 | markdown 文件，人人可审核 |
| 适用规模 | 大规模（万级文档） | 中小规模（百级文档） |
