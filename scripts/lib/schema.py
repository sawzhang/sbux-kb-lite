"""Schema 校验逻辑"""

import re
from pathlib import Path

from scripts.config import CATEGORIES, REQUIRED_FRONTMATTER, SOURCES_DIR, WIKI_DIR
from scripts.lib.wiki_io import extract_wiki_links, list_wiki_pages, parse_frontmatter


def validate_page(path: Path) -> list[str]:
    """校验单个 wiki 页面是否符合 schema，返回错误列表"""
    errors = []
    content = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    # 检查 frontmatter 必填字段
    for field in REQUIRED_FRONTMATTER:
        if field not in meta:
            errors.append(f"缺少 frontmatter 字段: {field}")

    # 检查 category 有效性
    if "category" in meta and meta["category"] not in CATEGORIES:
        errors.append(f"无效分类: {meta['category']}，有效值: {CATEGORIES}")

    # 检查 H1 标题
    if not re.search(r"^# .+", body, re.MULTILINE):
        errors.append("缺少 H1 标题")

    # 检查文件名规范
    if not re.match(r"^[a-z0-9][a-z0-9-]*\.md$", path.name):
        errors.append(f"文件名不符合 kebab-case 规范: {path.name}")

    # 检查 sources 引用有效性
    if "sources" in meta:
        for src in meta["sources"]:
            if not (SOURCES_DIR / src).exists():
                errors.append(f"引用的 source 不存在: {src}")

    return errors


def find_broken_links() -> list[tuple[Path, str]]:
    """查找所有断链：[[page-name]] 指向的页面不存在"""
    broken = []
    all_page_stems = {p.stem for p in list_wiki_pages()}

    for page_path in list_wiki_pages():
        content = page_path.read_text(encoding="utf-8")
        links = extract_wiki_links(content)
        for link in links:
            if link not in all_page_stems:
                broken.append((page_path, link))
    return broken


def find_orphan_pages() -> list[Path]:
    """查找孤立页面：不被任何其他页面引用"""
    all_pages = list_wiki_pages()
    all_page_stems = {p.stem for p in all_pages}

    # 收集所有被引用的页面
    referenced = set()
    for page_path in all_pages:
        content = page_path.read_text(encoding="utf-8")
        links = extract_wiki_links(content)
        referenced.update(links)

    orphans = []
    for page_path in all_pages:
        if page_path.stem not in referenced:
            orphans.append(page_path)
    return orphans
