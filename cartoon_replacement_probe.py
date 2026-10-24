#!/usr/bin/env python3
"""Read-only HLS checks for replacement Gopal, Shinchan and Bangla cartoon candidates.
Media bytes may depict a paid-subscription notice instead of a cartoon.
Does not validate Hindi audio, broadcaster rights, or Link3 playback.
"""
import concurrent.futures
import datetime
import json
from pathlib import Path
from urllib.parse import urlsplit
from cartoon_stream_probe import probe

ROOT=Path(__file__).resolve().parent
def check(item):
    r=probe({"name":item["label"],"url":item["url"]})
    r["series"]=item["series"]
    r["source"]=item["source"]
    r["declared_language_only"]=("Hindi" in item["label"])
    r["notes"]=item["notes"]
    r["hostname"]=urlsplit(item["url"]).hostname
    return r

def main():
    items=json.loads((ROOT/"cartoon_replacement_candidates.json").read_text(encoding="utf-8"))["candidates"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        results=list(pool.map(check,items))
    report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "checked":len(results),
            "manifests":sum(bool(x["manifest_ok"]) for x in results),
            "media_segments":sum(bool(x["media_sample_ok"]) for x in results),
            "warning":"A successful media segment may still be subscription-renewal video; no stream image/audio verified. 24/7 show identity and Hindi language NOT verified, Link3 untested.",
            "results":results}
    (ROOT/"cartoon_replacement_health.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for x in results: print(x["name"],"manifest",x["manifest_ok"],"media",x["media_sample_ok"],"error",x.get("error") or x.get("segment_error") or "")
if __name__=="__main__":
    main()
