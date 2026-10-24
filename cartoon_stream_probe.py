#!/usr/bin/env python3
"""Read-only HTTP checks for cartoon live HLS candidates (GitHub network only).
This does not assert Link3 playback, copyright permissions or program identity.
"""
import concurrent.futures
import datetime
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CAT=ROOT/"cartoon_stream_candidates.json"
OUT=ROOT/"cartoon_stream_health.json"

def fetch(url, timeout=11):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/vnd.apple.mpegurl, */*"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        data=resp.read(128*1024)
        return resp.geturl(),data,resp.headers.get("Content-Type","")

def probe(item):
    record={"name":item["name"],"url":item["url"],"manifest_ok":False,
            "media_sample_ok":False,"status":"unverified Link3/rights/audio"}
    try:
        u,b,ct=fetch(item["url"])
        s=b.decode("utf-8","replace")
        if not s.lstrip().startswith("#EXTM3U"):
            record["error"]="response is not M3U8"
            return record
        record["manifest_ok"]=True
        media_urls=[]
        for line in s.splitlines():
            if line.strip() and not line.startswith("#"):
                media_urls.append(urllib.parse.urljoin(u,line.strip()))
        record["entries"]=len(media_urls)
        # A successful master playlist is not media proof; follow one video
        # variant, then sample its first actual segment (byte-range limited).
        current_url,current_text=u,s
        if "#EXT-X-STREAM-INF" in s and media_urls:
            current_url,media,ct=fetch(media_urls[0],timeout=9)
            current_text=media.decode("utf-8","replace")
            if not current_text.startswith("#EXTM3U"):
                record["error"]="variant did not return M3U8"
                return record
        chunks=[]
        for line in current_text.splitlines():
            if line.strip() and not line.startswith("#"):
                chunks.append(urllib.parse.urljoin(current_url,line.strip()))
        if "#EXTINF:" in current_text and chunks:
            try:
                target=chunks[0]
                req=urllib.request.Request(target,headers={"User-Agent":"Mozilla/5.0","Range":"bytes=0-1023"})
                with urllib.request.urlopen(req,timeout=9) as resp:
                    sample=resp.read(1024)
                record["media_sample_ok"]=len(sample)>100
                record["segment_bytes_sampled"]=len(sample)
            except Exception as ex:
                record["segment_error"]=str(ex)[:160]
        else:
            record["error"]="no conventional media segment in returned manifest"
    except Exception as ex:
        record["error"]=str(ex)[:160]
    return record

def main():
    o=json.loads(CAT.read_text(encoding="utf-8"))
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        res=list(pool.map(probe,o["sources"]))
    summary={"checked_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "manifest_count":sum(bool(x["manifest_ok"]) for x in res),
             "media_sample_count":sum(bool(x["media_sample_ok"]) for x in res),
             "warning":"GitHub runner HTTP check, not Link3 test, channel identity, audio language, or license verification. Not a zero-buffer claim.",
             "results":res}
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for x in res:
        print(x["name"],"manifest",x["manifest_ok"],"media",x["media_sample_ok"],x.get("error",""))

if __name__=="__main__":
    main()
