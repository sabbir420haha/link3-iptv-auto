#!/usr/bin/env python3
"""Decode HLS media of found BD Kids, Bengali-animation candidates. No IPTV playlists touched."""
from pathlib import Path
import concurrent.futures, datetime,json,zlib
import av
ROOT=Path(__file__).resolve().parent
rows=json.loads((ROOT/"bangla_cartoon_new_sources.json").read_text(encoding="utf8"))["sources"]
def go(item):
 r={**item,"opened":False,"moving_video":False,"frames":0,"distinct":0,"audio":False}
 try:
  with av.open(item["url"],mode="r",timeout=(8.0,14.0)) as c:
   r["opened"]=True
   vs=[s for s in c.streams if s.type=="video"]
   aud=[s for s in c.streams if s.type=="audio"]
   r["audio"]=bool(aud)
   r["audio_languages"]=[s.metadata.get("language") for s in aud]
   r["streams"]=[{"codec":x.codec_context.name,"width":x.codec_context.width,"height":x.codec_context.height} for x in vs]
   if not vs:
    r["error"]="No video streams"
    return r
   hashes=set()
   for packet in c.demux(vs[0]):
    for frame in packet.decode():
     hashes.add(zlib.crc32(bytes(frame.planes[0])))
     r["frames"]+=1
     if r["frames"]>=8:break
    if r["frames"]>=8:break
   r["distinct"]=len(hashes)
   r["moving_video"]=r["frames"]>=5 and len(hashes)>=3
 except Exception as e:r["error"]=str(e)[:200]
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(go,rows))
report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"notes":"Video frames and audio presence do not prove Bengali spoken language, animated content, stable 24/7 availability or rights. All user added feeds stay TEST only.", "results":results}
(ROOT/"bangla_cartoon_new_health.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
for r in results:print(r["label"],"moving",r["moving_video"],"frames",r["frames"],"distinct",r["distinct"],"res",r.get("streams"),"error",r.get("error"))
