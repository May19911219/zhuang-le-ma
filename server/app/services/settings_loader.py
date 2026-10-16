import json
import os
from pathlib import Path

from app.config import ENV_PATH, clear_settings_cache


def claude_settings_path() -> Path:
    """定位 Claude 配置文件，可用环境变量覆盖默认路径。"""
    override = os.environ.get("CLAUDE_SETTINGS_PATH", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".claude" / "settings.json"


def import_claude_settings() -> bool:
    """把 Claude 配置里的密钥和接口地址写入 server/.env。"""
    if os.environ.get("ZHUANG_SKIP_SETTINGS_IMPORT") == "1":
        return False
    path = claude_settings_path()
    if not path.is_file():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    env = data.get("env") or {}
    token = str(env.get("ANTHROPIC_AUTH_TOKEN") or "").strip()
    base_url = str(env.get("ANTHROPIC_BASE_URL") or "").strip()
    if not token or not base_url:
        return False
    _write_env_values({"AI_API_KEY": token, "AI_BASE_URL": base_url})
    clear_settings_cache()
    return True


def _write_env_values(updates: dict[str, str]) -> None:
    """合并写入 .env，保留文件里已有的其他配置。"""
    lines: list[str] = []
    if ENV_PATH.is_file():
        lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    next_lines: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in updates:
            next_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            next_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            next_lines.append(f"{key}={value}")
    if not any(line.startswith("AI_MODEL=") for line in next_lines):
        next_lines.append("AI_MODEL=claude-sonnet-4-5")
    if not any(line.startswith("ADMIN_PASSWORD=") for line in next_lines):
        next_lines.append("ADMIN_PASSWORD=zhuang-le-ma")
    ENV_PATH.write_text("\n".join(next_lines) + "\n", encoding="utf-8")
