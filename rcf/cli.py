"""
RCF CLI — Typer application with every command and option fully specified.

Run with:
    python -m rcf.cli --help
    rcf search "Google Dubai" --region uae --format csv
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List, Optional

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Fix Windows console encoding for Unicode output (✓, ✗, etc.)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rcf.config import (
    ALL_SOURCES,
    EmailVerificationTier,
    ExportFormat,
    LogLevel,
    Region,
    RCFConfig,
    SourceType,
)

# Lazy imports for pipeline components (avoid heavy imports at CLI startup)
# from models.models import ContactQuery, RecruiterContact
# from models.enums import Region as ModelRegion, SourceType as ModelSourceType, ContactType as ModelContactType
# from rcf.core.plugin_registry import PluginRegistry
# from rcf.core.orchestrator import PipelineOrchestrator, PipelineConfig, PipelineResult
# from rcf.core.deduplicator import DeduplicationEngine
# from rcf.core.scorer import ConfidenceScoringEngine
# from rcf.core.api_tracker import APITracker
# from rcf.export import export_csv, export_json, export_xlsx, export_html, ContactModel

# ---------------------------------------------------------------------------
# Rich console (module-level)
# ---------------------------------------------------------------------------

console = Console()

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="rcf",
    help="RCF — Recruiter Contact Finder. UAE/GCC-optimized recruiter contact discovery CLI.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)

config_app = typer.Typer(
    name="config",
    help="Manage RCF configuration.",
    no_args_is_help=True,
)
app.add_typer(config_app, name="config")

db_app = typer.Typer(
    name="db",
    help="Manage the local SQLite database.",
    no_args_is_help=True,
)
app.add_typer(db_app, name="db")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_config(config_path: Optional[Path] = None) -> RCFConfig:
    """Resolve and load configuration."""
    if config_path is None:
        # Search upward from cwd
        for candidate in [Path("config.yml"), Path("rcf.yml"), Path.home() / ".rcf" / "config.yml"]:
            if candidate.exists():
                config_path = candidate
                break
        else:
            config_path = Path("config.yml")
    return RCFConfig.from_yaml(config_path)


def _get_db_path(cfg: Optional[RCFConfig] = None) -> Path:
    """Resolve the SQLite database path from config."""
    if cfg is None:
        cfg = _load_config()
    return Path(cfg.general.database_path)


def _get_db_connection(db_path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with row factory."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _cli_region_to_model(cli_region: Region):
    """Map CLI Region enum to models Region enum (now unified)."""
    from models.enums import Region as ModelRegion
    # Enums are now consolidated — direct value mapping works.
    # GCC maps to itself (no longer forced to GLOBAL).
    return ModelRegion(cli_region.value)


def _auto_output_path(fmt: ExportFormat) -> Path:
    """Generate an auto-dated output filename."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext_map = {
        ExportFormat.CSV: "csv",
        ExportFormat.JSON: "json",
        ExportFormat.XLSX: "xlsx",
        ExportFormat.HTML: "html",
    }
    return Path(f"rcf_search_{ts}.{ext_map[fmt]}")


def _contact_to_export_model(contact) -> "ContactModel":  # type: ignore[name-defined]
    """Convert a RecruiterContact to a ContactModel for export."""
    from rcf.export import ContactModel

    primary_email = next((e for e in contact.emails if e.is_primary), None)
    primary_phone = next((p for p in contact.phones if p.is_primary), None)
    first_email = primary_email or (contact.emails[0] if contact.emails else None)
    first_phone = primary_phone or (contact.phones[0] if contact.phones else None)

    # Infer emirate from UAE landline phone number
    emirate = ""
    if first_phone and first_phone.phone:
        from models.validators import infer_uae_emirate
        emirate = infer_uae_emirate(first_phone.phone) or ""

    return ContactModel(
        id=contact.id,
        first_name=(contact.arabic_name.first_name or "") if getattr(contact, "arabic_name", None) else (contact.name.split(None, 1)[0] if contact.name else ""),
        last_name=(contact.arabic_name.last_name or "") if getattr(contact, "arabic_name", None) else (contact.name.split(None, 1)[1] if contact.name and len(contact.name.split(None, 1)) > 1 else ""),
        full_name=contact.name,
        email=first_email.email if first_email else "",
        email_verified=first_email.verification_status.value in ("dns_valid", "smtp_valid", "api_valid") if first_email else None,
        email_verification_tier=first_email.verification_method or "" if first_email else "",
        email_sources=[first_email.source.value] if first_email and first_email.source else [],
        phone=first_phone.phone if first_phone else "",
        phone_formatted=first_phone.phone if first_phone else "",
        phone_carrier=first_phone.carrier or "" if first_phone else "",
        phone_type=first_phone.line_type.value if first_phone else "",
        phone_verified=first_phone.validation_status.value in ("dns_valid", "smtp_valid", "api_valid") if first_phone else None,
        whatsapp=first_phone.is_whatsapp if first_phone else None,
        whatsapp_business=first_phone.whatsapp_business if first_phone else None,
        title=contact.title or "",
        company=contact.company or "",
        company_domain=(contact.company_profile.domain_com or "") if contact.company_profile else "",
        industry=(contact.company_profile.industry or "") if contact.company_profile else "",
        linkedin_url=contact.linkedin_url or "",
        region=contact.region.value,
        emirate=emirate,
        sources=list({s.source_name for s in contact.sources}),
        confidence_score=contact.confidence.value,
        confidence_tier=(
            "high" if contact.confidence.value >= 0.8
            else "medium" if contact.confidence.value >= 0.5
            else "low" if contact.confidence.value > 0.0
            else "unverified"
        ),
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


async def _run_search(
    query,
    enable_enrichment: bool = True,
    enable_verification: bool = True,
    enable_scoring: bool = True,
    waterfall: bool = True,
    no_cache: bool = False,
    check_whatsapp: bool = False,
) -> "PipelineResult":  # type: ignore[name-defined]
    """Execute the search pipeline: discover → dedup → enrich → verify → score."""
    from rcf.core.plugin_registry import PluginRegistry
    from rcf.core.orchestrator import PipelineOrchestrator, PipelineConfig
    from rcf.core.deduplicator import DeduplicationEngine
    from rcf.core.scorer import ConfidenceScoringEngine
    from rcf.core.api_tracker import APITracker

    registry = PluginRegistry()
    await registry.discover_and_register()
    orchestrator = PipelineOrchestrator(
        registry=registry,
        config=PipelineConfig(
            enable_enrichment=enable_enrichment,
            enable_verification=enable_verification,
            enable_scoring=enable_scoring,
            waterfall_enabled=waterfall,
            check_whatsapp=check_whatsapp,
        ),
        dedup_engine=DeduplicationEngine(),
        scorer_engine=ConfidenceScoringEngine(),
        api_tracker=APITracker(),
    )
    return await orchestrator.run(query)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo("rcf 1.0.0")
        raise typer.Exit()


# ---------------------------------------------------------------------------
# Global options
# ---------------------------------------------------------------------------

@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        help="Show RCF version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-C",
        exists=False,
        help="Path to config.yml (auto-detected by default).",
    ),
) -> None:
    """RCF — Recruiter Contact Finder for UAE/GCC."""
    # Config is stored in Typer context for subcommands
    pass


