# ai-generated: 85% - generated as HTTP integration coverage for the Lab 2 published API contract

import json
import os
import urllib.error
import urllib.request


BASE_URL = os.environ.get("SVCDESK_URL", "http://127.0.0.1:8080")
WINDOW = {"from": "2026-09-01T00:00:00Z", "to": "2026-09-02T00:00:00Z"}


def request_json(path, method="GET", body=None, headers=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = dict(headers or {})
    if data is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE_URL + path, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def sample_events():
    return [
        {"event_id": "commit-1", "type": "commit", "at": "2026-09-01T00:00:00Z", "sha": "sha-1", "branch": "release", "change_id": "change-1", "reverts": None},
        {"event_id": "deploy-1", "type": "deployment", "at": "2026-09-01T00:10:00Z", "deployment_id": "deploy-1", "environment": "production", "outcome": "success", "commits": ["sha-1"], "unplanned": False, "caused_by": None},
    ]


def metrics(events=None, window=None):
    return request_json("/dora/metrics", "POST", {"window": window or WINDOW, "events": sample_events() if events is None else events})


def test_health_endpoint_is_ready():
    status, body = request_json("/health")
    assert status == 200
    assert body["status"] == "ok"


def test_metrics_calculate_all_five_values():
    status, body = metrics()
    assert status == 200
    assert body["spec_version"] == "1.0.0"
    assert body["deployment_frequency_per_day"] == 1 / 1  # one deployment over one day
    assert body["change_lead_time_seconds_p50"] == 600
    assert body["failed_deployment_recovery_time_seconds_p50"] is None
    assert body["change_fail_rate"] == 0.0
    assert body["deployment_rework_rate"] == 0.0


def test_metrics_are_repeatable():
    first = metrics()[1]
    second = metrics()[1]
    assert first == second


def test_metrics_do_not_depend_on_event_order():
    events = sample_events()
    assert metrics(events)[1] == metrics(list(reversed(events)))[1]


def test_duplicate_event_id_uses_first_occurrence():
    events = sample_events()
    duplicate = dict(events[1], at="2026-09-01T00:30:00Z")
    assert metrics(events + [duplicate])[1] == metrics(events)[1]


def test_empty_log_returns_zero_counts_and_null_rates():
    status, body = metrics(events=[])
    assert status == 200
    assert body["deployment_frequency_per_day"] == 0.0
    assert body["change_lead_time_seconds_p50"] is None
    assert body["failed_deployment_recovery_time_seconds_p50"] is None
    assert body["change_fail_rate"] is None
    assert body["deployment_rework_rate"] is None
    assert all(value == 0 for value in body["counts"].values())
    assert all(value == 0 for value in body["anomalies"].values())


def test_invalid_window_is_rejected_with_error_object():
    status, body = metrics(window={"from": WINDOW["to"], "to": WINDOW["from"]})
    assert status in (400, 422)
    assert "error" in body


def test_missing_window_is_rejected():
    status, body = request_json("/dora/metrics", "POST", {"events": []})
    assert status in (400, 422)
    assert "error" in body


def test_non_array_events_are_rejected():
    status, body = request_json("/dora/metrics", "POST", {"window": WINDOW, "events": {}})
    assert status in (400, 422)
    assert "error" in body


def test_unknown_revert_sha_is_rejected():
    events = [{"event_id": "commit-1", "type": "commit", "at": "2026-09-01T00:00:00Z", "sha": "sha-1", "branch": "main", "change_id": None, "reverts": "missing"}]
    status, body = metrics(events)
    assert status in (400, 422)
    assert "error" in body


def test_ticket_events_returns_sorted_lifecycle_array():
    status, body = request_json("/dora/ticket-events")
    assert status == 200
    assert isinstance(body, list)
    assert body == sorted(body, key=lambda event: (event["at"], event["ticket_id"]))


def test_created_ticket_is_exported_to_lifecycle_stream():
    status, ticket = request_json("/tickets", "POST", {
        "title": "Lab 2 integration test",
        "reporter": {"name": "Test runner"},
        "impact": 2,
        "urgency": 2,
    }, {"X-Test-Clock": "2026-09-01T10:00:00Z"})
    assert status == 201
    stream_status, events = request_json("/dora/ticket-events")
    assert stream_status == 200
    assert any(event["ticket_id"] == ticket["id"] and event["phase"] == "created" and event["state"] == "new" for event in events)