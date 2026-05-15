"""Lampion MCP Server — exposes Lampion API as MCP tools and resources."""
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP, Context

from lampion_mcp.client import LampionClient

# Module-level config set by cli.py before mcp.run()
_API_URL: str = ""
_TOKEN: str = ""


def configure(api_url: str, token: str):
    global _API_URL, _TOKEN
    _API_URL = api_url
    _TOKEN = token


@dataclass
class AppContext:
    client: LampionClient


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    client = LampionClient(api_url=_API_URL, token=_TOKEN)
    try:
        yield AppContext(client=client)
    finally:
        await client.close()


mcp = FastMCP("Lampion", lifespan=app_lifespan)


def _client(ctx: Context) -> LampionClient:
    return ctx.request_context.lifespan_context.client


def _json(data) -> str:
    return json.dumps(data, indent=2, default=str)


MAX_ROWS = 100


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS — Actions with side effects
# ═══════════════════════════════════════════════════════════════════════════════

# ── Projects ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_projects(ctx: Context) -> str:
    """List all projects in the organization."""
    return _json(await _client(ctx).list_projects())


@mcp.tool()
async def get_project(ctx: Context, project_id: str) -> str:
    """Get details of a project including region and creation date."""
    return _json(await _client(ctx).get_project(project_id))


@mcp.tool()
async def create_project(ctx: Context, name: str, region: str = "fr-par-1") -> str:
    """Create a new managed PostgreSQL project. Returns the project ID and connection details.
    Available regions: fr-par-1 (Paris). More coming soon."""
    return _json(await _client(ctx).create_project(name, region))


@mcp.tool()
async def delete_project(ctx: Context, project_id: str) -> str:
    """Permanently delete a project and all its branches, databases, and data. IRREVERSIBLE.
    Note: requires admin role. API keys have developer role — this may return 403."""
    await _client(ctx).delete_project(project_id)
    return "Project deleted."


# ── Branches ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_branches(ctx: Context, project_id: str) -> str:
    """List all branches of a project with their compute status."""
    return _json(await _client(ctx).list_branches(project_id))


@mcp.tool()
async def create_branch(ctx: Context, project_id: str, name: str, parent_id: str) -> str:
    """Create a copy-on-write branch from a parent. parent_id is the timeline_id of the parent
    (use the project_id for the main branch)."""
    return _json(await _client(ctx).create_branch(project_id, name, parent_id))


@mcp.tool()
async def delete_branch(ctx: Context, project_id: str, branch_id: str) -> str:
    """Delete a branch and stop its compute."""
    await _client(ctx).delete_branch(project_id, branch_id)
    return "Branch deleted."


@mcp.tool()
async def reset_branch(ctx: Context, project_id: str, branch_id: str) -> str:
    """Reset a branch to its parent's current state (like git reset --hard).
    Destroys the current data and recreates the branch as a fresh fork."""
    return _json(await _client(ctx).reset_branch(project_id, branch_id))


@mcp.tool()
async def merge_branch(ctx: Context, project_id: str, branch_id: str,
                       database: str = "postgres", schema_name: str = "public",
                       dry_run: bool = False) -> str:
    """Merge schema changes from a branch into the primary branch.
    Only DDL (schema) is merged, not data. Set dry_run=True to preview the SQL without executing."""
    return _json(await _client(ctx).merge_branch(project_id, branch_id, database, schema_name, dry_run))


@mcp.tool()
async def promote_branch(ctx: Context, project_id: str, branch_id: str) -> str:
    """Promote a branch to become the new primary. Replaces main's data with this branch's data.
    DESTRUCTIVE: all data on main is lost. The promoted branch becomes a sibling."""
    return _json(await _client(ctx).promote_branch(project_id, branch_id))


# ── Endpoints / Computes ─────────────────────────────────────────────────────

@mcp.tool()
async def list_endpoints(ctx: Context, project_id: str) -> str:
    """List all endpoints (computes) of a project with connection strings, status, and passwords."""
    return _json(await _client(ctx).list_endpoints(project_id))


@mcp.tool()
async def get_endpoint(ctx: Context, project_id: str, endpoint_id: str) -> str:
    """Get details of a single endpoint including connection string and compute status."""
    return _json(await _client(ctx).get_endpoint(project_id, endpoint_id))


