# 星巴克 AI 点单 - 轻量知识库方案设计

## 问题背景

在星巴克 AI 点单场景中，当用户意图为闲聊（咨询品牌文化、咖啡知识、门店故事等），需要从内部文章中给出准确回答。

**当前方案（RAG）的痛点：**
- 需要 chunk 分割、embedding 生成、向量数据库维护
- 对于一个相对固定、规模不大的知识库来说，基础设施太重
- 检索质量依赖 chunk 策略和 embedding 模型，调优成本高
- 新增/修改文章需要重新处理 pipeline

## 两个启发方案

### 1. LLM Wiki（Karpathy）

核心思想：**让 LLM 主动维护一个结构化 wiki，而不是每次查询时从原始文档重新检索。**

三层架构：
- **Raw Sources** — 原始文章（不可变）
- **The Wiki** — LLM 生成的结构化 markdown 页面（实体页、概念摘要、交叉引用）
- **The Schema** — 定义 wiki 结构和规范的配置

关键操作：
- **Ingest**：新文章进来时，LLM 阅读并更新 10-15 个相关 wiki 页面
- **Query**：搜索 wiki 回答问题，有价值的探索回写为新页面
- **Lint**：定期检查矛盾、过期内容、缺失引用

### 2. Graphify（知识图谱）

核心思想：**用图拓扑聚类替代向量嵌入，构建可查询的知识图谱。**

- 两阶段提取：AST 结构分析 + LLM 语义提取
- Leiden 社区检测算法做聚类（不需要向量数据库）
- 关系分三类：EXTRACTED / INFERRED / AMBIGUOUS
- 查询时走图而非原始文件，token 消耗降低 71.5x

---

## 方案选择：LLM Wiki 路线（推荐）

### 为什么选 Wiki 而不是 Graph

| 维度 | LLM Wiki | Knowledge Graph |
|------|----------|-----------------|
| 复杂度 | 低，纯 markdown 文件 | 中，需要图数据结构 |
| 维护成本 | LLM 自动维护 | 需要图算法、社区检测 |
| 可读性 | 人类可直接阅读和审核 | 需要可视化工具 |
| 适配场景 | 品牌文化、闲聊知识 | 更适合代码/复杂关系 |
| 增量更新 | 天然支持，ingest 新文章即可 | 需要重建图 |
| 与 MCP 集成 | wiki 页面直接作为 tool context | 需要额外查询层 |

**星巴克闲聊知识库的特点：**
- 知识规模有限（品牌历史、咖啡文化、门店故事、产品知识）
- 更新频率低（不是实时变化的数据）
- 关系结构简单（不是复杂的实体网络）
- 需要人类可审核（品牌内容需要准确性把关）

Wiki 路线在这个场景下是最佳平衡点。

---

## 详细设计

### 目录结构

```
sbux-kb-lite/
├── sources/                    # 原始文章（不可变）
│   ├── brand-history.md
│   ├── coffee-culture.md
│   └── ...
├── wiki/                       # LLM 维护的知识 wiki
│   ├── _index.md               # 全局索引（所有页面 + 一句话摘要）
│   ├── brand/
│   │   ├── starbucks-origin.md
│   │   ├── logo-evolution.md
│   │   └── mission-values.md
│   ├── coffee/
│   │   ├── bean-types.md
│   │   ├── roast-levels.md
│   │   └── brewing-methods.md
│   ├── products/
│   │   ├── signature-drinks.md
│   │   └── seasonal-specials.md
│   └── culture/
│       ├── third-place.md
│       └── sustainability.md
├── schema/
│   ├── wiki-rules.md           # Wiki 页面结构规范
│   └── categories.md           # 知识分类定义
├── scripts/
│   ├── ingest.py               # 文章导入脚本
│   ├── query.py                # 查询接口
│   └── lint.py                 # Wiki 健康检查
└── DESIGN.md
```

### Wiki 页面结构规范

每个 wiki 页面遵循统一格式：

