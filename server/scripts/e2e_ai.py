"""手动跑通解析、版本和生成方案。配置了 AI 时会真实请求模型。"""

import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import clear_settings_cache, get_settings
from app.db import init_db
from app.services.settings_loader import import_claude_settings


def main() -> None:
    """对正在运行的服务执行一次用户流程。"""
    import_claude_settings()
    clear_settings_cache()
    init_db()
    settings = get_settings()
    base = os.environ.get("ZHUANG_API", "http://127.0.0.1:8765")
    with httpx.Client(base_url=base, timeout=120.0) as client:
        parsed = client.post("/api/parse", json={"query": "我想装 Node.js"}).json()
        print("parse", parsed["slug"], parsed["name"])
        versions = client.get("/api/software/node/versions", params={"platform": "windows"}).json()
        version = versions["versions"][0]["version"]
        print("version", version, versions["source"])
        plan = client.post(
            "/api/plans",
            json={"slug": "node", "version": version, "platform": "windows"},
        )
        plan.raise_for_status()
        body = plan.json()
        print("plan", body["id"], body["generatedBy"], body["installType"])
        print(body["markdown"][:500])
        if settings.ai_api_key and body["generatedBy"] != "ai":
            raise SystemExit("已配置 AI，但方案不是 AI 生成")
        if not settings.ai_api_key:
            print("AI 未配置，本次使用本地安装说明")


if __name__ == "__main__":
    main()
