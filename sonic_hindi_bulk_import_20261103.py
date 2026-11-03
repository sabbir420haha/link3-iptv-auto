#!/usr/bin/env python3
"""Import up to 150 distinct, public, previously unlisted Sonic Hindi test streams.

All entries are unverified viewer trials, not declarations of working video.
Never write to the MAIN playlist or unrelated channels.
"""
from __future__ import annotations

import base64
import concurrent.futures
import datetime
import json
import os
import re
import urllib.parse
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(".")
SOURCES = ROOT / "sonic_hindi_bulk_search_sources_20261103.json"
REPORT = ROOT / "sonic_hindi_bulk_result_20261103.json"
TARGETS = [
    ROOT / "three_channel_test_refresh_20261102.m3u",
    ROOT / "three_channel_test.m3u",
]
HISTORY = [
    "sonic_hindi_test_index.json",
    "sonic_hindi_candidates.json",
    "sonic_hindi_probe_results.json",
    "favorites_test_registry.json",
    "sonic_hindi_discovery_2026-10-26.json",
    "sonic_hindi_search_batch2_2026-10-26.json",
    "sonic_hindi_extensive_20261027_sources.json",
    "documentary_hd_tests.m3u",
] + [str(p) for p in TARGETS]
URL_RX = re.compile(r'https?://[^\s"''<>]+', re.I)
EXTINF_RX = re.compile(r"^#EXTINF:.*,\s*(.+)$", re.I)
SONIC_RX = re.compile(r"sonic", re.I)
NOT_HINDI_RX = re.compile(
    r"bangla|bengali|tamil|malayalam|telugu|kannada|marathi|gujarati|sonic the hedgehog|super sonic|sonic tv|sonic 2|in-mar",
    re.I,
)
BLOCK_RX = re.compile(
    r"widevine|drm_key|license_key|\.mpd(?:[?#]|$)|/stalker/|"
    r"[?&](?:token|signature|sig|hdntl|hdnts|auth|mac|play_token|"
    r"key|cookie|session|exp|uid|deviceMac|u|p)=|wmsAuthSign=|checkedby",
    re.I,
)
PRIVATE_RX = re.compile(
    r"^https?://(?:localhost|127\.|192\.168\.|10\.|172\.(?:1[6-9]|2\d|3[01])\.)",
    re.I,
)
STREAM_RX = re.compile(
    r"\.m3u8(?:[?#]|$)|\.ts(?:[?#]|$)|"
    r"(?:\bid|[?&]c)=815\b|(?:\bid|[?&]c)=sonic|/sonic(?:/|$)|"
    r"/t/127/|sonic_hindi",
    re.I,
)
LOGO = "https://jiotv.catchup.cdn.jio.com/dare_images/images/sonic_Hindi.png"


def normalize(raw: str) -> str:
    """Normalize only URL presentation, never change source paths or tokens."""
    return (raw.replace("&amp;", "&").replace("\\u0026", "&")
            .split("|User-Agent=")[0].split("|Referer=")[0]
            .rstrip("}]),.;'\"\\").rstrip("/").strip())


def history_urls() -> set[str]:
    """Block all previously tested and known-bad sources and playlist URLs."""
    seen: set[str] = set()
    for filename in HISTORY:
        path = ROOT / filename
        if not path.is_file():
            continue
        contents = path.read_text(errors="replace")
        if filename in [str(p) for p in TARGETS]:
            marker = "# SONIC HINDI BULK TEST 2026-11-03 — ALL UNVERIFIED"
            if marker in contents:
                begin = contents.index(marker)
                anchor = contents.find("# HUNGAMA NOVEMBER 01 SECOND BATCH", begin)
                if anchor < 0:
                    raise RuntimeError("Missing safe anchor in previous bulk TEST")
                contents = contents[:begin] + contents[anchor:]
        for m in URL_RX.finditer(contents):
            seen.add(normalize(m.group()))
        if path.suffix == ".json":
            try:
                obj = json.loads(path.read_text())
                def walk(value: object) -> None:
                    if isinstance(value, str) and value.startswith(("http://", "https://")):
                        seen.add(normalize(value))
                    elif isinstance(value, dict):
                        for item in value.values():
                            walk(item)
                    elif isinstance(value, list):
                        for item in value:
                            walk(item)
                walk(obj)
            except (ValueError, OSError):
                pass
    return seen


