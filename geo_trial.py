#!/usr/bin/env python3
"""Generate the separate IPTV Pro Favorites TEST playlist from pinned registry.

TEST N means the same URL after every GitHub Actions six-hour refresh.
This script NEVER writes main playlist.m3u or alters channel preferences.
All sources are publicly labelled candidates, not verified Link3 playback.
"""
import datetime
import json
import re
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "favorites_test_registry.json"
MAIN = ROOT / "playlist.m3u"
OUTPUT = ROOT / "geo_trials.m3u"
STATUS = ROOT / "status.json"
EXCLUDED = {"Channel 24", "Sonic Bangla", "Sonic Hindi",
            "Discovery Bangla", "Nat Geo HD Bangla"}

def favorites():
    result = []
    for line in MAIN.read_text(encoding="utf-8").splitlines():
        if (line.startswith("#EXTINF:") and
                'group-title="00 | MY FAVORITES"' in line):
            name = line.split(",", 1)[-1].strip()
            if name not in EXCLUDED:
                result.append(name)
    return result

def usable(url):
    if not isinstance(url, str):
        return False
    parsed = urllib.parse.urlsplit(url)
    return (parsed.scheme in ("http", "https") and bool(parsed.hostname)
            and not parsed.username and not parsed.password)

def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    favorites_list = favorites()
    lines = [
        "#EXTM3U",
        "# Favorites TEST only. Stable source numbers, max 30 distinct URLs per channel.",
        "# Unverified on Link3; identity, language, rights and no-buffer playback not guaranteed.",
        "# No excluded Channel 24 / Sonic / Discovery Bangla / Nat Geo Bangla tests.",
    ]
    counts = {}
    for name in favorites_list:
        record = registry.get("channels", {}).get(name, {})
        candidates = record.get("candidates", [])
        logo = record.get("logo", "")
        group = "9 | TEST - " + name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        seen = set()
        count = 0
        for candidate in candidates[:30]:
            url = candidate["url"]
            num = str(candidate["number"])
            if not usable(url) or url in seen or not re.fullmatch(r"\d{2}", num):
                continue
            seen.add(url)
            title = f"{name} TEST {num}"
            lines.append(
                f'#EXTINF:-1 tvg-id="fav-{slug}-{num}" '
                f'tvg-name="{title}" tvg-logo="{logo}" '
                f'group-title="{group}",{title}'
            )
            lines.append(url)
            count += 1
        counts[name] = count
    # Fail safely: never overwrite a populated test playlist with zero channels.
    expected = sum(len(registry.get("channels", {}).get(n, {}).get("candidates", [])[:30])
                   for n in favorites_list)
    if len(favorites_list) == 0 or sum(counts.values()) != expected:
        raise RuntimeError(
            f"Refusing to publish incomplete TEST playlist: {sum(counts.values())} "
            f"of {expected} registered URLs, {len(favorites_list)} favorites"
        )
    rendered = "\n".join(lines) + "\n"
    OUTPUT.write_text(rendered, encoding="utf-8")
    # Distinct URL bypasses IPTV Pro caches that retained an older empty geo list.
    (ROOT / "favorites_tests.m3u").write_text(rendered, encoding="utf-8")
    status = json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}
    status["bd_geo_trials"] = {
        "updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "channel_count": len(favorites_list),
        "entries": sum(counts.values()),
        "by_name": counts,
        "max_per_channel": 30,
        "stable_test_numbers": True,
        "excluded": sorted(EXCLUDED),
        "warning": "Testing only; streams not verified on user's Link3. Production playlist is not altered. TEST numbers map to fixed registry URLs.",
    }
    STATUS.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("Favorites trials", sum(counts.values()), "from", len(counts), "channels")
    print(counts)

if __name__ == "__main__":
    main()
