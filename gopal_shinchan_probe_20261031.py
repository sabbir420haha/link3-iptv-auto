#!/usr/bin/env python3
"""Independent, non-invasive one-time candidate HLS media checks; no playlist changes."""
import concurrent.futures, datetime, json, subprocess, ssl, urllib.error, urllib.parse, urllib.request
from pathlib import Path

CANDIDATES = {
    "gopal_tplay_kids_path": "https://tplay.live/playlist/kids/gopal-bhar/index.m3u8",
    "shinchan_bdott_named": "http://bd.ottbd.online:2082/live/Durjoy859/01327184859/19978.m3u8",
    "shinchan_ranapk_hindi_named": "https://ranapkx.site/RANAPK33k/TVD/play.php?id=734314&e=.m3u8",
}
UA = "VLC/3.0.20 LibVLC/3.0.20"
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"*/*"})
    with urllib.request.urlopen(req,timeout=18,context=ssl._create_unverified_context() if "tplay.live" in url else None) as res:
        return {"status":res.status,"url":res.url,"type":res.headers.get("Content-Type",""),"data":res.read(16000)}
def check(pair):
    label,url=pair
    o={"name":label,"url":url,"status":"unverified","manifest_valid":False,"media_bytes_valid":False,"video_decoded":False,"show_verified":False,"hindi_audio_verified":False}
    try:
        f=fetch(url)
        o.update(http=f["status"],final_url=f["url"],content_type=f["type"],first_bytes=f["data"][:55].decode("utf8","replace"))
        txt=f["data"].decode("utf8","replace")
        if "#EXTM3U" not in txt[:120]: raise RuntimeError("not HLS manifest")
        o["manifest_valid"]=True
        parent=f["url"]
        if "#EXT-X-STREAM-INF" in txt:
            lines=[line.strip() for line in txt.splitlines() if line.strip()]
            for i,line in enumerate(lines[:-1]):
                if line.startswith("#EXT-X-STREAM-INF"):
                    parent=urllib.parse.urljoin(parent,lines[i+1]);f=fetch(parent);txt=f["data"].decode("utf8","replace");break
        if "#EXTINF" not in txt:raise RuntimeError("not a media playlist")
        segment=next((s.strip() for s in txt.splitlines() if s.strip() and not s.strip().startswith("#")),None)
        if not segment:raise RuntimeError("no media segment")
        sf=fetch(urllib.parse.urljoin(parent,segment))
        b=sf["data"]
        o.update(segment_http=sf["status"],segment_bytes=len(b),segment_prefix_hex=b[:12].hex())
        if len(b)<1000 or b.startswith(b"<html") or b.startswith(b"<!DOCTYPE"):raise RuntimeError("no fresh media bytes")
        o["media_bytes_valid"]=True
        cmd=["ffprobe","-v","error","-rw_timeout","8000000","-user_agent",UA,"-show_entries","stream=codec_type,codec_name,width,height:stream_tags=language","-of","json",url]
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=18)
        o["ffprobe_returncode"]=p.returncode
        if p.returncode==0:
            obj=json.loads(p.stdout);o["streams"]=obj.get("streams",[])
            o["video_decoded"]=any(s.get("codec_type")=="video" for s in o["streams"])
            o["audio_detected"]=any(s.get("codec_type")=="audio" for s in o["streams"])
        else:o["ffprobe_error"]=p.stderr[-300:]
    except Exception as e:o["error"]=str(e)[:280]
    return o

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    results=list(pool.map(check,CANDIDATES.items()))
report={"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"note":"Media bytes do not verify show identity or spoken language. No playlist edits permitted without independently verified programme and audio.","results":results}
Path("gopal_shinchan_probe_20261031.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
print(json.dumps(report,indent=2,ensure_ascii=False))