```markdown
---
title: 星巴克起源故事
category: brand
tags: [历史, 创始人, 西雅图]
sources: [brand-history.md, founder-interview.md]
last_updated: 2026-04-09
---

# 星巴克起源故事

## 核心要点
- 1971 年创立于西雅图派克市场
- 三位创始人：Jerry Baldwin, Zev Siegl, Gordon Bowker
- ...

## 详细内容
...

## 相关页面
- [[logo-evolution]] — Logo 的演变与品牌含义
- [[mission-values]] — 企业使命与核心价值观
- [[third-place]] — "第三空间"理念
```

### 查询流程（MCP 集成）

```
用户闲聊消息
    │
    ▼
意图识别（已有）→ 判定为"闲聊/知识咨询"
    │
    ▼
关键词/主题提取
    │
    ▼
搜索 wiki/_index.md → 定位相关页面
    │
    ▼
读取 1-3 个 wiki 页面作为 context
    │
    ▼
LLM 生成回答（带品牌调性）
```

**关键优势：不需要 embedding、不需要向量数据库、不需要 chunk。**
wiki 页面本身就是预处理好的、结构化的、可直接消费的知识。

### Ingest 流程

```python
# scripts/ingest.py 核心逻辑

def ingest_article(source_path: str):
    """
    1. 读取原始文章
    2. LLM 提取关键实体、概念、事实
    3. 查找 wiki 中已有相关页面
    4. 更新已有页面 or 创建新页面
    5. 更新交叉引用
    6. 更新 _index.md
    """
```

### Lint 流程

```python
# scripts/lint.py 定期检查

def lint_wiki():
    """
    - 检查断链（引用了不存在的页面）
    - 检查孤立页面（没有被任何页面引用）
    - 检查内容矛盾（同一事实在不同页面描述不一致）
    - 检查 sources 引用是否有效
    - 生成健康报告
    """
```

---

## 与现有 MCP 点单系统的集成方式

在现有星巴克 MCP tools 的基础上，新增一个轻量的知识查询能力：

**Option A：作为 MCP tool**
```
mcp__starbucks__queryKnowledge(query: str) -> str
```
在 tool 内部搜索 wiki 并返回相关内容，LLM 据此回答。

**Option B：作为 system prompt context**
将 `_index.md` 放入 system prompt，LLM 在判断需要时自行读取 wiki 页面。
更轻量，但需要控制 token 用量。

**推荐 Option A** — 按需加载，不占用 system prompt 空间。

---

## 与 RAG 方案对比

| 维度 | RAG | LLM Wiki |
|------|-----|----------|
| 基础设施 | 向量数据库 + embedding 服务 | 纯文件系统 |
| 数据处理 | chunk + embed + index | LLM 一次性 ingest |
| 查询方式 | 向量相似度搜索 | 关键词匹配 + 索引查找 |
| 准确性 | 依赖 chunk/embedding 质量 | wiki 页面经过 LLM 理解和整合 |
| 可维护性 | pipeline 复杂 | markdown 文件，人人可编辑审核 |
| 成本 | 持续的 embedding 计算 + 存储 | 仅 ingest 时调用 LLM |
| 适用规模 | 大规模文档（万级） | 中小规模（百级以内） |

---

## 参考实现分析：yologdev/karpathy-llm-wiki

### 项目概述

这是 Karpathy LLM Wiki 概念的一个**自主 AI 开发**实现。核心亮点：一个 founding prompt 启动，AI agent（yoyo）每 4 小时自动执行 growth session，零人工代码，自主把 wiki 从单个 markdown 文件发展成完整 Next.js Web 应用。

### 架构分析

**技术栈：** Next.js + TypeScript + Tailwind CSS + Vitest

**核心代码（`src/lib/`）：**
```
src/lib/
├── ingest.ts      # 文章导入：清洗 → 保存 raw → 生成 wiki 页 → 更新索引 → 交叉链接
├── query.ts       # 查询：关键词搜索索引 → LLM ranking → 读取页面 → 合成回答
├── lint.ts        # 健康检查：孤立页、断链、过期内容、矛盾检测
├── wiki.ts        # Wiki 操作：CRUD、交叉引用管理
├── raw.ts         # 原始文件管理
├── llm.ts         # 多 LLM 提供商适配（Claude/OpenAI/Gemini/Ollama）
├── frontmatter.ts # YAML frontmatter 解析
├── types.ts       # 类型定义
└── __tests__/     # 测试
```

