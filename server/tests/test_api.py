import pytest
from fastapi.testclient import TestClient

from app.config import clear_settings_cache
from app.db import init_db, reset_db
from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """为每个测试准备独立数据库，并跳过 Claude 配置导入。"""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv("ADMIN_PASSWORD", "test-pass")
    monkeypatch.setenv("AI_API_KEY", "")
    monkeypatch.setenv("AI_BASE_URL", "")
    monkeypatch.setenv("ZHUANG_SKIP_SETTINGS_IMPORT", "1")
    clear_settings_cache()
    reset_db()
    init_db()
    with TestClient(app) as test_client:
        yield test_client
    reset_db()
    clear_settings_cache()


def test_health_and_presets(client: TestClient):
    """预置软件会在启动时写入。"""
    assert client.get("/api/health").json()["ok"] is True
    names = [item["name"] for item in client.get("/api/software").json()]
    assert "MySQL" in names
    assert "Node.js" in names
    assert "VS Code" in names
    assert "nvm" in names


def test_parse_mysql_sentence(client: TestClient):
    """一句话能识别出 MySQL，而不会把 JavaScript 认成 Java。"""
    parsed = client.post("/api/parse", json={"query": "我想装 MySQL"}).json()
    assert parsed["slug"] == "mysql"
    assert parsed["matched"] is True
    other = client.post("/api/parse", json={"query": "我想装 JavaScript"}).json()
    assert other["slug"] != "jdk"


def test_versions_use_cache(client: TestClient, monkeypatch):
    """远程版本写入后，第二次直接走缓存。"""
    calls = {"count": 0}

    def fake_fetch(_software):
        """记录远程拉取次数并返回固定版本。"""
        calls["count"] += 1
        return ["22.14.0", "20.18.3"]

    monkeypatch.setattr("app.services.plans.fetch_remote_versions", fake_fetch)
    first = client.get("/api/software/node/versions", params={"platform": "windows"})
    assert first.status_code == 200
    body = first.json()
    assert body["source"] == "remote"
    assert body["versions"][0]["version"] == "22.14.0"
    assert body["versions"][0]["isLatestStable"] is True
    second = client.get("/api/software/node/versions", params={"platform": "windows"})
    assert second.json()["source"] == "cache"
    assert calls["count"] == 1


def test_builtin_versions_when_remote_and_ai_fail(client: TestClient, monkeypatch):
    """远程和 AI 都失败时使用内置版本。"""

    def fake_fetch(_software):
        """模拟远程源不可用。"""
        raise RuntimeError("offline")

    monkeypatch.setattr("app.services.plans.fetch_remote_versions", fake_fetch)
    monkeypatch.setattr("app.services.plans.ai_versions", lambda _software: [])
    response = client.get("/api/software/go/versions", params={"platform": "linux"})
    assert response.status_code == 200
    assert response.json()["source"] == "builtin"
    assert response.json()["versions"][0]["version"] == "1.24.1"


def test_node_plan_fallback_and_stats(client: TestClient):
    """没有 AI 时仍给出带验证命令的脚本，并累计选择次数。"""
    created = client.post(
        "/api/plans",
        json={"slug": "node", "version": "22.14.0", "platform": "windows"},
    )
    assert created.status_code == 200
    body = created.json()
    assert body["generatedBy"] == "fallback"
    assert body["scriptShell"] == "powershell"
    assert "node -v" in body["script"]
    assert "验证" in body["script"]
    assert "一键安装脚本" in body["markdown"]
    again = client.post(
        "/api/plans",
        json={"slug": "node", "version": "22.14.0", "platform": "windows"},
    )
    assert again.json()["id"] == body["id"]
    login = client.post("/api/admin/login", json={"password": "test-pass"})
    token = login.json()["token"]
    stats = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert stats.json()[0]["count"] == 2


def test_vscode_plan_is_official_link(client: TestClient):
    """VS Code 只给官方下载页，不生成脚本。"""
    response = client.post(
        "/api/plans",
        json={"slug": "vscode", "version": "1.97.2", "platform": "macos"},
    )
    body = response.json()
    assert body["installType"] == "official_link"
    assert body["script"] == ""
    assert "https://code.visualstudio.com/Download" in body["markdown"]
    assert "教程" not in body["markdown"]


def test_feedback_and_admin_flow(client: TestClient):
    """用户反馈可以被管理员修改方案并标记已处理。"""
    plan = client.post(
        "/api/plans",
        json={"slug": "git", "version": "2.48.1", "platform": "linux"},
    ).json()
    feedback = client.post(
        f"/api/plans/{plan['id']}/feedback",
        json={"verdict": "invalid", "content": "验证命令没跑过"},
    )
    assert feedback.status_code == 200
    denied = client.get("/api/admin/feedback")
    assert denied.status_code == 401
    token = client.post("/api/admin/login", json={"password": "test-pass"}).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    rows = client.get("/api/admin/feedback", headers=headers).json()
    assert rows[0]["status"] == "pending"
    updated = client.patch(
        f"/api/admin/feedback/{rows[0]['id']}",
        headers=headers,
        json={"status": "resolved"},
    )
    assert updated.json()["status"] == "resolved"
    edited = client.put(
        f"/api/admin/plans/{plan['id']}",
        headers=headers,
        json={"markdown": "# 已改过的安装说明", "script": "echo ok"},
    )
    assert "已改过" in edited.json()["markdown"]
    regenerated = client.post(f"/api/admin/plans/{plan['id']}/regenerate", headers=headers)
    assert regenerated.status_code == 503
    deleted = client.delete(f"/api/admin/plans/{plan['id']}", headers=headers)
    assert deleted.json()["ok"] is True


def test_clean_version_filters_prerelease():
    """预发布标签不会进入版本列表。"""
    from app.services.versions import clean_version, sort_versions

    assert clean_version("v22.14.0") == "22.14.0"
    assert clean_version("go1.23.6") == "1.23.6"
    assert clean_version("v22.0.0-rc.1") is None
    assert sort_versions(["1.0.0", "1.2.0", "1.2.0"]) == ["1.2.0", "1.0.0"]
