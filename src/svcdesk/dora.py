# ai-generated: 90% - generated from the published METRIC-SPEC.md and validated against its practice fixture

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple


class DORAValidationError(ValueError):
    pass


_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})$")
_UTC = timezone.utc
_SECOND = Decimal("1")
_SIX_PLACES = Decimal("0.000001")


def _instant(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not _RFC3339.fullmatch(value):
        raise DORAValidationError("%s must be an RFC 3339 instant with an offset" % field)
    normalized = value[:-1] + "+00:00" if value[-1:] in {"Z", "z"} else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DORAValidationError("%s must be an RFC 3339 instant with an offset" % field) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DORAValidationError("%s must include an offset" % field)
    return parsed.astimezone(_UTC)


def _text(value: Any, field: str, maximum: Optional[int] = None) -> str:
    if not isinstance(value, str) or not value or (maximum is not None and len(value) > maximum):
        raise DORAValidationError("%s must be a non-empty string" % field)
    return value


def _string_list(value: Any, field: str) -> List[str]:
    if not isinstance(value, list):
        raise DORAValidationError("%s must be an array" % field)
    return [_text(item, field) for item in value]


def _normalize_events(raw_events: List[Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    events: List[Dict[str, Any]] = []
    seen_event_ids = set()
    commits: Dict[str, Dict[str, Any]] = {}
    deployments: Dict[str, Dict[str, Any]] = {}
    incidents: Dict[str, Dict[str, Any]] = {}
    incident_phases = set()

    for raw in raw_events:
        if not isinstance(raw, dict):
            raise DORAValidationError("each event must be an object")
        event_id = _text(raw.get("event_id"), "event_id", 64)
        if event_id in seen_event_ids:
            continue
        seen_event_ids.add(event_id)

        event_type = raw.get("type")
        if event_type not in {"commit", "deployment", "incident"}:
            raise DORAValidationError("event type is invalid")
        event = dict(raw)
        event["_at"] = _instant(raw.get("at"), "event.at")

        if event_type == "commit":
            sha = _text(raw.get("sha"), "commit.sha")
            if sha in commits:
                raise DORAValidationError("commit sha must be unique")
            event["sha"] = sha
            event["branch"] = _text(raw.get("branch"), "commit.branch")
            reverts = raw.get("reverts")
            change_id = raw.get("change_id")
            if reverts is None:
                event["change_id"] = _text(change_id, "commit.change_id")
            else:
                event["reverts"] = _text(reverts, "commit.reverts")
                if change_id is not None:
                    raise DORAValidationError("a revert commit must have a null change_id")
                event["change_id"] = None
            commits[sha] = event

        elif event_type == "deployment":
            deployment_id = _text(raw.get("deployment_id"), "deployment.deployment_id")
            if deployment_id in deployments:
                raise DORAValidationError("deployment_id must be unique")
            event["deployment_id"] = deployment_id
            event["environment"] = _text(raw.get("environment"), "deployment.environment")
            if raw.get("outcome") not in {"success", "failure"}:
                raise DORAValidationError("deployment.outcome is invalid")
            event["commits"] = _string_list(raw.get("commits"), "deployment.commits")
            if not isinstance(raw.get("unplanned"), bool):
                raise DORAValidationError("deployment.unplanned must be a boolean")
            event["unplanned"] = raw["unplanned"]
            caused_by = raw.get("caused_by")
            if caused_by is not None:
                caused_by = _text(caused_by, "deployment.caused_by")
            event["caused_by"] = caused_by
            deployments[deployment_id] = event

        else:
            incident_id = _text(raw.get("incident_id"), "incident.incident_id")
            phase = raw.get("phase")
            if phase not in {"opened", "resolved"}:
                raise DORAValidationError("incident.phase is invalid")
            phase_key = (incident_id, phase)
            if phase_key in incident_phases:
                raise DORAValidationError("an incident may have only one event per phase")
            incident_phases.add(phase_key)
            event["incident_id"] = incident_id
            event["phase"] = phase
            event["deployments"] = _string_list(raw.get("deployments"), "incident.deployments")
            incident = incidents.setdefault(incident_id, {"opened": None, "resolved": None})
            incident[phase] = event

        events.append(event)

    for commit in commits.values():
        parent_sha = commit.get("reverts")
        if parent_sha is not None and parent_sha not in commits:
            raise DORAValidationError("reverts references an unknown sha")

    for deployment in deployments.values():
        if any(sha not in commits for sha in deployment["commits"]):
            raise DORAValidationError("deployment commits references an unknown sha")
        caused_by = deployment["caused_by"]
        if caused_by is not None and caused_by not in incidents:
            raise DORAValidationError("caused_by references an unknown incident")

    for incident in incidents.values():
        if incident["resolved"] is not None and incident["opened"] is None:
            raise DORAValidationError("a resolved incident must also be opened")
        for phase_event in (incident["opened"], incident["resolved"]):
            if phase_event is not None and any(deployment_id not in deployments for deployment_id in phase_event["deployments"]):
                raise DORAValidationError("incident deployments references an unknown deployment")

    return events, commits, deployments, incidents


def _change_map(commits: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    resolved: Dict[str, str] = {}

    def resolve(sha: str, visiting: set) -> str:
        if sha in resolved:
            return resolved[sha]
        if sha in visiting:
            raise DORAValidationError("revert chain contains a cycle")
        commit = commits[sha]
        parent = commit.get("reverts")
        if parent is None:
            change_id = commit["change_id"]
        else:
            change_id = resolve(parent, visiting | {sha})
        resolved[sha] = change_id
        return change_id

    for sha in commits:
        resolve(sha, set())
    return resolved


def _seconds_between(later: datetime, earlier: datetime) -> Decimal:
    delta = later - earlier
    seconds = delta.days * 86400 + delta.seconds
    return Decimal(seconds) + Decimal(delta.microseconds) / Decimal(1000000)


def _duration(value: Decimal) -> int:
    return int(max(value, Decimal(0)).quantize(_SECOND, rounding=ROUND_HALF_UP))


def _median(values: List[Decimal]) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        value = ordered[middle]
    else:
        value = (ordered[middle - 1] + ordered[middle]) / Decimal(2)
    return _duration(value)


def _ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    value = (Decimal(numerator) / Decimal(denominator)).quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)
    return float(value)


def _format_instant(value: datetime) -> str:
    value = value.astimezone(_UTC)
    if value.microsecond:
        return value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _overlap_count(incidents: Dict[str, Dict[str, Any]], window_to: datetime) -> int:
    intervals = []
    for incident_id, phases in incidents.items():
        opened = phases["opened"]
        if opened is None:
            continue
        resolved = phases["resolved"]
        end = resolved["_at"] if resolved is not None else window_to
        intervals.append((incident_id, opened["_at"], end))

    overlaps = 0
    for index, (_, first_start, first_end) in enumerate(intervals):
        for _, second_start, second_end in intervals[index + 1:]:
            if first_start < second_end and second_start < first_end:
                overlaps += 1
    return overlaps


def calculate_metrics(body: Any) -> Dict[str, Any]:
    if not isinstance(body, dict):
        raise DORAValidationError("request body must be an object")
    window = body.get("window")
    if not isinstance(window, dict):
        raise DORAValidationError("window is required")
    window_from = _instant(window.get("from"), "window.from")
    window_to = _instant(window.get("to"), "window.to")
    if window_to <= window_from:
        raise DORAValidationError("window.to must be after window.from")
    raw_events = body.get("events")
    if not isinstance(raw_events, list):
        raise DORAValidationError("events must be an array")

    events, commits, deployments, incidents = _normalize_events(raw_events)
    change_ids = _change_map(commits)
    first_commit_by_change: Dict[str, datetime] = {}
    for sha, change_id in change_ids.items():
        instant = commits[sha]["_at"]
        if change_id not in first_commit_by_change or instant < first_commit_by_change[change_id]:
            first_commit_by_change[change_id] = instant

    production = [
        event for event in events
        if event["type"] == "deployment"
        and event["environment"] == "production"
        and window_from <= event["_at"] < window_to
    ]
    production.sort(key=lambda event: (event["_at"], event["deployment_id"].encode("utf-8"), event["event_id"].encode("utf-8")))
    successful = [event for event in production if event["outcome"] == "success"]
    failed = [event for event in production if event["outcome"] == "failure"]

    lead_values: List[Decimal] = []
    seen_lead_shas = set()
    negative_lead_pairs = 0
    for deployment in successful:
        for sha in deployment["commits"]:
            if sha in seen_lead_shas:
                continue
            seen_lead_shas.add(sha)
            value = _seconds_between(deployment["_at"], commits[sha]["_at"])
            if value < 0:
                negative_lead_pairs += 1
                value = Decimal(0)
            lead_values.append(value)

    first_incident_by_deployment: Dict[str, Tuple[datetime, str, Optional[datetime]]] = {}
    for incident_id, phases in incidents.items():
        opened = phases["opened"]
        if opened is None:
            continue
        resolved = phases["resolved"]
        resolved_at = resolved["_at"] if resolved is not None else None
        for deployment_id in opened["deployments"]:
            candidate = (opened["_at"], incident_id, resolved_at)
            previous = first_incident_by_deployment.get(deployment_id)
            if previous is None or (candidate[0], candidate[1].encode("utf-8")) < (previous[0], previous[1].encode("utf-8")):
                first_incident_by_deployment[deployment_id] = candidate

    recovery_values: List[Decimal] = []
    open_failures = 0
    for deployment in failed:
        covering = first_incident_by_deployment.get(deployment["deployment_id"])
        if covering is None or covering[2] is None:
            open_failures += 1
            continue
        recovery_values.append(max(Decimal(0), _seconds_between(covering[2], deployment["_at"])))

    delivered_at_by_change: Dict[str, datetime] = {}
    for deployment in successful:
        changes_in_deployment = {change_ids[sha] for sha in deployment["commits"]}
        for change_id in changes_in_deployment:
            if change_id not in delivered_at_by_change:
                delivered_at_by_change[change_id] = deployment["_at"]

    true_lead_values = [
        max(Decimal(0), _seconds_between(delivered_at, first_commit_by_change[change_id]))
        for change_id, delivered_at in delivered_at_by_change.items()
    ]

    deployment_count = len(production)
    window_seconds = _seconds_between(window_to, window_from)
    frequency = (Decimal(deployment_count) * Decimal(86400) / window_seconds).quantize(_SIX_PLACES, rounding=ROUND_HALF_UP)
    commits_in_production = {
        sha
        for deployment in production
        for sha in deployment["commits"]
    }
    rework_count = sum(1 for deployment in production if deployment["unplanned"] and deployment["caused_by"] is not None)

    return {
        "spec_version": "1.0.0",
        "window": {"from": _format_instant(window_from), "to": _format_instant(window_to)},
        "deployment_frequency_per_day": float(frequency),
        "change_lead_time_seconds_p50": _median(lead_values),
        "failed_deployment_recovery_time_seconds_p50": _median(recovery_values),
        "change_fail_rate": _ratio(len(failed), deployment_count),
        "deployment_rework_rate": _ratio(rework_count, deployment_count),
        "counts": {
            "deployments": deployment_count,
            "successful_deployments": len(successful),
            "failed_deployments": len(failed),
            "recovered_failures": len(recovery_values),
            "open_failures": open_failures,
            "rework_deployments": rework_count,
            "lead_time_pairs": len(lead_values),
            "changes": len(set(change_ids.values())),
        },
        "anomalies": {
            "negative_lead_time_pairs": negative_lead_pairs,
            "deployments_without_commits": sum(1 for deployment in production if not deployment["commits"]),
            "commits_never_on_main": sum(1 for sha in commits_in_production if commits[sha]["branch"] != "main"),
            "revert_chains_collapsed": sum(1 for commit in commits.values() if commit.get("reverts") is not None),
            "overlapping_incident_pairs": _overlap_count(incidents, window_to),
        },
        "ground_truth": {
            "changes_delivered": len(delivered_at_by_change),
            "true_change_lead_time_seconds_p50": _median(true_lead_values),
        },
    }