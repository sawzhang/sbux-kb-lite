"""Claude API 封装"""

import json
import os

import anthropic

from scripts.config import LLM_MAX_TOKENS, LLM_MODEL


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("请设置 ANTHROPIC_API_KEY 环境变量")
    return anthropic.Anthropic(api_key=api_key)


def call_llm(system: str, user: str, *, max_tokens: int = LLM_MAX_TOKENS) -> str:
    """调用 Claude，返回文本响应"""
    client = get_client()
    resp = client.messages.create(
        model=LLM_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


def call_llm_json(system: str, user: str, *, max_tokens: int = LLM_MAX_TOKENS) -> dict:
    """调用 Claude 并解析 JSON 响应"""
    text = call_llm(system, user, max_tokens=max_tokens)
    # 尝试从 markdown code block 中提取 JSON
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        text = text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        text = text[start:end].strip()
    return json.loads(text)
