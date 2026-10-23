# NUHASH IPTV — 15-second delayed HLS relay (experimental)

This is an **isolated test**, NOT a replacement for \`playlist.m3u\`. It is a
small RAM-based HLS timeshift relay that polls three public unencrypted feeds:
Channel 24, Hungama and Zee Bangla. It starts fetching video even before a
client requests it and serves content approximately 15 seconds behind the
freshest fetched source segments.

A delayed time-shift can mask **brief upstream jitter**, but cannot guarantee
bufferless playback. If the provider blocks the hosting server or goes down for
more than the reserve, the viewer will still stall. This is **server buffering**,
not an IPTV Pro app setting. It adds start-up delay and recurring hosting cost.

## Status

Code only: **not deployed**. Railway connection, service deployment, and
real-world IPTV Pro tests are required before publishing a usable relay URL.

## Deploy only after hosting is explicitly connected

Build from the **repo root** with \`Dockerfile.relay\` as the Dockerfile path.
The app uses Railway's supplied \`PORT\`. Configure:

- \`RELAY_TOKEN\`: 24+ random URL-safe characters. Treat as a password; never
  commit the value. Keep the generated link private.
- \`HLS_DELAY_SECONDS\`: \`15\` (default; 8–30 allowed).

A basic readiness endpoint is \`/health\`. The user-specific IPTV Pro **test**
playlist is \`https://<your-service-host>/t/<secret>/playlist.m3u\`. It contains
only the three pilot channels. Do not set it as the main playlist.

The prefetcher stores at most ~40 MB of segments per channel and discards data
after 85 seconds. It refuses HLS manifests using encryption, DRM declarations,
or fMP4 init maps; nothing bypasses permissions or authentication.

## Operational limits

The service has no disk persistence or horizontal-sharing: running multiple
instances independently can waste bandwidth and produce inconsistent sessions.
Start with **one always-on instance**, and verify provider permissions to relay
each stream. Some public hosts block cloud datacenter IPs. A pass from GitHub
does not prove playback through Link3 or Railway.

Only expand the selected channels or swap the main M3U after the separate
IPTV Pro test actually works. If Railway is disconnected or no always-on
hosting is available, this code alone does not buffer anything.
