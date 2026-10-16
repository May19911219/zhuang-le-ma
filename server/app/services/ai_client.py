import json
import re

import httpx

from app.config import get_settings

PLAN_SYSTEM = """你是安装脚本作者。只输出一个 JSON 对象，不要使用 Markdown 围栏，不要输出额外解释。
字段必须是 installType、markdown、script、scriptShell、officialUrl。
installType 只能是 script 或 official_link。
如果调用方要求官方下载页，installType 必须是 official_link，script 为空字符串，scriptShell 为空字符串。markdown 只写官方下载链接、打开方式和怎么确认已经装好，不要写安装脚本。
如果是脚本安装，Windows 的 scriptShell 用 powershell，macOS 和 Linux 用 bash。
script 必须包含中文注释、环境变量配置、安装后的验证命令，以及权限不足或命令找不到时的处理。
markdown 使用简体中文，并且包含这三节：一键安装脚本、脚本运行说明、执行后建议。脚本放在对应语言的代码块里。
不要推荐学习资料、课程、书籍或博客，不要介绍软件是什么，不要写历史和优缺点。"""

VERSION_SYSTEM = """你只输出 JSON 数组，元素是版本号字符串，最新稳定版放在第一位。
不要包含 alpha、beta、rc、preview。不要输出解释。最多 8 个。"""


def ai_ready() -> bool:
    """判断 AI 密钥和接口地址是否都已配置。"""
    settings = get_settings()
    return bool(settings.ai_api_key.strip() and settings.ai_base_url.strip())


def completions_url(base_url: str) -> str:
    """把 Base URL 拼成 OpenAI 兼容的 chat completions 地址。"""
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def extract_json(text: str):
    """从模型回复里取出 JSON 对象或数组。"""
    raw = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fenced:
        raw = fenced.group(1).strip()
    start_obj = raw.find("{")
    start_arr = raw.find("[")
    if start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
        end = raw.rfind("]")
        return json.loads(raw[start_arr : end + 1])
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("模型没有返回 JSON")
    return json.loads(raw[start : end + 1])


def chat_json(system: str, user: str, timeout: float = 90.0):
    """调用 OpenAI 兼容聊天接口，并把回复解析成 JSON。"""
    settings = get_settings()
    if not ai_ready():
        raise RuntimeError("AI 未配置")
    models = [settings.ai_model.strip() or "claude-sonnet-4-5"]
    extras = ["claude-sonnet-4-5", "claude-3-5-sonnet-20241022"]
    if "deepseek" in settings.ai_base_url.lower():
        extras.insert(0, "deepseek-chat")
    for extra in extras:
        if extra not in models:
            models.append(extra)
    last_error = "AI 请求失败"
    url = completions_url(settings.ai_base_url)
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key.strip()}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        for model in models:
            payload = {
                "model": model,
                "temperature": 0.2,
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            }
            try:
                response = client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                if isinstance(content, list):
                    content = "".join(
                        part.get("text", "") for part in content if isinstance(part, dict)
                    )
                return extract_json(str(content))
            except Exception as exc:
                last_error = str(exc)
                continue
    raise RuntimeError(last_error)
