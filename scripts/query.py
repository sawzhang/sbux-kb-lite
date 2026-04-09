#!/usr/bin/env python3
"""
Query 脚本：搜索 wiki 并生成回答

两种模式：
  1. Claude Code 模式（默认）：输出检索到的 wiki 页面内容，由 Claude Code 直接回答
     python3 scripts/query.py "星巴克的Logo有什么含义？"

  2. API 模式：调用 Claude API 生成回答（需要 ANTHROPIC_API_KEY）
     python3 scripts/query.py --api "星巴克的Logo有什么含义？"
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import WIKI_DIR
from scripts.lib.wiki_io import get_index_content, list_wiki_pages, read_wiki_page
from scripts.lib.synonyms import expand_query_tokens


# ============================================================
# 本地关键词检索（不依赖外部 LLM）
# ============================================================

STOP_WORDS = {"星巴克", "星巴", "巴克", "咖啡", "什么", "怎么", "如何", "为什么",
               "哪些", "是什么", "含义", "区别", "介绍", "关于", "请问",
               "的", "了", "吗", "呢", "吧", "是", "在", "有", "和", "与",
               "starbucks", "coffee", "the", "is", "are", "what", "how", "about"}


def tokenize_chinese(text: str, for_query: bool = False) -> list[str]:
    """简易中文分词：提取连续中文片段和英文单词"""
    tokens = []
    # 中文 2-4 字 n-gram
    chinese_chars = re.findall(r'[\u4e00-\u9fff]+', text)
    for seg in chinese_chars:
        for n in (4, 3, 2):
            for i in range(len(seg) - n + 1):
                gram = seg[i:i+n]
                if for_query and any(sw in gram for sw in STOP_WORDS if len(sw) >= 2):
                    continue
                tokens.append(gram)
        if len(seg) >= 2 and not (for_query and any(sw in seg for sw in STOP_WORDS if len(sw) >= 2)):
            tokens.append(seg)
    # 英文单词
    for w in re.findall(r'[a-zA-Z]{2,}', text):
        wl = w.lower()
        if for_query and wl in STOP_WORDS:
            continue
        tokens.append(wl)
    return tokens


def compute_coverage(q_core_tokens: set[str], page_all_tokens: set[str]) -> float:
    """计算 query 核心 token 被页面覆盖的比例（0.0~1.0）"""
    if not q_core_tokens:
        return 0.0
    covered = sum(1 for t in q_core_tokens if t in page_all_tokens)
    return covered / len(q_core_tokens)


def get_confidence(top_score: float, top_coverage: float) -> str:
    """基于得分和覆盖度计算 confidence level"""
    if top_score <= 0 or top_coverage <= 0:
        return "NONE"
    if top_score >= 15 and top_coverage >= 0.5:
        return "HIGH"
    if top_score >= 8 and top_coverage >= 0.3:
        return "MEDIUM"
    if top_score >= 3:
        return "LOW"
    return "NONE"


def search_wiki(question: str, top_k: int = 5) -> list[tuple[Path, float, dict]]:
    """基于关键词匹配搜索 wiki 页面，返回 (path, score, meta) 列表

    流程：分词 → 同义词扩展 → 逐页匹配 → coverage 加权 → 排序
    """
    raw_tokens = set(tokenize_chinese(question, for_query=True))
    if not raw_tokens:
        return []

    # 同义词扩展
    q_tokens = expand_query_tokens(raw_tokens)

    # 保留原始 query 的核心 token（用于 coverage 计算）
    q_core = raw_tokens

    results = []
    for page_path in list_wiki_pages():
        meta, body = read_wiki_page(page_path)
        title = meta.get("title", "")
        tags = meta.get("tags", [])
        category = meta.get("category", "")

        # 文件名也参与匹配（kebab-case 拆分）
        stem_words = set(page_path.stem.split("-"))

        # 构建页面文本用于匹配
        page_text = f"{title} {' '.join(tags)} {category} {body[:2000]}"
        p_tokens = set(tokenize_chinese(page_text))
        # 文件名 stem 也加入 page tokens
        p_tokens_full = p_tokens | stem_words

        # 计算匹配分数（用扩展后的 q_tokens）
        overlap = q_tokens & p_tokens
        q_english = {t for t in q_tokens if re.match(r'^[a-z]+$', t)}
        stem_overlap = q_english & stem_words
        if not overlap and not stem_overlap:
            continue

        score = 0.0
        for token in overlap:
            length_boost = len(token) if len(token) >= 3 else 1
            if token in title:
                score += 10.0 * length_boost
            if any(token in t for t in tags):
                score += 6.0 * length_boost
            if token in body[:500]:
                score += 2.0
            elif token in body:
                score += 0.5

        for token in stem_overlap:
            score += 15.0

        long_overlap = {t for t in overlap if len(t) >= 3}
        if not long_overlap and not stem_overlap:
            score *= 0.3

        # Coverage：query 核心 token 被页面覆盖的比例
        coverage = compute_coverage(q_core, p_tokens_full)

        # Coverage 加权：coverage 低的页面得分打折
        # 这解决了"咖啡机压力泵"匹配到 espresso 页面的问题
        # espresso 页面能匹配"咖啡"相关词但"压力泵"完全没覆盖 → coverage 低
        if coverage < 0.3:
            score *= coverage * 2  # 严重惩罚
        elif coverage < 0.5:
            score *= 0.7

        if score > 0:
            meta_with_coverage = dict(meta)
            meta_with_coverage["_coverage"] = round(coverage, 2)
            results.append((page_path, score, meta_with_coverage))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]


def format_context(pages: list[tuple[Path, float, dict]], max_pages: int = 3) -> str:
    """将检索到的 wiki 页面格式化为上下文"""
    parts = []
    for page_path, score, meta in pages[:max_pages]:
        _, body = read_wiki_page(page_path)
        title = meta.get("title", page_path.stem)
        category = meta.get("category", "")
        rel_path = page_path.relative_to(WIKI_DIR)
        parts.append(f"### [{category}] {title}\n> 来源: wiki/{rel_path}\n\n{body}")
    return "\n\n---\n\n".join(parts)


# ============================================================
# Claude Code 模式：输出结构化结果供 Claude Code 直接使用
# ============================================================

def query_for_claude_code(question: str) -> str:
    """搜索 wiki 并输出结构化结果，供 Claude Code 直接阅读和回答"""
    results = search_wiki(question, top_k=5)

    if not results:
        return f"## 查询：{question}\n\nconfidence: NONE\n\n未找到相关知识页面。建议诚实告知用户知识库中没有相关信息。"

    top_score = results[0][1]
    top_coverage = results[0][2].get("_coverage", 0)
    confidence = get_confidence(top_score, top_coverage)

    output = f"## 查询：{question}\n\n"
    output += f"**confidence: {confidence}**\n\n"

    if confidence == "NONE":
        output += "知识库中没有与该问题直接相关的内容。建议诚实告知用户。\n"
        return output

    if confidence == "LOW":
        output += "> 注意：相关度较低，知识库可能不包含该问题的完整答案。如果信息不足，请诚实说明。\n\n"

    output += f"找到 {len(results)} 个相关页面（显示前 3 个）：\n\n"

    for i, (path, score, meta) in enumerate(results[:5], 1):
        rel = path.relative_to(WIKI_DIR)
        cov = meta.get("_coverage", 0)
        output += f"{i}. [{meta.get('title', path.stem)}](wiki/{rel}) (score: {score:.1f}, coverage: {cov:.0%})\n"

    output += "\n---\n\n"
    output += "## 参考知识\n\n"
    output += format_context(results, max_pages=3)

    output += "\n\n---\n\n"
    output += "## 回答指引\n\n"
    output += "请基于以上知识页面回答用户问题。要求：\n"
    output += "- 准确：只基于提供的知识内容回答，不要编造\n"
    output += "- 调性：温暖、专业、有故事感，符合星巴克品牌气质\n"
    output += "- 在回答末尾注明参考的 wiki 页面\n"
    if confidence == "LOW":
        output += "- 如果知识不足以完整回答，请诚实说明\n"

    return output


# ============================================================
# API 模式：调用 Claude API 生成回答（需要 ANTHROPIC_API_KEY）
# ============================================================

def query_with_api(question: str) -> str:
    """使用 Claude API 搜索 wiki 并生成回答"""
    from scripts.lib.llm import call_llm, call_llm_json

    index_content = get_index_content()
    if not index_content or "AUTO-GENERATED INDEX START" not in index_content:
        return "知识库尚未初始化。请先运行 ingest 导入文章。"

    RANK_SYSTEM = """你是星巴克知识库的搜索助手。根据用户问题和 wiki 索引，选出最相关的 1-3 个页面。
