#!/usr/bin/env python3
"""
Local Ingest：不依赖外部 LLM API，直接将 source 文章转化为 wiki 页面。

source 文章已经结构化（有 frontmatter、H1 标题、分节内容），
本脚本做确定性转换：提取核心要点、生成交叉引用、写入 wiki 页面。

用法：python3 scripts/ingest_local.py           # 处理所有 source
      python3 scripts/ingest_local.py --file sources/xxx.md  # 处理单篇
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import CATEGORIES, SOURCES_DIR, WIKI_DIR
from scripts.lib.wiki_io import (
    append_log,
    list_wiki_pages,
    parse_frontmatter,
    rebuild_index,
    write_wiki_page,
)

TODAY = date.today().isoformat()

# 关键词 → wiki 页面名映射（用于生成交叉引用）
# 在处理完所有文章后动态构建
PAGE_REGISTRY: dict[str, list[str]] = {}  # page_stem -> [keywords]


def extract_bullet_points(body: str, max_points: int = 5) -> list[str]:
    """从正文提取 bullet points 作为核心要点"""
    points = []
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("- **") or line.startswith("- "):
            text = line.lstrip("- ").strip()
            if len(text) > 10 and len(text) < 200:
                points.append(text)
                if len(points) >= max_points:
                    break
    # fallback: 取段落首句
    if len(points) < 3:
        for line in body.split("\n"):
            line = line.strip()
            if (line and not line.startswith("#") and not line.startswith("-")
                    and not line.startswith(">") and not line.startswith("```")
                    and len(line) > 20):
                # 取第一句
                sent = line.split("。")[0] + "。" if "。" in line else line[:80]
                if sent not in points:
                    points.append(sent)
                if len(points) >= max_points:
                    break
    return points[:max_points]


def extract_tags(title: str, body: str, category: str) -> list[str]:
    """从标题和正文提取标签"""
    tags = []
    # 从标题提取关键词
    keyword_map = {
        "brand": ["品牌", "历史", "创始人", "Logo", "使命", "中国", "全球", "上市", "CEO"],
        "coffee": ["咖啡豆", "产地", "烘焙", "冲煮", "风味", "阿拉比卡", "手冲", "浓缩"],
        "products": ["饮品", "星冰乐", "拿铁", "季节", "限定", "周边", "食品"],
        "culture": ["第三空间", "门店", "设计", "伙伴", "可持续", "环保", "社区"],
    }
    for kw in keyword_map.get(category, []):
        if kw in title or kw in body[:500]:
            tags.append(kw)
    # 补充一些通用标签
    if "星巴克" in title:
        tags.append("星巴克")
    if "中国" in body[:500]:
        tags.append("中国市场")
    return tags[:5] if tags else [category]


def find_related_pages(stem: str, category: str, title: str, body: str,
                       all_pages: dict[str, dict]) -> list[str]:
    """找到相关的 wiki 页面（基于关键词匹配）"""
    related = []
    body_lower = (title + " " + body[:1000]).lower()

    for other_stem, other_info in all_pages.items():
        if other_stem == stem:
            continue
        other_title = other_info.get("title", "")
        # 简单的关键词匹配
        score = 0
        if other_info.get("category") == category:
            score += 1
        # 检查标题中的关键词是否出现在当前文章中
        for word in re.findall(r'[\u4e00-\u9fff]+', other_title):
            if len(word) >= 2 and word in body_lower:
                score += 2
        if score >= 2:
            related.append(other_stem)

    # 限制数量
    return related[:5]


def ingest_source(source_path: Path, all_pages: dict[str, dict]) -> list[str]:
    """处理一篇 source 文章，返回生成的 wiki 页面路径列表"""
    content = source_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    source_name = source_path.name
    title = meta.get("title", "").strip('"').strip("'") if meta.get("title") else ""
    category = meta.get("category", "").strip()

    # 如果没有 frontmatter，从内容推断
    if not title:
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
    if not title:
        title = source_path.stem.replace("-", " ").title()

    if not category or category not in CATEGORIES:
        # 根据关键词推断 category
        text = (title + " " + body[:500]).lower()
        if any(kw in text for kw in ["咖啡豆", "产地", "烘焙", "冲煮", "风味", "萃取", "研磨"]):
            category = "coffee"
        elif any(kw in text for kw in ["饮品", "星冰乐", "拿铁", "限定", "月饼", "食品", "周边"]):
            category = "products"
        elif any(kw in text for kw in ["第三空间", "门店设计", "伙伴", "围裙", "可持续", "社区", "环保"]):
            category = "culture"
        else:
            category = "brand"

    # wiki 页面路径
    page_stem = source_path.stem
    page_path = WIKI_DIR / category / f"{page_stem}.md"

    # 提取核心要点
    key_points = extract_bullet_points(body)
    tags = extract_tags(title, body, category)

    # 清理 body（去掉 source 的 frontmatter 标记行）
    clean_body = body.strip()

    # 查找相关页面
    related = find_related_pages(page_stem, category, title, clean_body, all_pages)

    # 构建 wiki 页面
    wiki_meta = {
        "title": title,
        "category": category,
        "tags": tags,
        "sources": [source_name],
        "created": TODAY,
        "updated": TODAY,
    }

    wiki_body = f"# {title}\n\n"
    wiki_body += "## 核心要点\n"
    for kp in key_points:
        wiki_body += f"- {kp}\n"
    wiki_body += "\n"

    # 保留原文的详细内容（去掉 H1 标题，因为已经在上面了）
    detail = clean_body
    if detail.startswith(f"# {title}"):
        detail = detail[len(f"# {title}"):].strip()
    # 把 ## 节保留作为详细内容
    if detail:
        wiki_body += detail + "\n"

    if related:
        wiki_body += "\n## 相关页面\n"
        for r in related:
            r_title = all_pages.get(r, {}).get("title", r)
            wiki_body += f"- [[{r}]] — {r_title}\n"

    write_wiki_page(page_path, wiki_meta, wiki_body)

    # 注册到全局页面表
    all_pages[page_stem] = {"title": title, "category": category, "path": str(page_path)}

    return [f"{category}/{page_stem}.md"]


def main():
    parser = argparse.ArgumentParser(description="本地 Ingest：将 source 文章转化为 wiki 页面")
    parser.add_argument("--file", type=Path, help="处理单篇文章")
    args = parser.parse_args()

    # 构建初始页面注册表
    all_pages: dict[str, dict] = {}

    if args.file:
        sources = [args.file if args.file.is_absolute() else Path.cwd() / args.file]
    else:
        sources = sorted(SOURCES_DIR.glob("*.md"))

    print(f"准备处理 {len(sources)} 篇 source 文章...\n")

    # Pass 1: 预扫描所有 source 建立页面注册表
    for src in sources:
        content = src.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        title = meta.get("title", "").strip('"').strip("'") if meta.get("title") else ""
        if not title:
            for line in content.split("\n"):
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        category = meta.get("category", "brand").strip()
        if category not in CATEGORIES:
            category = "brand"
        all_pages[src.stem] = {"title": title or src.stem, "category": category}

    # Pass 2: 生成 wiki 页面
    total_pages = []
    for i, src in enumerate(sources, 1):
        try:
            pages = ingest_source(src, all_pages)
            total_pages.extend(pages)
            print(f"  [{i:3d}/{len(sources)}] {src.name} → wiki/{pages[0]}")
        except Exception as e:
            print(f"  [{i:3d}/{len(sources)}] {src.name} → 错误: {e}")

    # Pass 3: 更新交叉引用（第二遍，现在所有页面都存在了）
    print(f"\n更新交叉引用...")
    wiki_pages = list_wiki_pages()
    updated = 0
    for wp in wiki_pages:
        content = wp.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(content)
        stem = wp.stem
        category = meta.get("category", "brand")

        # 重新计算 related pages
        related = find_related_pages(stem, category, meta.get("title", ""), body, all_pages)

        if related and "## 相关页面" not in body:
            body += "\n## 相关页面\n"
            for r in related:
                r_title = all_pages.get(r, {}).get("title", r)
                body += f"- [[{r}]] — {r_title}\n"
            write_wiki_page(wp, meta, body)
            updated += 1

    print(f"更新了 {updated} 个页面的交叉引用")

    # 重建索引
    rebuild_index()
    append_log("batch-ingest", f"处理 {len(sources)} 篇文章", total_pages)

    print(f"\n{'='*50}")
    print(f"完成！共生成 {len(total_pages)} 个 wiki 页面")

    # 统计
    categories_count = {}
    for p in total_pages:
        cat = p.split("/")[0]
        categories_count[cat] = categories_count.get(cat, 0) + 1
    for cat, count in sorted(categories_count.items()):
        print(f"  {cat}: {count} 页")


if __name__ == "__main__":
    main()
