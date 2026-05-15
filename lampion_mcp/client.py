"""HTTP client for the Lampion REST API."""
import httpx


class LampionClient:
    def __init__(self, api_url: str, token: str):
        self._client = httpx.AsyncClient(
            base_url=api_url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            timeout=60.0,
        )

    async def close(self):
        await self._client.aclose()

    async def _get(self, path: str, **params) -> dict | list:
        r = await self._client.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, body: dict | None = None) -> dict:
        r = await self._client.post(path, json=body or {})
        r.raise_for_status()
        return r.json() if r.status_code != 204 else {}

    async def _patch(self, path: str, body: dict) -> dict:
        r = await self._client.patch(path, json=body)
        r.raise_for_status()
        return r.json()

    async def _delete(self, path: str) -> None:
        r = await self._client.delete(path)
        r.raise_for_status()

    async def _get_text(self, path: str, **params) -> str:
        r = await self._client.get(path, params={k: v for k, v in params.items() if v is not None})
        r.raise_for_status()
        return r.text

    # ── Projects ─────────────────────────────────────────────────────────────

    async def list_projects(self) -> list[dict]:
        return await self._get("/v1/projects")

    async def get_project(self, project_id: str) -> dict:
        return await self._get(f"/v1/projects/{project_id}")

    async def create_project(self, name: str, region: str = "fr-par-1") -> dict:
        return await self._post("/v1/projects", {"name": name, "region": region})

    async def delete_project(self, project_id: str) -> None:
        await self._delete(f"/v1/projects/{project_id}")

    # ── Branches ─────────────────────────────────────────────────────────────

    async def list_branches(self, project_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/branches")

    async def create_branch(self, project_id: str, name: str, parent_id: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/branches", {
            "name": name, "parent_id": parent_id,
        })

    async def delete_branch(self, project_id: str, branch_id: str) -> None:
        await self._delete(f"/v1/projects/{project_id}/branches/{branch_id}")

    async def reset_branch(self, project_id: str, branch_id: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/branches/{branch_id}/reset")

    async def merge_branch(self, project_id: str, branch_id: str,
                           database: str = "postgres", schema_name: str = "public",
                           dry_run: bool = False) -> dict:
        return await self._post(f"/v1/projects/{project_id}/branches/{branch_id}/merge", {
            "database": database, "schema_name": schema_name, "dry_run": dry_run,
        })

    async def promote_branch(self, project_id: str, branch_id: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/branches/{branch_id}/promote")

    # ── Endpoints / Computes ─────────────────────────────────────────────────

    async def list_endpoints(self, project_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/endpoints")

    async def get_endpoint(self, project_id: str, endpoint_id: str) -> dict:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}")

    async def suspend_endpoint(self, project_id: str, endpoint_id: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/suspend")

    async def resume_endpoint(self, project_id: str, endpoint_id: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/resume")

    # ── SQL ───────────────────────────────────────────────────────────────────

    async def execute_sql(self, project_id: str, endpoint_id: str, query: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/sql", {"query": query})

    # ── Schema ───────────────────────────────────────────────────────────────

    async def get_schema(self, project_id: str, database: str | None = None,
                         schema: str | None = None, endpoint_id: str | None = None) -> dict:
        return await self._get(f"/v1/projects/{project_id}/schema",
                               database=database, schema=schema, endpoint_id=endpoint_id)

    # ── Databases ────────────────────────────────────────────────────────────

    async def list_databases(self, project_id: str, endpoint_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/databases")

    async def create_database(self, project_id: str, endpoint_id: str, name: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/databases", {"name": name})

    async def drop_database(self, project_id: str, endpoint_id: str, name: str) -> None:
        await self._delete(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/databases/{name}")

    # ── Roles ────────────────────────────────────────────────────────────────

    async def list_roles(self, project_id: str, endpoint_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/roles")

    async def create_role(self, project_id: str, endpoint_id: str, name: str,
                          password: str | None = None, can_login: bool = True) -> dict:
        body: dict = {"name": name, "can_login": can_login}
        if password:
            body["password"] = password
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/roles", body)

    async def drop_role(self, project_id: str, endpoint_id: str, name: str) -> None:
        await self._delete(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/roles/{name}")

    # ── Extensions ───────────────────────────────────────────────────────────

    async def list_extensions(self, project_id: str, endpoint_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/extensions")

    async def install_extension(self, project_id: str, endpoint_id: str, name: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/extensions", {"name": name})

    async def uninstall_extension(self, project_id: str, endpoint_id: str, name: str) -> None:
        await self._delete(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/extensions/{name}")

    # ── Metrics & Logs ───────────────────────────────────────────────────────

    async def get_metrics(self, project_id: str, endpoint_id: str | None = None) -> dict:
        return await self._get(f"/v1/projects/{project_id}/metrics", endpoint_id=endpoint_id)

    async def get_slow_queries(self, project_id: str, endpoint_id: str,
                               order_by: str = "total_time", limit: int = 20) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/analyse/slow-queries",
                               order_by=order_by, limit=limit)

    async def get_logs(self, project_id: str, endpoint_id: str, lines: int = 200) -> dict:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/logs", lines=lines)

    async def get_project_usage(self, project_id: str, period: str | None = None) -> dict:
        return await self._get(f"/v1/projects/{project_id}/usage", period=period)

    async def get_org_usage(self, period: str | None = None) -> dict:
        return await self._get("/v1/usage", period=period)

    # ── Backups ──────────────────────────────────────────────────────────────

    async def list_backups(self, project_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/backups")

    async def create_backup(self, project_id: str, branch_id: str, name: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/backups", {"branch_id": branch_id, "name": name})

    async def restore_backup(self, project_id: str, backup_id: str, name: str | None = None) -> dict:
        return await self._post(f"/v1/projects/{project_id}/backups/{backup_id}/restore", {"name": name} if name else {})

    # ── Dump ─────────────────────────────────────────────────────────────────

    async def pg_dump(self, project_id: str, endpoint_id: str,
                      database: str = "postgres", table: str | None = None) -> str:
        return await self._get_text(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/dump",
                                    database=database, table=table)

    # ── Anonymization ───────────────────────────────────────────────────────

    async def get_anonymization(self, project_id: str, branch_id: str) -> dict:
        return await self._get(f"/v1/projects/{project_id}/branches/{branch_id}/anonymization")

    async def enable_anonymization(self, project_id: str, branch_id: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/branches/{branch_id}/anonymization/enable")

    async def disable_anonymization(self, project_id: str, branch_id: str) -> dict:
        return await self._post(f"/v1/projects/{project_id}/branches/{branch_id}/anonymization/disable")

    async def list_masking_functions(self, project_id: str, branch_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/branches/{branch_id}/anonymization/functions")

    async def list_masking_rules(self, project_id: str, branch_id: str) -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/branches/{branch_id}/anonymization/rules")

    async def add_masking_rule(self, project_id: str, branch_id: str,
                               table_name: str, column_name: str, masking_function: str,
                               schema_name: str = "public") -> dict:
        return await self._post(f"/v1/projects/{project_id}/branches/{branch_id}/anonymization/rules", {
            "schema_name": schema_name, "table_name": table_name,
            "column_name": column_name, "masking_function": masking_function,
        })

    async def delete_masking_rule(self, project_id: str, branch_id: str, rule_id: str) -> None:
        await self._delete(f"/v1/projects/{project_id}/branches/{branch_id}/anonymization/rules/{rule_id}")

    # ── IP Allowlist ────────────────────────────────────────────────────────

    async def get_allowlist(self, project_id: str, endpoint_id: str) -> dict:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/allowlist")

    async def set_allowlist(self, project_id: str, endpoint_id: str,
                            allowlist: list[str], allow_console_access: bool = True) -> dict:
        return await self._patch(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/allowlist", {
            "allowlist": allowlist, "allow_console_access": allow_console_access,
        })

    # ── Data Residency ──────────────────────────────────────────────────────

    async def get_residency(self, project_id: str) -> dict:
        return await self._get(f"/v1/projects/{project_id}/residency")

    # ── Permissions ─────────────────────────────────────────────────────────

    async def list_permissions(self, project_id: str, endpoint_id: str,
                               database: str = "postgres") -> list[dict]:
        return await self._get(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/permissions",
                               database=database)

    async def grant_permission(self, project_id: str, endpoint_id: str,
                               role_name: str, table_name: str, privilege: str,
                               database: str = "postgres", schema_name: str = "public") -> dict:
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/permissions/grant", {
            "role_name": role_name, "table_name": table_name, "privilege": privilege,
            "database": database, "schema_name": schema_name,
        })

    async def revoke_permission(self, project_id: str, endpoint_id: str,
                                role_name: str, table_name: str, privilege: str,
                                database: str = "postgres", schema_name: str = "public") -> dict:
        return await self._post(f"/v1/projects/{project_id}/endpoints/{endpoint_id}/permissions/revoke", {
            "role_name": role_name, "table_name": table_name, "privilege": privilege,
            "database": database, "schema_name": schema_name,
        })
