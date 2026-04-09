# Wiki 页面结构规范

## 文件命名

- 使用 kebab-case：`/^[a-z0-9][a-z0-9-]*\.md$/`
- 按分类放入子目录：`wiki/{category}/{page-name}.md`
- 示例：`wiki/brand/starbucks-origin.md`

## 页面结构

每个 wiki 页面必须包含：

### 1. YAML Frontmatter（必填）

```yaml
---
title: 页面标题（中文）
category: brand | coffee | products | culture
tags: [标签1, 标签2]
sources: [source-file-1.md, source-file-2.md]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

必填字段：title, category, tags, sources, created, updated

### 2. H1 标题

与 frontmatter 中的 title 一致。

### 3. 核心要点

用 bullet points 列出 3-5 个关键事实，方便快速扫描。

### 4. 详细内容

展开说明，分小节组织。

### 5. 相关页面

使用 `[[page-name]]` 格式链接相关页面：

```markdown
## 相关页面
- [[starbucks-origin]] — 星巴克起源故事
- [[logo-evolution]] — Logo 演变历史
```

## 特殊页面

- `wiki/index.md` — 全局索引，每个 wiki 页面一行：`- [{title}](path) — {一句话摘要}`
- `wiki/log.md` — 变更日志，记录每次 ingest 的操作

## 内容原则

- 事实准确，来源可追溯
- 语气符合星巴克品牌调性：温暖、专业、有故事感
- 中文为主，专有名词保留英文
