#!/usr/bin/env python3
"""
Crawl 脚本：通过 Claude Code 的 WebSearch + WebFetch 抓取星巴克相关文章

本脚本设计为由 Claude Code 直接执行（利用其内置的 WebSearch/WebFetch 工具），
而不是作为独立 Python 脚本运行。

## 使用方式（在 Claude Code 中）

直接告诉 Claude Code：
  "运行 crawl 抓取星巴克文章" 或 "帮我抓取星巴克知识库文章"

Claude Code 会：
1. 读取本脚本中定义的搜索主题列表
2. 用 WebSearch 搜索每个主题
3. 用 WebFetch 抓取文章内容
4. 保存为 markdown 到 sources/ 目录

## 也可以作为独立脚本运行（降级模式）

使用 requests + BeautifulSoup 从预定义 URL 列表抓取：
  python3 scripts/crawl.py --standalone
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.config import SOURCES_DIR

# ============================================================
# 搜索主题定义 — Claude Code 模式和独立模式共用
# ============================================================

SEARCH_TOPICS = {
    "brand": [
        "星巴克品牌历史 创始人故事",
        "星巴克 Howard Schultz 创业故事",
        "星巴克Logo演变 双尾美人鱼",
        "星巴克企业使命 核心价值观",
        "星巴克中国市场发展历程",
        "星巴克上海烘焙工坊 Roastery",
        "星巴克全球扩张策略",
        "Starbucks brand history origin story",
        "Starbucks mission values corporate culture",
        "星巴克品牌命名由来 白鲸记",
        "星巴克 Pike Place 第一家门店",
        "星巴克收购历史 Il Giornale",
    ],
    "coffee": [
        "咖啡豆品种 阿拉比卡 罗布斯塔 区别",
        "咖啡产地 埃塞俄比亚 哥伦比亚 风味特点",
        "咖啡烘焙度 浅烘 中烘 深烘 区别",
        "星巴克咖啡豆产地 采购标准",
        "意式浓缩咖啡 espresso 制作原理",
        "手冲咖啡 冲煮方法 技巧",
        "冷萃咖啡 cold brew 制作方法",
        "星巴克 CAFE Practices 咖啡采购认证",
        "咖啡风味轮 品鉴方法",
        "云南咖啡 星巴克合作 种植",
        "咖啡处理法 水洗 日晒 蜜处理",
        "拿铁艺术 latte art 咖啡拉花",
        "星巴克臻选 Reserve 精品咖啡",
        "Starbucks coffee sourcing single origin",
    ],
    "culture": [
        "星巴克第三空间 Third Place 理念",
        "星巴克门店设计 本地化",
        "星巴克伙伴文化 员工福利",
        "星巴克可持续发展 环保举措",
        "星巴克社区公益 社会责任",
        "星巴克数字化转型 移动点单",
        "星巴克会员体系 星星奖励",
        "星巴克门店故事 特色门店",
        "Starbucks third place concept store design",
        "星巴克咖啡师培训 黑围裙",
        "星巴克季节限定 节日杯 文化",
        "星巴克宠物友好门店",
    ],
    "products": [
        "星巴克经典饮品 拿铁 卡布奇诺 星冰乐",
        "星巴克季节限定饮品 南瓜拿铁",
        "星巴克隐藏菜单 特调饮品",
        "星巴克食品 蛋糕 三明治",
        "星巴克杯子文化 城市杯 联名款",
        "星巴克咖啡豆零售 家用产品",
        "Starbucks Frappuccino history invention",
        "星巴克茶饮 Teavana",
    ],
}

# 所有主题的 flat 列表
ALL_TOPICS = []
for category, topics in SEARCH_TOPICS.items():
    for topic in topics:
        ALL_TOPICS.append({"category": category, "query": topic})


def get_topic_list() -> list[dict]:
    """返回搜索主题列表供 Claude Code 使用"""
    return ALL_TOPICS


def save_article(filename: str, title: str, source_url: str, content: str, category: str) -> Path:
    """保存抓取的文章到 sources/ 目录"""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    # 清理 filename
    filename = re.sub(r"[^\w\u4e00-\u9fff-]", "-", filename)
    filename = re.sub(r"-+", "-", filename).strip("-").lower()
    if not filename.endswith(".md"):
        filename += ".md"

    path = SOURCES_DIR / filename
    # 避免重名
    if path.exists():
        stem = path.stem
        for i in range(2, 100):
            path = SOURCES_DIR / f"{stem}-{i}.md"
            if not path.exists():
                break

    article = f"---\n"
    article += f"title: \"{title}\"\n"
    article += f"source: \"{source_url}\"\n"
    article += f"category: {category}\n"
    article += f"---\n\n"
    article += f"# {title}\n\n"
    article += content

    path.write_text(article, encoding="utf-8")
    return path


def list_saved_sources() -> list[str]:
    """列出已保存的 source 文件"""
    if not SOURCES_DIR.exists():
        return []
    return sorted([f.name for f in SOURCES_DIR.glob("*.md")])


# ============================================================
# 独立模式（降级）：用 requests 抓取预定义 URL
# ============================================================

def standalone_crawl():
    """独立运行模式 — 仅打印搜索主题，提示用 Claude Code 运行"""
    print("=" * 60)
    print("星巴克知识库文章抓取")
    print("=" * 60)
    print()
    print(f"共定义 {len(ALL_TOPICS)} 个搜索主题：")
    print()

    for i, topic in enumerate(ALL_TOPICS, 1):
        print(f"  {i:3d}. [{topic['category']:8s}] {topic['query']}")

    print()
    print("=" * 60)
    print("推荐：在 Claude Code 中运行以获得最佳效果")
    print()
    print("  在 Claude Code 中输入：")
    print("  > 帮我运行 crawl 脚本抓取星巴克文章到 sources 目录")
    print()
    print("  Claude Code 会使用内置的 WebSearch + WebFetch 工具")
    print("  自动搜索、抓取、保存文章。")
    print("=" * 60)

    already = list_saved_sources()
    if already:
        print(f"\n已有 {len(already)} 篇文章：")
        for f in already[:10]:
            print(f"  - {f}")
        if len(already) > 10:
            print(f"  ... 及其他 {len(already) - 10} 篇")


def main():
    parser = argparse.ArgumentParser(description="抓取星巴克相关文章")
    parser.add_argument("--standalone", action="store_true", help="独立运行模式（打印主题列表）")
    parser.add_argument("--list-topics", action="store_true", help="以 JSON 输出主题列表")
    args = parser.parse_args()

    if args.list_topics:
        print(json.dumps(ALL_TOPICS, ensure_ascii=False, indent=2))
    else:
        standalone_crawl()


if __name__ == "__main__":
    main()
