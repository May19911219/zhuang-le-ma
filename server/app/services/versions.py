import re
from xml.etree import ElementTree

import httpx
from packaging.version import InvalidVersion, Version

from app.models import Software
from app.services.ai_client import VERSION_SYSTEM, ai_ready, chat_json

USER_AGENT = "zhuang-le-ma/1.0"
VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?$")
PRERELEASE_RE = re.compile(r"(alpha|beta|rc|preview|nightly|snapshot|dev)", re.IGNORECASE)


def clean_version(raw: str) -> str | None:
    """把标签整理成稳定版本号，预发布版本返回空。"""
    text = raw.strip()
    text = re.sub(r"^(refs/tags/)", "", text)
    text = re.sub(r"^(mysql-|go)", "", text, flags=re.IGNORECASE)
    if text.lower().startswith("v") and len(text) > 1 and text[1].isdigit():
        text = text[1:]
    if PRERELEASE_RE.search(text):
        return None
    matched = re.search(r"(\d+\.\d+(?:\.\d+)?)", text)
    if not matched:
        return None
    version = matched.group(1)
    if not VERSION_RE.match(version):
        return None
    return version


def sort_versions(values: list[str], limit: int = 8) -> list[str]:
    """去重后按版本号从新到旧排序。"""
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)

    def sort_key(value: str) -> Version:
        """把版本号转成可比较对象，异常时垫底。"""
        try:
            return Version(value.split("+")[0])
        except InvalidVersion:
            return Version("0")

    unique.sort(key=sort_key, reverse=True)
    return unique[:limit]


def _get_json(url: str):
    """请求 JSON 接口。"""
    with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def _get_text(url: str) -> str:
    """请求文本接口。"""
    with httpx.Client(timeout=20.0, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.text


def _github_versions(repo: str) -> list[str]:
    """从 GitHub Releases 或 tags 读取稳定版本。"""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=headers) as client:
        releases = client.get(f"https://api.github.com/repos/{repo}/releases?per_page=40")
        found: list[str] = []
        if releases.status_code == 200:
            for item in releases.json():
                if item.get("draft") or item.get("prerelease"):
                    continue
                cleaned = clean_version(str(item.get("tag_name") or ""))
                if cleaned:
                    found.append(cleaned)
        if found:
            return sort_versions(found)
        tags = client.get(f"https://api.github.com/repos/{repo}/tags?per_page=40")
        tags.raise_for_status()
        for item in tags.json():
            cleaned = clean_version(str(item.get("name") or ""))
            if cleaned:
                found.append(cleaned)
        return sort_versions(found)


def _nodejs_versions() -> list[str]:
    """从 nodejs.org 读取发行版。"""
    data = _get_json("https://nodejs.org/dist/index.json")
    found = []
    for item in data[:80]:
        cleaned = clean_version(str(item.get("version") or ""))
        if cleaned:
            found.append(cleaned)
    return sort_versions(found)


def _go_versions() -> list[str]:
    """从 go.dev 读取稳定版。"""
    data = _get_json("https://go.dev/dl/?mode=json")
    found = []
    for item in data:
        if item.get("stable") is False:
            continue
        cleaned = clean_version(str(item.get("version") or ""))
        if cleaned:
            found.append(cleaned)
    return sort_versions(found)


def _adoptium_versions() -> list[str]:
    """从 Adoptium 读取 JDK 正式版。"""
    url = (
        "https://api.adoptium.net/v3/info/release_versions"
        "?project=jdk&release_type=ga&vendor=eclipse&page_size=20&sort_order=DESC"
    )
    data = _get_json(url)
    found = []
    for item in data.get("versions") or []:
        cleaned = clean_version(str(item.get("semver") or item.get("openjdk_version") or ""))
        if cleaned:
            found.append(cleaned)
    return sort_versions(found)


def _maven_versions() -> list[str]:
    """从 Maven Central 元数据读取版本。"""
    xml_text = _get_text(
        "https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/maven-metadata.xml"
    )
    root = ElementTree.fromstring(xml_text)
    found = []
    for node in root.findall(".//version"):
        cleaned = clean_version(node.text or "")
        if cleaned:
            found.append(cleaned)
    return sort_versions(found)


def _vscode_versions() -> list[str]:
    """从 VS Code 更新接口读取稳定版。"""
    data = _get_json("https://update.code.visualstudio.com/api/releases/stable")
    found = [cleaned for item in data[:20] if (cleaned := clean_version(str(item)))]
    return sort_versions(found)


def _jetbrains_versions(code: str) -> list[str]:
    """从 JetBrains 产品接口读取正式版。"""
    data = _get_json(
        f"https://data.services.jetbrains.com/products/releases?code={code}&latest=false&type=release"
    )
    found = []
    for item in data.get(code) or []:
        cleaned = clean_version(str(item.get("version") or ""))
        if cleaned:
            found.append(cleaned)
    return sort_versions(found)


def fetch_remote_versions(software: Software) -> list[str]:
    """按软件来源拉取远程版本列表。"""
    source = software.source_type
    if source == "nodejs":
        return _nodejs_versions()
    if source == "go":
        return _go_versions()
    if source == "adoptium":
        return _adoptium_versions()
    if source == "maven":
        return _maven_versions()
    if source == "vscode":
        return _vscode_versions()
    if source == "jetbrains":
        return _jetbrains_versions(software.source_ref or "IIU")
    if source == "github" and software.source_ref:
        return _github_versions(software.source_ref)
    return []


def ai_versions(software: Software) -> list[str]:
    """让 AI 提供稳定版本列表。"""
    if not ai_ready():
        return []
    payload = chat_json(
        VERSION_SYSTEM,
        f"软件名称：{software.name}。只给出还能下载安装的稳定版本。",
        timeout=45.0,
    )
    if not isinstance(payload, list):
        return []
    return sort_versions([cleaned for item in payload if (cleaned := clean_version(str(item)))])
