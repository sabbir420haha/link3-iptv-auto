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
    ("SM-IPTV", "https://raw.githubusercontent.com/sm-monirulislam/SM-IPTV/main/Combined_Live_TV.m3u"),
    ("iptv-org-india-raw", "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/in.m3u"),
    ("indian-kids-special", "https://raw.githubusercontent.com/arshdeep1112/Indian-IPTV/main/channels/iptv_kids.m3u8"),
    ("Bengali-public-collection", "https://raw.githubusercontent.com/skmasum98/IPTV/master/myiptv.m3u8"),
    ("public-SonyLIV-candidates", "https://raw.githubusercontent.com/PrattoySaha/IPTV/main/Not%20working.m3u8"),
    ("public-Indian-family-candidates", "https://raw.githubusercontent.com/anasselkadii/jcartoondashboard/main/epesodes/toffee.m3u8"),
    ("fresh-India-weekly-verified", "https://raw.githubusercontent.com/gnaidu05/iptv/main/playlists/india-active.m3u"),
    ("fresh-India-public-geo", "https://raw.githubusercontent.com/gnaidu05/iptv/main/playlists/india-geo.m3u"),
    ("updated-Hindi-streams", "https://raw.githubusercontent.com/wizakorhd/iptv/main/playlist-hindi.m3u"),
    ("updated-Hindi-top", "https://raw.githubusercontent.com/wizakorhd/iptv/main/playlist-top.m3u"),
    ("recent-BD-India", "https://raw.githubusercontent.com/md-sayem-hossain/My-BD-IPTV-Playlist/main/playlist.m3u"),
]

# These are candidate public URLs only, not a guarantee of rights or playback.
EXTRA_CANDIDATES = {
    # The original user-confirmed Hungama is pinned separately and never replaced.
    "Hungama HD": [
        "http://103.185.24.134:3001/HUNGAMA/index.m3u8",
        "http://66.102.126.10:8000/play/a023/index.m3u8",
    ],
    "Zee Bangla HD": [
        "https://tvsen6.aynaott.com/ZeeBangla/index.m3u8",
        "https://raw.githubusercontent.com/amazeyourself/adaptive-streams/refs/heads/main/streams/in/YuppTV/ZeeBanglaHD.m3u8",
    ],
    # New candidates from published GitHub playlists; none are claimed working.
    # Segment testing from GitHub Actions determines if they are published.
    "Discovery Bangla": [
        "https://khulnalive.anytv.live/discoverybangla/index.m3u8",
        "https://ccntv.anytv.live/discoverybangla/index.m3u8",
    ],
    "Disney HD Hindi": [
        "https://kingkohli.pages.dev/Play/DisneyHD_Watch_index.m3u8",
        "https://disneyhindi-lh.akamaihd.net/i/disneyhindi_1@174991/master.m3u8",
        "http://202.70.146.135:8000/play/a01q/index.m3u8",
        "http://4ce5e2d62ee2c10e43c709f9b87c44d5.streamhost.cc/m3u8/Kids/8f3e6367117c923.m3u8",
    ],
    "Nick Hindi": [
        "http://103.153.175.254:8080/hls/stream23.m3u8",
        "https://madplay.live/jiotv/app/live/545/null/index.m3u8",
        "https://snehapi.in1.bitmana.io/jioapi/snehjioxx.php?c=Nick_Hindi&q=800&e=junk.m3u8",
    ],
    "Sonic Hindi": [
        "http://4ce5e2d62ee2c10e43c709f9b87c44d5.streamhost.cc/m3u8/Kids/4415aa98f2f6f59.m3u8",
        "https://robi.iptv.digijadoo.net/live/sonic/chunks.m3u8",
    ],
    "Sonic Bangla": [
        "http://live.balajibroadband.com:3500/live/1345.m3u8",
    ],
    "Sony MAX HD": [
        "https://stream.ottplus.bd/live/max_hd_abr/live/max_hd_720/chunks.m3u8",
        "https://stream.ottplus.bd/live/max_hd_abr/index.m3u8",
        "https://stream.ottplus.bd/live/sony_max_sd_abr/live/sony_max_sd_720/chunks.m3u8",
        "https://cdn.rangdhanu.live/SonyMaxHD/video.m3u8",
        "http://208.86.19.13:81/7066.stream/index.m3u8",
        "http://dx3.gcdn.co/hindi-SONYMAXHD/index.m3u8",
        "http://103.185.24.134:3001/SonyMAX/index.m3u8",
        "http://103.151.60.162:2122/play/a014/index.m3u8?hls",
        "https://nitro-x-methods.shop/NITRO-X-TOFFEE/master.m3u8/?id=set_max_hd",
    ],
    "Sony Ten 1 HD": [
        "https://feed.play.mv/live/10005200/fMLTkj4OJC/master.m3u8",
        "http://103.185.24.134:3001/SonyTenSports1/index.m3u8",
    ],
    "Sony Ten 3 HD": [
        "https://feed.play.mv/live/10005200/RG2fKR6d9p/master.m3u8",
        "https://cloudplay-sonyliv.pages.dev/ten3.m3u8",
    ],
    "Nat Geo HD Bangla": [
        "http://103.89.248.130:8082/National-geo-graphy-bangla/index.m3u8",
        "http://103.55.144.46/hls/ngohd.m3u8",
        "http://103.153.175.254:8080/hls/stream13.m3u8",
    ],
}