def admissible(url: str) -> bool:
    """Keep public unprotected stream URLs; user will verify the playback."""
    if len(url) > 650 or not url.startswith(("http://", "https://")):
        return False
    if BLOCK_RX.search(url) or PRIVATE_RX.search(url) or re.search(r"[$\x27\x22]|%7C|hdntl=|hdnts=|~hmac=|moonkerala\.xyz", url, re.I):
        return False
    if re.search(r"sonic[-_]?bangla|sonic[-_]?marathi|sonic[-_]?gujarati|sonicbangla|(?:[?&]id=134[56](?:[&#]|$))|(?:[?&]c=Sonic_(?:Marathi|Gujarati|Bangla))|animetv/animetv|sat7kids", url, re.I):
        return False
    if not STREAM_RX.search(url):
        return False
    if re.search(r"/live/[^/]+/[^/]+/\d+\.(?:ts|m3u8)", url, re.I):
        return False  # third-party reseller credentials
    if re.search(r"\.(?:jpeg|jpg|png|gif|svg|mp3|aac)(?:[?#]|$)", url, re.I):
        return False
    return True


def fetch_source(source: dict[str, str]) -> tuple[dict[str, str], str, str]:
    """Read a public GitHub source file through the official contents API."""
    owner_repo, file_path = source["repo"], source["path"]
    quoted = urllib.parse.quote(file_path, safe="/")
    api = f"https://api.github.com/repos/{owner_repo}/contents/{quoted}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "SonicBulkTrial/1.0"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.get(api, headers=headers, timeout=18)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and data.get("content"):
            content = base64.b64decode(data["content"]).decode("utf-8", "replace")
            return source, content[:1_600_000], ""
        if isinstance(data, dict) and data.get("download_url"):
            r = requests.get(data["download_url"], timeout=18)
            r.raise_for_status()
            return source, r.text[:1_600_000], ""
        return source, "", "missing content"
    except Exception as exc:
        return source, "", str(exc)[:180]


def candidates_from_source(source: dict[str, str], content: str) -> list[dict[str, str]]:
    """Parse labeled Sonic entries; never create URL variations by guessing."""
    result: list[dict[str, str]] = []
    lines = content.splitlines()
    origin = f"{source['repo']}/{source['path']}"
    for index, raw in enumerate(lines):
        if len(raw) > 2500:
            continue
        match = EXTINF_RX.match(raw.strip())
        if not match:
            continue
        name = match.group(1).strip()
        if not SONIC_RX.search(name) or NOT_HINDI_RX.search(name):
            continue
        if NOT_HINDI_RX.search(raw):  # language explicitly Bengali, Tamil, etc.
            continue
        ahead = lines[index + 1:index + 8]
        if any(re.search(r"license|widevine|drm_key|cookie", x, re.I)
               for x in ahead if x.strip().startswith("#")):
            continue
        for line in ahead:
            if line.startswith("#EXTINF"):
                break
            if line.lstrip().startswith("#"):
                continue
            m = URL_RX.search(line.strip())
            if m:
                result.append({"url": normalize(m.group()), "source": origin,
                               "label": name, "method": "m3u"})
                break
    # Also support JSON channel catalogs when a Sonic item contains its own URL.
    if source["path"].lower().endswith(".json"):
        try:
            value = json.loads(content)
            def walk(item: object, depth: int = 0) -> None:
                if depth > 12:
                    return
                if isinstance(item, list):
                    for child in item:
                        walk(child, depth + 1)
                elif isinstance(item, dict):
                    name = next((item[k] for k in
                                 ("name", "title", "channel", "channel_name", "tvg_name")
                                 if isinstance(item.get(k), str)), "")
                    if SONIC_RX.search(name) and not NOT_HINDI_RX.search(name):
                        for field in ("url", "link", "streamUrl", "stream_url",
                                      "stream", "src", "hls"):
                            if isinstance(item.get(field), str):
                                result.append({"url": normalize(item[field]),
                                               "source": origin, "label": name,
                                               "method": "json"})
                    for child in item.values():
                        walk(child, depth + 1)
            walk(value)
        except (ValueError, TypeError):
            pass
    return result


