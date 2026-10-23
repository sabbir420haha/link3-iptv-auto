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
    ("SM-IPTV", "https://raw.githubusercontent.com/sm-monirulislam/SM-IPTV/main/Combined_Live_TV.m3u"),
    ("iptv-org-india-raw", "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/in.m3u"),
]

# These are candidate public URLs only, not a guarantee of rights or playback.
EXTRA_CANDIDATES = {
    "Hungama HD": [
        "http://ajkiptv.ridsys.in/riptv/live/HUNGAMA/index.m3u8",
        "http://103.185.24.134:3001/HUNGAMA/index.m3u8",
        "http://66.102.126.10:8000/play/a023/index.m3u8",
        "http://111.88.78.21:8000/play/a0z1/index.m3u8",
    ],
    "Zee Bangla HD": [
        "https://stream.ottplus.bd/live/zee_bangla_abr/live/zee_bangla_720/chunks.m3u8",
        "https://raw.githubusercontent.com/amazeyourself/adaptive-streams/refs/heads/main/streams/in/YuppTV/ZeeBanglaHD.m3u8",
        "https://tvsen6.aynaott.com/ZeeBangla/index.m3u8",
    ],
    "Discovery Bangla": [
        "http://103.180.212.191:3500/live/573.m3u8",
        "http://202.70.146.135:8000/play/a05z/index.m3u8",
        "https://ccntv.anytv.live/discoverybangla/index.m3u8",
        "https://food-dlvr-ott.akamaized.net/primary/4/686a061683e44b518cdf57677e352ef3/index_21.m3u8",
        "https://varun-iptv.netlify.app/m3u/discoverybengali.m3u8",
        "https://jioplaylistdown.yecic62314.workers.dev/live.m3u8?id=573",
    ],
    "Nick Hindi": [
        "https://jiotvmblive.cdn.jio.com/bpk-tv/Nick_voot_MOB/output03/index.m3u8",
        "https://madplay.live/jiotv/app/live/545/null/index.m3u8",
        "https://snehapi.in1.bitmana.io/jioapi/snehjioxx.php?c=Nick_Hindi&q=800&e=junk.m3u8",
        "https://fifabangladesh2-xyz-ekkj.spidy.online/VHOD/NEW/go.php?id=Nick_voot_MOB",
    ],
    "Sonic Bangla": ["http://live.balajibroadband.com:3500/live/1345.m3u8"],
    "Sonic Hindi": [
        "https://sar.pages.dev/sonic.m3u8",
        "https://robi.iptv.digijadoo.net/live/sonic/chunks.m3u8",
        "https://snehapi.in1.bitmana.io/jioapi/snehjioxx.php?c=sonic_Hindi&q=800&e=junk.m3u8",
    ],
    "Sony MAX HD": [
        "https://dai.google.com/linear/hls/event/UcjHNJmCQ1WRlGKlZm73QA/master.m3u8",
        "https://pubads.g.doubleclick.net/ssai/event/Qyqz40bSQriqSuAC7R8_Fw/master.m3u8",
    ],
    "Sony Ten 1 HD": [
        "http://103.83.80.54:6088/play/a0ol/index.m3u8",
        "http://103.214.202.218:8081/live/ten1hd/chunks.m3u8",
        "https://pubads.g.doubleclick.net/ssai/event/yeYP86THQ4yl7US8Zx5eug/master.m3u8",
        "https://dai.google.com/linear/hls/event/wG75n5U8RrOKiFzaWObXbA/master.m3u8",
        "https://sliv.tgaadi.workers.dev/ten1hd.m3u8",
    ],
    "Nat Geo HD Bangla": ["http://tv.pmcon.net/hls/stream13.m3u8"],
    "Sony Ten 3 HD": [
        "http://103.83.80.54:6088/play/a0om/index.m3u8",
        "http://103.214.202.218:8081/live/ten3hd/chunks.m3u8",
        "http://103.99.249.139/sonyten3/index.m3u8",
        "https://pubads.g.doubleclick.net/ssai/event/nmQFuHURTYGQBNdUG-2Qdw/master.m3u8",
        "https://dai.google.com/linear/hls/event/ltsCG7TBSCSDmyq0rQtvSA/master.m3u8",
        "https://sliv.tgaadi.workers.dev/ten3hd.m3u8",
        "https://ott.bingebd.com/live/ngrp:APNTn-asdt-t1asnd2a-sWgtsrhQW_AQTY1025_sony_ten_3PQRT_98sdfhs0_f36erxty_forsgst63_DH/chunklist.m3u8",
    ],
}

def key(value):
    name = re.sub(r"\s*\(\d{3,4}p\)\s*", "", value or "", flags=re.I)
    name = re.sub(r"\s*\[(geo-blocked|not 24/7)\]\s*", "", name, flags=re.I)
    return re.sub(r"[^a-z0-9]+", "", name.lower().replace("&", "and"))

# Public IP addresses explicitly appearing in the iptv-org Hungama TV catalogue.
# All private, loopback and link-local IPs remain blocked.
PUBLIC_HUNGAMA_IPS = {"103.185.24.134", "66.102.126.10", "111.88.78.21",
    "103.180.212.191", "202.70.146.135", "103.83.80.54", "103.214.202.218", "103.99.249.139"}

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
            if not locked and host not in PUBLIC_HUNGAMA_IPS:
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
                               if health.get(c["url"]) and (not item.get("requires_media_segment") or segments.get(c["url"])) and heights.get(c["url"], 0) >= minimum
                               and c["url"] not in used), None)
            elif item.get("prefer_current") and current and health.get(current) and (not item.get("requires_media_segment") or segments.get(current)) and current not in used:
                chosen = next((c for c in choices if c["url"] == current), None)
            else:
                chosen = next((c for c in choices if health.get(c["url"]) and (not item.get("requires_media_segment") or segments.get(c["url"])) and c["url"] not in used), None)
            if chosen:
                state = ("REMOTE_HD_MANIFEST" if item.get("quality") == "hd"
                         else "BEST_AVAILABLE_NOT_VERIFIED_HD" if item.get("quality") == "best_available"
                         else "REMOTE_MANIFEST_REACHABLE")
            else:
                old = current or item.get("last_known_url", "")
                if old and not item.get("quality") and not item.get("skip_unverified_fallback") and allowed(old) and matches_channel(item, old) and old not in item.get("exclude_urls",[]) and old not in used:
                    chosen = {"url": old, "logo": "", "source": "fallback"}
                    state = "FALLBACK_NOT_REVERIFIED"
        if chosen and chosen["url"] not in used:
            used.add(chosen["url"])
            name = clean(item["name"])
            group = clean(item["group"])
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
    summary = {"updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "channels": len(used), "target_channels": len(channels),
               "groups": dict(Counter(x["group"] for x in channels)),
               "remote_manifests_probed": len(health), "media_segments_probed": len(segments), "sources": source_stats,
               "channel_status": report,
               "warning": "Remote HLS check does not guarantee Link3 playback, picture quality, buffering or access rights"}
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published", len(used), "streams from", len(channels), "targets")

if __name__ == "__main__":
    main()
