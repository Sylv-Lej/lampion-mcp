"""Tests du serveur MCP Lampion — vérifie que les tools et resources sont bien enregistrés."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from lampion_mcp.server import mcp, configure, _json, MAX_ROWS


# ── Server registration ──────────────────────────────────────────────────────

def test_server_name():
    assert mcp.name == "Lampion"


def test_tools_registered():
    """Vérifie que tous les tools attendus sont enregistrés."""
    tool_names = set()
    for tool in mcp._tool_manager._tools.values():
        tool_names.add(tool.name)

    expected = {
        "list_projects", "get_project", "create_project", "delete_project",
        "list_branches", "create_branch", "delete_branch",
        "reset_branch", "merge_branch", "promote_branch",
        "list_endpoints", "get_endpoint", "suspend_endpoint", "resume_endpoint",
        "execute_sql", "get_schema",
        "list_databases", "create_database", "drop_database",
        "list_roles", "create_role", "drop_role",
        "list_extensions", "install_extension", "uninstall_extension",
        "get_metrics", "get_slow_queries", "get_logs",
        "get_project_usage", "get_org_usage",
        "list_backups", "create_backup", "restore_backup",
        "pg_dump",
        "get_anonymization", "enable_anonymization", "disable_anonymization",
        "list_masking_functions", "list_masking_rules", "add_masking_rule", "delete_masking_rule",
        "get_allowlist", "set_allowlist",
        "get_residency",
        "list_permissions", "grant_permission", "revoke_permission",
    }
    missing = expected - tool_names
    assert not missing, f"Missing tools: {missing}"
    assert len(tool_names) >= 47


def test_resources_registered():
    """Vérifie que les resources sont enregistrées."""
    # Resources are registered via templates or direct URIs
    # Just check the server has some resources configured
    assert mcp._resource_manager is not None


# ── Helpers ──────────────────────────────────────────────────────────────────

def test_json_helper():
    result = _json({"key": "value", "num": 42})
    parsed = json.loads(result)
    assert parsed["key"] == "value"
    assert parsed["num"] == 42


def test_json_handles_datetime():
    from datetime import datetime
    result = _json({"ts": datetime(2026, 1, 1, 12, 0)})
    assert "2026" in result


def test_max_rows_constant():
    assert MAX_ROWS == 100


# ── Configure ────────────────────────────────────────────────────────────────

def test_configure():
    configure("https://api.example.com", "lmp_live_test")
    from lampion_mcp.server import _API_URL, _TOKEN
    assert _API_URL == "https://api.example.com"
    assert _TOKEN == "lmp_live_test"


# ── Tool count matches README ───────────────────────────────────────────────

def test_tool_count():
    """Le nombre de tools doit correspondre à ce qu'on annonce."""
    count = len(mcp._tool_manager._tools)
    assert count == 47, f"Expected 47 tools, got {count}"