def main() -> None:
    """Fetch, deduplicate, rank, and commit only numbered user TEST entries."""
    sources = json.loads(SOURCES.read_text())["files"]
    old = history_urls()
    found: dict[str, dict[str, str]] = {}
    problems = Counter()
    print(f"Checking {len(sources)} distinct source files; {len(old)} known URLs excluded.",
          flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as executor:
        futures = [executor.submit(fetch_source, src) for src in sources]
        for done in concurrent.futures.as_completed(futures):
            source, content, error = done.result()
            if error:
                problems["source_fetch_failed"] += 1
                continue
            problems["source_fetch_ok"] += 1
            for obj in candidates_from_source(source, content):
                url = obj["url"]
                problems["raw_sonic_entries"] += 1
                if not admissible(url):
                    problems["blocked_or_not_stream"] += 1
                elif url in old:
                    problems["previously_recorded"] += 1
                elif url in found:
                    problems["repeated_in_other_repo"] += 1
                else:
                    found[url] = obj
    # Prioritize explicitly Hindi-tagged references and diverse upstream hosts.
    def rank(x: dict[str, str]) -> tuple[int, str]:
        label = x["label"].lower()
        url = x["url"].lower()
        weight = 2 if "hindi" in label or "hindi" in url else 1
        if "sonic" in url:
            weight += 1
        return (-weight, url)
    sorted_candidates = sorted(found.values(), key=rank)
    selected = sorted_candidates[:150]
    # Pure source listing. Neither the source, video nor its Hindi audio is verified.
    records = []
    inserted_sections = []
    for number, item in enumerate(selected, start=140):
        label = f"Sonic Hindi TEST {number}"
        section = (
            f"# PUBLIC SOURCE: {item['source']}\n"
            f"# UNVERIFIED USER TRIAL: {item['label']}; not tested on Link3, "
            f"no claim of Hindi audio or video working.\n"
            f'#EXTINF:-1 tvg-id="sonic-hindi-bulk-{number}" '
            f'tvg-name="{label}" tvg-logo="{LOGO}" '
            f'group-title="TEST CHANNELS - SINGLE GROUP",{label}\n'
            f"{item['url']}\n"
        )
        inserted_sections.append(section)
        records.append({"test_id": number, **item, "remote_verified": False,
                        "link3_verified": False, "hindi_verified": False})
    if records:
        marker = "# SONIC HINDI BULK TEST 2026-11-03 — ALL UNVERIFIED\n"
        block = marker + "".join(inserted_sections) + "\n"
        originals = [p.read_text() for p in TARGETS]
        for path, original in zip(TARGETS, originals):
            if not original.startswith("#EXTM3U"):
                raise RuntimeError(f"Unsafe TEST playlist state: {path}")
            if marker in original:
                bulk_start = original.index(marker)
                bulk_end = original.find("# HUNGAMA NOVEMBER 01 SECOND BATCH", bulk_start)
                if bulk_end < 0:
                    raise RuntimeError(f"Cannot replace existing bulk section: {path}")
                original = original[:bulk_start] + original[bulk_end:]
            if not original.startswith("#EXTM3U"):
                raise RuntimeError(f"Unsafe TEST playlist state: {path}")
            if "Hungama TEST 29" not in original:
                raise RuntimeError(f"Missing existing Hungama TEST 29 in {path}")
            anchor = "# HUNGAMA NOVEMBER 01 SECOND BATCH"
            insertion_at = original.find(anchor)
            if insertion_at < 0:
                raise RuntimeError(f"Missing safe insertion anchor in {path}")
            updated = original[:insertion_at] + block + original[insertion_at:]
            if updated.count("#EXTINF:") != original.count("#EXTINF:") + len(records):
                raise RuntimeError(f"Channel count mismatch in {path}")
            path.write_text(updated)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = {"checked_utc": now, "source_count": len(sources),
              "all_new_candidates": len(sorted_candidates),
              "added_to_each_test_playlist": len(records), "test_start": 140,
              "test_end": (139 + len(records)), "unverified": True,
              "main_playlist_touched": False, "other_test_channels_touched": False,
              "counts": dict(problems), "entries": records}
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print("SONIC_BULK_RESULT " + json.dumps({
        "source_files": len(sources), "new_distinct": len(sorted_candidates),
        "added": len(records), "first": 140, "last": 139 + len(records),
        "counts": dict(problems)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