返回 JSON：{"pages": ["brand/xxx.md"], "reason": "原因"}
只返回 JSON。"""

    ANSWER_SYSTEM = """你是星巴克的知识顾问。基于提供的 wiki 知识页面回答用户问题。
要求：准确、温暖专业、200字以内、注明参考页面。"""

    print(f"搜索中: {question}")
    rank_result = call_llm_json(
        RANK_SYSTEM,
        f"## 用户问题\n{question}\n\n## Wiki 索引\n{index_content}",
    )

    selected_pages = rank_result.get("pages", [])
    if not selected_pages:
        return "抱歉，知识库中没有找到与您问题相关的内容。"

    print(f"找到 {len(selected_pages)} 个相关页面: {selected_pages}")

    context_parts = []
    for rel_path in selected_pages:
        page_path = WIKI_DIR / rel_path
        if not page_path.exists():
            stem = Path(rel_path).stem
            for p in list_wiki_pages():
                if p.stem == stem:
                    page_path = p
                    break
            else:
                continue
        meta, body = read_wiki_page(page_path)
        context_parts.append(f"### {meta.get('title', page_path.stem)}\n{body}")

    if not context_parts:
        return "抱歉，未能加载相关知识页面。"

    context = "\n\n---\n\n".join(context_parts)
    return call_llm(ANSWER_SYSTEM, f"## 用户问题\n{question}\n\n## 参考知识\n{context}")


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="查询星巴克知识库",
        epilog="""
