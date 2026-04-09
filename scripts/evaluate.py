#!/usr/bin/env python3
"""
知识库质量评估脚本

评估维度：
1. 结构健康度（Structure Health）— lint 指标
2. 知识覆盖率（Coverage）— 测试问题集的召回率
3. 检索准确率（Retrieval Precision）— top-K 结果是否相关
4. 内容丰富度（Content Richness）— 页面内容质量指标

用法：python3 scripts/evaluate.py
      python3 scripts/evaluate.py --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import CATEGORIES, WIKI_DIR
from scripts.lib.schema import find_broken_links, find_orphan_pages, validate_page
from scripts.lib.wiki_io import list_wiki_pages, read_wiki_page, extract_wiki_links
from scripts.query import search_wiki

# ============================================================
# 测试问题集（问题 + 期望命中的 wiki 页面 stem）
# ============================================================

TEST_QUERIES = [
    # Brand
    {"q": "星巴克是谁创立的？", "expect": ["starbucks-founding-1971", "howard-schultz-story"]},
    {"q": "星巴克的Logo是什么意思？", "expect": ["logo-siren-mythology", "logo-evolution-history"]},
    {"q": "Howard Schultz的故事", "expect": ["howard-schultz-story", "schultz-italy-trip"]},
    {"q": "星巴克中国有多少家门店？", "expect": ["china-market-growth", "starbucks-china-entry"]},
    {"q": "星巴克品牌名字怎么来的？", "expect": ["starbucks-name-origin"]},
    {"q": "星巴克上海烘焙工坊", "expect": ["shanghai-roastery"]},
    {"q": "星巴克的使命是什么？", "expect": ["starbucks-mission-values"]},
    {"q": "星巴克会员体系怎么积星？", "expect": ["starbucks-membership-system"]},
    {"q": "星巴克在云南做了什么？", "expect": ["starbucks-yunnan-project", "yunnan-coffee-terroir"]},
    {"q": "星巴克和瑞幸的竞争", "expect": ["starbucks-competitors-china"]},

    # Coffee
    {"q": "阿拉比卡和罗布斯塔有什么区别？", "expect": ["arabica-vs-robusta"]},
    {"q": "耶加雪菲咖啡什么风味？", "expect": ["yirgacheffe-coffee", "ethiopia-coffee-origin"]},
    {"q": "浅烘和深烘有什么区别？", "expect": ["blonde-roast-explained", "dark-roast-character"]},
    {"q": "怎么做手冲咖啡？", "expect": ["pour-over-guide"]},
    {"q": "冷萃咖啡是怎么做的？", "expect": ["cold-brew-method", "nitro-cold-brew"]},
    {"q": "咖啡因含量多少？", "expect": ["coffee-caffeine-facts"]},
    {"q": "什么是咖啡风味轮？", "expect": ["coffee-flavor-wheel"]},
    {"q": "苏门答腊咖啡有什么特点？", "expect": ["sumatra-coffee"]},
    {"q": "咖啡豆的研磨度怎么选？", "expect": ["coffee-grind-size"]},
    {"q": "咖啡是怎么从产地到杯子的？", "expect": ["seed-to-cup-journey"]},

    # Culture
    {"q": "什么是第三空间？", "expect": ["third-place-concept", "ray-oldenburg-third-place"]},
    {"q": "星巴克围裙颜色有什么区别？", "expect": ["green-apron-black-apron"]},
    {"q": "星巴克员工有什么福利？", "expect": ["partner-benefits", "partner-culture"]},
    {"q": "星巴克门店设计有什么特色？", "expect": ["store-design-philosophy", "store-localization-design"]},
    {"q": "星巴克的环保措施", "expect": ["sustainability-commitment", "greener-store-program"]},
    {"q": "星巴克城市杯是什么？", "expect": ["city-mug-collection"]},
    {"q": "星巴克圣诞红杯", "expect": ["starbucks-holiday-cups"]},
    {"q": "星巴克非遗概念店", "expect": ["non-heritage-concept-stores"]},

    # Products
    {"q": "星冰乐是怎么发明的？", "expect": ["frappuccino-history"]},
    {"q": "南瓜拿铁是什么？", "expect": ["pumpkin-spice-latte"]},
    {"q": "焦糖玛奇朵怎么喝？", "expect": ["caramel-macchiato-story"]},
    {"q": "星巴克有哪些季节限定饮品？", "expect": ["starbucks-seasonal-drinks"]},
    {"q": "什么是氮气冷萃？", "expect": ["nitro-cold-brew"]},
    {"q": "星巴克有素食选择吗？", "expect": ["starbucks-plant-based"]},
    {"q": "星巴克月饼", "expect": ["mooncake-gift-box"]},
    {"q": "星巴克臻选门店有什么特别的？", "expect": ["starbucks-reserve-experience", "reserve-exclusive-drinks"]},
]


def evaluate_structure() -> dict:
    """评估结构健康度"""
    pages = list_wiki_pages()
    total = len(pages)

    schema_errors = 0
    for p in pages:
        schema_errors += len(validate_page(p))

    broken = len(find_broken_links())
    orphans = len(find_orphan_pages())

    # 交叉引用密度
    total_links = 0
    for p in pages:
        content = p.read_text(encoding="utf-8")
        total_links += len(extract_wiki_links(content))
    avg_links = total_links / total if total > 0 else 0

    return {
        "total_pages": total,
        "schema_errors": schema_errors,
        "broken_links": broken,
        "orphan_pages": orphans,
        "total_cross_refs": total_links,
        "avg_cross_refs_per_page": round(avg_links, 1),
        "schema_compliance": round((1 - schema_errors / max(total * 6, 1)) * 100, 1),  # 6 required fields
    }


def evaluate_content_richness() -> dict:
    """评估内容丰富度"""
    pages = list_wiki_pages()
    word_counts = []
    section_counts = []
    has_key_points = 0
    has_related = 0
    category_dist = {}

    for p in pages:
        meta, body = read_wiki_page(p)
        # 字数统计（中文字符 + 英文单词）
        cn_chars = len(re.findall(r'[\u4e00-\u9fff]', body))
        en_words = len(re.findall(r'[a-zA-Z]+', body))
        word_counts.append(cn_chars + en_words)

        # 章节数
        sections = len(re.findall(r'^##\s', body, re.MULTILINE))
        section_counts.append(sections)

        # 核心要点
        if "## 核心要点" in body:
            has_key_points += 1

        # 相关页面
        if "## 相关页面" in body:
            has_related += 1

        # 分类分布
        cat = meta.get("category", "unknown")
        category_dist[cat] = category_dist.get(cat, 0) + 1

    total = len(pages)
    return {
        "avg_word_count": round(sum(word_counts) / total) if total else 0,
        "min_word_count": min(word_counts) if word_counts else 0,
        "max_word_count": max(word_counts) if word_counts else 0,
        "avg_sections": round(sum(section_counts) / total, 1) if total else 0,
        "has_key_points_pct": round(has_key_points / total * 100, 1) if total else 0,
        "has_related_pct": round(has_related / total * 100, 1) if total else 0,
        "category_distribution": category_dist,
    }


def evaluate_retrieval(verbose: bool = False) -> dict:
    """评估检索准确率"""
    hit_at_1 = 0
    hit_at_3 = 0
    hit_at_5 = 0
    mrr_sum = 0.0
    total = len(TEST_QUERIES)
    failures = []

    for tc in TEST_QUERIES:
        question = tc["q"]
        expected = set(tc["expect"])

        results = search_wiki(question, top_k=5)
        result_stems = [r[0].stem for r in results]

        # Hit@K: 期望页面是否出现在 top-K 结果中
        hit_1 = bool(expected & set(result_stems[:1]))
        hit_3 = bool(expected & set(result_stems[:3]))
        hit_5 = bool(expected & set(result_stems[:5]))

        if hit_1:
            hit_at_1 += 1
        if hit_3:
            hit_at_3 += 1
        if hit_5:
            hit_at_5 += 1

        # MRR: 第一个命中结果的倒数排名
        rr = 0.0
        for i, stem in enumerate(result_stems):
            if stem in expected:
                rr = 1.0 / (i + 1)
                break
        mrr_sum += rr

        if not hit_3:
            failures.append({
                "question": question,
                "expected": list(expected),
                "got": result_stems[:5],
            })

        if verbose:
            status = "✓" if hit_3 else "✗"
            print(f"  {status} {question}")
            if not hit_3:
                print(f"    期望: {list(expected)}")
                print(f"    实际: {result_stems[:5]}")

    return {
        "total_queries": total,
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
        "hit_at_5": hit_at_5,
        "precision_at_1": round(hit_at_1 / total * 100, 1),
        "precision_at_3": round(hit_at_3 / total * 100, 1),
        "precision_at_5": round(hit_at_5 / total * 100, 1),
        "mrr": round(mrr_sum / total, 3),
        "failures": failures,
    }


def print_report(structure: dict, content: dict, retrieval: dict):
    """输出评估报告"""
    print("=" * 60)
    print("星巴克知识库质量评估报告")
    print("=" * 60)

    print("\n## 1. 结构健康度 (Structure Health)")
    print(f"  总页面数:        {structure['total_pages']}")
    print(f"  Schema 合规率:   {structure['schema_compliance']}%")
    print(f"  Schema 错误:     {structure['schema_errors']}")
    print(f"  断链数:          {structure['broken_links']}")
    print(f"  孤立页面:        {structure['orphan_pages']}")
    print(f"  交叉引用总数:    {structure['total_cross_refs']}")
    print(f"  平均引用/页:     {structure['avg_cross_refs_per_page']}")

    print("\n## 2. 内容丰富度 (Content Richness)")
    print(f"  平均字数/页:     {content['avg_word_count']}")
    print(f"  字数范围:        {content['min_word_count']} ~ {content['max_word_count']}")
    print(f"  平均章节数/页:   {content['avg_sections']}")
    print(f"  核心要点覆盖率:  {content['has_key_points_pct']}%")
    print(f"  相关页面覆盖率:  {content['has_related_pct']}%")
    print(f"  分类分布:        {content['category_distribution']}")

    print("\n## 3. 检索准确率 (Retrieval Precision)")
    print(f"  测试问题数:      {retrieval['total_queries']}")
    print(f"  Precision@1:     {retrieval['precision_at_1']}% ({retrieval['hit_at_1']}/{retrieval['total_queries']})")
    print(f"  Precision@3:     {retrieval['precision_at_3']}% ({retrieval['hit_at_3']}/{retrieval['total_queries']})")
    print(f"  Precision@5:     {retrieval['precision_at_5']}% ({retrieval['hit_at_5']}/{retrieval['total_queries']})")
    print(f"  MRR:             {retrieval['mrr']}")

    if retrieval['failures']:
        print(f"\n  未命中的查询 ({len(retrieval['failures'])} 个):")
        for f in retrieval['failures']:
            print(f"    - {f['question']}")
            print(f"      期望: {f['expected']}")
            print(f"      实际 top5: {f['got']}")

    # 综合评分
    print("\n## 4. 综合评分")
    s1 = min(100, structure['schema_compliance'])
    s2 = content['has_key_points_pct'] * 0.5 + content['has_related_pct'] * 0.5
    s3 = retrieval['precision_at_3']
    overall = round(s1 * 0.2 + s2 * 0.3 + s3 * 0.5, 1)
    print(f"  结构健康度:      {s1:.1f} / 100 (权重 20%)")
    print(f"  内容丰富度:      {s2:.1f} / 100 (权重 30%)")
    print(f"  检索准确率:      {s3:.1f} / 100 (权重 50%)")
    print(f"  ────────────────────────")
    print(f"  综合得分:        {overall} / 100")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="知识库质量评估")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细检索结果")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    if args.verbose:
        print("检索测试详情:\n")

    structure = evaluate_structure()
    content = evaluate_content_richness()
    retrieval = evaluate_retrieval(verbose=args.verbose)

    if args.json:
        print(json.dumps({
            "structure": structure,
            "content": content,
            "retrieval": retrieval,
        }, ensure_ascii=False, indent=2))
    else:
        print_report(structure, content, retrieval)


if __name__ == "__main__":
    main()
