#!/usr/bin/env python3
"""Non-destructive Channel24 geo candidates quick network check.
Checks from GitHub runner only, never claims Link3 playback or 0-buffer.
Does not update M3U playlists, channel sources or production catalogue.
"""
import concurrent.futures
import datetime
import json
from pathlib import Path
from urllib.parse import urlsplit
from update import probe, segment_probe

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/"channel24_geo_candidates.json"
OUTPUT=ROOT/"channel24_geo_probe.json"

def inspect(item):
    url=item["url"]
    label=item["label"]
    reachable=probe(url)
    media=segment_probe(url) if reachable else False
    return {
        "label":label,
        "host":urlsplit(url).hostname,
        "manifest_or_media_reachable_from_github":reachable,
        "media_segment_readable_from_github":media,
        "link3_playback":"NOT_TESTED",
        "noted_referer":bool(item.get("referrer")),
    }

def main():
    catalog=json.loads(INPUT.read_text(encoding="utf-8"))
    sources=catalog["sources"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results=list(pool.map(inspect, sources))
    report={
        "checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "checked_count":len(results),
        "media_segment_pass_count":sum(x["media_segment_readable_from_github"] for x in results),
        "warning":"Github-network checks, NOT Link3 or IPTV Pro. A failing host may work inside an ISP; successful bytes do not prove Channel24 identity or no buffering. No source URLs modified.",
        "results":results,
    }
    OUTPUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for r in results:
        print(r["label"],"manifest=",r["manifest_or_media_reachable_from_github"],
              "media=",r["media_segment_readable_from_github"])

if __name__=="__main__":
    main()