@mcp.tool()
async def suspend_endpoint(ctx: Context, project_id: str, endpoint_id: str) -> str:
    """Suspend a compute (scale to zero). The database data is preserved."""
    return _json(await _client(ctx).suspend_endpoint(project_id, endpoint_id))


@mcp.tool()
async def resume_endpoint(ctx: Context, project_id: str, endpoint_id: str) -> str:
    """Resume a suspended compute. Takes a few seconds to start."""
    return _json(await _client(ctx).resume_endpoint(project_id, endpoint_id))


# ── SQL ───────────────────────────────────────────────────────────────────────

@mcp.tool()
async def execute_sql(ctx: Context, project_id: str, endpoint_id: str, query: str) -> str:
    """Execute a SQL query on an endpoint. Returns columns, rows, and duration.
    Destructive DDL (DROP, TRUNCATE) is blocked on protected branches.
    Results are limited to 100 rows."""
    result = await _client(ctx).execute_sql(project_id, endpoint_id, query)
    if isinstance(result.get("rows"), list) and len(result["rows"]) > MAX_ROWS:
        total = len(result["rows"])
        result["rows"] = result["rows"][:MAX_ROWS]
        result["truncated"] = True
        result["total_rows"] = total
        result["note"] = f"Showing first {MAX_ROWS} of {total} rows"
    return _json(result)


# ── Schema ───────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_schema(ctx: Context, project_id: str, database: str = "",
                     schema: str = "", endpoint_id: str = "") -> str:
    """Introspect database schema progressively:
    - No params: list databases
    - database only: list schemas
    - database + schema: list tables with columns and types"""
    return _json(await _client(ctx).get_schema(
        project_id,
        database=database or None,
        schema=schema or None,
        endpoint_id=endpoint_id or None,
    ))


# ── Databases ────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_databases(ctx: Context, project_id: str, endpoint_id: str) -> str:
    """List PostgreSQL databases on an endpoint."""
    return _json(await _client(ctx).list_databases(project_id, endpoint_id))


@mcp.tool()
async def create_database(ctx: Context, project_id: str, endpoint_id: str, name: str) -> str:
    """Create a new PostgreSQL database."""
    return _json(await _client(ctx).create_database(project_id, endpoint_id, name))


@mcp.tool()
async def drop_database(ctx: Context, project_id: str, endpoint_id: str, name: str) -> str:
    """Drop a PostgreSQL database. Cannot drop system databases."""
    await _client(ctx).drop_database(project_id, endpoint_id, name)
    return f"Database '{name}' dropped."


# ── Roles ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_roles(ctx: Context, project_id: str, endpoint_id: str) -> str:
    """List PostgreSQL roles on an endpoint."""
    return _json(await _client(ctx).list_roles(project_id, endpoint_id))


@mcp.tool()
async def create_role(ctx: Context, project_id: str, endpoint_id: str, name: str,
                      password: str = "", can_login: bool = True) -> str:
    """Create a PostgreSQL role. Leave password empty for auto-generated."""
    return _json(await _client(ctx).create_role(project_id, endpoint_id, name, password or None, can_login))


@mcp.tool()
async def drop_role(ctx: Context, project_id: str, endpoint_id: str, name: str) -> str:
    """Drop a PostgreSQL role. Cannot drop cloud_admin."""
    await _client(ctx).drop_role(project_id, endpoint_id, name)
    return f"Role '{name}' dropped."


# ── Extensions ───────────────────────────────────────────────────────────────

@mcp.tool()
async def list_extensions(ctx: Context, project_id: str, endpoint_id: str) -> str:
    """List available PostgreSQL extensions with their install status."""
    return _json(await _client(ctx).list_extensions(project_id, endpoint_id))


@mcp.tool()
async def install_extension(ctx: Context, project_id: str, endpoint_id: str, name: str) -> str:
    """Install a PostgreSQL extension (e.g. pgvector, postgis, pg_trgm)."""
    return _json(await _client(ctx).install_extension(project_id, endpoint_id, name))


@mcp.tool()
async def uninstall_extension(ctx: Context, project_id: str, endpoint_id: str, name: str) -> str:
    """Uninstall a PostgreSQL extension."""
    await _client(ctx).uninstall_extension(project_id, endpoint_id, name)
    return f"Extension '{name}' uninstalled."


