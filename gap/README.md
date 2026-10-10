<!-- ai-generated: 65% - AI drafted the explanation from the measured client and server percentiles -->

# Client/server latency gap

The downstream Toxiproxy latency toxic was configured for 100 ms with 10 ms jitter and toxicity 1.0. In the
60-second open-loop run, the client p99 was 334.6 ms while the service's own request histogram reported 225.2 ms,
leaving a measured gap of 109.4 ms. This is expected: the server histogram starts when the application receives a
request and stops after its handler has built the response, so it includes the `kb-index` call but not the later
delay Toxiproxy adds on the response path to the client. The client p99 also includes scheduling correction and
network transit, while the server p99 is interpolated from finite histogram buckets. The toxic's 100 ms base plus
jitter accounts for most of the difference; the remainder is normal variation between two p99 samples from
different populations, not an extra duration to subtract from each individual request. A repeated checker run uses
the same toxic but a shorter sample, so the exact gap can vary while its dominant cause remains downstream delay.
