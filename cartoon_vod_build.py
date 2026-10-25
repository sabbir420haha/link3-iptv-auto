#!/usr/bin/env python3
"""Build an on-demand M3U from media you own or are licensed to stream.

No download, scraper, access-token extraction, DRM bypass or content rehosting.
Only real media URLs are written to the file. Empty requested series are skipped.
Source: cartoon_vod_catalog.json; verified demo: cartoon_vod_health.json.
Never changes the live or Favorites playlists.
"""
import json
import re
import urllib.parse
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CATALOG=ROOT/"cartoon_vod_catalog.json"
HEALTH=ROOT/"cartoon_vod_health.json"
OUTPUT=ROOT/"cartoon_vod.m3u"
VIDEO_EXTS=(".mp4",".m3u8",".m4v",".webm",".mov",".mkv")

def safe(value):
    return str(value).replace('"',"'").replace("\n"," ").replace("\r"," ").strip()

def direct_video(url):
    u=urllib.parse.urlsplit(url)
    return u.scheme=="https" and u.hostname and any(u.path.lower().endswith(ext) for ext in VIDEO_EXTS)

def main():
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    report=json.loads(HEALTH.read_text(encoding="utf-8"))
    approved_samples={r["url"] for r in report.get("results",[]) if r.get("http_ok") and r.get("bytes_ok")}
    out=["#EXTM3U",
         "# VOD content: direct MP4/HLS media only, NO pages or live TV.",
         "# Public example titles are CC-licensed Blender films. Check own media rights.",
         "# Full movie and 10-sec samples are labelled separately, never misleadingly as requested cartoons."]
    seen=set()
    records=[]
    # Preserve the same first four videos that were confirmed on Link3.
    pinned=("Big Buck Bunny - Full Movie (W3C)", "Big Buck Bunny - 10s Video Test",
            "Big Buck Bunny - Short Intro", "Sintel - 10s Video Sample")
    items=catalog["free_cartoons_demo"]
    items=sorted(items, key=lambda item: (0,pinned.index(item["title"])) if item["title"] in pinned else (1,catalog["free_cartoons_demo"].index(item)))
    for episode in items:
        if episode["url"] not in approved_samples:
            continue
        name=episode["title"]
        if "Backup" in name:
            group="CARTOON VOD | Backup URLs"
        elif "PG - Scary" in name:
            group="CARTOON VOD | PG - Scary"
        elif "Full" in name or "Operation Barbershop" in name:
            group="CARTOON VOD | Full Movies"
        else:
            group="CARTOON VOD | Short Clips"
        records.append((episode,group))
    for required in pinned:
        if not any(ep["title"]==required for ep,_ in records):
            raise ValueError("Missing previously working VOD episode: "+required)
    for show in catalog["requested_series"]:
        lang_req=show["required_language"]
        for ep in show["episodes"]:
            if not ep.get("authorized_for_streaming",False):
                raise ValueError("Episode must have affirmative streaming authorization")
            if lang_req!="any" and ep.get("language")!=lang_req:
                raise ValueError(f'{show["series"]}: required {lang_req}, got {ep.get("language")}')
            ep={**ep,"series":show["series"]}
            records.append((ep,"CARTOON VOD | "+show["series"]))
    for idx,(ep,group) in enumerate(records,1):
        url=ep["url"]
        if not direct_video(url) or url in seen:
            raise ValueError(f"Not unique direct HTTPS media: {safe(ep.get('title',idx))}")
        seen.add(url)
        title=safe(ep["title"])
        out.append(f'#EXTINF:-1 tvg-id="vod-{idx:03d}" tvg-name="{title}" group-title="{safe(group)}",{title}')
        out.append(url)
    OUTPUT.write_text("\n".join(out)+"\n",encoding="utf-8")
    print("VOD episodes:",len(records),"Requested series episodes:",sum(len(s["episodes"]) for s in catalog["requested_series"]))

if __name__=="__main__":main()
