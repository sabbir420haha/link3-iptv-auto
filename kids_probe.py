#!/usr/bin/env python3
"""Read-only HLS manifest/segment test for public Sonic Hindi, Sonic Bangla and Hungama sources.
Checked from GitHub Actions, not from the end user's Link3 ISP. Never alters playlist.
"""
import concurrent.futures
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

BASE=Path(__file__).resolve().parent
items=json.loads((BASE/"kids_candidate_sources.json").read_text(encoding="utf-8"))["sources"]
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; HLS-Test/1.0)","Accept":"application/vnd.apple.mpegurl,application/x-mpegURL,*/*"}

def fetch(url, timeout=7, readsize=65536):
    req=urllib.request.Request(url,headers=HEADERS)
    with urllib.request.urlopen(req,timeout=timeout) as res:
        return res.geturl(),res.read(readsize),res.headers.get("Content-Type","")

def check(item):
    z={k:item[k] for k in ["kind","label","url","provenance"]}
    z.update({"manifest_ok":False,"segment_ok":False,"video_bytes":0,"resolution":None,"variant_count":0,"error":None})
    u=item["url"]
    # Direct MPEG-TS streams from published playlists are not HLS manifests.
    # Inspect only 1,504 bytes (eight 188-byte TS packets) and require sync,
    # without rebroadcasting/caching video or assuming the channel is correct.
    part=urllib.parse.urlsplit(u)
    no_extension_play = bool(re.fullmatch(r"/play/a[0-9a-z]+",part.path.lower()))
    if part.path.lower().endswith(".ts") or no_extension_play:
        try:
            req=urllib.request.Request(u,headers={**HEADERS,"Range":"bytes=0-1503"})
            with urllib.request.urlopen(req,timeout=10) as res:
                data=res.read(1504)
                ctype=res.headers.get("Content-Type","")
            if no_extension_play and data.lstrip().startswith(b"#EXTM3U"):
                # The endpoint returns HLS text despite having no .m3u8 extension:
                # fall through to manifest parsing and test a media segment too.
                pass
            else:
                z["video_bytes"]=len(data)
                z["segment_ok"]=(len(data)>=752 and
                                all(data[pos]==0x47 for pos in (0,188,376,564)))
                if not z["segment_ok"]:
                    z["error"]=f"No MPEG-TS packet sync (bytes={len(data)}, type={ctype[:60]})"
                return z
        except Exception as e:
            z["error"]=f"{type(e).__name__}: {str(e)[:145]}"
            return z
    # Check published HLS .m3u8 and PHP resolver URLs. Reject HTML replies below.
    if not (part.path.lower().endswith(".m3u8") or
            (part.path.lower().endswith(".php") and
             any(a in part.query.lower() for a in ("id=", "c=", "format=", "e="))) or no_extension_play):
        z["error"]="Unsupported path; cannot establish direct HLS"
        return z
    try:
        for level in range(3):
            url,data,ctype=fetch(u,9)
            if not data.lstrip().startswith(b"#EXTM3U"):
                z["error"]="URL did not return HLS text (may be HTML/auth)"
                return z
            z["manifest_ok"]=True
            t=data.decode("utf-8-sig","replace")
            lines=[v.strip() for v in t.splitlines() if v.strip()]
            options=[]
            for n,line in enumerate(lines[:-1]):
                if line.startswith("#EXT-X-STREAM-INF") and not lines[n+1].startswith("#"):
                    b=re.search(r"BANDWIDTH=(\d+)",line)
                    rs=re.search(r"RESOLUTION=(\d+)x(\d+)",line)
                    options.append((int(rs.group(2)) if rs else 0,int(b.group(1)) if b else 0,urllib.parse.urljoin(url,lines[n+1]),f"{rs.group(1)}x{rs.group(2)}" if rs else None))
            if options:
                z["variant_count"]=max(z["variant_count"],len(options))
                target=max(options,key=lambda a:(a[0],a[1]))
                z["resolution"]=target[3]
                u=target[2]
                continue
            if "#EXTINF:" not in t:
                z["error"]="No playable live media entries in HLS"
                return z
            segs=[v for v in lines if not v.startswith("#")]
            if not segs:
                z["error"]="Empty media segment playlist"
                return z
            # Read only a small range, never cache/rebroadcast full media.
            target=urllib.parse.urljoin(url,segs[0])
            req=urllib.request.Request(target,headers={**HEADERS,"Range":"bytes=0-2047"})
            with urllib.request.urlopen(req,timeout=9) as res:
                data=res.read(2048)
                z["video_bytes"]=len(data)
                z["segment_ok"]=len(data)>256
            return z
        z["error"]="Too many HLS master manifest levels"
        return z
    except Exception as e:
        z["error"]=f"{type(e).__name__}: {str(e)[:145]}"
        return z

with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    result=list(pool.map(check,items))
report={"checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "scope":"GitHub Actions runner, NOT Link3/TV decoder; segment HTTP bytes do NOT establish channel identity/audio",
        "candidate_count":len(items),"manifest_ok":sum(x["manifest_ok"] for x in result),
        "segment_ok":sum(x["segment_ok"] for x in result),
        "results":result}
(BASE/"kids_probe_health.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
for x in result:
    print(x["kind"],x["label"],"manifest",x["manifest_ok"],"segment",x["segment_ok"],"resolution",x["resolution"],"error",x["error"])
print("Summary:",len(result),"checked,",report["manifest_ok"],"manifest,",report["segment_ok"],"segment")
