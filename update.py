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
    ("fresh-Bangladesh-genre", "https://raw.githubusercontent.com/tahsinulmohsin/jagobd-m3u8-scraper/master/playlist.m3u8"),
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
    ("2026-India-experimental", "https://raw.githubusercontent.com/ttmttm/iptv_2026/master/streams/in.m3u"),
    ("public-cartoon-2026", "https://raw.githubusercontent.com/hmripon66/cartoon-iptv-by-TechEduByte/main/Cartoon%20by%20techedubyte.m3u8"),
    ("regional-sports-2026", "https://raw.githubusercontent.com/8figalltimepro/special-train/main/HINDI%26sports%281%29.m3u8"),
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
        # Pattern-only probes on the server that already plays the user's
        # Hungama, Duronto, Nick Bangla and Nat Geo Bangla. Not sourced links
        # and never published unless the server returns a valid video segment.
        "http://103.135.253.32:8080/DISCOVERY-BANGLA/index.m3u8",
        "http://103.135.253.32:8080/DISCOVERY-BENGALI/index.m3u8",
        "http://103.135.253.32:8080/DISCOVERY-HD-BANGLA/index.m3u8",
        # AirtelXstream's explicitly named Bengali channel; HLS variant is
        # a candidate, not confirmed public/open or DRM-free.
        "https://load.airtelxstream.in/discoverychannelbengali/smil:common.smil/playlist.m3u8?DVR",
        # Publicly published explicitly as Bengali/Bangla, not generic Discovery HD.
        "https://app-re.sm-monirul-islam-rs.workers.dev/discovery-bangla/index.m3u8",
        "http://103.89.248.130:8082/DISCOVERY-BANGLA/index.m3u8",
        "http://103.180.212.191:3500/live/573.m3u8",
        "http://103.17.193.159:5001/live/573.m3u8",
        "http://103.107.79.87:8080/CH8110HD08/video.m3u8",
        "http://175.107.244.52:4455/play/a01v/index.m3u8",
        # Independent 2026 public list, labelled Discovery Bengali.
        "http://103.159.180.34:5001/live/573.m3u8",
        # Named Discovery Bangla in independent public catalogues.
        "http://103.229.254.25:7001/play/a03g/index.m3u8",
        "http://103.107.79.87:8080/CH8110HD08/tracks-v1a1/mono.m3u8",
        "https://cdn1-freeiptv25.vercel.app/m3u/discoverybengali.m3u8",
        "https://food-dlvr-ott.akamaized.net/primary/4/686a061683e44b518cdf57677e352ef3/index_19.m3u8",
        "https://starplay2.netlify.app/m3u/discoverybengali.m3u8",
        "http://iptv.kitv.live:1935/live/CTGDDN/CTGDDN/61.ts",
        "https://food-dlvr-ott.akamaized.net/primary/4/686a061683e44b518cdf57677e352ef3/index_21.m3u8",
        "https://khulnalive.anytv.live/discoverybangla/index.m3u8",
        "https://ccntv.anytv.live/discoverybangla/index.m3u8",
    ],
    "Disney HD Hindi": [
        # Disney Channel HD (1080p) named in an independent iptv-org-derived list.
        "http://66.102.120.18:8000/play/a013/index.m3u8",
        # Disney Channel Hindi+English audio per the approved 2026 iptv-org issue;
        # source only lists SD/576p, thus strict HD validation rejects if not HD.
        "http://ptu.ridsys.in/riptv/live/DISNEY_CHANNEL/index.m3u8",
        "http://ajkiptv.ridsys.in/riptv/live/DISNEY_CHANNEL/index.m3u8",
        "http://103.182.170.32:8888/play/a04g",
        # Public directory explicitly identifies this as Disney CHANNEL, not Junior.
        "http://139.23.241.38:8088/602/tracks-v1a1/mono.m3u8",
        # Independently labelled Disney Channel, not Disney Junior; HD/audio unverified.
        "http://ott.artmott.com/DisneyChannel/tracks-v1a1/mono.m3u8",
        # Listed as Disney CHANNEL (not Junior) by the Indian IPTV catalogues.
        # The first is SD and NOT asserted to be HD or Hindi-audio verified.
        "http://116.90.120.149:8000/play/a0bx/index.m3u8",
        "https://live.dinesh29.com.np/stream/jiotvplus/disneychannel/master.m3u8",
        "https://tvsen7.aynaott.com/disney/index.m3u8",
        "https://yowaimo.in/Sflex-ArtlPVT0719/DISNEY_CHANNEL.m3u8",
        "http://181.119.215.61:8000/play/a0g1/index.m3u8",
        "http://66.102.126.10:8000/play/a013/index.m3u8",
        "http://116.90.120.151:8000/play/a0hp/index.m3u8",
        "http://103.162.136.235:4500/play/a01g/index.m3u8",
        "https://kingkohli.pages.dev/Play/DisneyHD_Watch_index.m3u8",
        "https://disneyhindi-lh.akamaihd.net/i/disneyhindi_1@174991/master.m3u8",
        "http://202.70.146.135:8000/play/a01q/index.m3u8",
        "http://4ce5e2d62ee2c10e43c709f9b87c44d5.streamhost.cc/m3u8/Kids/8f3e6367117c923.m3u8",
    ],
    "Nick Hindi": [
        # Published Indian Nick from the identical Hungama IP, audio unverified.
        "http://103.135.253.32:8080/NICK/index.m3u8",
        "https://tvsen7.aynaott.com/nicklodean/index.m3u8",
        "http://103.185.24.134:3001/NICK/index.m3u8",
        "http://103.162.136.235:4500/play/a01f/index.m3u8",
        "http://149.71.34.166:8000/play/a00u/index.m3u8",
        "http://103.153.175.254:8080/hls/stream23.m3u8",
        "https://madplay.live/jiotv/app/live/545/null/index.m3u8",
        "https://snehapi.in1.bitmana.io/jioapi/snehjioxx.php?c=Nick_Hindi&q=800&e=junk.m3u8",
    ],
    "Duronto TV": [
        # Same public host as user-confirmed Hungama: strongest untried candidate.
        "http://103.135.253.32:8080/DORONTU-TV/index.m3u8",
        "https://tvsen5.aynaott.com/6xyZ3N4oHv2KBJdB6W4p/index.fmp4.m3u8",
        "https://tvsen6.aynaott.com/6xyZ3N4oHv2KBJdB6W4p/tracks-v1a1/mono.ts.m3u8",
        "https://app24.jagobd.com.bd/c3VydmVyX8RpbEU9Mi8xNy8yMFDEEHGcfRgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcEdsEfeDeKiNkVN3PTOmdFseWRtaW51aiPhnPTI2/duronto.stream/tracks-v1a1/mono.m3u8",
        "https://tvsen4.aynaott.com/durontotv/index.m3u8",
        "https://tvsen5.aynaott.com/durontotv/index.m3u8",
        "https://box.bbaria.net/DurontoTV/index.m3u8",
        "http://103.106.243.163:8989/duronto-tv/index.m3u8",
        "http://27.147.156.14:1935/Durunto-TV/Duronto-TV.stream/playlist.m3u8",
        "http://89.187.185.89:3232/ban-duronto/index.m3u8",
        "http://ctgiptv.kitv.live:1935/live/ASNet/asnetwork/12.m3u8",
    ],
    "Sonic Hindi": [
        # Fresh India/Nepal iptv-org Sonic 576p (audio language not yet confirmed).
        "http://103.185.24.134:3001/SONIC/index.m3u8",
        "http://144.217.70.181:9587/hin2/SONIC/tracks-v1a1/mono.m3u8",
        "https://prod-sports-hin-fa.jiocinema.com/bpk-tv/JC_SonicNick/JCHLS/index.m3u8",
        "https://live.dinesh29.com.np/stream/jiotvplus/sonichindi/master.m3u8",
        "http://198.195.239.50:8095/sonic/tracks-v1a1/mono.m3u8",
        "http://103.151.60.162:2122/play/a02v/index.m3u8?hls",
        "https://live20.bozztv.com/giatvplayout7/giatv-209622/index.m3u8",
        "http://103.229.254.25:7001/play/a0dl/index.m3u8",
        "http://103.72.101.252:8080/live/815.m3u8",
        "http://103.162.136.235:4500/play/a01k/index.m3u8",
        "http://4ce5e2d62ee2c10e43c709f9b87c44d5.streamhost.cc/m3u8/Kids/4415aa98f2f6f59.m3u8",
        "https://robi.iptv.digijadoo.net/live/sonic/chunks.m3u8",
    ],
    "Sonic Bangla": [
        # Published as Sonic Bengali in public lists; audio still needs viewer check.
        "http://103.180.212.191:3500/live/1345.m3u8",
        "http://103.17.193.159:5001/live/1345.m3u8",
        "http://14.102.123.50:5001/live/1345.m3u8",
        # Listed as Sonic Bangla in a 2026 channel collection.
        "http://103.204.43.87:8080/live/1/1/274.m3u8",
        "http://198.195.239.50:8095/sonic/tracks-v1a1/mono.m3u8",
        "https://snehjiotv.in1.bitmana.io/snehjioox.php?c=Sonic_Bangla&q=1200&e=junk.m3u8",
        "https://edge01.iptv.digijadoo.net/live/sonic/chunks.m3u8",
        "https://edge01.iptv.digijadoo.net/live/sonic/playlist.m3u8",
        "http://live.balajibroadband.com:3500/live/1345.m3u8",
    ],
    "Sony MAX HD": [
        "https://drk6xq0vhn.gpcdn.net/live/max_hd_abr/index.m3u8",
        "https://sl.vodep39240327.workers.dev/channel/SONY%20MAX%20HD.m3u8",
        "https://stream.ottplus.live/live/max_hd_abr/index.m3u8",
        "https://stream.ottplus.live/live/max_hd_abr/live/max_hd_720/chunks.m3u8",
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
        "https://drk6xq0vhn.gpcdn.net/live/ten_1_hd_abr/index.m3u8",
        "https://stream.ottplus.live/live/ten_1_hd_abr/live/ten_1_hd_720/chunks.m3u8",
        "https://stream.ottplus.live/live/ten_1_hd_abr/live/ten_1_hd_720/index.m3u8",
        "http://103.162.136.235:4500/play/a018/index.m3u8",
        "https://sl.vodep39240327.workers.dev/channel/SONY%20TEN%201%20HD.m3u8",
        "https://feed.play.mv/live/10005200/fMLTkj4OJC/master.m3u8",
        "http://103.185.24.134:3001/SonyTenSports1/index.m3u8",
    ],
    "Sony Ten 3 HD": [
        # Keep user-confirmed TEN-3 SD-looking stream pinned. Check HD origin separately.
        "https://tataplay.slivcdn.com/hls/live/2020591/TEN3HD/master.m3u8",
        # Same exact public IP as the 3 Link3-verified Hungama/Nick/Duronto streams.
        # Publicly listed as Sony Ten 3 (resolution not established).
        "http://103.135.253.32:8080/TEN-3/index.m3u8",
        "http://66.102.120.18:8000/play/a00z/index.m3u8",
        "http://103.122.74.6:8888/hls/SONY.SPORTS.3.m3u8",
        "http://103.84.57.155:8000/play/a02q/index.m3u8",
        "http://103.162.136.235:4500/play/a01d/index.m3u8",
        "https://sl.vodep39240327.workers.dev/channel/SONY%20TEN%203%20HD.m3u8",
        "https://feed.play.mv/live/10005200/RG2fKR6d9p/master.m3u8",
        "https://cloudplay-sonyliv.pages.dev/ten3.m3u8",
    ],
    "Nat Geo HD Bangla": [
        "http://103.81.104.222/live/national-geographic/index.m3u8",
        # India/English audio is possible; not asserted Bangla unless confirmed.
        "http://103.135.253.32:8080/NATGEO-HD/index.m3u8",
        "https://tvsen6.aynaott.com/natgeo/index.m3u8",
        "http://103.167.167.5:8111/play/a036/index.m3u8",
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
# Accept any truly globally routable public IP. Source hosts explicitly marked
# BDIX and non-global/private/reserved IP addresses remain filtered.
# GitHub Actions validates HLS bytes from outside the Bangladesh ISP network.

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
            # A globally routable IP is not automatically BDIX-only.
            # Segment probing still determines whether an offered feed is accessible.
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

def direct_media_ok(data):
    """Accept only MPEG-TS sync bytes or MP4 ftyp, never HTML or fake placeholder."""
    if len(data) < 564 or data[:1] == b"<":
        return False
    if data[0] == 0x47 and data[188] == 0x47 and data[376] == 0x47:
        return True
    return b"ftyp" in data[:20] and len(data) >= 1000


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
                return direct_media_ok(body) if current == url else False
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
            chunk = response.read(4096)
        return ("#EXTM3U" in chunk.decode("utf-8-sig", errors="replace")
                and ("#EXT-X-" in chunk.decode("utf-8-sig", errors="replace")
                     or "#EXTINF" in chunk.decode("utf-8-sig", errors="replace"))) or direct_media_ok(chunk)
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
    if host == "103.135.253.32" and item.get("requires_media_segment"):
        # Link3 user plays Hungama from this exact host. Only rank other
        # channels higher IF their own video segment is independently checked.
        value += 35
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
    required_pins = {"Hungama", "Sony Aath", "Channel 24", "Independent TV"}
    actual_pins = {x["name"] for x in channels if x.get("locked")}
    # User specifically excluded six non-playing channels. Never silently restore them.
    user_excluded = {"Jago News 24", "TBN24", "Green TV", "Nexus TV",
                     "Colors Bangla", "Aakaash Aath"}
    all_names = {x["name"] for x in channels}
    if (len(channels) < 98 or not required_pins.issubset(actual_pins)
            or user_excluded.intersection(all_names)):
        raise ValueError("Channel catalog, excluded names, or original pinned streams unexpectedly changed")
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
        limit = 24 if item["name"] == "Discovery Bangla" else 9
        tasks.append((item, current, dedup[:limit]))

    candidates = []
    for item, old, choices in tasks:
        if not item.get("locked"):
            limit = 24 if item["name"] == "Discovery Bangla" else 6
            candidates += [c["url"] for c in choices[:limit]]
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
    verified_backups = []
    # Backup URLs are from the same public server as user-tested Hungama.
    # Publish ONLY if a distinct, real video segment is independently readable.
    backups_by_name = {
        "Duronto TV": "http://103.135.253.32:8080/DORONTU-TV/index.m3u8",
        "Nat Geo HD Bangla": "http://103.135.253.32:8080/NATGEO-HD/index.m3u8",
    }
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
                               if health.get(c["url"]) and (not item.get("requires_media_segment") or segments.get(c["url"])) and (heights.get(c["url"], 0) >= minimum or (item.get("requires_media_segment") and not item.get("strict_hd_manifest") and heights.get(c["url"], 0) == 0))
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
            alternate = backups_by_name.get(item["name"])
            if (alternate and alternate not in used and alternate != chosen["url"]
                    and allowed(alternate) and health.get(alternate) and segments.get(alternate)
                    and alternate not in item.get("exclude_urls", [])):
                used.add(alternate)
                alt_title = name + " (Backup - Hungama IP)"
                output.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="" group-title="{group}",{alt_title}')
                output.append(alternate)
                verified_backups.append({"name": item["name"], "url": alternate,
                                         "media_segment_checked": True,
                                         "label": "Alternate video source, user playback not yet checked"})
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
                for e in alternatives[:24 if target["name"] == "Discovery Bangla" else 9]
            ],
            "note": "Checked from GitHub Actions, not Link3. No DRM/geo bypass."
        })
    summary = {"updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "channels": len(used), "target_channels": len(channels),
               "groups": dict(Counter(x["group"] for x in channels)),
               "remote_manifests_probed": len(health), "media_segments_probed": len(segments),
               "experimental_unverified": experimental_count,
               "backup_streams": verified_backups,
               "candidate_audit": candidate_audit, "sources": source_stats,
               "channel_status": report,
               "warning": "Channels in 98 TEST Experimental are unverified public playlist candidates, NOT known working. Remote checks do not prove Link3 playback, rights, HD quality or buffering"}
    REPORT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Published", len(used), "streams from", len(channels), "targets")

if __name__ == "__main__":
    main()
