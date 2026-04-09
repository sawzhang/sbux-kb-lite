#!/usr/bin/env python3
"""
Lint 脚本：Wiki 健康检查

用法：python -m scripts.lint
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import INDEX_PATH
from scripts.lib.schema import find_broken_links, find_orphan_pages, validate_page
from scripts.lib.wiki_io import list_wiki_pages, read_wiki_page


def lint() -> int:
    """运行 wiki 健康检查，返回问题数量"""
    pages = list_wiki_pages()
    total_issues = 0

    if not pages:
        print("Wiki 为空，没有页面可检查。")
        return 0

    print(f"检查 {len(pages)} 个 wiki 页面...\n")

    # 1. 页面 Schema 校验
    print("## Schema 校验")
    schema_issues = 0
    for p in pages:
        errors = validate_page(p)
        if errors:
            rel = p.relative_to(p.parent.parent.parent)
            for err in errors:
                print(f"  {rel}: {err}")
                schema_issues += 1
    if schema_issues == 0:
        print("  全部通过")
    total_issues += schema_issues

    # 2. 断链检查
    print("\n## 断链检查")
    broken = find_broken_links()
    if broken:
        for page_path, link in broken:
            rel = page_path.relative_to(page_path.parent.parent.parent)
            print(f"  {rel}: [[{link}]] 指向的页面不存在")
        total_issues += len(broken)
    else:
        print("  没有断链")

    # 3. 孤立页面检查
    print("\n## 孤立页面检查")
    orphans = find_orphan_pages()
    if orphans:
        for p in orphans:
            rel = p.relative_to(p.parent.parent.parent)
            print(f"  {rel}: 不被任何其他页面引用")
        total_issues += len(orphans)
    else:
        print("  没有孤立页面")

    # 4. 索引完整性检查
    print("\n## 索引完整性检查")
    if not INDEX_PATH.exists():
        print("  index.md 不存在！")
        total_issues += 1
    else:
        index_content = INDEX_PATH.read_text(encoding="utf-8")
        index_issues = 0
        for p in pages:
            meta, _ = read_wiki_page(p)
            title = meta.get("title", p.stem)
            if title not in index_content and p.stem not in index_content:
                rel = p.relative_to(p.parent.parent.parent)
                print(f"  {rel}: 未出现在 index.md 中")
                index_issues += 1
        if index_issues == 0:
            print("  全部通过")
        total_issues += index_issues

    # 总结
    print(f"\n{'='*40}")
    if total_issues == 0:
        print(f"健康报告：{len(pages)} 个页面，0 个问题")
    else:
        print(f"健康报告：{len(pages)} 个页面，{total_issues} 个问题")

    return total_issues


def main():
    issues = lint()
    sys.exit(1 if issues > 0 else 0)


if __name__ == "__main__":
    main()
