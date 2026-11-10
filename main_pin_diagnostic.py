#!/usr/bin/env python3
"""Read-only diagnostic for the nine currently failing Main playlist pins.

This script never changes playlist.m3u or channels.json. It checks DNS,
HTTP response/redirect, HLS manifest, real media segments and live progress
from GitHub Actions. It does not bypass DRM, credentials, cookies, tokens,
geo restrictions or provider access controls. A GitHub pass is not Link3 proof.
"""
import concurrent.futures
import datetime
import hashlib
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from update import allowed, fetch_hls_bytes, parse_m3u, probe, segment_probe
from tv_playback_health import hls_window

BASE = Path(__file__).resolve().parent
PLAYLIST = BASE / "playlist.m3u"
OUTPUT = BASE / "main_pin_health.json"
TARGETS = (
    "Duronto TV", "Hungama Backup", "Sony MAX HD", "Nat Geo HD Bangla",
    "Nick Bangla", "Sony Aath", "Sony Ten 1 HD", "Sony Ten 3 HD",
    "Independent TV",
)
HEADERS = {"User-Agent": "Mozilla/5.0 (Link3-Main-Diagnostic/1.0)"}


def safe_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return "HTTP_" + str(exc.code)
    reason = getattr(exc, "reason", None)
    if isinstance(reason, socket.gaierror):
        return "DNS_" + str(reason.errno)
    if reason:
        return type(reason).__name__ + ":" + str(reason)[:90]
    return type(exc).__name__ + ":" + str(exc)[:110]


def http_probe(url):
    host = urllib.parse.urlsplit(url).hostname or ""
    out = {"host": host, "url_sha256": hashlib.sha256(url.encode()).hexdigest()[:16]}
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        out["dns_ok"] = True
        out["dns_ips"] = sorted({x[4][0] for x in infos})[:6]
    except Exception as exc:
        out["dns_ok"] = False
        out["dns_error"] = safe_error(exc)
        out["http_ok"] = False
        out["http_error"] = "DNS_LOOKUP_FAILED"
        return out

    try:
        request = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-8191"})
        with urllib.request.urlopen(request, timeout=12) as response:
            body = response.read(8192)
            final = urllib.parse.urlsplit(response.geturl())
            out.update({
                "http_ok": response.status in (200, 206),
                "http_status": response.status,
                "final_host": final.hostname,
                "content_type": response.headers.get("Content-Type", "")[:100],
                "bytes_read": len(body),
                "body_kind": (
                    "HLS_MANIFEST" if b"#EXTM3U" in body[:500]
                    else "HTML" if body.lstrip().lower().startswith((b"<html", b"<!doctype"))
                    else "MPEG_TS" if len(body) >= 377 and body[0] == 0x47 and body[188] == 0x47
                    else "OTHER"
                ),
            })
    except Exception as exc:
        out["http_ok"] = False
        out["http_error"] = safe_error(exc)
    return out


def check(entry):
    name, url = entry["name"], entry["url"]
    started = time.monotonic()
    result = {"name": name, **http_probe(url)}
    result["manifest_ok"] = bool(probe(url)) if allowed(url, locked=True) else False
    result["segment_check_1"] = bool(segment_probe(url)) if result["manifest_ok"] else False
    time.sleep(2)
    result["segment_check_2"] = bool(segment_probe(url)) if result["manifest_ok"] else False
    result["elapsed_seconds"] = round(time.monotonic() - started, 1)
    result["source_note"] = "Current Main URL, read-only check from GitHub runner; not Link3"
    return result


def progress(entry):
    name, url = entry["name"], entry["url"]
    start = time.monotonic()
    try:
        first = hls_window(url)
        time.sleep(18)
        second = hls_window(url)
        advanced = (
            first.get("last_sequence") is not None
            and second.get("last_sequence") is not None
            and second["last_sequence"] > first["last_sequence"]
        ) or first["segment_hash"] != second["segment_hash"]
        status = "ADVANCED" if advanced else "NOT_ADVANCED"
        return {
            "name": name, "status": status,
            "first_sequence": first.get("last_sequence"),
            "second_sequence": second.get("last_sequence"),
            "elapsed_seconds": round(time.monotonic() - start, 1),
        }
    except Exception as exc:
        return {
            "name": name, "status": "UNREACHABLE_FROM_GITHUB",
            "error": safe_error(exc),
            "elapsed_seconds": round(time.monotonic() - start, 1),
        }


def main():
    playlist = parse_m3u(PLAYLIST.read_text(encoding="utf-8"))
    by_name = {x["name"]: x for x in playlist}
    missing = [name for name in TARGETS if name not in by_name]
    entries = [by_name[name] for name in TARGETS if name in by_name]
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
        checks = list(pool.map(check, entries))
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
        progress_checks = list(pool.map(progress, entries))
    report = {
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "GitHub runner only; not Link3 Broadband or IPTV Pro",
        "main_playlist_changed": False,
        "channels_expected": list(TARGETS),
        "missing_from_main": missing,
        "summary": {
            "channels_checked": len(checks),
            "dns_pass": sum(x.get("dns_ok", False) for x in checks),
            "http_pass": sum(x.get("http_ok", False) for x in checks),
            "manifest_pass": sum(x.get("manifest_ok", False) for x in checks),
            "two_segment_pass": sum(x.get("segment_check_1", False) and x.get("segment_check_2", False) for x in checks),
            "live_progress_pass": sum(x.get("status") == "ADVANCED" for x in progress_checks),
        },
        "checks": checks,
        "live_progress": progress_checks,
        "interpretation": (
            "A GitHub failure identifies an origin/DNS/HTTP issue visible from GitHub. "
            "A GitHub pass does not prove Link3 access or IPTV Pro playback. "
            "No playlist URL is changed."
        ),
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
