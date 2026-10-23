#!/usr/bin/env python3
"""Curated IPTV Pro M3U refresh. No video rehosting, token bypass or DRM handling.
A successful remote HLS check does not establish Link3 playback or streaming rights.
"""
import concurrent.futures
import datetime as datetime
import ipaddress
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "channels.json"
OUTPUT = ROOT / "playlist.m3u"
REPORT = ROOT / "status.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Link3-IPTV-Curator/2.0)"}
SOURCES = [
    ("iptv-bd", "https://iptv-org.github.io/iptv/countries/bd.m3u"),
    ("iptv-in", "https://iptv-org.github.io/iptv/countries/in.m3u"),
    ("iptv-ben", "https://iptv-org.github.io/iptv/languages/ben.m3u"),
    ("iptv-hin", "https://iptv-org.github.io/iptv/languages/hin.m3u"),
    ("iptv-kids", "https://iptv-org.github.io/iptv/categories/kids.m3u"),
    ("iptv-sports", "https://iptv-org.github.io/iptv/categories/sports.m3u"),
    ("iptv-entertainment", "https://iptv-org.github.io/iptv/categories/entertainment.m3u"),
    ("iptv-documentary", "https://iptv-org.github.io/iptv/categories/documentary.m3u"),
    ("Zaman-Active", "https://raw.githubusercontent.com/Zaman-Topu/Ip-tv-Collection/main/FINAL_IPTV_ACTIVE.m3u"),
    ("Saeid-Mixed-BDIX", "https://raw.githubusercontent.com/saeidrahmanbd/BDIX-IPTV/main/IPTV-Playlist.m3u"),
    ("Mrgify-Mixed-BDIX", "https://raw.githubusercontent.com/abusaeeidx/Mrgify-BDIX-IPTV/main/playlist.m3u"),
]

def key(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower().replace("&", "and"))

def allowed(url, locked=False):
    try:
        p = urllib.parse.urlsplit(url)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
            return False
        host = p.hostname.lower().strip(".")
        if host == "localhost" or host.endswith((".local", ".internal", ".lan")):
            return False
        if any(x in host for x in ("bdix", "tplay", "t-play")):
            return False
        if any(x in p.query.lower() for x in ("token=", "auth=", "expires=", "signature=", "hdnea=", "session=")):
            return False
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return False
            # Only the explicitly user-confirmed Hungama URL may use numeric IP.
            if not locked:
                return False
        except ValueError:
            pass
        return True
    except (ValueError, TypeError):
        return False

def load_url(url, timeout=11, max_bytes=12_000_000):
    if not allowed(url):
        raise ValueError("Refusing unsafe playlist/source URL")
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError("HTTP " + str(response.status))
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("source is too large")
    return raw.decode("utf-8-sig", errors="replace")

def parse_m3u(text, source="previous"):
    channels = []
    info = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            head, _, title = line.partition(",")
            attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', head))
            info = {
                "name": title.strip(),
                "id": attrs.get("tvg-id", ""),
                "logo": attrs.get("tvg-logo", ""),
                "source": source,
            }
        elif line.startswith(("http://", "https://")) and info is not None:
            channels.append({**info, "url": line})
            info = None
    return channels

def fetch_playlist(source):
    name, url = source
    try:
        body = load_url(url)
        if "#EXTINF" not in body:
            raise ValueError("not M3U channel list")
        return name, parse_m3u(body, name), None
    except Exception as error:
        return name, [], str(error)[:130]

def probe(url):
    if not allowed(url):
        return False
    try:
        request = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-4095"})
        with urllib.request.urlopen(request, timeout=8) as response:
            if response.status not in (200, 206):
                return False
            chunk = response.read(4096).decode("utf-8-sig", errors="replace")
        return "#EXTM3U" in chunk and ("#EXT-X-" in chunk or "#EXTINF" in chunk)
    except Exception:
        return False

def score(item, entry, old):
    url = entry["url"]
    host = urllib.parse.urlsplit(url).hostname or ""
    value = 15 if url.startswith("https:") else 0
    if entry["source"].startswith("iptv-"):
        value += 20
    elif entry["source"] == "Zaman-Active":
        value += 8
    elif "BDIX" in entry["source"]:
        value -= 12
    if host.endswith(("cloudfront.net", "akamaized.net", "gpcdn.net", "aynaott.com", "amagi.tv")):
        value += 10
    if any(x in url for x in ("_abr/", "/master", "/index.m3u8")):
        value += 5
    if url == old:
        value += 30
    return value