# ── Metrics & Observability ──────────────────────────────────────────────────

@mcp.tool()
async def get_metrics(ctx: Context, project_id: str, endpoint_id: str = "") -> str:
    """Get live metrics: connections, cache hit ratio, storage, CPU, memory, I/O."""
    return _json(await _client(ctx).get_metrics(project_id, endpoint_id or None))


@mcp.tool()
async def get_slow_queries(ctx: Context, project_id: str, endpoint_id: str,
                           order_by: str = "total_time", limit: int = 20) -> str:
    """Get top slow queries from pg_stat_statements. order_by: total_time, mean_time, calls."""
    return _json(await _client(ctx).get_slow_queries(project_id, endpoint_id, order_by, limit))


@mcp.tool()
async def get_logs(ctx: Context, project_id: str, endpoint_id: str, lines: int = 100) -> str:
    """Tail PostgreSQL server logs."""
    return _json(await _client(ctx).get_logs(project_id, endpoint_id, lines))


@mcp.tool()
async def get_project_usage(ctx: Context, project_id: str, period: str = "") -> str:
    """Get monthly usage for a project: compute hours, storage GB, transfer GB."""
    return _json(await _client(ctx).get_project_usage(project_id, period or None))


@mcp.tool()
async def get_org_usage(ctx: Context, period: str = "") -> str:
    """Get organization-wide usage with plan info and cost estimation."""
    return _json(await _client(ctx).get_org_usage(period or None))


# ── Backups ──────────────────────────────────────────────────────────────────

@mcp.tool()
async def list_backups(ctx: Context, project_id: str) -> str:
    """List backup snapshots (LSN) available for point-in-time restore."""
    return _json(await _client(ctx).list_backups(project_id))


@mcp.tool()
async def create_backup(ctx: Context, project_id: str, branch_id: str, name: str) -> str:
    """Create a backup snapshot of a branch. Captures the current LSN for later restore."""
    return _json(await _client(ctx).create_backup(project_id, branch_id, name))


@mcp.tool()
async def restore_backup(ctx: Context, project_id: str, backup_id: str, name: str = "") -> str:
    """Restore a backup as a new branch (point-in-time recovery)."""
    return _json(await _client(ctx).restore_backup(project_id, backup_id, name or None))


# ── Dump ─────────────────────────────────────────────────────────────────────

@mcp.tool()
async def pg_dump(ctx: Context, project_id: str, endpoint_id: str,
                  database: str = "postgres", table: str = "") -> str:
    """Download a pg_dump SQL dump of a database or a single table."""
    result = await _client(ctx).pg_dump(project_id, endpoint_id, database, table or None)
    if len(result) > 50000:
        return result[:50000] + f"\n\n-- TRUNCATED (showing first 50KB of {len(result)} bytes)"
    return result


# ── Anonymization (PII Masking) ─────────────────────────────────────────────

@mcp.tool()
async def get_anonymization(ctx: Context, project_id: str, branch_id: str) -> str:
    """Get anonymization status and masking rules for a branch."""
    return _json(await _client(ctx).get_anonymization(project_id, branch_id))


@mcp.tool()
async def enable_anonymization(ctx: Context, project_id: str, branch_id: str) -> str:
    """Enable dynamic PII masking on a branch. Creates a lampion_analyst role with read-only
    masked access. All non-admin roles see anonymized data. cloud_admin sees real data."""
    return _json(await _client(ctx).enable_anonymization(project_id, branch_id))


@mcp.tool()
async def disable_anonymization(ctx: Context, project_id: str, branch_id: str) -> str:
    """Disable anonymization on a branch. Removes all masks and drops the analyst role."""
    return _json(await _client(ctx).disable_anonymization(project_id, branch_id))


@mcp.tool()
async def list_masking_functions(ctx: Context, project_id: str, branch_id: str) -> str:
    """List available masking functions (e.g. anon.fake_email, anon.hash, anon.partial)."""
    return _json(await _client(ctx).list_masking_functions(project_id, branch_id))


