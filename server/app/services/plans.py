import json
import re
from datetime import timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.catalog import PRESETS
from app.models import Feedback, Plan, SelectionStat, Software, VersionEntry, utcnow
from app.services.ai_client import PLAN_SYSTEM, ai_ready, chat_json
from app.services.scripts import fallback_markdown, shell_for
from app.services.versions import ai_versions, fetch_remote_versions, sort_versions

PLATFORMS = {"windows", "macos", "linux"}
CACHE_SECONDS = 24 * 60 * 60
VERSION_PATTERN = re.compile(r"^\d+\.\d+(?:\.\d+)?$")


def normalize_platform(platform: str) -> str:
    """校验并规范化平台名称。"""
    value = platform.strip().lower()
    if value in {"win32", "win", "windows"}:
        return "windows"
    if value in {"darwin", "mac", "macos", "osx"}:
        return "macos"
    if value == "linux":
        return "linux"
    raise HTTPException(status_code=400, detail="平台只能是 windows、macos 或 linux")


def software_payload(row: Software) -> dict:
    """把软件记录转成接口字段。"""
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "installType": row.install_type,
        "officialUrl": row.official_url,
        "sourceType": row.source_type,
    }


def parse_query(db: Session, query: str) -> dict:
    """从一句话里识别预置软件，识别不到时再交给 AI。"""
    text = query.strip().lower()
    for noise in ("我想装", "我想要装", "帮我装", "请安装", "安装", "装一个", "装个", "装"):
        text = text.replace(noise, " ")
    text = re.sub(r"\s+", " ", text).strip(" 吧了呢啊。.!！")
    for item in PRESETS:
        names = [item["name"].lower(), item["slug"], *item["aliases"]]
        if any(_contains_alias(text, alias) for alias in names if alias):
            row = db.query(Software).filter(Software.slug == item["slug"]).one()
            return {**software_payload(row), "matched": True}
    if ai_ready():
        try:
            guessed = chat_json(
                "只输出 JSON：{\"name\":\"软件名\",\"installType\":\"script 或 official_link\",\"officialUrl\":\"没有则空字符串\"}。不要解释。",
                f"用户原话：{query}",
                timeout=40.0,
            )
            name = str(guessed.get("name") or "").strip()
            if name:
                row = _ensure_software(
                    db,
                    name,
                    str(guessed.get("installType") or "script"),
                    str(guessed.get("officialUrl") or ""),
                )
                return {**software_payload(row), "matched": False}
        except Exception:
            pass
    cleaned = query.strip()
    for noise in ("我想装", "我想要装", "帮我装", "请安装", "安装", "装一个", "装个"):
        if cleaned.startswith(noise):
            cleaned = cleaned[len(noise) :].strip()
    row = _ensure_software(db, cleaned or query.strip(), "script", "")
    return {**software_payload(row), "matched": False}


def _contains_alias(text: str, alias: str) -> bool:
    """按词边界判断一句话里有没有某个软件别名。"""
    pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _slugify(name: str) -> str:
    """把软件名变成 slug。"""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "software"


