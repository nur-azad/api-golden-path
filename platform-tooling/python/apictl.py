#!/usr/bin/env python3
"""Minimal apictl prototype: validate OpenAPI YAML against a small rule set and emit Backstage metadata."""
import sys
import yaml
import click
from rich.console import Console
from rich.table import Table
from pathlib import Path

console = Console()

import re


def is_semver(v: str) -> bool:
    semver_re = r"^\d+\.\d+\.\d+(?:[-+].*)?$"
    return bool(re.match(semver_re, v))


def has_response_schema(doc: dict) -> bool:
    # Ensure each operation has at least one response with a content/schema entry
    paths = doc.get("paths", {}) or {}
    for p in paths.values():
        for op in p.values():
            if not isinstance(op, dict):
                continue
            responses = op.get("responses", {})
            if not responses:
                return False
            has_schema = False
            for r in responses.values():
                if isinstance(r, dict) and r.get("content"):
                    has_schema = True
                    break
            if not has_schema:
                return False
    return True


def all_params_have_description(doc: dict) -> bool:
    paths = doc.get("paths", {}) or {}
    for p in paths.values():
        for op in p.values():
            if not isinstance(op, dict):
                continue
            params = op.get("parameters", [])
            for param in params:
                if isinstance(param, dict) and not param.get("description"):
                    return False
    return True


def unique_operation_ids(doc: dict) -> bool:
    seen = set()
    paths = doc.get("paths", {}) or {}
    for p in paths.values():
        for op in p.values():
            if not isinstance(op, dict):
                continue
            oid = op.get("operationId")
            if oid:
                if oid in seen:
                    return False
                seen.add(oid)
    return True


def paths_use_api_prefix(doc: dict) -> bool:
    # Recommend top-level paths start with /api or /v
    paths = doc.get("paths", {}) or {}
    for path in paths.keys():
        if not (path.startswith("/api") or path.startswith("/v") or path.startswith("/health") or path.startswith("/swagger")):
            return False
    return True


RULES = [
    {
        "id": "OPENAPI_PRESENT",
        "severity": "error",
        "message": "`openapi` field must be present and 3.0+",
        "check": lambda doc: "openapi" in doc and str(doc.get("openapi", "")).startswith("3."),
    },
    {
        "id": "INFO_TITLE",
        "severity": "error",
        "message": "`info.title` must be provided",
        "check": lambda doc: isinstance(doc.get("info"), dict) and bool(doc["info"].get("title")),
    },
    {
        "id": "INFO_VERSION",
        "severity": "warning",
        "message": "`info.version` should follow semantic versioning (MAJOR.MINOR.PATCH)",
        "check": lambda doc: isinstance(doc.get("info"), dict) and bool(doc["info"].get("version")) and is_semver(str(doc["info"].get("version"))),
    },
    {
        "id": "PATHS",
        "severity": "error",
        "message": "`paths` must contain at least one endpoint",
        "check": lambda doc: isinstance(doc.get("paths"), dict) and len(doc.get("paths", {})) > 0,
    },
    {
        "id": "RESPONSES_HAVE_SCHEMA",
        "severity": "error",
        "message": "Each operation should declare response `content` with a schema",
        "check": lambda doc: has_response_schema(doc),
    },
    {
        "id": "SECURITY",
        "severity": "warning",
        "message": "Consider declaring securitySchemes in components.securitySchemes",
        "check": lambda doc: isinstance(doc.get("components"), dict) and bool(doc.get("components", {}).get("securitySchemes")),
    },
    {
        "id": "OPENTELEMETRY_TAG",
        "severity": "warning",
        "message": "Recommend `x-opentelemetry` metadata or explicit telemetry fields for observability",
        "check": lambda doc: bool(doc.get("x-opentelemetry") or doc.get("info", {}).get("x-opentelemetry")),
    },
    {
        "id": "PARAM_DESCRIPTIONS",
        "severity": "warning",
        "message": "All parameters should include a description",
        "check": lambda doc: all_params_have_description(doc),
    },
    {
        "id": "UNIQUE_OPERATION_IDS",
        "severity": "warning",
        "message": "OperationIds should be unique across the spec",
        "check": lambda doc: unique_operation_ids(doc),
    },
    {
        "id": "PATH_PREFIX",
        "severity": "warning",
        "message": "Recommend top-level paths to use `/api` or `/v` prefix for discoverability and consistency",
        "check": lambda doc: paths_use_api_prefix(doc),
    },
]


