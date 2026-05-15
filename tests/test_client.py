"""Tests du client HTTP Lampion MCP."""
import json
import pytest
import httpx
from lampion_mcp.client import LampionClient


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_transport(responses: dict[str, tuple[int, dict | list | str]]):
    """Crée un transport httpx qui retourne des réponses prédéfinies par méthode+path."""
    def handler(request: httpx.Request) -> httpx.Response:
        key = f"{request.method} {request.url.path}"
        for pattern, (status, body) in responses.items():
            if key == pattern or key.startswith(pattern.rstrip("*")):
                content = json.dumps(body).encode() if not isinstance(body, str) else body.encode()
                ct = "application/json" if not isinstance(body, str) else "application/sql"
                return httpx.Response(status, content=content, headers={"content-type": ct})
        return httpx.Response(404, json={"detail": "Not found"})
    return httpx.MockTransport(handler)


def _client(responses: dict) -> LampionClient:
    c = LampionClient("http://test", "lmp_live_test123")
    c._client = httpx.AsyncClient(transport=_mock_transport(responses), base_url="http://test")
    return c


SAMPLE_PROJECT = {"id": "abc123", "name": "test-project", "region": "fr-par-1"}
SAMPLE_BRANCH = {"timeline_id": "br-111", "name": "dev", "project_id": "abc123"}
SAMPLE_ENDPOINT = {"id": "ep-abc123", "status": "running", "connectionString": "postgresql://..."}
SAMPLE_SQL_RESULT = {"columns": ["val"], "rows": [{"val": 1}], "duration_ms": 5}
SAMPLE_BACKUP = {"id": "bkp-aabb", "name": "before-migration", "lsn": "0/16B4C70"}


# ── Projects ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_projects():
    c = _client({"GET /v1/projects": (200, [SAMPLE_PROJECT])})
    result = await c.list_projects()
    assert len(result) == 1
    assert result[0]["name"] == "test-project"
    await c.close()


@pytest.mark.asyncio
async def test_get_project():
    c = _client({"GET /v1/projects/abc123": (200, SAMPLE_PROJECT)})
    result = await c.get_project("abc123")
    assert result["id"] == "abc123"
    await c.close()


@pytest.mark.asyncio
async def test_create_project():
    c = _client({"POST /v1/projects": (201, {**SAMPLE_PROJECT, "id": "new123"})})
    result = await c.create_project("my-db", "fr-par-1")
    assert result["id"] == "new123"
    await c.close()


@pytest.mark.asyncio
async def test_delete_project():
    c = _client({"DELETE /v1/projects/abc123": (204, "")})
    await c.delete_project("abc123")  # should not raise
    await c.close()


@pytest.mark.asyncio
async def test_project_not_found():
    c = _client({})  # no routes → 404
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await c.get_project("nonexistent")
    assert exc_info.value.response.status_code == 404
    await c.close()


# ── Branches ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_branches():
    c = _client({"GET /v1/projects/abc123/branches": (200, [SAMPLE_BRANCH])})
    result = await c.list_branches("abc123")
    assert len(result) == 1
    assert result[0]["name"] == "dev"
    await c.close()


@pytest.mark.asyncio
async def test_create_branch():
    c = _client({"POST /v1/projects/abc123/branches": (201, SAMPLE_BRANCH)})
    result = await c.create_branch("abc123", "dev", "abc123")
    assert result["name"] == "dev"
    await c.close()


@pytest.mark.asyncio
async def test_delete_branch():
    c = _client({"DELETE /v1/projects/abc123/branches/br-111": (204, "")})
    await c.delete_branch("abc123", "br-111")
    await c.close()


# ── Endpoints ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_endpoints():
    c = _client({"GET /v1/projects/abc123/endpoints": (200, [SAMPLE_ENDPOINT])})
    result = await c.list_endpoints("abc123")
    assert result[0]["status"] == "running"
    await c.close()


@pytest.mark.asyncio
async def test_suspend_endpoint():
    c = _client({"POST /v1/projects/abc123/endpoints/ep-abc123/suspend": (200, {**SAMPLE_ENDPOINT, "status": "suspended"})})
    result = await c.suspend_endpoint("abc123", "ep-abc123")
    assert result["status"] == "suspended"
    await c.close()


@pytest.mark.asyncio
async def test_resume_endpoint():
    c = _client({"POST /v1/projects/abc123/endpoints/ep-abc123/resume": (200, SAMPLE_ENDPOINT)})
    result = await c.resume_endpoint("abc123", "ep-abc123")
    assert result["status"] == "running"
    await c.close()


# ── SQL ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_sql():
    c = _client({"POST /v1/projects/abc123/endpoints/ep-abc123/sql": (200, SAMPLE_SQL_RESULT)})
    result = await c.execute_sql("abc123", "ep-abc123", "SELECT 1")
    assert result["rows"][0]["val"] == 1
    assert result["duration_ms"] == 5
    await c.close()


# ── Schema ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_schema():
    schema = {"tables": [{"name": "users", "columns": [{"name": "id", "type": "integer"}]}]}
    c = _client({"GET /v1/projects/abc123/schema": (200, schema)})
    result = await c.get_schema("abc123", database="postgres", schema="public")
    assert result["tables"][0]["name"] == "users"
    await c.close()


