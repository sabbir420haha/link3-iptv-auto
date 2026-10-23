#!/usr/bin/env python3
"""Diagnostic: check selected TV HLS sources twice from GitHub's network.

Never replaces streams, never promises Link3 or TV playback. A quick segment
check may pass while a real stream stalls minutes later. Used to identify
origin-side errors without modifying user-confirmed streams.
"""
import concurrent.futures
import datetime
import json
import time
from pathlib import Path
from update import parse_m3u, probe, segment_probe

BASE = Path(__file__).resolve().parent
PLAYLIST = BASE / "playlist.m3u"
CATALOG = BASE / "channels.json"
OUTPUT = BASE / "tv_stream_health.json"

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
    report = {
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checked": len(checks),
        "manifest_reachable": sum(bool(x["manifest_ok"]) for x in checks),
        "two_segment_checks_passed": sum(bool(x["segment_check_1"] and x["segment_check_2"]) for x in checks),
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
