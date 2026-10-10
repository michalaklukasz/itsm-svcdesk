---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 28d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
    latency:
      objective: 0.99
      threshold_seconds: 0.23
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.23"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
  alerts:
    - {alert: KbSearchAvailabilityBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchAvailabilityBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 65% - AI drafted the structure and calculations; objectives and rationale use the measured profile -->

# SLO for `GET /kb/search`

## Availability

The availability SLI counts every `/kb/search` response that is not a 5xx as good. I set a 99% objective over
28 days, giving 403.2 error-budget minutes. The measured run returned 10 upstream-related 502s out of 2,400
responses (about 0.42%); the dependency has its own non-zero failure probability, which this service cannot repair.
A 99.5% objective would leave almost no headroom for that observed variability, while 99% leaves room for ordinary
random variation without treating a sustained outage as acceptable.

## Latency

The latency SLI counts `/kb/search` responses at or below 230 ms, with a 99% objective and the same 403.2-minute
budget. The measured p50 was 38.5 ms, p95 99.7 ms, p99 220.0 ms, and p99.9 272.9 ms; `kb-index` itself measured
218.1 ms at p99. The 230 ms threshold is just above the measured p99 but below the rare slow mode, and is an
explicit histogram boundary so this SLI counts observations rather than interpolating them.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---:|---|---|---|
| KbSearchAvailabilityBurnFast | availability | 14.4 | 1h / 5m | 14.4x; the full budget would be consumed in about 46h 40m | P1 page |
| KbSearchAvailabilityBurnSlow | availability | 6 | 6h / 30m | 6x; the full budget would be consumed in about 4d 16h | P2 chat |

The fast alert requires both the one-hour and five-minute views to show a 14.4x burn, so a transient burst does not
wake someone unnecessarily; at that rate, delaying action risks spending the budget in under two days. The slower
six-hour/30-minute alert is useful for a persistent but less acute dependency failure and goes to chat rather than
the pager. Both expressions filter to the search route and compare the observed error ratio directly with the
declared burn rate.

## Buckets

The measured p99, 220 ms, falls in `(0.22, 0.225]`; that 5 ms bucket is 2.27% of the p99. The fine ladder from
180 ms to 270 ms in 5 ms steps resolves the whole ±10% band around the measurement: even the endpoint buckets
covering 198 ms and 242 ms are only 5 ms wide. The remaining boundaries retain useful coverage below and above
the slow mode without spending the 30-boundary budget on unnecessary precision elsewhere.