@mcp.tool()
async def list_masking_rules(ctx: Context, project_id: str, branch_id: str) -> str:
    """List active masking rules for a branch (schema.table.column -> function)."""
    return _json(await _client(ctx).list_masking_rules(project_id, branch_id))


@mcp.tool()
async def add_masking_rule(ctx: Context, project_id: str, branch_id: str,
                           table_name: str, column_name: str, masking_function: str,
                           schema_name: str = "public") -> str:
    """Add a masking rule on a column. Use list_masking_functions to see available functions.
    Example: table_name='users', column_name='email', masking_function='anon.fake_email()'"""
    return _json(await _client(ctx).add_masking_rule(
        project_id, branch_id, table_name, column_name, masking_function, schema_name))


@mcp.tool()
async def delete_masking_rule(ctx: Context, project_id: str, branch_id: str, rule_id: str) -> str:
    """Delete a masking rule."""
    await _client(ctx).delete_masking_rule(project_id, branch_id, rule_id)
    return "Masking rule deleted."


# ── IP Allowlist ────────────────────────────────────────────────────────────

@mcp.tool()
async def get_allowlist(ctx: Context, project_id: str, endpoint_id: str) -> str:
    """Get the IP allowlist for an endpoint."""
    return _json(await _client(ctx).get_allowlist(project_id, endpoint_id))


@mcp.tool()
async def set_allowlist(ctx: Context, project_id: str, endpoint_id: str,
                        allowlist: list[str], allow_console_access: bool = True) -> str:
    """Set the IP allowlist for an endpoint. Pass an empty list to disable.
    allow_console_access: whether the web console can still query when allowlist is active."""
    return _json(await _client(ctx).set_allowlist(project_id, endpoint_id, allowlist, allow_console_access))


# ── Data Residency ──────────────────────────────────────────────────────────

@mcp.tool()
async def get_residency(ctx: Context, project_id: str) -> str:
    """Get data residency information: where project data physically resides,
    encryption status, certifications, and compliance details."""
    return _json(await _client(ctx).get_residency(project_id))


# ── Permissions (GRANT/REVOKE) ──────────────────────────────────────────────

@mcp.tool()
async def list_permissions(ctx: Context, project_id: str, endpoint_id: str,
                           database: str = "postgres") -> str:
    """List table-level permissions for all roles."""
    return _json(await _client(ctx).list_permissions(project_id, endpoint_id, database))


@mcp.tool()
async def grant_permission(ctx: Context, project_id: str, endpoint_id: str,
                           role_name: str, table_name: str, privilege: str,
                           database: str = "postgres", schema_name: str = "public") -> str:
    """Grant a privilege on a table to a role. privilege: SELECT, INSERT, UPDATE, DELETE, ALL."""
    return _json(await _client(ctx).grant_permission(
        project_id, endpoint_id, role_name, table_name, privilege, database, schema_name))


@mcp.tool()
async def revoke_permission(ctx: Context, project_id: str, endpoint_id: str,
                            role_name: str, table_name: str, privilege: str,
                            database: str = "postgres", schema_name: str = "public") -> str:
    """Revoke a privilege on a table from a role."""
    return _json(await _client(ctx).revoke_permission(
        project_id, endpoint_id, role_name, table_name, privilege, database, schema_name))


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES — Read-only data accessible by URI
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("lampion://projects")
async def projects_resource(ctx: Context) -> str:
    """List all projects with their IDs, names, and regions."""
    return _json(await _client(ctx).list_projects())


@mcp.resource("lampion://projects/{project_id}")
async def project_resource(ctx: Context, project_id: str) -> str:
    """Get project details."""
    return _json(await _client(ctx).get_project(project_id))


@mcp.resource("lampion://projects/{project_id}/endpoints")
async def endpoints_resource(ctx: Context, project_id: str) -> str:
    """List endpoints with connection strings and status."""
    return _json(await _client(ctx).list_endpoints(project_id))


@mcp.resource("lampion://projects/{project_id}/branches")
async def branches_resource(ctx: Context, project_id: str) -> str:
    """List branches of a project."""
    return _json(await _client(ctx).list_branches(project_id))


@mcp.resource("lampion://usage")
async def usage_resource(ctx: Context) -> str:
    """Organization-wide usage, plan, and cost estimation."""
    return _json(await _client(ctx).get_org_usage())
