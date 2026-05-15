# Lampion MCP Server

Serveur MCP (Model Context Protocol) pour Lampion — permet aux agents IA (Claude, Cursor, Windsurf, etc.) de gerer des bases de donnees PostgreSQL managees.

## Installation

```bash
cd console/mcp
pip install -e .
```

## Usage

```bash
# Via CLI
lampion-mcp --token lmp_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Via env vars
export LAMPION_TOKEN=lmp_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export LAMPION_API_URL=https://api.lampion.cloud  # optionnel
lampion-mcp
```

## Configuration Claude Desktop

Fichier `~/.claude/claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "lampion": {
      "command": "lampion-mcp",
      "env": {
        "LAMPION_TOKEN": "lmp_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

## Configuration Cursor / VS Code

Fichier `.cursor/mcp.json` ou `.vscode/mcp.json` :

```json
{
  "servers": {
    "lampion": {
      "command": "lampion-mcp",
      "env": {
        "LAMPION_TOKEN": "lmp_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
      }
    }
  }
}
```

## Tools disponibles (47)

### Projets
- `list_projects` — Lister les projets
- `get_project` — Details d'un projet
- `create_project` — Creer un projet PostgreSQL (choix de region : Scaleway Paris ou OVH Gravelines)
- `delete_project` — Supprimer un projet (admin requis)

### Branches
- `list_branches` — Lister les branches
- `create_branch` — Creer une branche copy-on-write
- `delete_branch` — Supprimer une branche
- `reset_branch` — Reset une branche a l'etat du parent (comme git reset --hard)
- `merge_branch` — Merger les changements de schema vers la branche principale (dry_run possible)
- `promote_branch` — Promouvoir une branche en nouvelle branche principale (destructif)

### Computes
- `list_endpoints` — Lister les endpoints avec connection strings
- `get_endpoint` — Details d'un endpoint
- `suspend_endpoint` — Suspendre (scale to zero)
- `resume_endpoint` — Relancer un compute

### SQL
- `execute_sql` — Executer une requete SQL
- `get_schema` — Introspecter le schema (databases -> schemas -> tables -> colonnes)

### Databases & Roles
- `list_databases` / `create_database` / `drop_database`
- `list_roles` / `create_role` / `drop_role`

### Extensions
- `list_extensions` / `install_extension` / `uninstall_extension`

### Observabilite
- `get_metrics` — Metriques temps reel (CPU, RAM, connections, cache)
- `get_slow_queries` — Top queries lentes (pg_stat_statements)
- `get_logs` — Tail des logs PostgreSQL
- `get_project_usage` / `get_org_usage` — Usage et couts

### Backups
- `list_backups` / `create_backup` / `restore_backup`

### Dump
- `pg_dump` — Export SQL d'une database

### Anonymisation (PII Masking)
- `get_anonymization` — Statut et regles de masquage d'une branche
- `enable_anonymization` — Activer le masquage dynamique (cree un role lampion_analyst)
- `disable_anonymization` — Desactiver le masquage
- `list_masking_functions` — Fonctions disponibles (fake_email, hash, partial, etc.)
- `list_masking_rules` — Regles actives (schema.table.column -> fonction)
- `add_masking_rule` — Ajouter une regle de masquage
- `delete_masking_rule` — Supprimer une regle

### Securite
- `get_allowlist` — IP allowlist d'un endpoint
- `set_allowlist` — Configurer l'IP allowlist
- `list_permissions` — Permissions table-level par role
- `grant_permission` — GRANT un privilege (SELECT, INSERT, UPDATE, DELETE, ALL)
- `revoke_permission` — REVOKE un privilege

### Compliance
- `get_residency` — Ou sont les donnees physiquement (datacenter, provider, chiffrement, certifications)

## Resources MCP (5)

- `lampion://projects` — Liste des projets
- `lampion://projects/{id}` — Details d'un projet
- `lampion://projects/{id}/endpoints` — Endpoints avec connection strings
- `lampion://projects/{id}/branches` — Branches d'un projet
- `lampion://usage` — Usage organisation et estimation des couts

## Exemples d'utilisation par un agent

> "Cree un projet PostgreSQL pour mon app de blog"

L'agent appellera `create_project(name="blog-db")` puis `list_endpoints()` pour obtenir la connection string.

> "Montre-moi le schema de ma base de donnees"

L'agent appellera `get_schema(project_id="xxx", database="postgres", schema="public")`.

> "Quelle est ma requete la plus lente ?"

L'agent appellera `get_slow_queries(project_id="xxx", endpoint_id="ep-xxx")`.

> "Anonymise les emails de la table users"

L'agent appellera `enable_anonymization()` puis `add_masking_rule(table_name="users", column_name="email", masking_function="anon.fake_email()")`.

> "Merge les changements de schema de ma branche dev vers main"

L'agent appellera `merge_branch(project_id="xxx", branch_id="dev-id", dry_run=True)` pour previsualiser, puis `merge_branch(..., dry_run=False)` pour executer.

## Generation d'API Key

1. Se connecter sur https://app.lampion.cloud
2. Aller dans Settings -> API Keys
3. Creer une cle (prefixe `lmp_live_`)
4. Copier la cle et la configurer dans le MCP server
