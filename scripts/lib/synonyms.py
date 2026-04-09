"""同义词表：用于查询扩展，提升检索的语义覆盖率"""

# 双向同义词映射
# key 的同义词 = value 列表中的所有词
# 查询时：如果 query 中出现 key，自动扩展 value 中的词加入匹配
SYNONYMS: dict[str, list[str]] = {
    # 品牌/组织
    "员工": ["伙伴", "partner", "咖啡师"],
    "伙伴": ["员工", "partner", "咖啡师"],
    "partner": ["伙伴", "员工"],
    "创始人": ["创立", "创办", "创建", "founder"],
    "创立": ["创始人", "创办", "创建", "成立"],
    "创办": ["创始人", "创立", "成立"],
    "founder": ["创始人", "创立"],

    # Logo/标志
    "标志": ["logo", "标识", "图标", "美人鱼"],
    "标识": ["logo", "标志"],
    "logo": ["标志", "标识", "美人鱼", "siren"],
    "siren": ["塞壬", "美人鱼", "logo"],
    "美人鱼": ["塞壬", "siren", "logo", "标志"],
    "塞壬": ["siren", "美人鱼"],

    # 环保/可持续
    "环保": ["可持续", "绿色", "减塑", "低碳", "sustainability"],
    "可持续": ["环保", "绿色", "减塑", "sustainability"],
    "绿色": ["环保", "可持续"],
    "减塑": ["环保", "可持续", "吸管"],
    "sustainability": ["可持续", "环保", "绿色"],

    # 门店/空间
    "门店": ["店铺", "店面", "store"],
    "店铺": ["门店", "店面"],
    "store": ["门店", "店铺"],
    "第三空间": ["third place", "社交空间"],
    "third": ["第三"],
    "place": ["空间", "场所"],

    # 咖啡术语
    "烘焙": ["roast", "烘培"],
    "roast": ["烘焙", "烘培"],
    "浅烘": ["light roast", "blonde", "浅焙"],
    "深烘": ["dark roast", "深焙"],
    "blonde": ["浅烘", "浅焙"],
    "冷萃": ["cold brew", "冷泡"],
    "cold": ["冷萃", "冷泡"],
    "brew": ["冲煮", "萃取"],
    "手冲": ["pour over", "滤杯"],
    "浓缩": ["espresso"],
    "espresso": ["浓缩", "意式"],
    "拉花": ["latte art"],
    "latte": ["拿铁"],
    "拿铁": ["latte"],
    "frappuccino": ["星冰乐"],
    "星冰乐": ["frappuccino"],

    # 产品
    "饮品": ["饮料", "产品", "drink"],
    "饮料": ["饮品", "drink"],
    "限定": ["季节", "节日", "seasonal"],
    "季节": ["限定", "seasonal"],
    "杯子": ["马克杯", "随行杯", "城市杯", "mug"],
    "mug": ["杯子", "马克杯"],
    "月饼": ["中秋", "mooncake"],
    "mooncake": ["月饼", "中秋"],

    # 人物
    "舒尔茨": ["schultz", "howard"],
    "schultz": ["舒尔茨", "howard"],
    "howard": ["舒尔茨", "schultz"],

    # 地点
    "云南": ["yunnan", "普洱"],
    "yunnan": ["云南"],
    "上海": ["shanghai"],
    "shanghai": ["上海"],
    "派克": ["pike place"],
    "pike": ["派克"],

    # 文化
    "围裙": ["apron", "黑围裙", "绿围裙"],
    "apron": ["围裙"],
    "福利": ["benefit", "待遇", "津贴"],
    "会员": ["membership", "星享", "积星"],
    "membership": ["会员", "星享"],
}


def expand_query_tokens(tokens: set[str]) -> set[str]:
    """将 query tokens 通过同义词表扩展"""
    expanded = set(tokens)
    for token in tokens:
        # 精确匹配
        if token in SYNONYMS:
            expanded.update(SYNONYMS[token])
        # 子串匹配（如 query 中有"创始人"，匹配 SYNONYMS key "创始人"）
        for key, values in SYNONYMS.items():
            if len(key) >= 2 and key in token:
                expanded.update(values)
    return expanded
