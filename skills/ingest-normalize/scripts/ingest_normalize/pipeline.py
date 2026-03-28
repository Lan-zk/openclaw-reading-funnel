"""Pipeline entrypoint for ingest-normalize."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from .adapters import get_adapter
from .adapters.base import AdapterFailure
from .io_utils import (
    ensure_utc_iso,
    generate_run_id,
    iso_now,
    load_source_config,
    make_failure_id,
    make_normalized_candidate_id,
    make_plan_id,
    make_source_entry_id,
    make_source_entry_snapshot_id,
    make_url_fingerprint,
    prepare_output_directory,
    write_json,
)
from .models import (
    FetchedSourceBatch,
    IngestFailureRecord,
    NormalizedCandidate,
    RawFeedItem,
    SourceDescriptor,
    SourceEntry,
    SourceEntryDraft,
    SourceSyncPlan,
)
from .normalizers.language import fill_language
from .normalizers.title import normalize_title
from .normalizers.url import normalize_url
from .reporting import STEP_FAILED, StepRecorder, build_ingest_report, determine_step_status

DESCRIPTOR_CORE_FIELDS = {
    "source_id",
    "source_name",
    "adapter_type",
    "enabled",
    "fetch_policy",
    "endpoint",
    "auth_ref",
    "tags",
    "default_language",
}


def discover_sources(
    source_config_path: str,
    runtime_overrides: dict[str, Any] | None = None,
    run_id: str = "pending-run",
) -> tuple[list[SourceDescriptor], list[IngestFailureRecord]]:
    runtime_overrides = runtime_overrides or {}
    config = load_source_config(source_config_path)
    source_filter = set(runtime_overrides.get("source_ids", []))
    descriptors: list[SourceDescriptor] = []
    failures: list[IngestFailureRecord] = []
    for source in config.get("sources", []):
        if source_filter and source.get("source_id") not in source_filter:
            continue
        if not source.get("enabled", True):
            continue
        try:
            adapter_type = source["adapter_type"]
            adapter = get_adapter(adapter_type)
            normalized = adapter.validate_source_config(source)
            descriptors.append(
                SourceDescriptor(
                    source_id=normalized["source_id"],
                    source_name=normalized["source_name"],
                    adapter_type=adapter_type,
                    enabled=True,
                    fetch_policy=normalized.get("fetch_policy", {}),
                    endpoint=normalized.get("endpoint"),
                    auth_ref=normalized.get("auth_ref"),
                    tags=list(normalized.get("tags", [])),
                    default_language=normalized.get("default_language"),
                    adapter_config={key: value for key, value in normalized.items() if key not in DESCRIPTOR_CORE_FIELDS},
                )
            )
        except (KeyError, ValueError, AdapterFailure) as exc:
            failure_type = getattr(exc, "failure_type", "CONFIG_ERROR")
            message = str(exc)
            scope_id = source.get("source_id")
            failures.append(
                IngestFailureRecord(
                    failure_id=make_failure_id(run_id, "discover_sources", "SOURCE", scope_id, message),
                    run_id=run_id,
                    step_name="discover_sources",
                    scope_type="SOURCE",
                    scope_id=scope_id,
                    failure_type=failure_type,
                    message=message,
                    details=getattr(exc, "details", {"adapter_type": source.get("adapter_type")}),
                    retryable=False,
                    recorded_at=iso_now(),
                )
            )
    return descriptors, failures


def sync_source_window(
    descriptors: list[SourceDescriptor],
    runtime_overrides: dict[str, Any] | None = None,
    run_id: str = "pending-run",
) -> tuple[list[SourceSyncPlan], list[IngestFailureRecord]]:
    runtime_overrides = runtime_overrides or {}
    failures: list[IngestFailureRecord] = []
    plans: list[SourceSyncPlan] = []
    now = _parse_runtime_datetime(runtime_overrides.get("now")) or datetime.now(timezone.utc)
    explicit_until = _parse_runtime_datetime(runtime_overrides.get("until"))
    explicit_since = _parse_runtime_datetime(runtime_overrides.get("since"))
    for descriptor in descriptors:
        until = explicit_until or now
        if explicit_since:
            since = explicit_since
        else:
            window_hours = int(descriptor.fetch_policy.get("default_window_hours", 24))
            since = until - timedelta(hours=window_hours)
        if since >= until:
            continue
        since_iso = ensure_utc_iso(since)
        until_iso = ensure_utc_iso(until)
        plans.append(
            SourceSyncPlan(
                source_id=descriptor.source_id,
                plan_id=make_plan_id(descriptor.source_id, since_iso, until_iso),
                mode=runtime_overrides.get("mode", "INCREMENTAL"),
                since=since_iso,
                until=until_iso or ensure_utc_iso(until),
                cursor=runtime_overrides.get("cursor"),
                page_limit=descriptor.fetch_policy.get("page_limit"),
                item_limit=descriptor.fetch_policy.get("item_limit"),
                planned_at=ensure_utc_iso(now),
            )
        )
    return plans, failures


def fetch_source_items(
    descriptors: list[SourceDescriptor],
    plans: list[SourceSyncPlan],
    run_id: str,
) -> tuple[list[FetchedSourceBatch], list[IngestFailureRecord]]:
    plan_by_source_id = {plan.source_id: plan for plan in plans}
    batches: list[FetchedSourceBatch] = []
    failures: list[IngestFailureRecord] = []
    for descriptor in descriptors:
        plan = plan_by_source_id.get(descriptor.source_id)
        if plan is None:
            continue
        adapter = get_adapter(descriptor.adapter_type)
        try:
            request = adapter.build_fetch_request(descriptor, plan)
            response = adapter.fetch_batch(request)
            raw_items = [] if response in (None, "", []) else [response]
            batches.append(
                FetchedSourceBatch(
                    source_id=descriptor.source_id,
                    plan_id=plan.plan_id,
                    adapter_type=descriptor.adapter_type,
                    fetch_window={"since": plan.since, "until": plan.until, "cursor": plan.cursor},
                    raw_items=raw_items,
                    raw_count=len(raw_items),
                    next_cursor=None,
                    fetched_at=iso_now(),
                    fetch_status=determine_step_status(len(raw_items)),
                )
            )
        except AdapterFailure as exc:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="fetch_source_items",
                    scope_type="SOURCE",
                    scope_id=descriptor.source_id,
                    failure_type=exc.failure_type,
                    message=exc.message,
                    details=exc.details,
                    retryable=exc.retryable,
                )
            )
    return batches, failures


def convert_to_feed(
    batches: list[FetchedSourceBatch],
    descriptor_by_source_id: dict[str, SourceDescriptor],
    run_id: str,
) -> tuple[list[RawFeedItem], list[IngestFailureRecord]]:
    items: list[RawFeedItem] = []
    failures: list[IngestFailureRecord] = []
    for batch in batches:
        if batch.raw_count == 0:
            continue
        descriptor = descriptor_by_source_id[batch.source_id]
        adapter = get_adapter(batch.adapter_type)
        try:
            converted_items, _ = adapter.convert_response_to_feed_items(descriptor, batch.raw_items[0])
            for item in converted_items:
                item.source_id = descriptor.source_id
                items.append(item)
        except AdapterFailure as exc:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="convert_to_feed",
                    scope_type="BATCH",
                    scope_id=batch.plan_id,
                    failure_type=exc.failure_type,
                    message=exc.message,
                    details=exc.details,
                    retryable=exc.retryable,
                )
            )
    return items, failures


def map_source_fields(
    items: list[RawFeedItem],
    descriptor_by_source_id: dict[str, SourceDescriptor],
    fetched_at: str,
    run_id: str = "pending-run",
) -> tuple[list[SourceEntryDraft], list[IngestFailureRecord]]:
    drafts: list[SourceEntryDraft] = []
    failures: list[IngestFailureRecord] = []
    for item in items:
        descriptor = descriptor_by_source_id.get(item.source_id)
        if descriptor is None:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="map_source_fields",
                    scope_type="ITEM",
                    scope_id=item.origin_item_id or None,
                    failure_type="MAPPING_ERROR",
                    message=f"Unknown source_id: {item.source_id}",
                    details={"source_id": item.source_id},
                    retryable=False,
                )
            )
            continue
        if not (item.origin_item_id or "").strip():
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="map_source_fields",
                    scope_type="ITEM",
                    scope_id=None,
                    failure_type="MAPPING_ERROR",
                    message="origin_item_id is required",
                    details={"source_id": item.source_id, "title": item.title},
                    retryable=False,
                )
            )
            continue
        drafts.append(
            SourceEntryDraft(
                source_adapter_type=descriptor.adapter_type,
                source_id=descriptor.source_id,
                source_name=descriptor.source_name,
                origin_item_id=item.origin_item_id.strip(),
                title=item.title,
                url=item.url,
                summary=item.summary,
                author=item.author,
                published_at=ensure_utc_iso(item.published_at),
                fetched_at=fetched_at,
                raw_payload=item.raw_payload,
            )
        )
    return drafts, failures


def persist_source_entries(
    drafts: list[SourceEntryDraft],
    run_id: str,
) -> list[SourceEntry]:
    entries: list[SourceEntry] = []
    for draft in drafts:
        source_entry_id = make_source_entry_id(draft.source_id, draft.origin_item_id)
        entries.append(
            SourceEntry(
                source_entry_id=source_entry_id,
                source_entry_snapshot_id=make_source_entry_snapshot_id(source_entry_id, draft.fetched_at),
                source_adapter_type=draft.source_adapter_type,
                source_id=draft.source_id,
                source_name=draft.source_name,
                origin_item_id=draft.origin_item_id,
                title=draft.title,
                url=draft.url,
                summary=draft.summary,
                author=draft.author,
                published_at=draft.published_at,
                fetched_at=draft.fetched_at,
                raw_payload=draft.raw_payload,
                run_id=run_id,
                status="INGESTED",
            )
        )
    return entries


def normalize_candidates(
    entries: list[SourceEntry],
    run_id: str,
) -> tuple[list[NormalizedCandidate], list[IngestFailureRecord]]:
    candidates: list[NormalizedCandidate] = []
    failures: list[IngestFailureRecord] = []
    for entry in entries:
        try:
            canonical_url = normalize_url(entry.url)
            normalized_entry_title = normalize_title(entry.title)
            language = fill_language(
                explicit_language=(entry.raw_payload or {}).get("language"),
                title=entry.title,
                summary=entry.summary,
            )
            if canonical_url is None and normalized_entry_title is None:
                raise ValueError("Entry requires at least one of url or title for normalization")
            candidates.append(
                NormalizedCandidate(
                    normalized_candidate_id=make_normalized_candidate_id(entry.source_entry_id),
                    source_entry_id=entry.source_entry_id,
                    canonical_url=canonical_url,
                    url_fingerprint=make_url_fingerprint(canonical_url),
                    title=entry.title,
                    normalized_title=normalized_entry_title,
                    summary=entry.summary,
                    language=language,
                    published_at=entry.published_at,
                    source_id=entry.source_id,
                    source_name=entry.source_name,
                    normalize_status="NORMALIZED",
                    run_id=run_id,
                )
            )
        except Exception as exc:
            failures.append(
                _make_failure(
                    run_id=run_id,
                    step_name="normalize_candidates",
                    scope_type="OBJECT",
                    scope_id=entry.source_entry_id,
                    failure_type="NORMALIZE_ERROR",
                    message=str(exc),
                    details={"source_entry_id": entry.source_entry_id},
                    retryable=False,
                )
            )
    return candidates, failures


def record_ingest_failures(failures: list[IngestFailureRecord]) -> list[IngestFailureRecord]:
    return list(failures)


def run_pipeline(
    source_config_path: str,
    output_root: str,
    run_id: str | None = None,
    runtime_overrides: dict[str, Any] | None = None,
    mode: str = "NORMAL",
) -> dict[str, Any]:
    runtime_overrides = dict(runtime_overrides or {})
    runtime_overrides.setdefault("mode", mode if mode != "NORMAL" else runtime_overrides.get("mode", "INCREMENTAL"))
    resolved_run_id = run_id or generate_run_id()
    workflow_started_at = iso_now()
    try:
        run_dir = prepare_output_directory(output_root, resolved_run_id)
    except Exception as exc:
        return {
            "run_id": resolved_run_id,
            "workflow_status": "FAILED",
            "error": str(exc),
            "artifact_paths": {},
        }

    recorder = StepRecorder(run_id=resolved_run_id, started_at=workflow_started_at)
    all_failures: list[IngestFailureRecord] = []
    metrics: dict[str, Any] = {
        "source_discovery_count": 0,
        "source_enabled_count": 0,
        "source_fetch_success_count": 0,
        "source_fetch_empty_count": 0,
        "source_fetch_failed_count": 0,
        "raw_feed_item_count": 0,
        "source_entry_count": 0,
        "normalized_candidate_count": 0,
        "workflow_duration_ms": 0,
    }
    source_entries: list[SourceEntry] = []
    normalized_candidates: list[NormalizedCandidate] = []
    system_failure: IngestFailureRecord | None = None
    artifact_paths = {
        "source_entries": str(run_dir / "source-entries.json"),
        "normalized_candidates": str(run_dir / "normalized-candidates.json"),
        "ingest_failures": str(run_dir / "ingest-failures.json"),
        "step_manifest": str(run_dir / "step-manifest.json"),
        "ingest_report": str(run_dir / "ingest-report.json"),
    }

    descriptor_by_source_id: dict[str, SourceDescriptor] = {}
    plans: list[SourceSyncPlan] = []
    batches: list[FetchedSourceBatch] = []
    feed_items: list[RawFeedItem] = []
    drafts: list[SourceEntryDraft] = []

    step_started = iso_now()
    descriptors, failures = discover_sources(source_config_path, runtime_overrides, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    descriptor_by_source_id = {item.source_id: item for item in descriptors}
    metrics["source_discovery_count"] = len(descriptors)
    metrics["source_enabled_count"] = len(descriptors)
    recorder.record(
        "discover_sources",
        determine_step_status(len(descriptors)),
        input_count=0,
        output_count=len(descriptors),
        failure_count=len(failures),
        started_at=step_started,
        finished_at=step_finished,
    )

    step_started = iso_now()
    plans, failures = sync_source_window(descriptors, runtime_overrides, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record(
        "sync_source_window",
        determine_step_status(len(plans)),
        input_count=len(descriptors),
        output_count=len(plans),
        failure_count=len(failures),
        started_at=step_started,
        finished_at=step_finished,
    )

    step_started = iso_now()
    batches, failures = fetch_source_items(descriptors, plans, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["source_fetch_success_count"] = sum(1 for batch in batches if batch.fetch_status == "SUCCESS_WITH_OUTPUT")
    metrics["source_fetch_empty_count"] = sum(1 for batch in batches if batch.fetch_status == "SUCCESS_EMPTY")
    metrics["source_fetch_failed_count"] = len([item for item in failures if item.step_name == "fetch_source_items"])
    recorder.record(
        "fetch_source_items",
        determine_step_status(len(batches)),
        input_count=len(plans),
        output_count=len(batches),
        failure_count=len(failures),
        started_at=step_started,
        finished_at=step_finished,
    )

    step_started = iso_now()
    feed_items, failures = convert_to_feed(batches, descriptor_by_source_id, resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    metrics["raw_feed_item_count"] = len(feed_items)
    recorder.record(
        "convert_to_feed",
        determine_step_status(len(feed_items)),
        input_count=len(batches),
        output_count=len(feed_items),
        failure_count=len(failures),
        started_at=step_started,
        finished_at=step_finished,
    )

    step_started = iso_now()
    fetched_at = batches[0].fetched_at if batches else iso_now()
    drafts, failures = map_source_fields(feed_items, descriptor_by_source_id, fetched_at=fetched_at, run_id=resolved_run_id)
    step_finished = iso_now()
    all_failures.extend(failures)
    recorder.record(
        "map_source_fields",
        determine_step_status(len(drafts)),
        input_count=len(feed_items),
        output_count=len(drafts),
        failure_count=len(failures),
        started_at=step_started,
        finished_at=step_finished,
    )

    step_started = iso_now()
    try:
        source_entries = persist_source_entries(drafts, resolved_run_id)
        persist_failures: list[IngestFailureRecord] = []
        persist_status = determine_step_status(len(source_entries))
    except Exception as exc:
        source_entries = []
        persist_failures = [
            _make_failure(
                run_id=resolved_run_id,
                step_name="persist_source_entries",
                scope_type="RUN",
                scope_id=None,
                failure_type="PERSIST_ERROR",
                message=str(exc),
                details={"error_type": type(exc).__name__},
                retryable=False,
            )
        ]
        system_failure = persist_failures[0]
        persist_status = STEP_FAILED
    step_finished = iso_now()
    all_failures.extend(persist_failures)
    metrics["source_entry_count"] = len(source_entries)
    recorder.record(
        "persist_source_entries",
        persist_status,
        input_count=len(drafts),
        output_count=len(source_entries),
        failure_count=len(persist_failures),
        started_at=step_started,
        finished_at=step_finished,
    )

    if system_failure is None:
        step_started = iso_now()
        normalized_candidates, failures = normalize_candidates(source_entries, resolved_run_id)
        step_finished = iso_now()
        all_failures.extend(failures)
        metrics["normalized_candidate_count"] = len(normalized_candidates)
        recorder.record(
            "normalize_candidates",
            determine_step_status(len(normalized_candidates)),
            input_count=len(source_entries),
            output_count=len(normalized_candidates),
            failure_count=len(failures),
            started_at=step_started,
            finished_at=step_finished,
        )
    else:
        recorder.record(
            "normalize_candidates",
            STEP_FAILED,
            input_count=len(source_entries),
            output_count=0,
            failure_count=0,
            started_at=iso_now(),
            finished_at=iso_now(),
        )

    step_started = iso_now()
    failure_ledger = record_ingest_failures(all_failures)
    step_finished = iso_now()
    recorder.record(
        "record_ingest_failures",
        determine_step_status(len(failure_ledger)),
        input_count=len(all_failures),
        output_count=len(failure_ledger),
        failure_count=0,
        started_at=step_started,
        finished_at=step_finished,
    )

    workflow_finished_at = iso_now()
    metrics["workflow_duration_ms"] = max(
        0,
        int(
            (
                _parse_runtime_datetime(workflow_finished_at) - _parse_runtime_datetime(workflow_started_at)
            ).total_seconds()
            * 1000
        ),
    )
    manifest = recorder.build_manifest(
        finished_at=workflow_finished_at,
        failures=failure_ledger,
        artifact_paths=artifact_paths,
    )
    report = build_ingest_report(
        manifest=manifest,
        failures=failure_ledger,
        metrics=metrics,
        generated_at=workflow_finished_at,
    )

    try:
        write_json(run_dir / "source-entries.json", source_entries)
        write_json(run_dir / "normalized-candidates.json", normalized_candidates)
        write_json(run_dir / "ingest-failures.json", failure_ledger)
        write_json(run_dir / "step-manifest.json", manifest)
        write_json(run_dir / "ingest-report.json", report)
    except Exception as exc:
        return {
            "run_id": resolved_run_id,
            "workflow_status": "FAILED",
            "error": str(exc),
            "artifact_paths": artifact_paths,
        }

    return {
        "run_id": resolved_run_id,
        "workflow_status": manifest.workflow_status,
        "artifact_paths": artifact_paths,
        "source_entry_count": len(source_entries),
        "normalized_candidate_count": len(normalized_candidates),
        "failure_record_count": len(failure_ledger),
    }


def _parse_runtime_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _make_failure(
    run_id: str,
    step_name: str,
    scope_type: str,
    scope_id: str | None,
    failure_type: str,
    message: str,
    details: dict[str, Any],
    retryable: bool,
) -> IngestFailureRecord:
    recorded_at = iso_now()
    return IngestFailureRecord(
        failure_id=make_failure_id(run_id, step_name, scope_type, scope_id, message),
        run_id=run_id,
        step_name=step_name,
        scope_type=scope_type,
        scope_id=scope_id,
        failure_type=failure_type,
        message=message,
        details=details,
        retryable=retryable,
        recorded_at=recorded_at,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ingest-normalize MVP pipeline.")
    parser.add_argument("--source-config-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--mode", default="NORMAL")
    parser.add_argument("--now")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--source-id", action="append", dest="source_ids")
    args = parser.parse_args(argv)
    runtime_overrides = {
        key: value
        for key, value in {
            "now": args.now,
            "since": args.since,
            "until": args.until,
            "source_ids": args.source_ids,
        }.items()
        if value not in (None, [])
    }
    result = run_pipeline(
        source_config_path=args.source_config_path,
        output_root=args.output_root,
        run_id=args.run_id,
        runtime_overrides=runtime_overrides,
        mode=args.mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["workflow_status"] != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
