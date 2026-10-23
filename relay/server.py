#!/usr/bin/env python3
"""Password-protected, in-memory delayed HLS test relay; no DRM support.

Server keeps ~15s behind live and proactively fetches source video segments.
This does NOT force IPTV Pro's own player to buffer. Run on always-on hosting.
Main playlist.m3u is read-only; trial creates a separate M3U endpoint.
"""
import hashlib
import ipaddress
import json
import math
import os
import re
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
TOKEN = os.getenv("RELAY_TOKEN", "")
PORT = int(os.getenv("PORT", "8080"))
DELAY = max(8, min(30, int(os.getenv("HLS_DELAY_SECONDS", "15"))))
NAMES = {"channel24": "Channel 24", "hungama": "Hungama",
         "zeebangla": "Zee Bangla"}
CHANNELS = {}


def get(url, limit):
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Invalid source URL")
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        ip = None
    if ip is not None and not ip.is_global:
        raise ValueError("Private upstream IP blocked")
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 NUHASH-IPTV-Relay",
                                "Accept": "application/vnd.apple.mpegurl, */*"})
    with urlopen(req, timeout=9) as r:
        data = r.read(limit+1)
    if len(data) > limit:
        raise ValueError("Response size limit exceeded")
    return data


def resolve(url):
    for _ in range(3):
        text = get(url, 180000).decode("utf-8-sig", "replace")
        if not text.startswith("#EXTM3U"):
            raise ValueError("Invalid HLS")
        if "#EXT-X-KEY:" in text or "#EXT-X-MAP:" in text:
            raise ValueError("Protected or fragmented sources not supported")
        if "#EXTINF:" in text:
            return url
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        variants = []
        for i, line in enumerate(lines[:-1]):
            if line.startswith("#EXT-X-STREAM-INF") and not lines[i+1].startswith("#"):
                h = re.search(r"RESOLUTION=\d+x(\d+)", line)
                b = re.search(r"BANDWIDTH=(\d+)", line)
                variants.append((int(h.group(1)) if h else 0,
                                 int(b.group(1)) if b else 0,
                                 urljoin(url, lines[i+1])))
        if not variants:
            raise ValueError("Unsupported master playlist")
        candidates = [x for x in variants if x[0] <= 720 and
                      (x[1] == 0 or x[1] <= 3000000)]
        url = max(candidates or variants, key=lambda x: (x[0], x[1]))[2]
    raise ValueError("Too many nested HLS playlists")


def parse(url):
    text = get(url, 180000).decode("utf-8-sig", "replace")
    if not text.startswith("#EXTM3U") or "#EXTINF:" not in text:
        raise ValueError("Not a live media manifest")
    if "#EXT-X-KEY:" in text or "#EXT-X-MAP:" in text:
        raise ValueError("Protected/fMP4 media not supported")
    m = re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)", text)
    seq = int(m.group(1)) if m else 0
    duration, entries = None, []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            duration = float(line.split(":")[1].split(",")[0])
        elif duration is not None and line and not line.startswith("#"):
            entries.append((seq, max(.2, min(16., duration)),
                            urljoin(url, line)))
            seq += 1
            duration = None
    return entries[-18:]


class Channel:
    def __init__(self, slug, name, origin, logo):
        self.slug, self.name, self.origin, self.logo = slug, name, origin, logo
        self.lock = threading.RLock()
        self.cache = OrderedDict()
        self.pending = set()
        self.media_url = None
        self.last_poll = 0
        self.error = "Warming source"
        self.pool = ThreadPoolExecutor(max_workers=4)

    def fetch_segment(self, key, seq, duration, url):
        try:
            data = get(url, 7000000)
            if len(data) < 188 or data.startswith((b"<html", b"<!DOCTYPE", b"#EXTM3U")):
                raise ValueError("No video bytes")
            with self.lock:
                self.cache[key] = (seq, duration, time.monotonic(), data)
                self.error = ""
        except Exception as exc:
            with self.lock:
                self.error = type(exc).__name__ + ": " + str(exc)[:95]
        finally:
            with self.lock:
                self.pending.discard(key)

    def poll(self):
        while True:
            try:
                if self.media_url is None:
                    self.media_url = resolve(self.origin)
                entries = parse(self.media_url)
                with self.lock:
                    self.last_poll = time.monotonic()
                    for seq, duration, url in entries:
                        key = hashlib.sha256(url.encode()).hexdigest()[:24]
                        if key not in self.cache and key not in self.pending:
                            self.pending.add(key)
                            self.pool.submit(self.fetch_segment, key, seq, duration, url)
                    now = time.monotonic()
                    for key, item in list(self.cache.items()):
                        if now-item[2] > 85:
                            self.cache.pop(key)
                    while sum(len(x[3]) for x in self.cache.values()) > 40000000:
                        self.cache.popitem(last=False)
            except Exception as exc:
                with self.lock:
                    self.error = type(exc).__name__ + ": " + str(exc)[:95]
                self.media_url = None
            time.sleep(1.5)

    def ready(self):
        with self.lock:
            now = time.monotonic()
            result = [(x[0], x[1], key) for key, x in self.cache.items()
                      if now-x[2] >= DELAY]
        result.sort()
        contiguous = []
        for item in result:
            if contiguous and item[0] != contiguous[-1][0]+1:
                contiguous = []
            contiguous.append(item)
        return contiguous[-10:]

    def segment(self, key):
        with self.lock:
            val = self.cache.get(key)
            return val[3] if val else None