def _ensure_software(db: Session, name: str, install_type: str, official_url: str) -> Software:
    """按名称找到或创建一条软件记录。"""
    slug = _slugify(name)
    row = db.query(Software).filter(Software.slug == slug).one_or_none()
    if row:
        return row
    if install_type not in {"script", "official_link"}:
        install_type = "official_link" if official_url else "script"
    row = Software(
        name=name.strip() or slug,
        slug=slug,
        source_type="generic",
        install_type=install_type,
        official_url=official_url,
        aliases=json.dumps([name.lower()], ensure_ascii=False),
        fallback_versions="[]",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_versions(db: Session, slug: str, platform: str) -> dict:
    """按缓存、远程源、AI、内置列表的顺序返回版本。"""
    normalize_platform(platform)
    software = db.query(Software).filter(Software.slug == slug).one_or_none()
    if software is None:
        raise HTTPException(status_code=404, detail="没有这个软件")
    cached = _fresh_versions(db, software.id)
    if cached:
        return _version_payload(software, cached, "cache")
    source = "remote"
    found: list[str] = []
    try:
        found = fetch_remote_versions(software)
    except Exception:
        found = []
    if not found:
        source = "ai"
        try:
            found = ai_versions(software)
        except Exception:
            found = []
    if not found:
        source = "builtin"
        found = sort_versions(json.loads(software.fallback_versions or "[]"))
    if not found:
        raise HTTPException(status_code=404, detail="没有查到可用版本")
    _replace_versions(db, software.id, found, source)
    rows = (
        db.query(VersionEntry)
        .filter(VersionEntry.software_id == software.id)
        .order_by(VersionEntry.id.asc())
        .all()
    )
    return _version_payload(software, rows, source)


def _fresh_versions(db: Session, software_id: int) -> list[VersionEntry]:
    """返回 24 小时内的版本缓存。"""
    rows = (
        db.query(VersionEntry)
        .filter(VersionEntry.software_id == software_id)
        .order_by(VersionEntry.id.asc())
        .all()
    )
    if not rows:
        return []
    fetched_at = rows[0].fetched_at
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    age = (utcnow() - fetched_at).total_seconds()
    if age > CACHE_SECONDS:
        return []
    return rows


def _replace_versions(db: Session, software_id: int, versions: list[str], source: str) -> None:
    """用新的版本列表替换该软件的缓存。"""
    db.query(VersionEntry).filter(VersionEntry.software_id == software_id).delete()
    now = utcnow()
    for index, version in enumerate(versions):
        db.add(
            VersionEntry(
                software_id=software_id,
                version=version,
                is_latest_stable=index == 0,
                source=source,
                fetched_at=now,
            )
        )
    db.commit()


def _version_payload(software: Software, rows: list[VersionEntry], source: str) -> dict:
    """组装版本列表响应。"""
    return {
        "software": software_payload(software),
        "source": source,
        "versions": [
            {
                "version": row.version,
                "isLatestStable": row.is_latest_stable,
            }
            for row in rows
        ],
    }


def get_or_create_plan(db: Session, slug: str, version: str, platform: str, force_ai: bool = False) -> Plan:
    """按软件、版本、平台返回方案，没有则生成并计数。"""
    platform = normalize_platform(platform)
    if not VERSION_PATTERN.match(version):
        raise HTTPException(status_code=400, detail="版本号格式不正确")
    software = db.query(Software).filter(Software.slug == slug).one_or_none()
    if software is None:
        raise HTTPException(status_code=404, detail="没有这个软件")
    existing = (
        db.query(Plan)
        .filter(Plan.software_id == software.id, Plan.version == version, Plan.platform == platform)
        .one_or_none()
    )
    if existing and not force_ai:
        _bump(db, software.id, version, platform)
        return existing
    markdown, script, script_shell, install_type, official_url, generated_by = _generate(
        software, version, platform, force_ai
    )
    if existing:
        existing.markdown = markdown
        existing.script = script
        existing.script_shell = script_shell
        existing.install_type = install_type
        existing.official_url = official_url
        existing.generated_by = generated_by
        existing.updated_at = utcnow()
        db.commit()
        db.refresh(existing)
        _bump(db, software.id, version, platform)
        return existing
    plan = Plan(
        software_id=software.id,
        version=version,
        platform=platform,
        markdown=markdown,
        script=script,
        script_shell=script_shell,
        install_type=install_type,
        official_url=official_url,
        generated_by=generated_by,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    _bump(db, software.id, version, platform)
    return plan


def _generate(software: Software, version: str, platform: str, force_ai: bool):
    """优先用 AI 生成方案，失败时使用本地安装说明。"""
    if ai_ready():
        try:
            return _generate_with_ai(software, version, platform)
        except Exception:
            if force_ai:
                raise HTTPException(status_code=502, detail="AI 重新生成失败")
    elif force_ai:
        raise HTTPException(status_code=503, detail="还没有配置 AI")
    markdown, script, script_shell = fallback_markdown(
        software.name,
        software.slug,
        version,
        platform,
        software.install_type,
        software.official_url,
    )
    return markdown, script, script_shell, software.install_type, software.official_url, "fallback"


def _generate_with_ai(software: Software, version: str, platform: str):
    """调用 AI 生成安装 Markdown 和脚本。"""
    user = "\n".join(
        [
            f"软件：{software.name}",
            f"版本：{version}",
            f"平台：{platform}",
            f"安装类型：{software.install_type}",
            f"官方地址：{software.official_url or '无'}",
        ]
    )
    data = chat_json(PLAN_SYSTEM, user)
    install_type = software.install_type
    if install_type != "official_link":
        install_type = "official_link" if data.get("installType") == "official_link" else "script"
    script = "" if install_type == "official_link" else str(data.get("script") or "")
    script_shell = "" if install_type == "official_link" else str(data.get("scriptShell") or shell_for(platform))
    official_url = str(data.get("officialUrl") or software.official_url or "")
    markdown = str(data.get("markdown") or "").strip()
    if install_type == "official_link" and official_url and official_url not in markdown:
        markdown = f"{markdown}\n\n官方下载页：{official_url}".strip()
    if not markdown or (install_type == "script" and not script):
        raise RuntimeError("AI 返回的方案不完整")
    if install_type == "script" and script_shell not in {"powershell", "bash"}:
        script_shell = shell_for(platform)
    return markdown, script, script_shell, install_type, official_url, "ai"


def plan_payload(db: Session, plan: Plan) -> dict:
    """把方案和所属软件转成接口字段。"""
    software = db.query(Software).filter(Software.id == plan.software_id).one()
    return {
        "id": plan.id,
        "software": software_payload(software),
        "version": plan.version,
        "platform": plan.platform,
        "markdown": plan.markdown,
        "script": plan.script,
        "scriptShell": plan.script_shell,
        "installType": plan.install_type,
        "officialUrl": plan.official_url,
        "generatedBy": plan.generated_by,
        "updatedAt": plan.updated_at.isoformat(),
    }


def add_feedback(db: Session, plan_id: int, verdict: str, content: str) -> Feedback:
    """保存用户对方案的有效或无效反馈。"""
    if verdict not in {"valid", "invalid"}:
        raise HTTPException(status_code=400, detail="反馈只能是 valid 或 invalid")
    plan = db.query(Plan).filter(Plan.id == plan_id).one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="没有这个方案")
    row = Feedback(plan_id=plan.id, verdict=verdict, content=content.strip(), status="pending")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _bump(db: Session, software_id: int, version: str, platform: str) -> None:
    """给一次软件、版本、平台选择加一。"""
    row = (
        db.query(SelectionStat)
        .filter(
            SelectionStat.software_id == software_id,
            SelectionStat.version == version,
            SelectionStat.platform == platform,
        )
        .one_or_none()
    )
    if row is None:
        row = SelectionStat(software_id=software_id, version=version, platform=platform, count=0)
        db.add(row)
    row.count += 1
    db.commit()