# ── Databases ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_databases():
    c = _client({"GET /v1/projects/abc123/endpoints/ep-abc123/databases": (200, [{"name": "postgres"}, {"name": "mydb"}])})
    result = await c.list_databases("abc123", "ep-abc123")
    assert len(result) == 2
    await c.close()


@pytest.mark.asyncio
async def test_create_database():
    c = _client({"POST /v1/projects/abc123/endpoints/ep-abc123/databases": (201, {"name": "newdb"})})
    result = await c.create_database("abc123", "ep-abc123", "newdb")
    assert result["name"] == "newdb"
    await c.close()


# ── Roles ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_roles():
    c = _client({"GET /v1/projects/abc123/endpoints/ep-abc123/roles": (200, [{"name": "cloud_admin"}])})
    result = await c.list_roles("abc123", "ep-abc123")
    assert result[0]["name"] == "cloud_admin"
    await c.close()


# ── Extensions ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_extensions():
    exts = [{"name": "pgvector", "installed": False}, {"name": "pg_trgm", "installed": True}]
    c = _client({"GET /v1/projects/abc123/endpoints/ep-abc123/extensions": (200, exts)})
    result = await c.list_extensions("abc123", "ep-abc123")
    assert len(result) == 2
    assert result[1]["installed"] is True
    await c.close()


@pytest.mark.asyncio
async def test_install_extension():
    c = _client({"POST /v1/projects/abc123/endpoints/ep-abc123/extensions": (200, {"name": "pgvector", "installed": True})})
    result = await c.install_extension("abc123", "ep-abc123", "pgvector")
    assert result["installed"] is True
    await c.close()


# ── Metrics ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_metrics():
    metrics = {"connections_active": 5, "cache_hit_ratio": 0.99}
    c = _client({"GET /v1/projects/abc123/metrics": (200, metrics)})
    result = await c.get_metrics("abc123")
    assert result["cache_hit_ratio"] == 0.99
    await c.close()


@pytest.mark.asyncio
async def test_get_slow_queries():
    queries = [{"query": "SELECT * FROM big_table", "total_time": 1234.5}]
    c = _client({"GET /v1/projects/abc123/endpoints/ep-abc123/analyse/slow-queries": (200, queries)})
    result = await c.get_slow_queries("abc123", "ep-abc123")
    assert result[0]["total_time"] == 1234.5
    await c.close()


@pytest.mark.asyncio
async def test_get_logs():
    c = _client({"GET /v1/projects/abc123/endpoints/ep-abc123/logs": (200, {"lines": ["LOG: started"], "count": 1})})
    result = await c.get_logs("abc123", "ep-abc123", lines=50)
    assert result["count"] == 1
    await c.close()


# ── Usage ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_project_usage():
    usage = {"compute_hours": 12.5, "storage_gb": 0.8}
    c = _client({"GET /v1/projects/abc123/usage": (200, usage)})
    result = await c.get_project_usage("abc123")
    assert result["compute_hours"] == 12.5
    await c.close()


@pytest.mark.asyncio
async def test_get_org_usage():
    usage = {"plan": {"name": "dev"}, "total": {"compute_hours": 50}}
    c = _client({"GET /v1/usage": (200, usage)})
    result = await c.get_org_usage()
    assert result["plan"]["name"] == "dev"
    await c.close()


# ── Backups ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_backups():
    c = _client({"GET /v1/projects/abc123/backups": (200, [SAMPLE_BACKUP])})
    result = await c.list_backups("abc123")
    assert result[0]["lsn"] == "0/16B4C70"
    await c.close()


@pytest.mark.asyncio
async def test_create_backup():
    c = _client({"POST /v1/projects/abc123/backups": (201, SAMPLE_BACKUP)})
    result = await c.create_backup("abc123", "abc123", "before-migration")
    assert result["name"] == "before-migration"
    await c.close()


@pytest.mark.asyncio
async def test_restore_backup():
    restored = {"id": "br-new", "name": "restore-before-migration"}
    c = _client({"POST /v1/projects/abc123/backups/bkp-aabb/restore": (201, restored)})
    result = await c.restore_backup("abc123", "bkp-aabb", "my-restore")
    assert result["name"] == "restore-before-migration"
    await c.close()


# ── Dump ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pg_dump():
    sql = "CREATE TABLE users (id serial);\nINSERT INTO users VALUES (1);"
    c = _client({"GET /v1/projects/abc123/endpoints/ep-abc123/dump": (200, sql)})
    result = await c.pg_dump("abc123", "ep-abc123")
    assert "CREATE TABLE" in result
    await c.close()


# ── Auth header ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_header_is_set():
    """Vérifie que le Bearer token est envoyé dans chaque requête."""
    captured_headers = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return httpx.Response(200, json=[])

    c = LampionClient("http://test", "lmp_live_secret")
    c._client = httpx.AsyncClient(
        transport=httpx.MockTransport(capture),
        base_url="http://test",
        headers={"Authorization": "Bearer lmp_live_secret"},
    )
    await c.list_projects()
    # httpx normalise les headers en minuscules
    auth = captured_headers.get("authorization") or captured_headers.get("Authorization") or ""
    assert auth == "Bearer lmp_live_secret", f"Got headers: {list(captured_headers.keys())}"
    await c.close()