示例：
  # Claude Code 模式（默认）— 输出检索结果，由 Claude Code 回答
  python3 scripts/query.py "星巴克Logo有什么含义？"

  # API 模式 — 调用 Claude API 直接生成回答
  python3 scripts/query.py --api "星巴克Logo有什么含义？"

  # 在 Claude Code 中使用：
  # > 帮我查询知识库：星巴克的第三空间是什么？
  # Claude Code 会运行 query.py，读取输出，然后基于知识回答
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("question", type=str, help="查询问题")
    parser.add_argument("--api", action="store_true",
                        help="使用 Claude API 模式（需要 ANTHROPIC_API_KEY）")
    parser.add_argument("--top-k", type=int, default=5,
                        help="返回前 K 个最相关页面（默认 5）")
    parser.add_argument("--json", action="store_true",
                        help="以 JSON 格式输出检索结果")
    args = parser.parse_args()

    if args.api:
        answer = query_with_api(args.question)
        print(f"\n{'='*50}")
        print(answer)
        print(f"{'='*50}")
    elif args.json:
        import json
        results = search_wiki(args.question, top_k=args.top_k)
        output = []
        for path, score, meta in results:
            rel = path.relative_to(WIKI_DIR)
            output.append({
                "path": str(rel),
                "title": meta.get("title", path.stem),
                "category": meta.get("category", ""),
                "score": round(score, 1),
                "tags": meta.get("tags", []),
            })
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # Claude Code 模式
        output = query_for_claude_code(args.question)
        print(output)


if __name__ == "__main__":
    main()
