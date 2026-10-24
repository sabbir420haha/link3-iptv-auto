#!/usr/bin/env python3
"""Build the user's separate Favorites TEST M3U, never the main playlist.

Each non-excluded My Favorites channel gets up to 30 DIFFERENT publicly
listed URLs, with its own named group and numbered entries. GitHub-sourced
seeds remain even when network discovery fails. Unverified != working.
"""
import concurrent.futures
import datetime
import json
import re
from collections import defaultdict
from pathlib import Path
from update import SOURCES, EXTRA_CANDIDATES, allowed, fetch_playlist, key

ROOT = Path(__file__).resolve().parent
MAIN = ROOT / "playlist.m3u"
CATALOG = ROOT / "channels.json"
OUTPUT = ROOT / "geo_trials.m3u"
STATUS = ROOT / "status.json"
MAX_PER_CHANNEL = 30
EXCLUDED = {"Channel 24", "Sonic Bangla", "Sonic Hindi",
            "Discovery Bangla", "Nat Geo HD Bangla"}
SEED_FILES = ("favorite_search_a.json", "favorite_search_b.json")
VALID_EXT = re.compile(r"\.m3u8(?:$|[?#])|\.ts(?:$|[?#])|[?&]e=\.m3u8(?:$|&)", re.I)

def favorites():
    """Use the playlist's actual Favorites entries, not a guessed catalogue."""
    lines = MAIN.read_text(encoding="utf-8").splitlines()
    items = []
    for i, line in enumerate(lines):
        if (not line.startswith("#EXTINF:") or
                'group-title="00 | MY FAVORITES"' not in line):
            continue
        name = line.split(",", 1)[-1].strip()
        if name in EXCLUDED:
            continue
        logo_match = re.search(r'tvg-logo="([^"]*)"', line)
        logo = logo_match.group(1) if logo_match else ""
        j = i + 1
        while j < len(lines) and lines[j].startswith("#"):
            j += 1
        main_url = lines[j].strip() if j < len(lines) else ""
        items.append({"name": name, "logo": logo, "main_url": main_url})
    return items

def seeds():
    all_seeds = defaultdict(list)
    for file in SEED_FILES:
        path = ROOT / file
        if path.exists():
            contents = json.loads(path.read_text(encoding="utf-8"))
            for name, candidates in contents.get("sources", {}).items():
                for entry in candidates:
                    all_seeds[name].append((entry["url"], "GitHub labelled M3U"))
    return all_seeds

def discover(names, catalog):
    """Only exact normalized channel labels (or documented aliases) match."""
    matches = {}
    for name in names:
        item = catalog.get(name, {})
        aliases = [name] + item.get("aliases", [])
        matches[name] = {key(x) for x in aliases}
    found = defaultdict(list)
    fetch_results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for source_name, entries, error in pool.map(fetch_playlist, SOURCES):
            fetch_results.append({"source": source_name,
                                  "count": len(entries), "error": error})
            for entry in entries:
                labelled = key(entry["name"])
                for name, options in matches.items():
                    if labelled in options:
                        found[name].append((entry["url"], source_name))
    return found, fetch_results

def eligible(url, banned):
    if not isinstance(url, str) or not VALID_EXT.search(url):
        return False
    if not allowed(url) or url in banned:
        return False
    return True

def main():
    favs = favorites()
    catalog = {x["name"]: x for x in json.loads(CATALOG.read_text(encoding="utf-8"))}
    candidates = seeds()
    extra, sources = discover([f["name"] for f in favs], catalog)
    output = [
        "#EXTM3U",
        "# Separate Favorites TEST playlist: max 30 alternatives per selected channel.",
        "# NOT Link3-verified; may fail, be region-restricted or require rights.",
        "# Main channel URLs are deliberately omitted; main playlist is not changed.",
    ]
    summary = {}
    for favorite in favs:
        name, logo, main_url = favorite["name"], favorite["logo"], favorite["main_url"]
        banned = set(catalog.get(name, {}).get("exclude_urls", []))
        banned.add(main_url)
        alternatives = list(candidates.get(name, []))
        alternatives.extend(extra.get(name, []))
        alternatives.extend((u, "curated-research") for u in EXTRA_CANDIDATES.get(name, []))
        distinct = []
        seen = set()
        for url, provenance in alternatives:
            # Every extra is tied to this particular channel's name in a
            # published source or explicitly curated lookup, not a guessed alias.
            if url in seen or not eligible(url, banned):
                continue
            seen.add(url)
            distinct.append((url, provenance))
            if len(distinct) == MAX_PER_CHANNEL:
                break
        summary[name] = len(distinct)
        group = "9 | TEST - " + name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        for index, (url, provenance) in enumerate(distinct, 1):
            number = f"{index:02d}"
            title = f"{name} TEST {number}"
            output.append(
                f'#EXTINF:-1 tvg-id="fav-{slug}-{number}" '
                f'tvg-name="{title}" tvg-logo="{logo}" '
                f'group-title="{group}",{title}'
            )
            output.append(url)
    OUTPUT.write_text("\n".join(output) + "\n", encoding="utf-8")
    report = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    report["bd_geo_trials"] = {
        "updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "entries": sum(summary.values()),
        "requested_limit_per_channel": MAX_PER_CHANNEL,
        "channel_count": len(favs),
        "by_name": summary,
        "discovery_sources": sources,
        "warning": "Unverified alternate stream URLs, not proof of playback, rights, HD, or low buffering on Link3. All changes apply only to geo_trials.m3u.",
    }
    STATUS.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("Favorites TEST:", len(favs), "channels", sum(summary.values()), "streams")
    print(summary)

if __name__ == "__main__":
    main()
