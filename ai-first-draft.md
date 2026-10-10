---
lab3_first_draft:
  source: ai
  tool: "Copilot SDK assistant in VS Code, 10 October 2026"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: refuted
  evidence: {p99_seconds: 0.22, bucket: [0.1, 0.25], relative_width: 0.682}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.22, bucket: [0.04, 0.5], relative_width: 2.091}
---
<!-- ai-generated: 75% - AI wrote the recorded first draft; verdict arithmetic and evaluation use the measured run -->

# The assistant's first draft, and two verdicts

## Prompt

For a FastAPI service exposing GET /kb/search that proxies a knowledge-base index with unknown latency and occasional upstream errors, recommend a Prometheus histogram bucket ladder in seconds and one alert rule for an availability SLO. State your assumptions and give the PromQL expression.

## Answer

With no latency measurements, start with Python prometheus_client's default bucket boundaries in seconds: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]. They cover several orders of magnitude and can be tuned after collecting production data. For a 99% availability objective over a 30-day window, alert when the fraction of failed /kb/search requests over the last hour exceeds 14.4 × (1 - 0.99), and require that condition for 5 minutes: sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search", http_response_status_code=~"5.."}[1h])) / sum(rate(http_server_request_duration_seconds_count{http_route="/kb/search"}[1h])) > 14.4 * (1 - 0.99). Add a shorter confirming window before paging, and validate the threshold against the dependency's measured error rate.

## Verdict on the draft ladder

My measured p99 was 0.220 seconds. The assistant's bucket is `(0.1, 0.25]`, so its width is
`(0.25 - 0.1) / 0.220 = 68.2%` of p99. It does not meet the 20% resolution requirement; within that bucket,
histogram interpolation could place the reported quantile anywhere across a 150 ms interval. Verdict: **refuted**.

## The draft alert rule

The draft correctly framed availability as a 5xx ratio and used a recognizable 14.4 burn rate, but its single
long-window condition has no short-window confirmation and is not a complete page policy. I retained the direct
error-ratio calculation and burn-rate threshold, then added a short window and a slower chat alert so brief bursts
do not page while sustained deterioration remains visible.

## Verdict on the instructor's flawed ladder

At the same measured p99 of 0.220 seconds, the flawed ladder's bucket is `(0.04, 0.5]`. Its width is
`(0.5 - 0.04) / 0.220 = 209.1%` of p99, allowing an interpolated quantile anywhere across 460 ms. Its fine
boundaries are spent below the p99 while its slow-latency bucket is too coarse. Verdict: **refuted**.
