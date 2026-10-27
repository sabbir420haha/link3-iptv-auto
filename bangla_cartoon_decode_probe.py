#!/usr/bin/env python3
"""Attempt decode of live Bengali cartoon frames with PyAV, not only manifest bytes.
Results must NOT be read as identification of show/audio language or authorized usage.
"""
import datetime, json, zlib
from pathlib import Path
import concurrent.futures
import av
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"bangla_cartoon_decoded_health.json"
SOURCES=[
 {"name":"Doraemon Bangla 24/7 candidate","url":"https://live20.bozztv.com/giatvplayout7/giatv-209902/tracks-v1a1/mono.ts.m3u8","group":"new"},
 {"name":"ZB Cartoon Bangla existing TEST","url":"https://server.zillarbarta.com/zbcatun/video.m3u8","group":"existing"},
 {"name":"Sonic Bangla Balaji","url":"http://live.balajibroadband.com:3500/live/1345.m3u8","group":"new-if-working"},
 {"name":"Sony Yay Bengali label","url":"https://yowaimo.in/Sflex-ArtlPVT0719/SONY_yay.m3u8","group":"new-if-working"}
]
def check(item):
 r={**item,"decoded_video_frames":0,"distinct_video_frames":0,"audio_stream_present":False}
 try:
  with av.open(item["url"],mode="r",timeout=(7.0,11.0)) as c:
   videos=[s for s in c.streams if s.type=="video"]
   audios=[s for s in c.streams if s.type=="audio"]
   r["audio_stream_present"]=bool(audios)
   r["audio_language_tags"]=[s.metadata.get("language") for s in audios]
   r["video_streams"]=[{"width":v.codec_context.width,"height":v.codec_context.height,"codec":v.codec_context.name} for v in videos]
   if not videos:
    r["error"]="No video stream"
    return r
   hashes=set()
   for packet in c.demux(videos[0]):
    for frame in packet.decode():
     hashes.add(zlib.crc32(bytes(frame.planes[0])))
     r["decoded_video_frames"]+=1
     if r["decoded_video_frames"]>=8: break
    if r["decoded_video_frames"]>=8: break
   r["distinct_video_frames"]=len(hashes)
   r["moving_video_observed"]=len(hashes)>=2
 except Exception as exc:
  r["error"]=str(exc)[:350]
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 result=list(pool.map(check,SOURCES))
OUT.write_text(json.dumps({"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"warning":"Decoded moving frames do not prove cartoon identity, Bangla dubbing, subscription-slate absence or stable Link3 playback.","results":result},indent=2,ensure_ascii=False)+"\n")
for r in result: print(r["name"],"frames",r["decoded_video_frames"],"distinct",r["distinct_video_frames"],"resolution",r.get("video_streams"),"error",r.get("error"))
