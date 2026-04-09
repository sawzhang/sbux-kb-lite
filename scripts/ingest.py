#!/usr/bin/env python3
"""
Ingest 脚本：将原始文章消化为 wiki 页面

用法：python -m scripts.ingest sources/xxx.md
"""

import argparse
import sys
from datetime import date
from pathlib import Path

# 允许从项目根目录运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import CATEGORIES, SOURCES_DIR, WIKI_DIR
from scripts.lib.llm import call_llm_json
from scripts.lib.schema import validate_page
from scripts.lib.wiki_io import (
    append_log,
    list_wiki_pages,
    read_wiki_page,
    rebuild_index,
    write_wiki_page,
)

INGEST_SYSTEM_PROMPT = """你是星巴克知识库的维护助手。你的任务是阅读一篇原始文章，将其消化为结构化的 wiki 页面。

## 知识分类
- brand: 品牌历史、创始人、Logo、使命、全球发展
- coffee: 咖啡豆品种、产地、烘焙、冲煮、风味
- products: 具体饮品、食品、周边产品
- culture: 第三空间、门店设计、员工文化、可持续发展

## 输出要求

返回 JSON，格式如下：
```json
{
  "pages": [
    {
      "filename": "kebab-case-name.md",
      "category": "brand",
      "title": "页面中文标题",
      "tags": ["标签1", "标签2"],
      "key_points": ["要点1", "要点2", "要点3"],
      "content": "详细内容（markdown 格式，使用 ## 小节）",
      "related_pages": ["other-page-name"]
    }
  ]
}
```

## 规则
1. 每篇原始文章应拆分为 2-5 个主题聚焦的 wiki 页面
2. filename 必须是 kebab-case，只含小写字母、数字、连字符
3. 内容要准确、有故事感，符合星巴克品牌调性
4. key_points 列出 3-5 个核心事实
5. related_pages 引用其他可能存在的页面（用 kebab-case 名称）
6. 不要编造文章中没有的信息
"""


def ingest(source_path: Path) -> None:
    """将一篇原始文章导入 wiki"""
    if not source_path.exists():
        print(f"错误：文件不存在 {source_path}")
        sys.exit(1)

    source_content = source_path.read_text(encoding="utf-8")
    source_name = source_path.name
    today = date.today().isoformat()

    # 获取现有 wiki 页面信息，帮助 LLM 做交叉引用
    existing_pages = []
    for p in list_wiki_pages():
        meta, _ = read_wiki_page(p)
        existing_pages.append({
            "filename": p.name,
            "title": meta.get("title", p.stem),
            "category": meta.get("category", ""),
        })

    existing_info = ""
    if existing_pages:
        existing_info = "\n\n## 已有的 wiki 页面（可用于 related_pages 引用）\n"
        for ep in existing_pages:
            existing_info += f"- {ep['filename']} ({ep['category']}): {ep['title']}\n"

    # 调用 LLM 生成 wiki 页面
    print(f"正在消化文章: {source_name} ...")
    user_prompt = f"请阅读以下原始文章并生成 wiki 页面：\n\n{source_content}{existing_info}"

    result = call_llm_json(INGEST_SYSTEM_PROMPT, user_prompt)

    pages_affected = []
    errors_found = []

    for page_data in result.get("pages", []):
        filename = page_data["filename"]
        if not filename.endswith(".md"):
            filename += ".md"

        category = page_data.get("category", "brand")
        if category not in CATEGORIES:
            print(f"  警告：无效分类 {category}，跳过页面 {filename}")
            continue

        page_path = WIKI_DIR / category / filename

        # 构建 frontmatter
        meta = {
            "title": page_data["title"],
            "category": category,
            "tags": page_data.get("tags", []),
            "sources": [source_name],
            "created": today,
            "updated": today,
        }

        # 如果页面已存在，合并 sources 和保留 created
        if page_path.exists():
            old_meta, _ = read_wiki_page(page_path)
            old_sources = old_meta.get("sources", [])
            if source_name not in old_sources:
                old_sources.append(source_name)
            meta["sources"] = old_sources
            meta["created"] = old_meta.get("created", today)

        # 构建 body
        key_points = page_data.get("key_points", [])
        content = page_data.get("content", "")
        related = page_data.get("related_pages", [])

        body = f"# {page_data['title']}\n\n"
        body += "## 核心要点\n"
        for kp in key_points:
            body += f"- {kp}\n"
        body += f"\n{content}\n"

        if related:
            body += "\n## 相关页面\n"
            for r in related:
                body += f"- [[{r}]]\n"

        # 写入
        write_wiki_page(page_path, meta, body)
        pages_affected.append(f"{category}/{filename}")
        print(f"  写入: wiki/{category}/{filename}")

        # 校验
        page_errors = validate_page(page_path)
        if page_errors:
            errors_found.extend([(f"{category}/{filename}", e) for e in page_errors])

    # 更新索引和日志
    rebuild_index()
    append_log(source_name, "ingest", pages_affected)

    print(f"\n完成！生成了 {len(pages_affected)} 个 wiki 页面")

    if errors_found:
        print("\n校验警告：")
        for page, err in errors_found:
            print(f"  {page}: {err}")


def main():
    parser = argparse.ArgumentParser(description="将原始文章导入 wiki 知识库")
    parser.add_argument("source", type=Path, help="原始文章路径（如 sources/xxx.md）")
    args = parser.parse_args()

    # 支持相对路径
    source_path = args.source
    if not source_path.is_absolute():
        source_path = Path.cwd() / source_path

    ingest(source_path)


if __name__ == "__main__":
    main()
