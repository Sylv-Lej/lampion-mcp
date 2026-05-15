"""CLI entry point for the Lampion MCP server."""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Lampion MCP Server — manage PostgreSQL projects from AI agents",
        epilog="Environment variables: LAMPION_API_URL, LAMPION_TOKEN",
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("LAMPION_API_URL", "https://api.lampion.cloud"),
        help="Lampion API base URL (default: LAMPION_API_URL or https://api.lampion.cloud)",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("LAMPION_TOKEN"),
        help="Lampion API key (lmp_live_xxx). Required. Can also be set via LAMPION_TOKEN env var.",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="MCP transport (default: stdio)",
    )
    args = parser.parse_args()

    if not args.token:
        print("Error: --token or LAMPION_TOKEN environment variable is required.", file=sys.stderr)
        print("Generate an API key at https://app.lampion.cloud/settings", file=sys.stderr)
        sys.exit(1)

    from lampion_mcp.server import configure, mcp
    configure(args.api_url, args.token)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
