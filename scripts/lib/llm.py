"""LLM API 封装 — 支持 Anthropic Claude 和 OpenAI"""

import json
import os

from scripts.config import LLM_MAX_TOKENS, LLM_MODELS, LLM_PROVIDER


def _get_provider() -> str:
    return LLM_PROVIDER


# ============================================================
# Anthropic
# ============================================================

def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("请设置 ANTHROPIC_API_KEY 环境变量")
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=LLM_MODELS["anthropic"],
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text


# ============================================================
# OpenAI
# ============================================================

def _call_openai(system: str, user: str, max_tokens: int) -> str:
    import openai
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("请设置 OPENAI_API_KEY 环境变量")
    client = openai.OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=LLM_MODELS["openai"],
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


# ============================================================
# 统一接口
# ============================================================

def call_llm(system: str, user: str, *, max_tokens: int = LLM_MAX_TOKENS) -> str:
    """调用 LLM，返回文本响应。根据 LLM_PROVIDER 环境变量自动选择 provider。"""
    provider = _get_provider()
    if provider == "openai":
        return _call_openai(system, user, max_tokens)
    else:
        return _call_anthropic(system, user, max_tokens)


def call_llm_json(system: str, user: str, *, max_tokens: int = LLM_MAX_TOKENS) -> dict:
    """调用 LLM 并解析 JSON 响应"""
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