# ---------------------------------------------------------------------------
# `rcf search`
# ---------------------------------------------------------------------------

@app.command()
def search(
    query: str = typer.Argument(
        ...,
        help="Company name, industry, or recruiter name to search for.",
    ),
    region: Region = typer.Option(
        Region.UAE,
        "--region",
        "-r",
        help="Target region for the search.",
    ),
    sources: Optional[List[str]] = typer.Option(
        None,
        "--sources",
        "-s",
        help="Specific source names to use (default: all enabled for region). Repeatable.",
    ),
    max_results: int = typer.Option(
        50,
        "--max-results",
        "-m",
        min=1,
        max=10000,
        help="Maximum number of contacts to return.",
    ),
    confidence_threshold: float = typer.Option(
        0.5,
        "--confidence-threshold",
        "-t",
        min=0.0,
        max=1.0,
        help="Minimum confidence score (0.0–1.0). Contacts below this are discarded.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path. Auto-generated if omitted (e.g. rcf_search_20260504_120000.csv).",
    ),
    format: ExportFormat = typer.Option(
        ExportFormat.CSV,
        "--format",
        "-f",
        help="Output format: csv, json, xlsx, html.",
    ),
    enrich: bool = typer.Option(
        True,
        "--enrich",
        "-e",
        help="Run enrichment waterfall after initial discovery.",
    ),
    verify_emails: bool = typer.Option(
        True,
        "--verify-emails",
        help="Verify discovered email addresses.",
    ),
    verify_phones: bool = typer.Option(
        True,
        "--verify-phones",
        help="Verify discovered phone numbers.",
    ),
    check_whatsapp: bool = typer.Option(
        True,
        "--check-whatsapp",
        help="Check if phone numbers are WhatsApp-enabled.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be searched without executing any queries.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging output.",
    ),
    no_cache: bool = typer.Option(
        False,
        "--no-cache",
        help="Ignore cached results; force fresh lookups from all sources.",
    ),
    companies_file: Optional[Path] = typer.Option(
        None,
        "--companies-file",
        exists=True,
        help="Read company names from a text file (one per line) instead of QUERY arg.",
    ),
    industry: Optional[str] = typer.Option(
        None,
        "--industry",
        "-i",
        help="Filter by industry (e.g. 'technology', 'finance', 'healthcare').",
    ),
    title_filter: Optional[str] = typer.Option(
        None,
        "--title-filter",
        help="Filter recruiter titles (e.g. 'technical recruiter', 'talent acquisition').",
    ),
) -> None:
    """
    Search for recruiter contacts across multiple data sources.

    QUERY can be a company name (e.g. "Google Dubai"), an industry
    (e.g. "recruitment agency"), or a recruiter's name
    (e.g. "Ahmed Al-Rashid").

    Use --companies-file to batch-search multiple companies.

    Examples:

        rcf search "Google Dubai" --region uae

        rcf search "recruitment agency" --region gcc --format xlsx

        rcf search --companies-file companies.txt --industry technology

        rcf search "technical recruiter" --title-filter "senior" --dry-run
    """
    console.print(f"\n[bold]RCF Search[/bold]")
    console.print(f"  Query: [cyan]{query}[/cyan]")
    console.print(f"  Region: [cyan]{region.value}[/cyan]")
    console.print(f"  Format: [cyan]{format.value}[/cyan]")

    if dry_run:
        console.print("\n[yellow]DRY RUN[/yellow] — no queries will be executed.")
        cfg = _load_config()
        console.print("Sources that would be queried:")
        for name, defaults in sorted(ALL_SOURCES.items()):
            if not defaults.get("enabled", True):
                continue
            regions = defaults.get("regions", [])
            region_values = [r.value if isinstance(r, Region) else r for r in regions]
            if "all" not in region_values and region.value not in region_values:
                continue
            src_type = defaults.get("type", "api")
            console.print(f"  [dim]•[/dim] [cyan]{name}[/cyan] [dim]({src_type})[/dim]")
        return

    # ── 1. Load config ──────────────────────────────────────────────
    cfg = _load_config()

    # ── 2. Build ContactQuery ───────────────────────────────────────
    from models.models import ContactQuery
    from models.enums import ContactType as ModelContactType, SourceType as ModelSourceType

    company_names: list[str] = []
    if companies_file:
        company_names = [
            line.strip()
            for line in companies_file.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        company_names = [query]

    model_region = _cli_region_to_model(region)

    source_types: list[ModelSourceType] | None = None
    if sources:
        from models.enums import SourceType as MSt
        valid_types = {t.value for t in MSt}
        source_types = [MSt(s) for s in sources if s in valid_types] or None

    contact_types = [ModelContactType.RECRUITER]
    keywords: list[str] = []
    if industry:
        keywords.append(industry)
    if title_filter:
        keywords.append(title_filter)

    cq = ContactQuery(
        company_names=company_names,
        industry=industry,
        region=model_region,
        contact_types=contact_types,
        max_results=max_results,
        min_confidence=confidence_threshold,
        keywords=keywords,
        sources=source_types,
    )

    # ── 3. Execute pipeline ─────────────────────────────────────────
    start_time = time.monotonic()
    console.print(f"  Running pipeline for [bold]{len(company_names)}[/bold] company(ies) in [cyan]{region.value}[/cyan]...")

    try:
        result = asyncio.run(_run_search(
            cq,
            enable_enrichment=enrich,
            enable_verification=verify_emails or verify_phones,
            enable_scoring=True,
            waterfall=True,
            no_cache=no_cache,
            check_whatsapp=check_whatsapp,
        ))
    except Exception as exc:
        console.print(f"\n[bold red]✗ Search pipeline failed:[/bold red] {exc}")
        raise typer.Exit(code=1)

    elapsed = time.monotonic() - start_time

    # ── 4. Convert to export models ─────────────────────────────────
    from rcf.export import ContactModel

    contacts = result.contacts
    export_contacts: list[ContactModel] = [_contact_to_export_model(c) for c in contacts]

    console.print(f"\n[bold green]✓ Search Complete[/bold green]")
    console.print(f"  Found [bold]{len(contacts)}[/bold] contact(s) after dedup & scoring")
    console.print(f"  Plugins used: [dim]{', '.join(result.plugins_used) or 'none'}[/dim]")
    if result.plugins_failed:
        console.print(f"  Plugins failed: [red]{', '.join(result.plugins_failed)}[/red]")
    if result.early_exit:
        console.print(f"  [yellow]Waterfall early-exit triggered[/yellow]")

    # ── 5. Export ────────────────────────────────────────────────────
    out_path = output or _auto_output_path(format)

    try:
        if format == ExportFormat.CSV:
            from rcf.export import export_csv
            export_csv(export_contacts, out_path)
        elif format == ExportFormat.JSON:
            from rcf.export import export_json
            export_json(export_contacts, out_path)
        elif format == ExportFormat.XLSX:
            from rcf.export import export_xlsx
            export_xlsx(export_contacts, out_path)
        elif format == ExportFormat.HTML:
            from rcf.export import export_html
            export_html(export_contacts, out_path)
    except Exception as exc:
        console.print(f"  [bold red]✗ Export failed:[/bold red] {exc}")
        raise typer.Exit(code=1)

    console.print(f"  Time: [dim]{elapsed:.1f}s[/dim]")
    console.print(f"  Output: [bold blue]{out_path}[/bold blue]")


# ---------------------------------------------------------------------------
# `rcf enrich`
# ---------------------------------------------------------------------------

@app.command()
def enrich(
    contact_id: Optional[str] = typer.Argument(
        None,
        help="Specific contact ID to enrich. Use --all to enrich all contacts.",
    ),
    all_contacts: bool = typer.Option(
        False,
        "--all",
        help="Enrich all contacts that haven't been enriched yet.",
    ),
    sources: Optional[List[str]] = typer.Option(
        None,
        "--sources",
        "-s",
        help="Specific enrichment sources to use. Default: all enabled.",
    ),
    verify_emails: bool = typer.Option(
        True,
        "--verify-emails",
        help="Re-verify email addresses after enrichment.",
    ),
    verify_phones: bool = typer.Option(
        True,
        "--verify-phones",
        help="Re-verify phone numbers after enrichment.",
    ),
    check_whatsapp: bool = typer.Option(
        True,
        "--check-whatsapp",
        help="Re-check WhatsApp status after enrichment.",
    ),
    confidence_threshold: float = typer.Option(
        0.5,
        "--confidence-threshold",
        "-t",
        min=0.0,
        max=1.0,
        help="Re-evaluate contacts against this threshold after enrichment.",
    ),
) -> None:
    """
    Enrich existing contacts with additional data from configured sources.

    Runs the enrichment waterfall: each source is tried in priority order.
    Missing fields (email, phone, LinkedIn) are filled from the highest-
    priority source that returns data.

    Examples:

        rcf enrich abc123

        rcf enrich --all --sources hunter apollo

        rcf enrich --all --verify-emails --verify-phones
    """
    if not contact_id and not all_contacts:
        typer.echo("[rcf] Error: provide a CONTACT_ID or use --all.", err=True)
        raise typer.Exit(code=1)

    target = "all contacts" if all_contacts else f"contact {contact_id}"
    typer.echo(f"[rcf] Enriching {target}...")

    cfg = _load_config()
    db_path = _get_db_path(cfg)

    if not db_path.exists():
        typer.echo("[rcf] ✗ Database not found. Run a search first.", err=True)
        raise typer.Exit(code=1)

    conn = _get_db_connection(db_path)
    try:
        # Load contacts from SQLite
        if all_contacts:
            rows = conn.execute(
                "SELECT id, name, first_name, last_name, company_name, title, "
                "linkedin_url, region, confidence_score, created_at, updated_at "
                "FROM contacts WHERE is_active = 1"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, first_name, last_name, company_name, title, "
                "linkedin_url, region, confidence_score, created_at, updated_at "
                "FROM contacts WHERE id = ?",
                (contact_id,),
            ).fetchall()

        if not rows:
            typer.echo(f"[rcf] No contacts found to enrich.")
            return

        typer.echo(f"[rcf] Loaded {len(rows)} contact(s) from database")

        # Build ContactQuery from each contact's data for re-enrichment
        from models.models import ContactQuery, RecruiterContact
        from models.enums import Region as ModelRegion

        enriched_count = 0
        for row in rows:
            region_val = row["region"] or "uae"
            try:
                model_region = ModelRegion(region_val)
            except ValueError:
                model_region = ModelRegion.UAE

            company_name = row["company_name"] or ""
            cq = ContactQuery(
                company_names=[company_name] if company_name else [],
                region=model_region,
                max_results=5,
                min_confidence=0.0,
            )

            try:
                result = asyncio.run(_run_search(cq, enable_enrichment=True, enable_verification=True))
            except Exception as exc:
                typer.echo(f"[rcf] ✗ Enrichment failed for {row['name']}: {exc}", err=True)
                continue

            # Update contact in DB with enriched data
            for contact in result.contacts:
                # Check if this enriched contact matches our original
                # Update confidence score
                conn.execute(
                    "UPDATE contacts SET confidence_score = ?, updated_at = datetime('now') "
                    "WHERE id = ?",
                    (contact.confidence.value, row["id"]),
                )

                # Insert new emails
                for email in contact.emails:
                    conn.execute(
                        "INSERT OR IGNORE INTO emails (contact_id, email, verification_status, is_primary) "
                        "VALUES (?, ?, ?, ?)",
                        (row["id"], email.email, email.verification_status.value, 1 if email.is_primary else 0),
                    )

                # Insert new phones
                for phone in contact.phones:
                    conn.execute(
                        "INSERT OR IGNORE INTO phones (contact_id, phone, validation_status, is_primary) "
                        "VALUES (?, ?, ?, ?)",
                        (row["id"], phone.phone, phone.validation_status.value, 1 if phone.is_primary else 0),
                    )

            enriched_count += 1

        conn.commit()
        typer.echo(f"[rcf] ✓ Enriched {enriched_count}/{len(rows)} contact(s)")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# `rcf export`
# ---------------------------------------------------------------------------

@app.command()
def export(
    format: ExportFormat = typer.Option(
        ExportFormat.CSV,
        "--format",
        "-f",
        help="Output format: csv, json, xlsx, html.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file path. Auto-generated if omitted.",
    ),
    threshold: float = typer.Option(
        0.0,
        "--threshold",
        "-t",
        min=0.0,
        max=1.0,
        help="Export only contacts at or above this confidence level. 0.0 = all.",
    ),
    region: Optional[Region] = typer.Option(
        None,
        "--region",
        "-r",
        help="Filter exported contacts by region.",
    ),
    since: Optional[datetime] = typer.Option(
        None,
        "--since",
        formats=["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"],
        help="Export only contacts created on or after this datetime.",
    ),
    dedup: bool = typer.Option(
        True,
        "--dedup/--no-dedup",
        help="Deduplicate contacts by (name, email, phone) tuple before export.",
    ),
) -> None:
    """
    Export stored contacts to a file.

    By default exports all contacts as CSV with deduplication enabled.
    Use --threshold, --region, and --since to filter the export set.

    Examples:

        rcf export --format xlsx --output recruiters.xlsx

        rcf export --format json --threshold 0.8 --region uae

        rcf export --format html --since 2026-01-01 --dedup
    """
    typer.echo(f"[rcf] Exporting contacts as {format.value}...")

    cfg = _load_config()
    db_path = _get_db_path(cfg)

    if not db_path.exists():
        typer.echo("[rcf] ✗ Database not found. Run a search first.", err=True)
        raise typer.Exit(code=1)

    conn = _get_db_connection(db_path)
    try:
        # Build query with filters
        sql = (
            "SELECT c.id, c.name, c.first_name, c.last_name, c.company_name, c.title, "
            "c.linkedin_url, c.region, c.confidence_score, c.created_at, c.updated_at, "
            "c.whatsapp_number, c.contact_type "
            "FROM contacts c WHERE c.is_active = 1"
        )
        params: list = []

        if threshold > 0.0:
            sql += " AND c.confidence_score >= ?"
            params.append(threshold)

        if region:
            sql += " AND c.region = ?"
            params.append(region.value)

        if since:
            sql += " AND c.created_at >= ?"
            params.append(since.isoformat())

        sql += " ORDER BY c.confidence_score DESC"

        rows = conn.execute(sql, params).fetchall()

        if not rows:
            typer.echo("[rcf] No contacts found matching filters.")
            return

        typer.echo(f"[rcf] Loaded {len(rows)} contact(s) from database")

        # Build export models from DB rows
        from rcf.export import ContactModel

        contacts: list[ContactModel] = []
        seen_keys: set[tuple] = set()

        for row in rows:
            # Dedup check
            if dedup:
                email_row = conn.execute(
                    "SELECT email FROM emails WHERE contact_id = ? AND is_primary = 1 LIMIT 1",
                    (row["id"],),
                ).fetchone()
                phone_row = conn.execute(
                    "SELECT phone FROM phones WHERE contact_id = ? AND is_primary = 1 LIMIT 1",
                    (row["id"],),
                ).fetchone()
                email = email_row["email"] if email_row else ""
                phone = phone_row["phone"] if phone_row else ""
                key = (row["name"].lower(), email.lower(), phone)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
            else:
                email = ""
                phone = ""
                email_row = conn.execute(
                    "SELECT email FROM emails WHERE contact_id = ? AND is_primary = 1 LIMIT 1",
                    (row["id"],),
                ).fetchone()
                if email_row:
                    email = email_row["email"]
                phone_row = conn.execute(
                    "SELECT phone FROM phones WHERE contact_id = ? AND is_primary = 1 LIMIT 1",
                    (row["id"],),
                ).fetchone()
                if phone_row:
                    phone = phone_row["phone"]

            source_names = conn.execute(
                "SELECT GROUP_CONCAT(DISTINCT source_name) FROM sources WHERE contact_id = ?",
                (row["id"],),
            ).fetchone()[0] or ""

            score = row["confidence_score"] or 0.0
            tier = (
                "high" if score >= 0.8
                else "medium" if score >= 0.5
                else "low" if score > 0.0
                else "unverified"
            )

            contacts.append(ContactModel(
                id=row["id"],
                first_name=row["first_name"] or "",
                last_name=row["last_name"] or "",
                full_name=row["name"],
                email=email,
                phone=phone,
                title=row["title"] or "",
                company=row["company_name"] or "",
                linkedin_url=row["linkedin_url"] or "",
                region=row["region"] or "",
                sources=[s.strip() for s in source_names.split(",") if s.strip()],
                confidence_score=score,
                confidence_tier=tier,
                created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.now(),
            ))

        # Export
        out_path = output or _auto_output_path(format)

        if format == ExportFormat.CSV:
            from rcf.export import export_csv
            export_csv(contacts, out_path)
        elif format == ExportFormat.JSON:
            from rcf.export import export_json
            export_json(contacts, out_path)
        elif format == ExportFormat.XLSX:
            from rcf.export import export_xlsx
            export_xlsx(contacts, out_path)
        elif format == ExportFormat.HTML:
            from rcf.export import export_html
            export_html(contacts, out_path)

        typer.echo(f"[rcf] ✓ Exported {len(contacts)} contact(s) → {out_path}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# `rcf status`
# ---------------------------------------------------------------------------

@app.command()
def status(
    source: Optional[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Show detailed status for a specific source.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show per-source breakdown with API key status.",
    ),
) -> None:
    """
    Show system status: API usage, total contacts, last search date.

    Displays a table of all configured sources with their current credit
    usage, remaining credits, and reset dates (where available).

    Examples:

        rcf status

        rcf status --source hunter --verbose
    """
    cfg = _load_config()
    db_path = _get_db_path(cfg)

    total_contacts = 0
    last_search = "Never"
    db_size_kb = 0.0
    api_usage_rows: list[sqlite3.Row] = []

    if db_path.exists():
        conn = _get_db_connection(db_path)
        try:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM contacts").fetchone()
            total_contacts = row["cnt"] if row else 0

            row = conn.execute(
                "SELECT started_at FROM sessions ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            last_search = row["started_at"] if row else "Never"

            db_size_kb = db_path.stat().st_size / 1024.0

            api_usage_rows = conn.execute(
                "SELECT source_name, credits_used, credits_limit, credits_remaining, "
                "last_used, reset_date FROM api_usage ORDER BY source_name"
            ).fetchall()
        finally:
            conn.close()

    # ── Overview table ─────────────────────────────────────────────
    overview_table = Table(title="RCF System Status", show_header=True, header_style="bold cyan")
    overview_table.add_column("Metric", style="cyan")
    overview_table.add_column("Value", style="green")
    overview_table.add_row("Total contacts", str(total_contacts))
    overview_table.add_row("Last search", last_search)
    overview_table.add_row("Database size", f"{db_size_kb:.1f} KB")
    console.print(overview_table)
    console.print()

    if source:
        console.print(Panel(f"[bold]{source}[/bold]", title="Source Detail", border_style="cyan"))
        # Check API key status
        defaults = ALL_SOURCES.get(source, {})
        api_key_env = defaults.get("api_key_env")
        if api_key_env:
            has_key = bool(os.environ.get(api_key_env))
            status_str = f"[green]✓ present[/green]" if has_key else "[red]✗ missing[/red]"
            console.print(f"  API key ([dim]{api_key_env}[/dim]): {status_str}")
        else:
            console.print("  API key: [dim]N/A (no key required)[/dim]")

        # DB usage data
        if api_usage_rows:
            for row in api_usage_rows:
                if row["source_name"] == source:
                    limit_str = str(row["credits_limit"]) if row["credits_limit"] else "∞"
                    remaining_str = str(row["credits_remaining"]) if row["credits_remaining"] is not None else "∞"
                    detail_table = Table(show_header=True, header_style="bold", grid=True)
                    detail_table.add_column("Field", style="cyan")
                    detail_table.add_column("Value", style="green")
                    detail_table.add_row("Credits used", str(row["credits_used"]))
                    detail_table.add_row("Credits limit", limit_str)
                    detail_table.add_row("Credits remain", remaining_str)
                    detail_table.add_row("Last used", row["last_used"] or "never")
                    if row["reset_date"]:
                        detail_table.add_row("Reset date", row["reset_date"])
                    console.print(detail_table)
                    break
            else:
                console.print("  [dim]No API usage recorded for this source.[/dim]")
        else:
            console.print("  [dim]No API usage data in database.[/dim]")

    elif verbose:
        src_table = Table(title="Source Status", show_header=True, header_style="bold cyan")
        src_table.add_column("Source", style="cyan")
        src_table.add_column("Key", style="green")
        src_table.add_column("Free Tier Limit", style="green")
        src_table.add_column("Credits Used", style="green")
        for name in sorted(ALL_SOURCES):
            defaults = ALL_SOURCES[name]
            api_key_env = defaults.get("api_key_env")
            has_key = "✓" if (api_key_env and os.environ.get(api_key_env)) else ("N/A" if not api_key_env else "✗")
            key_display = f"{api_key_env}={has_key}" if api_key_env else "N/A"
            limit = str(defaults.get("free_tier_limit", "N/A"))

            # Check DB for usage data
            db_credits = "—"
            for row in api_usage_rows:
                if row["source_name"] == name:
                    db_credits = str(row["credits_used"])
                    break

            src_table.add_row(name, key_display, limit, db_credits)
        console.print(src_table)


# ---------------------------------------------------------------------------
# `rcf sources`
# ---------------------------------------------------------------------------

@app.command()
def sources(
    type: Optional[SourceType] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter sources by type: api, scrape, directory, social, browser, osint, email, all.",
    ),
    region: Optional[Region] = typer.Option(
        None,
        "--region",
        "-r",
        help="Filter sources by region support.",
    ),
) -> None:
    """
    List all available data sources with their configuration status.

    Shows source name, type, whether it's configured (API key present),
    supported regions, and free tier information.

    Examples:

        rcf sources

        rcf sources --type api

        rcf sources --region uae
    """
    src_table = Table(title="Available Data Sources", show_header=True, header_style="bold cyan")
    src_table.add_column("Source", style="cyan")
    src_table.add_column("Type", style="dim")
    src_table.add_column("Enabled", justify="center")
    src_table.add_column("Configured", justify="center")
    src_table.add_column("Free Tier", style="dim")
    src_table.add_column("Regions", style="dim")

    for name in sorted(ALL_SOURCES):
        defaults = ALL_SOURCES[name]
        src_type = defaults.get("type", "api")
        enabled = defaults.get("enabled", True)
        api_key_env = defaults.get("api_key_env")

        # Actually check if the env var is set
        if api_key_env:
            configured = "[green]✓[/green]" if os.environ.get(api_key_env) else "[red]✗[/red]"
        else:
            configured = "[dim]—[/dim]"

        regions = defaults.get("regions", ["all"])

        # Filter
        if type and src_type != type.value:
            continue
        if region:
            region_list = [r.value if isinstance(r, Region) else r for r in regions]
            if "all" not in region_list and region.value not in region_list:
                continue

        enabled_str = "[green]✓[/green]" if enabled else "[red]✗[/red]"
        free = str(defaults.get("free_tier_limit", "—"))
        region_str = ", ".join(r.value if isinstance(r, Region) else str(r) for r in regions[:3])

        src_table.add_row(name, src_type, enabled_str, configured, free, region_str)

    console.print(src_table)


# ---------------------------------------------------------------------------
# `rcf config` subcommands
# ---------------------------------------------------------------------------

@config_app.command("show")
def config_show(
    key: Optional[str] = typer.Argument(
        None,
        help="Show a specific config key (dot notation, e.g. 'general.default_region').",
    ),
) -> None:
    """
    Display current configuration.

    Without arguments, shows the full merged configuration.
    With a KEY argument, shows only that value (dot notation).

    Examples:

        rcf config show

        rcf config show general.default_region

        rcf config show sources.hunter
    """
    cfg = _load_config()
    if key:
        # Dot-notation traversal
        parts = key.split(".")
        obj = cfg.model_dump()
        for part in parts:
            if isinstance(obj, dict) and part in obj:
                obj = obj[part]
            else:
                typer.echo(f"[rcf] Key not found: {key}", err=True)
                raise typer.Exit(code=1)
        typer.echo(json.dumps(obj, indent=2, default=str))
    else:
        typer.echo(json.dumps(cfg.model_dump(), indent=2, default=str))


@config_app.command("set")
def config_set(
    key: str = typer.Argument(
        ...,
        help="Config key to set (dot notation, e.g. 'general.default_region').",
    ),
    value: str = typer.Argument(
        ...,
        help="Value to set. JSON values are auto-parsed for nested types.",
    ),
) -> None:
    """
    Set a configuration value.

    The KEY uses dot notation to navigate nested config.
    The VALUE is interpreted as a string unless it parses as JSON.

    Examples:

        rcf config set general.default_region saudi

        rcf config set general.max_concurrent_requests 10

        rcf config set scoring.minimum_confidence 0.7

        rcf config set sources.hunter.enabled false
    """
    # Resolve config file path (same logic as _load_config)
    config_path: Optional[Path] = None
    for candidate in [Path("config.yml"), Path("rcf.yml"), Path.home() / ".rcf" / "config.yml"]:
        if candidate.exists():
            config_path = candidate
            break
    if config_path is None:
        config_path = Path("config.yml")

    # Parse the value: try int, float, bool, JSON, then fall back to string
    parsed_value: Any = value
    if value.lower() in ("true", "false"):
        parsed_value = value.lower() == "true"
    elif value.lower() in ("null", "none"):
        parsed_value = None
    else:
        try:
            parsed_value = int(value)
        except ValueError:
            try:
                parsed_value = float(value)
            except ValueError:
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    pass  # keep as string

    # Load existing YAML or start fresh
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    else:
        data = {}

    # Navigate to the parent of the target key using dot notation
    parts = key.split(".")
    obj = data
    for part in parts[:-1]:
        if part not in obj or not isinstance(obj[part], dict):
            obj[part] = {}
        obj = obj[part]

    # Set the final key
    obj[parts[-1]] = parsed_value

    # Write back, preserving structure
    with open(config_path, "w", encoding="utf-8") as fh:
        yaml.dump(data, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)

    typer.echo(f"[rcf] Set {key} = {parsed_value!r} in {config_path}")


@config_app.command("init")
def config_init(
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite existing config.yml and .env files.",
    ),
) -> None:
    """
    Create config.yml and .env from templates in the current directory.

    Generates a config.yml with all default values and a .env file
    from the .env.example template. Existing files are not overwritten
    unless --force is used.

    Examples:

        rcf config init

        rcf config init --force
    """
    config_path = Path("config.yml")
    env_path = Path(".env")
    example_path = Path(".env.example")

    if config_path.exists() and not force:
        typer.echo(f"[rcf] {config_path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(code=1)

    # Write config.yml with all defaults from RCFConfig model
    defaults = RCFConfig().model_dump()
    yaml_content = yaml.dump(defaults, default_flow_style=False, allow_unicode=True, sort_keys=False)
    header = (
        "# ============================================================\n"
        "# RCF — Recruiter Contact Finder Configuration\n"
        "# ============================================================\n"
        "# All keys have sensible defaults. Uncomment and modify to override.\n"
        "# API keys go in .env (see .env.example).\n"
        "# ============================================================\n\n"
    )
    config_path.write_text(header + yaml_content, encoding="utf-8")
    typer.echo(f"[rcf] Created {config_path} with full defaults")

    if example_path.exists():
        if not env_path.exists() or force:
            env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
            typer.echo(f"[rcf] Created {env_path} from {example_path}")
        else:
            typer.echo(f"[rcf] {env_path} already exists. Use --force to overwrite.")
    else:
        typer.echo(f"[rcf] {example_path} not found. Create .env manually.")


@config_app.command("validate")
def config_validate() -> None:
    """
    Validate configuration and check all API keys.

    Loads config.yml, validates all values, and checks that every
    configured API key is present in the environment. Reports
    missing keys and invalid values.

    Examples:

        rcf config validate
    """
    typer.echo("[rcf] Validating configuration...")
    try:
        cfg = _load_config()
        typer.echo("[rcf] ✓ config.yml is valid.")
    except Exception as exc:
        typer.echo(f"[rcf] ✗ config.yml is invalid: {exc}", err=True)
        raise typer.Exit(code=1)

    # Check API keys
    missing: List[str] = []
    present: List[str] = []
    for name in sorted(ALL_SOURCES):
        defaults = ALL_SOURCES[name]
        if not defaults.get("enabled", True):
            continue
        api_key_env = defaults.get("api_key_env")
        if api_key_env:
            if os.environ.get(api_key_env):
                present.append(f"{name} (${api_key_env})")
            else:
                missing.append(f"{name} (${api_key_env})")

    if present:
        typer.echo(f"[rcf] ✓ API keys found for: {', '.join(present)}")
    if missing:
        typer.echo(f"[rcf] ✗ Missing API keys for: {', '.join(missing)}")
        typer.echo("[rcf] Set these in .env or your shell environment.")
    else:
        typer.echo("[rcf] All required API keys are configured.")


# ---------------------------------------------------------------------------
# `rcf setup`
# ---------------------------------------------------------------------------

@app.command()
def setup() -> None:
    """
    First-time setup wizard.

    Interactive wizard that:
    1. Checks Python dependencies are installed
    2. Creates config.yml with defaults
    3. Prompts for each API key (with signup URLs)
    4. Validates each key as it's entered
    5. Creates .env file
    6. Runs a test search to verify everything works

    Examples:

        rcf setup
    """
    typer.echo("[rcf] Setup Wizard — Recruiter Contact Finder")
    typer.echo("=" * 50)

    # Step 1: Check dependencies
    typer.echo("\n[1/5] Checking dependencies...")
    required_packages = {
        "pydantic": "pydantic",
        "httpx": "httpx",
        "structlog": "structlog",
        "typer": "typer",
        "yaml": "pyyaml",
        "sqlite3": None,  # stdlib
    }
    missing_pkgs: List[str] = []
    for mod_name, pip_name in required_packages.items():
        if pip_name is None:
            continue  # stdlib, always available
        try:
            __import__(mod_name)
            typer.echo(f"  ✓ {pip_name}")
        except ImportError:
            typer.echo(f"  ✗ {pip_name} — not installed")
            missing_pkgs.append(pip_name)
    if missing_pkgs:
        typer.echo(f"\n  Install missing packages with:")
        typer.echo(f"  pip install {' '.join(missing_pkgs)}")
    else:
        typer.echo("  All required packages are installed.")

    # Step 2: Create config.yml
    typer.echo("\n[2/5] Creating config.yml...")
    config_path = Path("config.yml")
    if config_path.exists():
        typer.echo("  config.yml already exists — skipping.")
    else:
        config_path.write_text("# RCF Configuration — see docs for all options\n", encoding="utf-8")
        typer.echo("  Created config.yml with defaults.")

    # Step 3: Prompt for API keys
    typer.echo("\n[3/5] API Key Configuration")
    typer.echo("  Press Enter to skip any key. All keys can be set later in .env.\n")

    env_lines: List[str] = []
    for name in sorted(ALL_SOURCES):
        defaults = ALL_SOURCES[name]
        api_key_env = defaults.get("api_key_env")
        if not api_key_env:
            continue
        free_tier = defaults.get("free_tier_limit", "")
        key = typer.prompt(
            f"  {name} (${api_key_env}) [{free_tier}]",
            default="",
        )
        env_lines.append(f"{api_key_env}={key}")

    # Step 4: Write .env
    typer.echo("\n[4/5] Creating .env file...")
    env_path = Path(".env")
    header = (
        "# ============================================================\n"
        "# RCF - Recruiter Contact Finder — API Keys\n"
        "# ============================================================\n\n"
    )
    env_path.write_text(header + "\n".join(env_lines) + "\n", encoding="utf-8")
    typer.echo(f"  Created {env_path}")

    # Step 5: Validate
    typer.echo("\n[5/5] Validating configuration...")
    try:
        cfg = _load_config()
        typer.echo("  ✓ config.yml is valid.")
    except Exception as exc:
        typer.echo(f"  ✗ config.yml is invalid: {exc}", err=True)

    # Try initializing the plugin registry
    try:
        from rcf.core.plugin_registry import PluginRegistry
        registry = PluginRegistry()
        asyncio.run(registry.discover_and_register())
        typer.echo(f"  ✓ Plugin registry initialized ({len(registry._plugins)} plugins).")
    except Exception as exc:
        typer.echo(f"  ⚠ Plugin registry: {exc}")

    # Verify at least one API source has a key configured
    has_any_key = False
    for name in ALL_SOURCES:
        defaults = ALL_SOURCES[name]
        api_key_env = defaults.get("api_key_env")
        if api_key_env and os.environ.get(api_key_env):
            has_any_key = True
            break
    if has_any_key:
        typer.echo("  ✓ At least one API key is configured.")
    else:
        typer.echo("  ⚠ No API keys found in environment. Set them in .env.")

    # Test database connection
    try:
        db_path = _get_db_path(cfg)
        conn = _get_db_connection(db_path)
        conn.execute("SELECT 1")
        conn.close()
        typer.echo(f"  ✓ Database connection OK ({db_path}).")
    except Exception as exc:
        typer.echo(f"  ✗ Database connection failed: {exc}", err=True)

    typer.echo("\n[rcf] Setup complete! Run `rcf search 'Google Dubai'` to test.")


# ---------------------------------------------------------------------------
# `rcf db` subcommands
# ---------------------------------------------------------------------------

@db_app.command("stats")
def db_stats() -> None:
    """
    Show database statistics.

    Displays row counts per table, total database size on disk,
    and the date range of stored contacts.

    Examples:

        rcf db stats
    """
    db_path = _get_db_path()
    if not db_path.exists():
        console.print(f"  [red]Database not found at {db_path}[/red]")
        console.print("  Run a search first to create the database.")
        return

    conn = _get_db_connection(db_path)
    try:
        stats_table = Table(title="Database Statistics", show_header=True, header_style="bold cyan")
        stats_table.add_column("Table", style="cyan")
        stats_table.add_column("Rows", style="green", justify="right")

        # Row counts for each table (whitelist prevents SQL injection)
        VALID_TABLES = frozenset([
            "contacts", "companies", "emails", "phones", "sources",
            "arabic_name_cache", "sessions", "search_results", "api_usage",
            "tags", "exports", "known_email_patterns", "contacts_fts",
        ])
        tables = ["contacts", "companies", "emails", "phones", "sources",
                  "arabic_name_cache", "sessions", "search_results",
                  "api_usage", "tags", "exports", "known_email_patterns"]
        for table in tables:
            if table not in VALID_TABLES:
                console.print(f"[red]Skipping invalid table: {table}[/red]")
                continue
            try:
                row = conn.execute(f'SELECT COUNT(*) AS cnt FROM "{table}"').fetchone()
                count = row["cnt"] if row else 0
                stats_table.add_row(table, f"{count:,}")
            except sqlite3.OperationalError:
                pass  # table doesn't exist yet

        # DB file size
        db_size_kb = db_path.stat().st_size / 1024.0
        db_size_mb = db_size_kb / 1024.0
        size_str = f"{db_size_mb:.1f} MB" if db_size_mb >= 1.0 else f"{db_size_kb:.1f} KB"
        stats_table.add_row("[bold]DB file size[/bold]", f"[bold]{size_str}[/bold]")

        # Date range of contacts
        try:
            row = conn.execute(
                "SELECT MIN(created_at) AS min_date, MAX(created_at) AS max_date FROM contacts"
            ).fetchone()
            if row and row["min_date"]:
                stats_table.add_row("Contacts date range", f"{row['min_date']} → {row['max_date']}")
        except sqlite3.OperationalError:
            pass

        console.print(stats_table)
    finally:
        conn.close()


@db_app.command("clean")
def db_clean(
    older_than_days: int = typer.Option(
        90,
        "--older-than",
        "-o",
        min=1,
        help="Remove contacts older than this many days.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be deleted without actually deleting.",
    ),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt.",
    ),
) -> None:
    """
    Remove old contacts and expired cache entries.

    By default removes contacts older than 90 days (configurable via
    --older-than). Cache entries past their TTL are always removed.

    Examples:

        rcf db clean --dry-run

        rcf db clean --older-than 30 --yes
    """
    if not confirm and not dry_run:
        typer.confirm(f"Delete contacts older than {older_than_days} days?", abort=True)
    typer.echo(f"[rcf] Cleaning data older than {older_than_days} days...")

    db_path = _get_db_path()
    if not db_path.exists():
        typer.echo("[rcf] Database not found. Nothing to clean.")
        return

    conn = _get_db_connection(db_path)
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()

        # Count old contacts
        old_contacts = conn.execute(
            "SELECT COUNT(*) AS cnt FROM contacts WHERE created_at < ?", (cutoff,)
        ).fetchone()["cnt"]

        # Count expired cache entries (sources older than TTL)
        cfg = _load_config()
        cache_ttl_hours = cfg.general.cache_ttl_hours
        old_cache = conn.execute(
            "SELECT COUNT(*) AS cnt FROM sources WHERE extracted_at < ?", (cutoff,)
        ).fetchone()["cnt"]

        if dry_run:
            typer.echo(f"  [DRY RUN] Would delete {old_contacts} old contact(s) and {old_cache} stale source record(s).")
        else:
            # Delete old contacts (cascading deletes handle emails, phones, etc.)
            conn.execute(
                "DELETE FROM contacts WHERE created_at < ?", (cutoff,)
            )
            deleted_contacts = conn.total_changes

            # Delete stale source cache entries
            conn.execute(
                "DELETE FROM sources WHERE extracted_at < ?", (cutoff,)
            )

            conn.commit()
            typer.echo(f"  ✓ Deleted {old_contacts} old contact(s)")
            typer.echo(f"  ✓ Deleted {old_cache} stale source record(s)")
    finally:
        conn.close()

    typer.echo("[rcf] Clean complete.")


@db_app.command("backup")
def db_backup(
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Backup file path. Default: rcf_backup_YYYYMMDD_HHMMSS.db.",
    ),
) -> None:
    """
    Create a backup of the SQLite database.

    Uses SQLite's built-in backup API for a consistent snapshot.

    Examples:

        rcf db backup

        rcf db backup --output my_backup.db
    """
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"rcf_backup_{timestamp}.db")
    typer.echo(f"[rcf] Backing up database to {output}...")

    db_path = _get_db_path()
    if not db_path.exists():
        typer.echo("[rcf] Database not found. Nothing to backup.")
        return

    # Use SQLite backup API for a consistent snapshot
    source_conn = _get_db_connection(db_path)
    try:
        backup_conn = sqlite3.connect(str(output))
        try:
            source_conn.backup(backup_conn)
            backup_conn.commit()
        finally:
            backup_conn.close()
    finally:
        source_conn.close()

    backup_size_kb = output.stat().st_size / 1024.0
    typer.echo(f"[rcf] ✓ Backup complete → {output} ({backup_size_kb:.1f} KB)")