def clean(value):
    return (value or "").replace('"', "").replace("\n", " ").replace("\r", " ")

def main():
    channels = json.loads(CATALOG.read_text(encoding="utf-8"))
    if len(channels) != 101 or sum(bool(x.get("locked")) for x in channels) != 4:
        raise ValueError("Channel catalog or pinned list unexpectedly changed")
    previous = {}
    if OUTPUT.exists():
        for c in parse_m3u(OUTPUT.read_text(encoding="utf-8")):
            previous[key(c["name"])] = c["url"]

    source_stats = []
    found = defaultdict(list)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for name, entries, error in pool.map(fetch_playlist, SOURCES):
            source_stats.append({"source": name, "count": len(entries), "error": error})
            for entry in entries:
                if allowed(entry["url"]):
                    found[key(entry["name"])].append(entry)

    tasks = []
    for item in channels:
        current = previous.get(key(item["name"]), "")
        locked = bool(item.get("locked"))
        pinned = item.get("last_known_url", "")
        choices = []
        for spelling in [item["name"]] + item.get("aliases", []):
            choices.extend(found.get(key(spelling), []))
        # Previously selected feeds survive transient source outages.
        if current:
            choices.append({"url": current, "logo": "", "source": "previous"})
        if pinned:
            choices.append({"url": pinned, "logo": "", "source": "seed"})
        choices = [c for c in choices if allowed(c["url"], locked and c["url"] == pinned)]
        if locked:
            choices = [c for c in choices if c["url"] == pinned]
        choices.sort(key=lambda c: score(item, c, current), reverse=True)
        seen_urls = set()
        dedup = []
        for c in choices:
            if c["url"] not in seen_urls:
                dedup.append(c)
                seen_urls.add(c["url"])
        tasks.append((item, current, dedup[:9]))

    candidates = []
    for item, old, choices in tasks:
        if not item.get("locked"):
            candidates += [c["url"] for c in choices[:6]]
    candidates = list(dict.fromkeys(candidates))
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        health = dict(zip(candidates, pool.map(probe, candidates)))

    used = set()
    output = ["#EXTM3U", "# Curated IPTV Pro: refreshed by GitHub Actions every 6 hours.",
              "# Manifest checks occur on GitHub, not the user's Link3 Wi-Fi."]
    report = []
    for item, current, choices in tasks:
        chosen = None
        state = "NO_STREAM_AVAILABLE"
        if item.get("locked"):
            chosen = {"url": item["last_known_url"], "logo": "", "source": "user-confirmed"}
            state = "PINNED_USER_WORKING"
        else:
            chosen = next((c for c in choices if health.get(c["url"]) and c["url"] not in used), None)
            if chosen:
                state = "REMOTE_MANIFEST_REACHABLE"
            else:
                old = current or item.get("last_known_url", "")
                if old and allowed(old) and old not in used:
                    chosen = {"url": old, "logo": "", "source": "fallback"}
                    state = "FALLBACK_NOT_REVERIFIED"
        if chosen and chosen["url"] not in used:
            used.add(chosen["url"])
            name = clean(item["name"])
            group = clean(item["group"])
            logo = clean(chosen.get("logo", ""))
            output.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
            output.append(chosen["url"])
        report.append({"name": item["name"], "state": state, "stream": chosen["url"] if chosen else None})
    if len(used) < 4:
        raise ValueError("Refusing to overwrite playlist with fewer than 4 streams")
    final = "\n".join(output) + "\n"
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(final, encoding="utf-8")
    temp.replace(OUTPUT)
    summary = {"updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "channels": len(used), "target_channels": len(channels),
               "groups": dict(Counter(x["group"] for x in channels)),
               "remote_manifests_probed": len(health), "sources": source_stats,
               "channel_status": report,
               "warning": "Remote HLS check does not guarantee Link3 playback, picture quality, buffering or access rights"}
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published", len(used), "streams from", len(channels), "targets")

if __name__ == "__main__":
    main()
