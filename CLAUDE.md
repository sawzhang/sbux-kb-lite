# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

星巴克 AI 点单轻量知识库，基于 Karpathy LLM Wiki 模式替代传统 RAG。用户闲聊意图（品牌文化、咖啡知识等）由 wiki 知识页面支撑回答。

三层架构：`sources/`（原始文章，不可变）→ `wiki/`（LLM 维护的结构化页面）→ `schema/`（规范定义）

## Commands

```bash
# 本地 ingest（不需要 API key，确定性转换）
python3 scripts/ingest_local.py

# API ingest（需要 ANTHROPIC_API_KEY，更智能的拆分）
python3 scripts/ingest.py sources/xxx.md

# 查询（Claude Code 模式，输出检索结果供 Claude Code 回答）
python3 scripts/query.py "星巴克的Logo有什么含义？"

# 查询（API 模式）
python3 scripts/query.py --api "问题"

# 查询（JSON 输出）
python3 scripts/query.py --json "问题"

# 健康检查
python3 scripts/lint.py

# 查看搜索主题列表
python3 scripts/crawl.py --standalone
```

## Architecture

**核心流程：Ingest → Query → Lint**

- `scripts/ingest_local.py` — 本地模式：读取 source → 提取要点/标签 → 生成 wiki 页面 → 重建索引。两遍处理：先扫描建立页面注册表，再生成页面和交叉引用。
- `scripts/ingest.py` — API 模式：调用 Claude 将 1 篇 source 拆分为 2-5 个 wiki 页面，生成交叉引用。
- `scripts/query.py` — 三种模式：Claude Code 模式（本地关键词检索 + 输出 context）、API 模式（Claude 生成回答）、JSON 模式。
- `scripts/lint.py` — 四项检查：Schema 校验、断链、孤立页、索引完整性。

**共享库 `scripts/lib/`：**
- `wiki_io.py` — frontmatter 解析/渲染、页面 CRUD、索引重建、日志追加
- `schema.py` — 页面校验、断链检测、孤立页检测
- `llm.py` — Anthropic API 封装（仅 API 模式需要）

**查询检索逻辑（`query.py`）：**
- 中文 2-4 字 n-gram + 英文单词分词
- 加权匹配：标题 10x、标签 6x、文件名 stem 15x、正文前 500 字 2x
- Stop words 过滤高频无意义词（星巴克、咖啡、什么等）

## Wiki Page Schema

每个 wiki 页面必须包含：
- YAML frontmatter：title, category, tags, sources, created, updated
- H1 标题（与 frontmatter title 一致）
- `## 核心要点`（3-5 个 bullet points）
- 详细内容（H2 小节）
- `## 相关页面`（`[[page-stem]]` 格式链接）

文件命名：kebab-case，放入 `wiki/{category}/` 子目录。
分类：brand / coffee / products / culture

## Key Conventions

- `wiki/index.md` 和 `wiki/log.md` 是自动维护的特殊页面，由脚本管理
- ingest 时保留已有页面的 `created` 日期，只更新 `updated`
- ingest 时合并 `sources` 列表，不覆盖
- 每次 ingest 后必须 `rebuild_index()` 和 `append_log()`
- `sources/` 目录下的文件视为不可变，不要修改原始文章
- 依赖 `pyyaml` 是必须的；`anthropic` 仅 API 模式需要
