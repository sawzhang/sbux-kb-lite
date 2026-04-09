"""项目配置"""

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
LLM_MODEL = "claude-sonnet-4-20250514"
LLM_MAX_TOKENS = 4096