def load_yaml(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_rules(doc):
    issues = []
    for r in RULES:
        try:
            ok = r["check"](doc)
        except Exception:
            ok = False
        if not ok:
            issues.append({"id": r["id"], "severity": r["severity"], "message": r["message"]})
    return issues


def print_report(issues):
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Severity")
    table.add_column("Message")
    for it in issues:
        table.add_row(it["id"], it["severity"], it["message"])
    console.print(table)


def emit_backstage_metadata(doc, out_path: Path):
    metadata = {
        "apiVersion": "backstage.io/v1alpha1",
        "kind": "Component",
        "metadata": {
            "name": doc.get("info", {}).get("title", "unnamed-api").lower().replace(" ", "-"),
            "description": doc.get("info", {}).get("description", ""),
            "tags": [t["name"] for t in doc.get("tags", []) if isinstance(t, dict) and t.get("name")] if doc.get("tags") else [],
        },
        "spec": {
            "type": "service",
            "lifecycle": "production",
            "owner": doc.get("info", {}).get("x-owner", "unknown"),
            "system": "api-platform",
        },
    }
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(metadata, f)
    console.print(f"Wrote Backstage metadata to {out_path}")


@click.group()
def cli():
    pass


@cli.command()
@click.argument("openapi_file", type=click.Path(exists=True))
@click.option("--emit-backstage", is_flag=True, help="Emit Backstage component metadata file")
@click.option("--strict", is_flag=True, help="Treat warnings as errors (exit non-zero on warnings)")
def validate(openapi_file, emit_backstage, strict):
    path = Path(openapi_file)
    try:
        doc = load_yaml(path)
    except Exception as e:
        console.print(f"[red]Failed to parse YAML: {e}")
        sys.exit(2)

    issues = run_rules(doc)
    if not issues:
        console.print("[green]No issues found — spec looks good.")
        if emit_backstage:
            emit_backstage_metadata(doc, path.parent / "backstage-component.yaml")
        sys.exit(0)

    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]

    if errors:
        console.print(f"[red]{len(errors)} errors found")
    if warnings:
        console.print(f"[yellow]{len(warnings)} warnings found")

    print_report(issues)
    if emit_backstage:
        emit_backstage_metadata(doc, path.parent / "backstage-component.yaml")

    # Exit non-zero if any errors exist. If --strict is set, treat warnings as errors.
    if errors or (strict and warnings):
        sys.exit(1)
    sys.exit(0)


@cli.command()
@click.argument("openapi_file", type=click.Path(exists=True))
@click.option("--catalog-url", default="http://localhost:7007", help="Backstage base URL")
def register(openapi_file, catalog_url):
    """[DRY RUN] Show what would be posted to the Backstage catalog to register this API."""
    path = Path(openapi_file)
    backstage_path = path.parent / "backstage-component.yaml"
    if not backstage_path.exists():
        console.print("[yellow]backstage-component.yaml not found — run 'validate --emit-backstage' first.")
        sys.exit(1)
    try:
        component = load_yaml(backstage_path)
    except Exception as e:
        console.print(f"[red]Failed to parse backstage-component.yaml: {e}")
        sys.exit(2)

    name = component.get("metadata", {}).get("name", "unknown")
    owner = component.get("spec", {}).get("owner", "unknown")
    endpoint = f"{catalog_url}/api/catalog/locations"

    console.print("\n[bold yellow][DRY RUN] Backstage Catalog Registration[/bold yellow]")
    console.print(f"[dim]Would POST to:[/dim] [cyan]{endpoint}[/cyan]\n")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Component name", name)
    table.add_row("Owner", owner)
    table.add_row("Kind", component.get("kind", "Component"))
    table.add_row("Lifecycle", component.get("spec", {}).get("lifecycle", "unknown"))
    table.add_row("System", component.get("spec", {}).get("system", "unknown"))
    console.print(table)
    console.print("\n[dim]Equivalent curl:[/dim]")
    console.print(f'[green]curl -X POST {endpoint} -H "Content-Type: application/json" \\\n  -d \'{{"type":"url","target":"<catalog-yaml-url>"}}\' [/green]')
    console.print("\n[dim]In production: the auto-discovery scanner opens a PR — squad approval triggers registration.[/dim]")


if __name__ == "__main__":
    cli()
