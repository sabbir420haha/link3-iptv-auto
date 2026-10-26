#!/usr/bin/env python3
"""Read-only remote Hungama HLS probes.

Sources in hungama_test3_sources.json are published test candidates, NOT
confirmed on Link3 and not guaranteed legally available in each region.
Never changes any existing playlist or "locked" production stream.
"""
import concurrent.futures
import datetime
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SRC=ROOT/"hungama_test3_sources.json"
OUT=ROOT/"hungama_test3_health.json"

def check(item):
    record={"id":item["id"],"url":item["url"],"bucket":item["bucket"],
            "manifest_ok":False,"segment_ok":False,
            "error":None}
    if not item["url"].lower().split("?")[0].endswith(".m3u8"):
        record["error"]="No direct m3u8 extension (kept as IPTV Pro trial)"
        return record
    def get(url,timeout=7):
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0",
                 "Accept":"application/vnd.apple.mpegurl, application/x-mpegURL, */*"})
        with urllib.request.urlopen(req,timeout=timeout) as response:
            return response.geturl(),response.read(96*1024),response.headers.get("Content-Type","")
    try:
        url,data,ctype=get(item["url"],8)
        if not data.lstrip().startswith(b"#EXTM3U"):
            record["error"]="Not an HLS manifest (maybe HTML/auth/redirect)"
            return record
        record["manifest_ok"]=True
        txt=data.decode("utf-8","replace")
        references=[urllib.parse.urljoin(url,l.strip()) for l in txt.splitlines() if l.strip() and not l.startswith("#")]
        if "#EXT-X-STREAM-INF" in txt and references:
            url,data,ctype=get(references[0],7)
            txt=data.decode("utf-8","replace")
        segments=[urllib.parse.urljoin(url,l.strip()) for l in txt.splitlines() if l.strip() and not l.startswith("#")]
        if "#EXTINF:" in txt and segments:
            target=segments[0]
            req=urllib.request.Request(target,headers={"User-Agent":"Mozilla/5.0","Range":"bytes=0-1023"})
            with urllib.request.urlopen(req,timeout=7) as resp:
                record["segment_ok"]=len(resp.read(1024))>100
        else: record["error"]="No readable media segment in HLS variant"
    except Exception as e:
        record["error"]=str(e)[:150]
    return record

def main():
    src=json.loads(SRC.read_text(encoding="utf-8"))["sources"]
    # CDN/recent sources first; remain conservative about remote request load.
    ordered=sorted(src,key=lambda s:0 if s["bucket"] in ("CDN","recent") else 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        results=list(pool.map(check,ordered))
    report={"checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "scope":"GitHub Actions runner only, NEVER Link3 ISP",
       "checked":len(results),
       "manifest_count":sum(bool(x["manifest_ok"]) for x in results),
       "segment_count":sum(bool(x["segment_ok"]) for x in results),
       "warning":"Video bytes do not independently establish actual Hungama TV identity, Hindi audio, legal rights or playback on Link3.",
       "results":results}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for r in results:print(r["id"],r["url"],"manifest",r["manifest_ok"],"segment",r["segment_ok"],r["error"])
if __name__=="__main__":
    main()