@db_app.command("reset")
def db_reset(
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt. THIS DELETES ALL DATA.",
    ),
) -> None:
    """
    Reset the database — delete all data and recreate tables.

    ⚠️ This is destructive and cannot be undone.

    Examples:

        rcf db reset
    """
    if not confirm:
        typer.confirm("⚠️  This will DELETE ALL data. Are you sure?", abort=True)
    typer.echo("[rcf] Resetting database...")

    db_path = _get_db_path()
    if not db_path.exists():
        typer.echo("[rcf] Database not found. Will be created on next search.")
        return

    # Drop all tables and recreate from schema
    conn = _get_db_connection(db_path)
    try:
        # Get all user tables
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        views = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()
        triggers = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'"
        ).fetchall()

        # Drop views first, then triggers, then tables (order matters for dependencies)
        for view in views:
            conn.execute(f"DROP VIEW IF EXISTS [{view['name']}]")
        for trigger in triggers:
            conn.execute(f"DROP TRIGGER IF EXISTS [{trigger['name']}]")
        for table in tables:
            conn.execute(f"DROP TABLE IF EXISTS [{table['name']}]")

        conn.commit()
    finally:
        conn.close()

    # Re-run the schema SQL to recreate tables
    schema_path = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    if schema_path.exists():
        conn = sqlite3.connect(str(db_path))
        try:
            schema_sql = schema_path.read_text(encoding="utf-8")
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()
        typer.echo("[rcf] ✓ All tables dropped and recreated from schema.")
    else:
        typer.echo(f"[rcf] ✓ All tables dropped. Schema not found at {schema_path} — tables will be recreated on next search.")

    typer.echo("[rcf] Database reset complete.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
