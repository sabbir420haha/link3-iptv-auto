#!/usr/bin/env python3
"""Read-only sustained HLS check for Channel 24, Hungama and Zee Bangla.

Observes whether each upstream live media playlist keeps advancing over 1 min.
Does not proxy, cache, delay, change URLs, download full video, or alter M3U.
GitHub runner results are NOT measurements over the user's Link3 Wi-Fi.
"""
from __future__ import annotations

import concurrent.futures
import datetime
import hashlib
import json
import re
import time
import urllib.parse
from pathlib import Path

from update import fetch_hls_bytes, parse_m3u

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "playlist.m3u"
OUTPUT = ROOT / "three_playback_health.json"
NAMES = ("Channel 24", "Hungama", "Zee Bangla")
INTERVAL_SECONDS = 8
SAMPLES = 9  # ~64 seconds, 3 channels in parallel.


def media_snapshot(url):
    """Fetch only HLS text, up to three levels, never download full segments."""
    current = url
    for _ in range(4):
        data, _ = fetch_hls_bytes(current, 62000, 9)
        text = data.decode("utf-8-sig", errors="replace")
        if "#EXTM3U" not in text[:500]:
            raise ValueError("HLS manifest unavailable to GitHub")
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if "#EXT-X-STREAM-INF" in text:
            options = []
            for idx, line in enumerate(lines[:-1]):
                if (line.startswith("#EXT-X-STREAM-INF") and
                        not lines[idx+1].startswith("#")):
                    height = re.search(r"RESOLUTION=\d+x(\d+)", line)
                    bw = re.search(r"BANDWIDTH=(\d+)", line)
                    options.append((int(height.group(1)) if height else 0,
                                    int(bw.group(1)) if bw else 0,
                                    urllib.parse.urljoin(current, lines[idx+1])))
            if not options:
                raise ValueError("No HLS variant URI")
            # Prefer <=720p to match mobile playback where possible.
            candidates = [x for x in options if x[0] <= 720] or options
            current = max(candidates, key=lambda x: (x[0], x[1]))[2]
            continue
        segments = [x for x in lines if not x.startswith("#")]
        if "#EXTINF" not in text or not segments:
            raise ValueError("No HLS media segments")
        match_seq = re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)", text)
        match_dur = re.search(r"#EXT-X-TARGETDURATION:(\d+)", text)
        if "#EXT-X-ENDLIST" in text:
            raise ValueError("VOD/ended HLS manifest, not live")
        last_uri = urllib.parse.urljoin(current, segments[-1])
        return {
            "seq": (int(match_seq.group(1)) + len(segments) - 1)
                   if match_seq else None,
            "latest_segment_fingerprint": hashlib.sha256(
                last_uri.encode()).hexdigest()[:16],
            "target_duration_seconds": int(match_dur.group(1))
                                       if match_dur else None,
            "media_host": urllib.parse.urlsplit(current).hostname or "",
        }
    raise ValueError("Nested HLS variants exceed limit")


def measure(entry):
    start = time.monotonic()
    checks = []
    for n in range(SAMPLES):
        if n:
            deadline = start + n * INTERVAL_SECONDS
            time.sleep(max(0.0, deadline - time.monotonic()))
        try:
            snap = media_snapshot(entry["url"])
            checks.append({"at_seconds": round(time.monotonic()-start, 1),
                           **snap, "ok": True})
        except Exception as exc:
            checks.append({"at_seconds": round(time.monotonic()-start, 1),
                           "ok": False,
                           "error": (type(exc).__name__ + ": " +
                                     str(exc))[:120]})
    good = [x for x in checks if x["ok"]]
    changes = 0
    longest_gap = 0.0
    previous = None
    for check in good:
        if previous is not None:
            moved = (check["latest_segment_fingerprint"] !=
                     previous["latest_segment_fingerprint"])
            if (check["seq"] is not None and previous["seq"] is not None
                    and check["seq"] > previous["seq"]):
                moved = True
            if moved:
                changes += 1
            longest_gap = max(longest_gap,
                              check["at_seconds"]-previous["at_seconds"]
                              if not moved else 0.0)
        previous = check
    manifest_progress = changes > 0
    status = ("manifest_unreachable" if not good else
              "no_new_segments" if not manifest_progress else
              "intermittent_errors" if len(good) != len(checks) else
              "advancing_on_github")
    return {
        "name": entry["name"],
        "status": status,
        "successful_polls": len(good),
        "attempted_polls": SAMPLES,
        "observed_changes": changes,
        "max_stalled_observation_seconds": round(longest_gap, 1),
        "target_duration_seconds": good[-1]["target_duration_seconds"] if good else None,
        "media_host": good[-1]["media_host"] if good else None,
        "samples": checks,
        "note": "GitHub vantage point only; no guarantee of IPTV Pro or Link3 playback",
    }


def main():
    entries = {e["name"]: e for e in
               parse_m3u(SOURCE.read_text(encoding="utf-8"))}
    if any(n not in entries for n in NAMES):
        raise RuntimeError("Some 3-channel test feeds are missing from playlist")
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(measure, [entries[n] for n in NAMES]))
    report = {
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "GitHub network ONLY; not Link3/mobile/TV",
        "relay_active": False,
        "changed_playlist": False,
        "sample_seconds": (SAMPLES-1)*INTERVAL_SECONDS,
        "streams": results,
        "warning": "Live playlist sequence progress does not prove client decode "
                   "or uninterrupted segment delivery. Does not cache/relay streams.",
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",
                      encoding="utf-8")
    for item in results:
        print(item["name"], item["status"], "advanced",
              item["observed_changes"], "times /", SAMPLES,
              "observations; no channel URL was modified")


if __name__ == "__main__":
    main()
