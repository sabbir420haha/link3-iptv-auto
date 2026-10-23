#!/usr/bin/env python3
"""Read-only, runner-only checks of newly discovered public IPTV candidates.
Never changes channels.json, playlist.m3u or pinned user-confirmed streams.
A network-accessible HLS fragment does not establish stream identity,
audio language, broadcast rights, or Link3 IPTV Pro playback.
"""
import concurrent.futures
import datetime
import json
import re
import urllib.parse
from pathlib import Path
from update import fetch_hls_bytes, allowed, direct_media_ok

OUT = Path(__file__).with_name("three_missing_probe.json")
CANDIDATES = [
    {
        "channel": "Disney HD Hindi",
        "url": "http://stream-7b694ce7e.nmbs.top/m3u/Kids/c86abe8bd6.m3u8",
        "evidence": "github.com/technl/Hanssettings - Disney Channel Hindi label (NOT HD evidence)",
        "expected_audio": "hi",
        "min_height": 720,
    },
    {
        "channel": "Sonic Hindi",
        "url": "http://4ce5e2d62ee2c10e43c709f9b87c44d5.streamhost.cc/m3u8/Kids/4415aa98f2f6f59.m3u8",
        "evidence": "github.com/imranemon1/emon - SONIC NICKELODEON SONIC HINDI label",
        "expected_audio": "hi",
    },
    {
        "channel": "Sonic Bangla",
        "url": "https://ott.bingebd.com/live/ngrp:ZXOrtTn-asdt-s78TYU34GTX-03as-f7as-1ffd2-t1682a-sgh32x-zp3e-dsf-3b7aa-ort_621h_sWT564hQW_AQTY1025_sonicPQRT_9653SDE_s9023FGWQ_uiou_f36erxty_fort63_DH/playlist.m3u8",
        "evidence": "github.com/skmasum98/IPTV - Sonic Bangla label",
        "expected_audio": "bn",
    },
    {
        "channel": "Sonic Bangla",
        "url": "http://14.102.123.50:5001/live/1345.m3u",
        "evidence": "github.com/RhqAB/TV - Sonic Bangla label and channel id 1345",
        "expected_audio": "bn",
    },
]

def is_media_fragment(data):
    if direct_media_ok(data):
        return True
    # CMAF fMP4 chunks usually start with styp or moof boxes.
    if len(data) > 512 and any(data[4:8] == x for x in (b"moof", b"styp", b"ftyp", b"mdat")):
        return True
    return False

def test(entry):
    result = {**entry, "manifest_ok": False, "media_segment_verified": False,
              "advertised_max_height": 0, "advertised_audio_languages": [],
              "channel_identity_verified": False, "hindi_or_bangla_audio_verified": False,
              "link3_verified": False, "publish_eligible": False,
              "note": "GitHub runner-only test. Playlist is unchanged."}
    current = entry["url"]
    if not allowed(current):
        result["error"] = "URL excluded by existing source-safety filter"
        return result
    try:
        languages = set()
        for _ in range(4):
            body, _ = fetch_hls_bytes(current, 24000, 9)
            text = body.decode("utf-8-sig", "replace")
            if "#EXTM3U" not in text[:500]:
                result["error"] = "No HLS manifest"
                return result
            if "METHOD=SAMPLE-AES" in text or "KEYFORMAT=" in text:
                result["error"] = "Protected/DRM stream is not supported"
                return result
            result["manifest_ok"] = True
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines:
                if line.startswith("#EXT-X-MEDIA:") and "TYPE=AUDIO" in line:
                    m = re.search(r'LANGUAGE="([^"]+)"', line, re.I)
                    if m:
                        languages.add(m.group(1).lower())
            result["advertised_audio_languages"] = sorted(languages)
            if "#EXT-X-STREAM-INF" in text:
                variants = []
                for i, line in enumerate(lines[:-1]):
                    if line.startswith("#EXT-X-STREAM-INF") and not lines[i+1].startswith("#"):
                        m = re.search(r'RESOLUTION=\d+x(\d+)', line, re.I)
                        height = int(m.group(1)) if m else 0
                        variants.append((height, urllib.parse.urljoin(current, lines[i+1])))
                if not variants:
                    result["error"] = "Master has no valid variant"
                    return result
                height, current = max(variants, key=lambda x: x[0])
                result["advertised_max_height"] = max(result["advertised_max_height"], height)
                continue
            if "#EXTINF" not in text:
                result["error"] = "No media-segment entries"
                return result
            fragments = [urllib.parse.urljoin(current, x) for x in lines if not x.startswith("#")]
            for uri in reversed(fragments[-3:]):
                try:
                    fragment, ctype = fetch_hls_bytes(uri, 8192, 9)
                    if "text/html" in ctype or "application/json" in ctype:
                        continue
                    if is_media_fragment(fragment):
                        result["media_segment_verified"] = True
                        break
                except Exception:
                    pass
            result["hindi_or_bangla_audio_verified"] = entry["expected_audio"] in languages
            if entry.get("min_height") and result["advertised_max_height"] < entry["min_height"]:
                result["note"] += " Disney HD requirement not verified."
            if not result["media_segment_verified"]:
                result["note"] += " No valid MPEG-TS/fMP4 fragment fetched."
            # Channel identity requires independently inspected video/audio or
            # an authenticated provider mapping, not merely a public M3U label.
            return result
        result["error"] = "Nested HLS manifest depth exceeded"
    except Exception as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)[:140]
    return result

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(test, CANDIDATES))
    report = {
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "GitHub Actions network, NOT Link3. No channel identities confirmed.",
        "candidate_count": len(results),
        "verified_media_candidates": sum(bool(x["media_segment_verified"]) for x in results),
        "publication_authorized": False,
        "candidates": results,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Three-channel candidate diagnostics complete:", report["verified_media_candidates"],
          "media candidates of", len(results), "(not published)")

if __name__ == "__main__":
    main()
