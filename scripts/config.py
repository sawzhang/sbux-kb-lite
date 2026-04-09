"""项目配置"""

import os
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent

# 目录路径
SOURCES_DIR = ROOT_DIR / "sources"
WIKI_DIR = ROOT_DIR / "wiki"
SCHEMA_DIR = ROOT_DIR / "schema"

# 特殊页面
INDEX_PATH = WIKI_DIR / "index.md"
LOG_PATH = WIKI_DIR / "log.md"

# Wiki 分类
CATEGORIES = ["brand", "coffee", "products", "culture"]

# Frontmatter 必填字段
REQUIRED_FRONTMATTER = ["title", "category", "tags", "sources", "created", "updated"]

# LLM 配置
# 支持 anthropic / openai，通过环境变量 LLM_PROVIDER 切换
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic")  # "anthropic" | "openai"
LLM_MAX_TOKENS = 4096

# 各 provider 默认模型
LLM_MODELS = {
    "anthropic": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    "openai": os.environ.get("OPENAI_MODEL", "gpt-4o"),
}
