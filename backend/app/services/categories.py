CATEGORIES = {
    "food": "餐饮",
    "transport": "交通",
    "shopping": "购物",
    "housing": "居住",
    "entertainment": "娱乐",
    "education": "学习",
    "health": "健康",
    "subscription": "订阅",
    "travel": "旅行",
    "social": "社交",
    "salary": "工资收入",
    "reimbursement": "报销",
    "other": "其他",
}

KEYWORD_RULES = {
    "salary": ["工资", "实习工资", "兼职", "薪水", "收入"],
    "reimbursement": ["报销"],
    "food": ["午饭", "晚饭", "早餐", "咖啡", "拉面", "外卖", "便当", "餐", "吃"],
    "transport": ["地铁", "公交", "出租车", "打车", "电车", "交通", "车票"],
    "shopping": ["amazon", "买", "购物", "衣服", "电子", "书"],
    "housing": ["房租", "水电", "家具", "家賃"],
    "entertainment": ["电影", "游戏", "演唱会", "娱乐"],
    "education": ["课程", "学会", "教材", "书籍"],
    "health": ["药", "医院", "健身", "体检"],
    "subscription": ["chatgpt", "netflix", "订阅", "云服务", "会员"],
    "travel": ["酒店", "机票", "签证", "旅行"],
    "social": ["朋友", "聚餐", "礼物", "烤肉"],
}


def categorize(text: str) -> str:
    lowered = text.lower()
    for category, keywords in KEYWORD_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "other"


def display_category(category: str) -> str:
    return CATEGORIES.get(category, category)