def load_channels():
    text = (ROOT / "playlist.m3u").read_text(encoding="utf-8")
    items = {}
    name = logo = ""
    for line in text.splitlines():
        if line.startswith("#EXTINF:"):
            name = line.rsplit(",", 1)[-1].strip()
            m = re.search(r'tvg-logo="([^"]+)"', line)
            logo = m.group(1) if m else ""
        elif line.startswith(("https://", "http://")) and name:
            items[name] = (line.strip(), logo)
            name = ""
    missing = set(NAMES.values())-set(items)
    if missing:
        raise ValueError("Missing test channels: " + ", ".join(sorted(missing)))
    return {slug: Channel(slug, title, *items[title])
            for slug, title in NAMES.items()}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return  # Never log bearer token in URL.

    def send(self, code, body, mime="text/plain", retry=False):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if retry:
            self.send_header("Retry-After", "3")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/health":
            self.send(200, json.dumps({
                "delay_seconds": DELAY,
                "channels": {key: {"cached": len(ch.cache),
                                   "error": ch.error}
                             for key, ch in CHANNELS.items()}
            }), "application/json")
            return
        prefix = "/t/" + TOKEN + "/"
        if not TOKEN or not path.startswith(prefix):
            self.send(404, "Not found")
            return
        suffix = path[len(prefix):]
        if suffix == "playlist.m3u":
            lines = ["#EXTM3U", "# Separate 15s-delay RELAY TEST; main playlist unchanged"]
            for key, ch in CHANNELS.items():
                lines += ['#EXTINF:-1 tvg-logo="' + ch.logo +
                          '" group-title="15s RELAY TEST",' + ch.name,
                          prefix + key + ".m3u8"]
            self.send(200, "\n".join(lines)+"\n", "audio/x-mpegurl")
        elif suffix.endswith(".m3u8") and "/" not in suffix:
            key = suffix[:-5]
            if key not in CHANNELS:
                self.send(404, "Not found")
                return
            chunks = CHANNELS[key].ready()
            if not chunks:
                self.send(503, "Buffer warming", retry=True)
                return
            header = ["#EXTM3U", "#EXT-X-VERSION:3",
                      "#EXT-X-TARGETDURATION:" +
                      str(math.ceil(max(c[1] for c in chunks))),
                      "#EXT-X-MEDIA-SEQUENCE:" + str(chunks[0][0])]
            for _, duration, digest in chunks:
                header += ["#EXTINF:" + str(round(duration, 3)) + ",",
                           prefix + "segment/" + key + "/" + digest + ".ts"]
            self.send(200, "\n".join(header)+"\n",
                      "application/vnd.apple.mpegurl")
        else:
            match = re.fullmatch(r"segment/([a-z0-9]+)/([a-f0-9]{24})\.ts", suffix)
            if not match or match.group(1) not in CHANNELS:
                self.send(404, "Not found")
                return
            data = CHANNELS[match.group(1)].segment(match.group(2))
            if data is None:
                self.send(404, "Segment expired")
            else:
                self.send(200, data, "video/mp2t")


def main():
    if not re.fullmatch(r"[A-Za-z0-9_-]{24,128}", TOKEN):
        raise SystemExit("Set long secret RELAY_TOKEN in hosting settings")
    global CHANNELS
    CHANNELS = load_channels()
    for ch in CHANNELS.values():
        threading.Thread(target=ch.poll, daemon=True).start()
    print("Starting limited HLS relay with", DELAY,
          "seconds delay and", len(CHANNELS), "channels", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