**Agent 自治系统（`.yoyo/`）：**
```
.yoyo/
├── scripts/
│   ├── grow.sh            # Growth session 编排器
│   └── format_issues.py   # Issue 安全清洗（防注入）
├── skills/                # Agent 指令模块
├── config.toml            # Agent 配置
├── journal.md             # 会话历史
└── learnings.md           # 累积学习
```

**四阶段 Growth Loop：**
1. **ASSESS** — 读 founding prompt + 检查代码状态 + 识别能力缺口
2. **PLAN** — 对比愿景 vs 现状，决定最多 3 个优先任务
3. **BUILD** — 实现 → build/lint/test → 独立 eval agent 审查 → 失败自动回滚
4. **COMMUNICATE** — 写 journal、记录 learnings、回应 GitHub issues

### 值得借鉴的设计

| 设计点 | 细节 | 对我们的启发 |
|--------|------|-------------|
| **Schema 即契约** | `SCHEMA.md` 定义页面命名（kebab-case）、结构（H1 + 摘要 + 正文 + 链接）、特殊页面（index.md, log.md） | 我们的 `schema/wiki-rules.md` 可直接参考 |
| **多 LLM 适配** | 通过 Vercel AI SDK 支持 Claude/OpenAI/Gemini/Ollama | 我们场景固定用 Claude，但接口抽象值得保留 |
| **机械验证 > 自我评估** | "Trust the harness, not the model" — build 失败触发独立 fix agent，diff 由独立 eval agent 审查 | Ingest 产出应有结构化校验，不能只靠 LLM 自己说"我做好了" |
| **安全防护** | Issue 内容用 nonce 边界包裹、HTML 注释剥离、作者白名单 | 如果开放用户输入影响 wiki，需要类似防注入机制 |
| **增量累积** | `journal.md` + `learnings.md` 跨 session 持久化 | 我们的 `wiki/log.md` 可记录每次 ingest 的变更摘要 |
| **自动回滚** | 代码破坏后回退到 last known-good | Ingest 失败时应保护 wiki 现有内容不被破坏 |

### 与我们场景的差异

| 维度 | yoyo 项目 | 我们的需求 |
|------|-----------|-----------|
| 目标 | 通用个人知识库 Web 应用 | 星巴克 MCP 点单场景的闲聊知识 |
| 运行方式 | 自主 agent 每 4h 自动进化 | 按需 ingest，查询时调用 |
| 复杂度 | 完整 Next.js 应用 | 轻量 Python 脚本 + markdown 文件 |
| Wiki 维护 | AI 自主决策 | 人工审核 + 脚本辅助 |
| 前端 | 有 Web UI + 图可视化 | 无需前端，纯 API/MCP tool |

### 结论

yoyo 项目验证了 LLM Wiki 模式的可行性，但它的重点在**自主 AI 开发**（agent 自己写代码进化自己），我们不需要这层。我们应该：

1. **直接借鉴其 `src/lib/` 的核心逻辑**（ingest/query/lint 三件套）
2. **采用其 Schema 规范**（页面结构、命名规则、特殊页面）
3. **跳过 agent 自治部分**（`.yoyo/` growth loop 对我们场景无意义）
4. **简化为 Python CLI + MCP tool**，不需要 Next.js Web 应用

---

## 下一步

1. 定义 `schema/categories.md` — 星巴克知识分类体系
2. 准备 `sources/` — 收集内部文章
3. 实现 `scripts/ingest.py` — 文章导入与 wiki 生成（参考 yoyo 的 ingest.ts 逻辑）
4. 实现 `scripts/query.py` — 查询接口（参考 yoyo 的 query.ts 逻辑）
5. 实现 `scripts/lint.py` — Wiki 健康检查
6. 集成到 MCP 点单流程中测试
