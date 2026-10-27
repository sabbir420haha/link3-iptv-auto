#!/usr/bin/env python3
"""On-demand independent public HLS Sonic Hindi probe. No playlist writes, DRM bypass, or fake PASS."""
import concurrent.futures,datetime,json,zlib
from pathlib import Path
import av
base=Path(__file__).resolve().parent
src=json.loads((base/'sonic_hindi_extensive_20261027_sources.json').read_text())['sources']
def check(s):
 r=dict(s,opened=False,moving_video=False,frames=0,distinct_frames=0,audio=False)
 try:
  with av.open(s['url'],mode='r',timeout=(6.5,10.5)) as c:
   r['opened']=True
   videos=[x for x in c.streams if x.type=='video']
   audio=[x for x in c.streams if x.type=='audio']
   r['audio']=len(audio)>0
   r['audio_tags']=[x.metadata.get('language') for x in audio]
   r['video_info']=[dict(codec=v.codec_context.name,width=v.codec_context.width,height=v.codec_context.height) for v in videos]
   if not videos:return dict(r,error='No video stream')
   fingerprints=set()
   for packet in c.demux(videos[0]):
    for frame in packet.decode():
     fingerprints.add(zlib.crc32(bytes(frame.planes[0])))
     r['frames']+=1
     if r['frames']>=7:break
    if r['frames']>=7:break
   r['distinct_frames']=len(fingerprints)
   r['moving_video']=r['frames']>=5 and len(fingerprints)>=3
 except Exception as e:r['error']=str(e)[:280]
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=11) as ex: results=list(ex.map(check,src))
report=dict(checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 note='Independent video decode does NOT establish correct Sonic broadcast, Hindi speech, stable Link3 playback. DRM/protected streams are excluded. One positive control is Hungama TV.',
 results=results)
(base/'sonic_hindi_extensive_20261027_health.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
for x in results:print(x['name'],x['moving_video'],x['frames'],x['audio'],x.get('video_info'),x.get('error',''))
