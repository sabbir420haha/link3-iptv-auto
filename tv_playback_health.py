#!/usr/bin/env python3
"""Diagnostic: check selected TV HLS sources twice from GitHub's network.

Never replaces streams, never promises Link3 or TV playback. A quick segment
check may pass while a real stream stalls minutes later. Used to identify
origin-side errors without modifying user-confirmed streams.
"""
import concurrent.futures
import datetime
import json
import re
import time
import hashlib
import urllib.parse
from pathlib import Path
from update import parse_m3u, probe, segment_probe, fetch_hls_bytes

BASE = Path(__file__).resolve().parent
PLAYLIST = BASE / "playlist.m3u"
CATALOG = BASE / "channels.json"
OUTPUT = BASE / "tv_stream_health.json"

# Distinguish source playlist stalling from a player/decoder that stops
# producing frames while its clock continues. These are strictly observations.
PROGRESS_CHANNELS = {
    "Channel 24", "Hungama", "Zee Bangla", "Zee Bangla HD",
    "Jamuna TV", "Somoy TV", "Discovery Bangla",
    "Nat Geo HD Bangla", "Independent TV", "Sony Ten 1 HD",
}


def hls_window(url):
    """Identify the newest media segment WITHOUT relaying its contents.

    Resolve master playlists read-only. Return only opaque hashes and
    sequence numbers so public diagnostics contain no signed segment links.
    """
    current = url
    for _ in range(4):
        raw, _ = fetch_hls_bytes(current, 50000, 9)
        body = raw.decode("utf-8-sig", "replace")
        if "#EXTM3U" not in body[:500]:
            raise ValueError("No HLS playlist from GitHub runner")
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        if "#EXT-X-STREAM-INF" in body:
            variants = []
            for i, line in enumerate(lines[:-1]):
                if line.startswith("#EXT-X-STREAM-INF") and not lines[i+1].startswith("#"):
                    height = re.search(r"RESOLUTION=\d+x(\d+)", line)
                    variants.append((int(height.group(1)) if height else 0,
                                     urllib.parse.urljoin(current, lines[i+1])))
            if not variants:
                raise ValueError("No media rendition in master")
            current = max(variants, key=lambda x: x[0])[1]
            continue
        if "#EXTINF" not in body:
            raise ValueError("No HLS media segment lines")
        last = [x for x in lines if not x.startswith("#")]
        if not last:
            raise ValueError("No media segment URI")
        seq = re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)", body)
        last_uri = urllib.parse.urljoin(current, last[-1])
        return {
            "first_sequence": int(seq.group(1)) if seq else None,
            "last_sequence": (int(seq.group(1)) + len(last) - 1) if seq else None,
            "segment_hash": hashlib.sha256(last_uri.encode()).hexdigest()[:16],
            "has_endlist": "#EXT-X-ENDLIST" in body,
        }
    raise ValueError("Nested HLS master depth exceeded")


def live_progress_check(entry):
    started = time.monotonic()
    try:
        first = hls_window(entry["url"])
        time.sleep(18)  # Most live sources publish a new 2-10s HLS segment.
        second = hls_window(entry["url"])
        advanced = ((first["last_sequence"] is not None and
                     second["last_sequence"] is not None and
                     second["last_sequence"] > first["last_sequence"]) or
                    first["segment_hash"] != second["segment_hash"])
        return {
            "name": entry["name"],
            "status": "advanced" if advanced else
                      "ended" if first["has_endlist"] else "not_advanced",
            "first_sequence": first["last_sequence"],
            "second_sequence": second["last_sequence"],
            "elapsed_seconds": round(time.monotonic()-started, 1),
            "note": "Source manifest progress only; not a test of IPTV Pro decoder",
        }
    except Exception as exc:
        return {
            "name": entry["name"], "status": "unreachable_from_github",
            "error": (type(exc).__name__ + ": " + str(exc))[:120],
            "elapsed_seconds": round(time.monotonic()-started, 1),
        }


def check(entry):
    name, url = entry["name"], entry["url"]
    start = time.monotonic()
    try:
        manifest = bool(probe(url))
        # Two independent video-segment checks can catch short source stalls.
        first = bool(segment_probe(url)) if manifest else False
        time.sleep(2)
        second = bool(segment_probe(url)) if manifest else False
        error = None
    except Exception as exc:
        manifest, first, second = False, False, False
        error = str(exc)[:180]
    return {
        "name": name,
        "host": __import__("urllib.parse", fromlist=["urlsplit"]).urlsplit(url).hostname,
        "manifest_ok": manifest,
        "segment_check_1": first,
        "segment_check_2": second,
        "elapsed_seconds": round(time.monotonic() - start, 1),
        "error": error,
        "scope": "GitHub Actions runner; NOT the user's Link3 / TV connection",
    }

def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    pinned = {x["name"] for x in catalog if x.get("locked")}
    playlist = parse_m3u(PLAYLIST.read_text(encoding="utf-8"))
    target = [x for x in playlist if x["name"] in pinned or x["name"] in {
        "Zee Bangla", "Zee Bangla HD", "Somoy TV", "Jamuna TV",
        "ATN Bangla", "BanglaVision", "Cartoon Network",
        "Discovery Kids", "NTV", "DBC News"
    }]
    # Complete each source independently; failed sources must never break build.
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        checks = list(pool.map(check, target))
    # Observe actual LIVE HLS sequence advancement across one 18s window on
    # diverse origins. A stuck player and stalled upstream need different fixes.
    progress_targets = [x for x in target if x["name"] in PROGRESS_CHANNELS]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        progress_checks = list(pool.map(live_progress_check, progress_targets))
    report = {
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checked": len(checks),
        "manifest_reachable": sum(bool(x["manifest_ok"]) for x in checks),
        "two_segment_checks_passed": sum(bool(x["segment_check_1"] and x["segment_check_2"]) for x in checks),
        "live_progress_window_seconds": 18,
        "live_progress_checks": progress_checks,
        "live_progress_advanced": sum(x["status"] == "advanced" for x in progress_checks),
        "note": (
            "This tests from GitHub, not Link3. A result is a snapshot of HLS "
            "availability, not proof of continuous TV playback or zero buffering. "
            "No channel URLs are modified by this diagnostic."
        ),
        "streams": checks,
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("TV remote HLS health:", report["two_segment_checks_passed"], "/", len(checks),
          "two video checks passed; no streams changed.")

if __name__ == "__main__":
    main()
