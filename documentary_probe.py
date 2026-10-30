#!/usr/bin/env python3
"""Probe documentary candidates from GitHub runner; NEVER modify playlist.m3u.
Only publish HD (>=720 pixels high) entries with a readable real video segment.
Remote checks cannot establish Link3 accessibility or confirm Bengali speech.
"""
import concurrent.futures as cf
import datetime as dt
import ipaddress
import json
import re
import subprocess
import tempfile
import urllib.parse as up
import urllib.request as req
from pathlib import Path

ROOT=Path(__file__).resolve().parent
POOL=json.loads((ROOT/"documentary_candidates.json").read_text())["candidates"]
OUT=ROOT/"documentary_probe_results.json"
PLAY=ROOT/"documentary_hd_tests.m3u"
LOGO="https://raw.githubusercontent.com/sabbir420haha/link3-iptv-auto/main/logos"
HEADERS={"User-Agent":"VLC/3.0.20 LibVLC/3.0.20","Accept":"*/*"}

def fetch(url,maxbytes=160000):
    u=up.urlsplit(url)
    if u.scheme not in ("http","https") or not u.hostname or u.username or u.password:
        raise ValueError("bad_url")
    try:
        ip=ipaddress.ip_address(u.hostname)
        if not ip.is_global: raise ValueError("non_public_ip")
    except ValueError as err:
        if str(err)=="non_public_ip": raise
    request=req.Request(url,headers=HEADERS)
    with req.urlopen(request,timeout=7) as res:
        code=res.status
        payload=res.read(maxbytes)
        mime=res.headers.get("content-type","")
        actual=res.url
        if code>=400: raise ValueError("HTTP "+str(code))
    return payload,actual,mime

def ffprobe(buf):
    with tempfile.NamedTemporaryFile(suffix=".ts") as f:
        f.write(buf);f.flush()
        try:
            raw=subprocess.run(["ffprobe","-v","error","-probesize","500000",
                                "-analyzeduration","1500000","-show_streams","-of","json",f.name],
                               capture_output=True,text=True,timeout=5).stdout
            streams=json.loads(raw).get("streams",[])
        except Exception: streams=[]
    video=[v for v in streams if v.get("codec_type")=="video"]
    h=max([int(v.get("height",0)) for v in video]+[0])
    lang=[str(v.get("tags",{}).get("language","")) for v in streams if v.get("codec_type")=="audio"]
    return h,lang

def manifest(url,depth=0):
    if re.search(r"(?:[?&]mac=|/play/live\\.php|/stalker/)",url,re.I):
        raise ValueError("credential_bound_portal_rejected")
    if depth>3: raise ValueError("nested_master")
    body,actual,mime=fetch(url)
    s=body.decode("utf-8","replace").lstrip("\ufeff")
    if "#EXTM3U" not in s[:200]: 
        if body[:1]==b"G" or len(body)>10000:
            height,audio=ffprobe(body)
            return height,audio,"transport",len(body)
        raise ValueError("not_hls")
    lines=[l.strip() for l in s.splitlines() if l.strip()]
    if "#EXT-X-STREAM-INF" in s:
        opts=[]
        for i,line in enumerate(lines[:-1]):
            if line.startswith("#EXT-X-STREAM-INF"):
                a=re.search(r"RESOLUTION=\d+x(\d+)",line)
                h=int(a.group(1)) if a else 0
                nxt=next((v for v in lines[i+1:] if not v.startswith("#")),None)
                if nxt: opts.append((h,up.urljoin(actual,nxt)))
        if not opts: raise ValueError("master_no_variant")
        advertised,url2=max(opts,key=lambda t:t[0])
        real,langs,typ,size=manifest(url2,depth+1)
        return max(real,advertised),langs,"master+"+typ,size
    if "#EXTINF" not in s and "#EXT-X-MAP" not in s: raise ValueError("no_hls_media")
    seg=next((lines[i+1] for i,line in enumerate(lines[:-1])
              if line.startswith("#EXTINF") and not lines[i+1].startswith("#")),None)
    if not seg:
        seg=next((v for v in lines if not v.startswith("#")),None)
    if not seg: raise ValueError("no_segment")
    data,_,ct=fetch(up.urljoin(actual,seg),1000000)
    if len(data)<512 or b"#EXTM3U" in data[:100]:
        raise ValueError("empty_or_fake_segment")
    if ct.lower().startswith("text/html") or b"<html" in data[:256].lower():
        raise ValueError("html_not_video")
    # Check TS sync byte / MP4 atoms; ffprobe may additionally recognize video.
    ts=(data[0]==0x47 or data[:1]==b"G")
    mp4=(b"ftyp" in data[:20] or b"moof" in data[:30] or b"styp" in data[:20])
    height,langs=ffprobe(data)
    if not (ts or mp4 or height>=144): raise ValueError("segment_not_video")
    for line in lines:
        if line.startswith("#EXT-X-MEDIA") and "TYPE=AUDIO" in line:
            m=re.search(r'LANGUAGE="([^"]+)"',line)
            if m: langs.append(m.group(1))
    return height,langs,"media",len(data)

def run(item):
    row={k:item[k] for k in ("id","channel","url","source")}
    try:
        h,l,t,n=manifest(item["url"])
        row.update({"status":"hd_video_verified" if h>=720 else "video_but_not_hd_confirmed",
                    "height":h,"audio_language_tags":l,"format":t,"segment_bytes":n,
                    "bengali_metadata":any(x.lower() in ("bn","ben","bengali") for x in l)})
    except Exception as e: row.update({"status":"failed","error":str(e)[:240]})
    return row

def main():
    with cf.ThreadPoolExecutor(max_workers=12) as pool:
        results=list(pool.map(run,POOL))
    publish=[x for x in results if x["status"]=="hd_video_verified"]
    doc=["#EXTM3U","# Remote GitHub runner verified real HD video segments; NOT Link3-verified.",
         "# Bengali spoken audio NOT guaranteed (unless metadata says so).",
         "# No MAIN source URLs or failed sources. Select TEST by number."]
    counts={}
    for item in publish:
        name=item["channel"]
        counts[name]=counts.get(name,0)+1
        num=str(counts[name]).zfill(2)
        slug="discovery-bangla" if name=="Discovery Bangla" else "nat-geo-hd-bangla"
        title=f"{name} NEW HD TEST {num}"
        doc.append(f'#EXTINF:-1 tvg-id="probe-{slug}-{num}" tvg-name="{title}" tvg-logo="{LOGO}/{slug}.png" group-title="HD VIDEO CHECKED | {name}",{title}')
        doc.append(item["url"])
    PLAY.write_text("\n".join(doc)+"\n")
    stats={"checked_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"checked_count":len(results),
           "hd_segment_verified_count":len(publish),
           "note":"GitHub network only. Video height observed/advertised; Bengali AUDIO and Link3 playback unverified.",
           "results":results}
    OUT.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"checked":len(results),"hd_video_verified":len(publish),
          "media_but_not_hd_confirmed":sum(x["status"]=="video_but_not_hd_confirmed" for x in results),
          "failed":sum(x["status"]=="failed" for x in results)}))
if __name__=="__main__": main()
