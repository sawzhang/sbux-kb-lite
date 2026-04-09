"""Wiki 页面读写、frontmatter 解析、index 操作"""

import re
from datetime import date
from pathlib import Path

import yaml

from scripts.config import INDEX_PATH, LOG_PATH, WIKI_DIR


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 markdown 的 YAML frontmatter，返回 (metadata, body)"""
    match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if not match:
        return {}, content
    meta = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    return meta, body


def render_frontmatter(meta: dict, body: str) -> str:
    """将 metadata 和 body 组合成带 frontmatter 的 markdown"""
    fm = yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False).strip()
    return f"---\n{fm}\n---\n\n{body}\n"


def read_wiki_page(path: Path) -> tuple[dict, str]:
    """读取 wiki 页面，返回 (metadata, body)"""
    if not path.exists():
        return {}, ""
    return parse_frontmatter(path.read_text(encoding="utf-8"))


def write_wiki_page(path: Path, meta: dict, body: str) -> None:
    """写入 wiki 页面"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_frontmatter(meta, body), encoding="utf-8")


def list_wiki_pages() -> list[Path]:
    """列出所有 wiki 页面（排除 index.md 和 log.md）"""
    pages = []
    for p in WIKI_DIR.rglob("*.md"):
        if p.name in ("index.md", "log.md"):
            continue
        pages.append(p)
    return sorted(pages)


def get_index_content() -> str:
    """读取 index.md 的内容"""
    if INDEX_PATH.exists():
        return INDEX_PATH.read_text(encoding="utf-8")
    return ""


def rebuild_index() -> None:
    """重建 wiki/index.md，遍历所有页面生成索引"""
    pages = list_wiki_pages()
    lines = []
    for p in pages:
        meta, body = read_wiki_page(p)
        title = meta.get("title", p.stem)
        category = meta.get("category", "unknown")
        rel_path = p.relative_to(WIKI_DIR)
        # 提取第一个 bullet point 作为摘要
        summary = _extract_summary(body)
        lines.append(f"- [{title}]({rel_path}) [{category}] — {summary}")

    index_body = "# Wiki 索引\n\n"
    index_body += "> 本文件由 ingest 脚本自动维护，列出所有 wiki 页面及一句话摘要。\n\n"
    index_body += "<!-- AUTO-GENERATED INDEX START -->\n"
    index_body += "\n".join(lines) + "\n" if lines else ""
    index_body += "<!-- AUTO-GENERATED INDEX END -->\n"
    INDEX_PATH.write_text(index_body, encoding="utf-8")


def append_log(source_name: str, action: str, pages_affected: list[str]) -> None:
    """追加 ingest 日志到 wiki/log.md"""
    today = date.today().isoformat()
    entry = f"\n## {today} — Ingest: {source_name}\n\n"
    entry += f"- 操作: {action}\n"
    for page in pages_affected:
        entry += f"- 页面: {page}\n"
    entry += "\n"

    existing = LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else "# 变更日志\n"
    LOG_PATH.write_text(existing + entry, encoding="utf-8")


def extract_wiki_links(content: str) -> list[str]:
    """提取 markdown 内容中的 [[page-name]] 链接"""
    return re.findall(r"\[\[([a-z0-9-]+)\]\]", content)


def _extract_summary(body: str) -> str:
    """从 body 中提取第一个 bullet point 作为摘要"""
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("- ") and len(line) > 5:
            return line[2:].strip()
    # fallback: 取第一个非空非标题行
    for line in body.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:80]
    return ""
