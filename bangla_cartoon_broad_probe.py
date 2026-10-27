#!/usr/bin/env python3
"""Broad read-only Bengali/cartoon lead audit. Decode 6 video frames with PyAV."""
from pathlib import Path
import concurrent.futures,datetime,json,zlib
import av
base=Path(__file__).resolve().parent
items=json.loads((base/"bangla_cartoon_broad_candidates.json").read_text())["candidates"]
def check(it):
 o={**it,"frames":0,"distinct":0,"moving_video":False,"audio":False}
 try:
  with av.open(it["url"],mode="r",timeout=(7.0,12.0)) as v:
   ss=[s for s in v.streams if s.type=="video"]
   aud=[s for s in v.streams if s.type=="audio"]
   o["audio"]=bool(aud)
   o["audio_language_tags"]=[s.metadata.get("language") for s in aud]
   o["video_codecs"]=[{"width":s.codec_context.width,"height":s.codec_context.height,"codec":s.codec_context.name} for s in ss]
   if not ss:return {**o,"error":"no video streams"}
   hashes=set()
   for packet in v.demux(ss[0]):
    for frame in packet.decode():
     hashes.add(zlib.crc32(bytes(frame.planes[0])))
     o["frames"]+=1
     if o["frames"]>=6:break
    if o["frames"]>=6:break
   o["distinct"]=len(hashes)
   o["moving_video"]=o["frames"]>=5 and len(hashes)>=3
 except Exception as e:o["error"]=str(e)[:240]
 return o
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex: outcomes=list(ex.map(check,items))
report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"warning":"Moving decoded frames never proves Bengali audio, show identity, 24/7 reliability or authorization. Inferred URLs are NEVER approved.", "results":outcomes}
(base/"bangla_cartoon_broad_health.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
for x in outcomes:print(x["title"],x["moving_video"],x["frames"],x.get("video_codecs"),x.get("error"))