def key(value):
    name = re.sub(r"\s*\(\d{3,4}p\)\s*", "", value or "", flags=re.I)
    name = re.sub(r"\s*\[(geo-blocked|not 24/7)\]\s*", "", name, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", name.lower().replace("&", "and"))

# Public IP addresses explicitly appearing in the iptv-org Hungama TV catalogue.
# All private, loopback and link-local IPs remain blocked.
# Only these PUBLIC numeric IPs from named public M3U catalogues are eligible.
# BDIX-named/private hosts remain blocked. GitHub then checks actual HLS bytes.
ALLOWED_PUBLIC_NUMERIC_IPS = {
    "103.185.24.134", "66.102.126.10", "103.151.60.162",
    "103.153.175.254", "103.89.248.130", "103.55.144.46",
    "202.70.146.135", "208.86.19.13",
}

def allowed(url, locked=False):
    try:
        p = urllib.parse.urlsplit(url)
        if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
            return False
        host = p.hostname.lower().strip(".")
        if host == "localhost" or host.endswith((".local", ".internal", ".lan")):
            return False
        if any(x in url.lower() for x in ("bdix", "tplay", "t-play", "192.168.", "10.0.0.")):
            return False
        if any(x in p.query.lower() for x in ("token=", "auth=", "expires=", "signature=", "hdnea=", "session=")):
            return False
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return False
            # Reject unknown public IPs, known internal IPs, and ISP-only numeric streams.
            if not locked and host not in ALLOWED_PUBLIC_NUMERIC_IPS:
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

def segment_probe(url):
    """Two-level HLS check: verify playlist and at least one actual media fragment.
    Verify HTTP response bytes, not just #EXTM3U or an HTML redirect.
    Runs from GitHub's network, so Link3 ISP-specific success is not guaranteed.
    """
    def get(uri, cap=24576):
        if not allowed(uri):
            raise ValueError("filtered remote URL")
        request=urllib.request.Request(uri,headers={**HEADERS,"Range":"bytes=0-8191"})
        with urllib.request.urlopen(request,timeout=9) as response:
            if response.status not in (200,206):
                raise ValueError("HTTP status " + str(response.status))
            data=response.read(cap)
            if not data:
                raise ValueError("empty response")
            return data,response.headers.get("Content-Type","").lower()

    try:
        current=url
        for depth in range(3):
            body,_=get(current,24000)
            text=body.decode("utf-8-sig",errors="replace")
            if "#EXTM3U" not in text[:500]:
                return False
            if "#EXT-X-KEY" in text and ("METHOD=SAMPLE-AES" in text or "KEYFORMAT=" in text):
                return False  # no protected/DRM stream support
            lines=[line.strip() for line in text.splitlines() if line.strip()]
            if "#EXT-X-STREAM-INF" in text:
                variants=[]
                for i,line in enumerate(lines[:-1]):
                    if line.startswith("#EXT-X-STREAM-INF") and not lines[i+1].startswith("#"):
                        match=re.search(r'RESOLUTION=\d+x(\d+)',line)
                        variants.append((int(match.group(1)) if match else 0,lines[i+1]))
                if not variants:
                    return False
                # Highest advertised quality. Test an actual segment at that rendition.
                current=urllib.parse.urljoin(current,max(variants,key=lambda v:v[0])[1])
                continue
            if "#EXTINF" not in text:
                return False
            uris=[line for line in lines if not line.startswith("#")]
            # Probe a recent segment, not an old expired segment.
            for target in reversed(uris[-3:]):
                fragment=urllib.parse.urljoin(current,target)
                try:
                    data,ctype=get(fragment,4096)
                    if data.startswith((b"<!DOCTYPE",b"<html",b"<?xml",b"#EXTM3U")):
                        continue
                    if b"mpegurl" in ctype.encode() or "text/html" in ctype or "application/json" in ctype:
                        continue
                    if len(data)>188:  # real transport/MP4 segment, not empty placeholder
                        return True
                except Exception:
                    continue
            return False
    except Exception:
        return False
    return False

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

def hd_resolution(url):
    """Return best height advertised by an HLS variant manifest.
    For a direct media playlist, an explicit /720/ or _720/ path is a hint,
    not a verified resolution; such streams are not considered HD here.
    """
    if not allowed(url):
        return 0
    try:
        request = urllib.request.Request(url, headers={**HEADERS, "Range": "bytes=0-16383"})
        with urllib.request.urlopen(request, timeout=9) as response:
            if response.status not in (200, 206):
                return 0
            body = response.read(16384).decode("utf-8-sig", errors="replace")
        if "#EXTM3U" not in body:
            return 0
        heights = [int(m.group(1)) for m in re.finditer(r'RESOLUTION=\d+x(\d+)', body, re.I)]
        return max(heights) if heights else 0
    except Exception:
        return 0

def matches_channel(item, url):
    """Reject known false positives from worldwide channel lists."""
    label = item["name"]
    url_low = url.lower()
    wrong = {
        "News 24": ("balkanweb.com",),  # News24 Albania is NOT Bangladesh News24
        "R Plus Gold": ("rplusnews24x7",),  # R Plus News is a different channel
        "Sony Ten 1 HD": ("dropbox.com", "badminton1.m3u8"),
        "Sony Ten 3 HD": ("dropbox.com",),
        "Star Sports 1 Hindi": ("pages.dev",),
        "Colors Bangla": ("/preview/",),
    }
    return not any(x in url_low for x in wrong.get(label, ()))

def score(item, entry, old):
    url = entry["url"]
    host = urllib.parse.urlsplit(url).hostname or ""
    value = 15 if url.startswith("https:") else 0
    if item.get("requires_media_segment") and entry["source"] == "curated-candidate":
        value += 65  # Check newly discovered replacements before old aliases.
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
    if len(channels) < 101 or sum(bool(x.get("locked")) for x in channels) != 4:
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
        choices.extend({"url": u, "logo": "", "source": "curated-candidate"}
                       for u in EXTRA_CANDIDATES.get(item["name"], []))
        # Previously selected feeds survive transient source outages.
        if current:
            choices.append({"url": current, "logo": "", "source": "previous"})
        if pinned:
            choices.append({"url": pinned, "logo": "", "source": "seed"})
        choices = [c for c in choices if allowed(c["url"], locked and c["url"] == pinned)
                   and matches_channel(item, c["url"])
                   and c["url"] not in item.get("exclude_urls", [])
                   and (not item.get("only_curated") or c["source"] in ("curated-candidate", "previous"))]
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
    hd_urls = list(dict.fromkeys(c["url"] for item, old, choices in tasks
                   if item.get("quality") == "hd" for c in choices[:6] if health.get(c["url"])))
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        heights = dict(zip(hd_urls, pool.map(hd_resolution, hd_urls)))
    priority_urls = list(dict.fromkeys(c["url"] for item, old, choices in tasks
                    if item.get("requires_media_segment") for c in choices[:9]
                    if health.get(c["url"])))
    with concurrent.futures.ThreadPoolExecutor(max_workers=14) as pool:
        segments = dict(zip(priority_urls, pool.map(segment_probe, priority_urls)))

    used = set()
    experimental_count = 0
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
            if item.get("quality") == "hd":
                minimum = int(item.get("min_height", 720))
                chosen = next((c for c in choices
                               if health.get(c["url"]) and (not item.get("requires_media_segment") or segments.get(c["url"])) and (heights.get(c["url"], 0) >= minimum or (item.get("requires_media_segment") and heights.get(c["url"], 0) == 0))
                               and c["url"] not in used), None)
            elif item.get("prefer_current") and current and health.get(current) and (not item.get("requires_media_segment") or segments.get(current)) and current not in used:
                chosen = next((c for c in choices if c["url"] == current), None)
            else:
                chosen = next((c for c in choices if health.get(c["url"]) and (not item.get("requires_media_segment") or segments.get(c["url"])) and c["url"] not in used), None)
            if chosen:
                state = ("REMOTE_HD_MANIFEST" if item.get("quality") == "hd" and heights.get(chosen["url"], 0)>=720
                         else "REMOTE_HLS_SEGMENT_RESOLUTION_UNVERIFIED" if item.get("quality") == "hd"
                         else "BEST_AVAILABLE_NOT_VERIFIED_HD" if item.get("quality") == "best_available"
                         else "REMOTE_MANIFEST_REACHABLE")
            else:
                old = current or item.get("last_known_url", "")
                if old and not item.get("quality") and not item.get("skip_unverified_fallback") and allowed(old) and matches_channel(item, old) and old not in item.get("exclude_urls",[]) and old not in used:
                    chosen = {"url": old, "logo": "", "source": "fallback"}
                    state = "FALLBACK_NOT_REVERIFIED"
            if not chosen and item.get("allow_unverified"):
                for candidate_url in item.get("experimental_urls", []):
                    if (allowed(candidate_url) and candidate_url not in item.get("exclude_urls", [])
                            and candidate_url not in used and matches_channel(item,candidate_url)):
                        chosen = {"url": candidate_url, "logo": "", "source": "experimental"}
                        state = "EXPERIMENTAL_NOT_PLAYBACK_VERIFIED"
                        experimental_count += 1
                        break
        if chosen and chosen["url"] not in used:
            used.add(chosen["url"])
            name = clean(item["name"])
            group = clean("98 | TEST - Unverified Non-BDIX" if state == "EXPERIMENTAL_NOT_PLAYBACK_VERIFIED" else item["group"])
            logo = clean(chosen.get("logo", ""))
            output.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}')
            output.append(chosen["url"])
        report.append({"name": item["name"], "state": state,
                       "stream": chosen["url"] if chosen else None,
                       "manifest_height": heights.get(chosen["url"], 0) if chosen else 0,
                       "media_segment_checked": bool(segments.get(chosen["url"],False)) if chosen else False})
    if len(used) < 4:
        raise ValueError("Refusing to overwrite playlist with fewer than 4 streams")
    final = "\n".join(output) + "\n"
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(final, encoding="utf-8")
    temp.replace(OUTPUT)
    # Keep per-candidate diagnostics for the channels the user specifically wants.
    # An HTTP HLS manifest is NOT equivalent to a playable video segment.
    candidate_audit = []
    for target, old, alternatives in tasks:
        if not target.get("requires_media_segment"):
            continue
        candidate_audit.append({
            "name": target["name"],
            "candidates": [
                {"source": e["source"], "url": e["url"],
                 "manifest_ok": bool(health.get(e["url"])),
                 "segment_ok": bool(segments.get(e["url"])),
                 "manifest_height": heights.get(e["url"], 0)}
                for e in alternatives[:9]
            ],
            "note": "Checked from GitHub Actions, not Link3. No DRM/geo bypass."
        })
    summary = {"updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "channels": len(used), "target_channels": len(channels),
               "groups": dict(Counter(x["group"] for x in channels)),
               "remote_manifests_probed": len(health), "media_segments_probed": len(segments),
               "experimental_unverified": experimental_count,
               "candidate_audit": candidate_audit, "sources": source_stats,
               "channel_status": report,
               "warning": "Channels in 98 TEST Experimental are unverified public playlist candidates, NOT known working. Remote checks do not prove Link3 playback, rights, HD quality or buffering"}
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published", len(used), "streams from", len(channels), "targets")

if __name__ == "__main__":
    main()
