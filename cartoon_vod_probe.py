#!/usr/bin/env python3
"""Test real MP4 VOD assets using a small HTTP range; don't download full films.
Checks bytes and probable MP4 signature; no link to an OTT watch page is accepted.
"""
import concurrent.futures
import datetime
import json
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent
DATA=ROOT/"cartoon_vod_catalog.json"
OUT=ROOT/"cartoon_vod_health.json"

def check(item):
    url=item["url"]
    info={"title":item["title"],"url":url,"http_ok":False,"bytes_ok":False,"content_type":None,"error":None}
    parts=urlsplit(url)
    if parts.scheme!="https" or not parts.path.lower().endswith(".mp4"):
        info["error"]="Not an HTTPS MP4 resource";return info
    try:
        req=urllib.request.Request(url,headers={"Range":"bytes=0-4095","User-Agent":"Mozilla/5.0","Accept":"video/mp4, */*"})
        with urllib.request.urlopen(req,timeout=17) as rsp:
            info["status_code"]=rsp.status
            info["content_type"]=rsp.headers.get("Content-Type","")
            body=rsp.read(4096)
        info["http_ok"]=info["status_code"] in (200,206)
        info["bytes_ok"]=bool(len(body)>=16 and body[4:8]==b"ftyp")
        info["sample_size"]=len(body)
    except Exception as err: info["error"]=str(err)[:170]
    return info

def main():
    catalog=json.loads(DATA.read_text(encoding="utf-8"))
    entries=catalog["free_cartoons_demo"]+[episode for show in catalog["requested_series"] for episode in show["episodes"]]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(check,entries))
    report={"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total":len(results),"playable_mp4_signatures":sum(x["bytes_ok"] for x in results),
            "warning":"GitHub server MP4 byte signature checked only; IPTV Pro and Link3 playback not established.",
            "results":results}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for row in results:print(row["title"],row["http_ok"],row["bytes_ok"],row["content_type"],row["error"])
if __name__=="__main__":main()
