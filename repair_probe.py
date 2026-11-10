#!/usr/bin/env python3
"""Probe fresh public HLS candidates for the user's 13 broken Link3 channels.

This script only edits three_channel_test.m3u and repair_probe_results.json.
It never edits playlist.m3u or channels.json and never bypasses tokens, cookies,
DRM, geo restrictions, or provider authentication.
GitHub-runner success is not proof of playback on the user's Link3 connection.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import re
import time
import urllib.parse
from pathlib import Path

import update as updater

ROOT = Path(__file__).resolve().parent
TEST = ROOT / "three_channel_test.m3u"
MAIN = ROOT / "playlist.m3u"
CATALOG = ROOT / "channels.json"
REGISTRY = ROOT / "favorites_test_registry.json"
SEARCH_A = ROOT / "favorite_search_a.json"
SEARCH_B = ROOT / "favorite_search_b.json"
REPORT = ROOT / "repair_probe_results.json"

TARGETS = [
    "ATN Bangla", "Cartoon Network", "Channel 24", "Duronto TV",
    "Hungama Backup", "Sony MAX HD", "Nat Geo HD Bangla", "Nick Bangla",
    "Somoy TV", "Sony Aath", "Sony Ten 1 HD", "Sony Ten 3 HD",
    "Independent TV",
]
REGISTRY_KEYS = {
    "ATN Bangla": ("ATN Bangla",),
    "Cartoon Network": ("Cartoon Network",),
    "Channel 24": ("Channel 24",),
    "Duronto TV": ("Duronto TV",),
    "Hungama Backup": ("Hungama", "Hungama Backup"),
    "Sony MAX HD": ("Sony MAX HD",),
    "Nat Geo HD Bangla": ("Nat Geo HD Bangla",),
    "Nick Bangla": ("Nick Bangla",),
    "Somoy TV": ("Somoy TV",),
    "Sony Aath": ("Sony Aath",),
    "Sony Ten 1 HD": ("Sony Ten 1 HD",),
    "Sony Ten 3 HD": ("Sony Ten 3 HD",),
    "Independent TV": ("Independent TV",),
}
MAX_CANDIDATES_PER_CHANNEL = 32
MAX_RESULTS_PER_CHANNEL = 4
WORKERS = 12
# These are subscription channels. Do not publish third-party raw URLs or
# attempt to bypass a licensed provider's sign-in, cookies, tokens or DRM.
SUBSCRIPTION_ONLY = {
    "Cartoon Network", "Hungama Backup", "Sony MAX HD",
    "Nat Geo HD Bangla", "Nick Bangla", "Sony Aath",
    "Sony Ten 1 HD", "Sony Ten 3 HD",
}
LIVE_WINDOW_SECONDS = 9
BLOCKED_HOSTS = (
    "toffeelive.com", "slivcdn.com", "sonyliv.com", "jiocinema.com",
    "hotstar.com", "xown.site",
)

def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def extract_urls(text: str) -> set[str]:
    return {line.strip() for line in text.splitlines()
            if line.strip().startswith(("http://", "https://"))}

def target_match(target: str, title: str, url: str) -> bool:
    value = (title + " " + url).lower().replace("_", " ").replace("-", " ")
    if target == "ATN Bangla":
        return ("atn bangla" in value or "atnbangla" in value) and not any(x in value for x in ("atn news", "atn bangla uk"))
    if target == "Cartoon Network":
        return "cartoon network" in value and not any(x in value for x in ("arabic", "pakistan", "cee", "german", "retro blast"))
    if target == "Channel 24":
        return ("channel 24" in value or "channel24" in value) and "pakistan" not in value
    if target == "Duronto TV":
        return "duronto" in value or "duranto" in value
    if target == "Hungama Backup":
        return "hungama" in value and not any(x in value for x in ("super hungama", "hungama music", "bollywood", "pop pataka", "kadak hits", "dil de", "bol hadipa", "hungama kids"))
    if target == "Sony MAX HD":
        return "sony max" in value and not any(x in value for x in ("sony max 2", "sonymax2"))
    if target == "Nat Geo HD Bangla":
        return (("nat geo" in value or "national geographic" in value or "natgeo" in value)
                and ("bangla" in value or "bengali" in value))
    if target == "Nick Bangla":
        return ("nick" in value and ("bangla" in value or "bengali" in value)
                and not any(x in value for x in ("nick jr", "nickjr", "nicktoons", "teen nick")))
    if target == "Somoy TV":
        return "somoy" in value and "somoy tv" in value
    if target == "Sony Aath":
        return "sony aath" in value or "sony 8" in value
    if target == "Sony Ten 1 HD":
        return (("sony ten 1" in value or "sony sports ten 1" in value or "sonyten1" in value)
                and not any(x in value for x in ("ten 2", "ten 3", "ten 5", "sonyten2", "sonyten3")))
    if target == "Sony Ten 3 HD":
        return (("sony ten 3" in value or "sony sports ten 3" in value or "sonyten3" in value)
                and not any(x in value for x in ("ten 1", "ten 2", "ten 5", "sonyten1", "sonyten2")))
    if target == "Independent TV":
        return "independent tv" in value or "independent television" in value
    return False

def bad_source(source: str) -> bool:
    value = source.lower()
    return any(x in value for x in (
        "not working", "don't try", "do not try", "dead stream",
        "expired", "known failed", "broken source",
    ))

def blocked_url(url: str) -> bool:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    return any(x in host for x in BLOCKED_HOSTS)

def add_candidate(bag: dict, target: str, url: str, source: str, title: str = "") -> None:
    url = (url or "").strip()
    if not url or bad_source(source) or blocked_url(url):
        return
    if not updater.allowed(url):
        return
    if not target_match(target, title or target, url):
        # Registry-keyed candidates may use a provider-specific URL path with
        # no channel name. Keep only those when the origin itself identifies
        # the requested channel; avoid broad generic/incorrect feeds.
        if not target_match(target, source, url):
            return
    bag[target].setdefault(url, {
        "url": url, "source": source[:500], "title": title[:160] or target
    })

def collect_candidates(main_text: str, test_text: str, catalog: list[dict]) -> tuple[dict, dict]:
    bag = {name: {} for name in TARGETS}
    fetch_report = {}
    excluded = extract_urls(main_text) | extract_urls(test_text)

    # Respect the catalog's existing exclusions and previously reported failures.
    for item in catalog:
        name = item.get("name", "")
        if name not in TARGETS:
            continue
        excluded.update(item.get("exclude_urls", []))
        excluded.update(item.get("known_user_failures", []))
        excluded.update(item.get("user_reported_failures", []))
        excluded.update(item.get("experimental_urls", []))

    # Existing researched candidates; the user still decides Link3 playback.
    for path in (REGISTRY, SEARCH_A, SEARCH_B):
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if path == REGISTRY:
            source_map = data.get("channels", {})
        else:
            source_map = data.get("sources", {})
        for target, keys in REGISTRY_KEYS.items():
            if target in SUBSCRIPTION_ONLY:
                continue
            for key in keys:
                raw_candidates = source_map.get(key, []) or []
                if isinstance(raw_candidates, dict):
                    raw_candidates = raw_candidates.get("candidates", []) or []
                for index, candidate in enumerate(raw_candidates, 1):
                    if isinstance(candidate, str):
                        url = candidate
                        origin = f"{path.name}:{key}:candidate-{index:02d}"
                    elif isinstance(candidate, dict):
                        url = candidate.get("url", "")
                        origin = candidate.get("origin", candidate.get("source", path.name))
                    else:
                        continue
                    if url and url not in excluded:
                        add_candidate(bag, target, url, origin, target)

    # Refresh the public source lists at run time rather than trusting a stale
    # copy. update.SOURCES contains iptv-org and other openly published M3Us.
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = {pool.submit(updater.fetch_playlist, src): src[0] for src in updater.SOURCES}
        for future in concurrent.futures.as_completed(futures):
            source_name = futures[future]
            try:
                name, entries, error = future.result()
            except Exception as exc:
                fetch_report[source_name] = {"ok": False, "error": str(exc)[:180]}
                continue
            fetch_report[name] = {"ok": not bool(error), "entries": len(entries), "error": error}
            for entry in entries:
                title, url = entry.get("name", ""), entry.get("url", "")
                if not url or url in excluded:
                    continue
                for target in TARGETS:
                    if target in SUBSCRIPTION_ONLY:
                        continue
                    if target_match(target, title, url):
                        add_candidate(bag, target, url, name, title)

    # Exclude every URL already present in either live playlist or catalog exclusions.
    for target in TARGETS:
        if target in SUBSCRIPTION_ONLY:
            bag[target] = {}
            continue
        bag[target] = {
            url: item for url, item in bag[target].items()
            if url not in excluded and updater.allowed(url) and not blocked_url(url)
        }
    return bag, fetch_report

def live_snapshot(url: str):
    """Resolve a public HLS master to its live media playlist and return progress markers."""
    current = url
    for _ in range(4):
        raw, _ctype = updater.fetch_hls_bytes(current, 32000, 9)
        body = raw.decode("utf-8-sig", errors="replace")
        if "#EXTM3U" not in body[:500]:
            return None
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        if "#EXT-X-STREAM-INF" in body:
            variants = []
            for i, line in enumerate(lines[:-1]):
                if line.startswith("#EXT-X-STREAM-INF") and not lines[i + 1].startswith("#"):
                    h = re.search(r"RESOLUTION=\d+x(\d+)", line)
                    b = re.search(r"BANDWIDTH=(\d+)", line)
                    variants.append((int(h.group(1)) if h else 0,
                                     int(b.group(1)) if b else 0,
                                     urllib.parse.urljoin(current, lines[i + 1])))
            if not variants:
                return None
            current = max(variants)[2]
            continue
        if "#EXT-X-ENDLIST" in body:
            return None
        seq_match = re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)", body)
        seq = int(seq_match.group(1)) if seq_match else None
        segments = [x for x in lines if not x.startswith("#")]
        if not segments:
            return None
        return {"sequence": seq, "last_segment": segments[-1], "target_duration": re.search(r"#EXT-X-TARGETDURATION:(\d+)", body).group(1) if re.search(r"#EXT-X-TARGETDURATION:(\d+)", body) else None}
    return None

def check_candidate(candidate: dict) -> dict:
    url = candidate["url"]
    result = {**candidate, "manifest_ok": False, "segment_ok": False,
              "live_progress": False, "height": 0, "status": "failed"}
    try:
        result["manifest_ok"] = bool(updater.probe(url))
        if not result["manifest_ok"]:
            result["status"] = "manifest_failed"
            return result
        result["segment_ok"] = bool(updater.segment_probe(url))
        if not result["segment_ok"]:
            result["status"] = "segment_failed"
            return result
        first = live_snapshot(url)
        if not first:
            result["status"] = "not_live_or_unreadable"
            return result
        time.sleep(LIVE_WINDOW_SECONDS)
        second = live_snapshot(url)
        if not second:
            result["status"] = "second_snapshot_failed"
            return result
        seq1, seq2 = first.get("sequence"), second.get("sequence")
        progressed = ((seq1 is not None and seq2 is not None and seq2 > seq1)
                      or first.get("last_segment") != second.get("last_segment"))
        if not progressed:
            result["status"] = "no_live_progress"
            return result
        if not updater.segment_probe(url):
            result["status"] = "second_segment_failed"
            return result
        result["live_progress"] = True
        result["height"] = updater.hd_resolution(url)
        result["status"] = "runner_live_hls_pass"
    except Exception as exc:
        result["status"] = "probe_error"
        result["error"] = str(exc)[:220]
    return result

def is_old_repair_extinf(line: str) -> bool:
    if not line.startswith("#EXTINF:"):
        return False
    name_match = re.search(r'tvg-name="([^"]+)"', line)
    name = name_match.group(1) if name_match else line.split(",")[-1]
    if " ALT " not in name and "REPAIR TEST" not in name and "AUTO TEST" not in name:
        return False
    return any(name.startswith(target + " ") for target in TARGETS) or name.startswith("Zee Bangla REPAIR TEST")

def remove_old_repair_entries(text: str) -> str:
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        if is_old_repair_extinf(lines[i]):
            # Remove source/warning comments immediately before this failed entry.
            while out and out[-1].startswith("#") and not out[-1].startswith("#EXTINF"):
                out.pop()
            i += 1
            while i < len(lines) and not lines[i].startswith("#EXTINF"):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out).rstrip() + "\n"

def build_entries(passed: dict, catalog: list[dict]) -> str:
    logos = {x.get("name"): x.get("logo", "") for x in catalog}
    lines = [
        "",
        "# AUTO REPAIR TESTS | Generated from fresh public source checks",
        "# GitHub runner manifest + media-segment + live-progress checks passed.",
        "# NOT Link3 verified. Check actual channel identity, language, quality and playback in IPTV Pro.",
        "# Only TEST playlist is updated; Main playlist is never modified.",
    ]
    for target in TARGETS:
        rows = passed.get(target, [])[:MAX_RESULTS_PER_CHANNEL]
        for index, row in enumerate(rows, 1):
            label = f"{target} AUTO TEST {index:02d}"
            tvgid = re.sub(r"[^a-z0-9]+", "-", target.lower()).strip("-")
            lines.extend([
                f"# SOURCE: {row['source']}",
                f"# RUNNER CHECK: manifest=PASS; media-segment=PASS; live-progress=PASS; advertised-height={row.get('height', 0)}",
                f"# UNVERIFIED: Link3/IPTV Pro playback and actual audio/channel identity must be checked by the user.",
                f'#EXTINF:-1 tvg-id="repair-auto-{tvgid}-{index:02d}" tvg-name="{label}" tvg-logo="{logos.get(target, "")}" group-title="TEST CHANNELS - SINGLE GROUP",{label}',
                row["url"],
            ])
    if not any(passed.get(name) for name in TARGETS):
        lines.extend(["# No new candidates passed the live HLS checks this run.", "# Do not add unverified URLs just to increase the count."])
    return "\n".join(lines) + "\n"

def main():
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    main_text = read_text(MAIN)
    test_text = read_text(TEST)
    catalog = json.loads(read_text(CATALOG))
    candidates, fetch_report = collect_candidates(main_text, test_text, catalog)

    all_jobs = []
    candidate_counts = {}
    for target in TARGETS:
        rows = list(candidates[target].values())
        rows.sort(key=lambda x: (x["url"].startswith("https://"), "iptv-org" in x["source"].lower()), reverse=True)
        rows = rows[:MAX_CANDIDATES_PER_CHANNEL]
        candidate_counts[target] = len(rows)
        for row in rows:
            all_jobs.append((target, row))

    checked = {target: [] for target in TARGETS}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(check_candidate, row): target for target, row in all_jobs}
        for future in concurrent.futures.as_completed(futures):
            target = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"status": "probe_error", "error": str(exc)[:220]}
            checked[target].append(result)

    passed = {}
    summary = {}
    for target in TARGETS:
        rows = [x for x in checked[target] if x.get("status") == "runner_live_hls_pass"]
        rows.sort(key=lambda x: (x.get("height", 0), x["url"].startswith("https://")), reverse=True)
        passed[target] = rows[:MAX_RESULTS_PER_CHANNEL]
        summary[target] = {
            "candidates": candidate_counts[target],
            "checked": len(checked[target]),
            "runner_live_hls_pass": len(rows),
            "added_to_test": len(passed[target]),
            "note": "Official subscription source required; no third-party raw URL is published." if target in SUBSCRIPTION_ONLY else "Public candidate probe only; Link3 playback still needs user confirmation.",
        }

    # Rebuild only the repair section. Previously user-reported failed repair
    # entries are removed so they cannot clutter the new test list.
    clean_test = remove_old_repair_entries(test_text)
    new_section = build_entries(passed, catalog)
    if "# AUTO REPAIR TESTS | Generated from fresh public source checks" in clean_test:
        clean_test = clean_test.split("# AUTO REPAIR TESTS | Generated from fresh public source checks", 1)[0].rstrip() + "\n"
    clean_test = clean_test.rstrip() + "\n" + new_section
    TEST.write_text(clean_test, encoding="utf-8")

    report = {
        "checked_utc": now,
        "scope": "GitHub runner only; not Link3 or IPTV Pro",
        "targets": TARGETS,
        "subscription_only_targets": sorted(SUBSCRIPTION_ONLY),
        "summary": summary,
        "source_fetches": fetch_report,
        "results": {name: checked[name] for name in TARGETS},
        "policy": "No Main edits; no auth/cookie/token/DRM/geo bypass; no known-failed URL reuse.",
        "max_candidates_per_channel": MAX_CANDIDATES_PER_CHANNEL,
        "max_results_per_channel": MAX_RESULTS_PER_CHANNEL,
        "test_playlist": "three_channel_test.m3u",
        "main_playlist_untouched": True,
    }
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"summary": summary, "source_fetches_ok": sum(1 for x in fetch_report.values() if x.get("ok"))}))

if __name__ == "__main__":
    main()
