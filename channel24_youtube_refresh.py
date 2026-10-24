#!/usr/bin/env python3
"""Best-effort Channel 24 official YouTube Live URL refresh.
Only updates separate Channel 24 YouTube TEST; preserves main Channel 24.
YouTube CDN URLs are short-lived and IPTV Pro playback is not guaranteed.
"""
import datetime
import json
import subprocess
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "channels.json"
PLAYLIST = ROOT / "playlist.m3u"
REPORT = ROOT / "channel24_youtube_status.json"
LIVE_PAGE = "https://www.youtube.com/@Channel24digital/live"
TEST_NAME = "Channel 24 YT HLS TEST"
SAFE_FALLBACK = "https://stream.ottplus.live/live/channel_24_abr/index.m3u8"

def extract():
    cmd = ["yt-dlp", "--no-warnings", "--no-playlist", "--dump-single-json",
           "--skip-download", LIVE_PAGE]
    data = json.loads(subprocess.check_output(cmd, timeout=100, text=True))
    if data.get("live_status") != "is_live":
        raise RuntimeError("Official page is not presently reporting an active live broadcast")
    urls = []
    for fmt in data.get("formats", []):
        url = fmt.get("url", "")
        proto = fmt.get("protocol", "")
        if proto in ("m3u8", "m3u8_native") and url.startswith("https://"):
            urls.append((fmt.get("height") or 0, url))
    if not urls:
        raise RuntimeError("No direct live HLS format; cannot embed YouTube watch page into IPTV Pro")
    urls.sort(reverse=True, key=lambda item: item[0])
    url = urls[0][1]
    host = (urlsplit(url).hostname or "").lower()
    if not (host.endswith(".googlevideo.com") or host == "manifest.googlevideo.com"):
        raise RuntimeError("Extracted HLS host not recognized as Googlevideo")
    exp = parse_qs(urlsplit(url).query).get("expire", [None])[0]
    if exp and int(exp) < datetime.datetime.now(datetime.timezone.utc).timestamp() + 2400:
        raise RuntimeError("YouTube URL expires too soon for scheduled playlist updates")
    # A webpage or HTML response is not a stream. Only publish an HLS manifest.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as response:
        head = response.read(48000).decode("utf-8", errors="replace")
    if not head.startswith("#EXTM3U") or "#EXT-X-" not in head:
        raise RuntimeError("Extracted Googlevideo URL does not return a valid HLS manifest")
    return url, data.get("id"), exp

def main():
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    channels = json.loads(CATALOG.read_text(encoding="utf-8"))
    main_channel = next(c for c in channels if c["name"] == TEST_NAME)
    result = {"checked_utc": now, "channel": TEST_NAME,
              "official_live_page": LIVE_PAGE, "source": "YouTube HLS trial",
              "warning": "Expiring URL; Github scheduler and IPTV Pro playback are not guaranteed"}
    try:
        url, video_id, expire = extract()
        result.update(status="youtube_hls_extracted", video_id=video_id, expires_unix=expire)
    except Exception as exc:
        result.update(status="youtube_unavailable_fallback", error=str(exc))
        # Never write a YouTube watch/live webpage or expired URL into IPTV Pro.
        url = SAFE_FALLBACK

    main_channel["last_known_url"] = url
    main_channel["user_verified_link3"] = False
    main_channel["source_quality_note"] = (
        "TEST-only official Channel 24 YouTube Live HLS trial, not Link3 verified. "
        "Falls back to OTTplus HLS (not YouTube) when extraction fails."
    )
    old = PLAYLIST.read_text(encoding="utf-8")
    lines = old.splitlines(keepends=True)
    updated = False
    for i, line in enumerate(lines):
        if line.startswith("#EXTINF:") and f'tvg-name="{TEST_NAME}"' in line:
            j = i + 1
            while j < len(lines) and lines[j].startswith("#"):
                j += 1
            if j < len(lines):
                lines[j] = url + "\n"
                updated = True
            break
    if not updated:
        raise RuntimeError("Channel 24 entry not found; refusing to modify any other channel")
    CATALOG.write_text(json.dumps(channels, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    PLAYLIST.write_text("".join(lines), encoding="utf-8")
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"])

if __name__ == "__main__":
    main()
