#!/usr/bin/env python3
"""Read-only fresh Bengali cartoon alternate source frame checks."""
from pathlib import Path
import av, concurrent.futures, datetime,json,zlib
root=Path(__file__).resolve().parent
items=json.loads((root/'bangla_more_cartoon_sources.json').read_text())['sources']
def inspect(item):
 out=dict(item,frames=0,unique_frames=0,moving_video=False,audio_present=False)
 try:
  with av.open(item['url'],mode='r',timeout=(7.0,12.0)) as container:
   videos=[s for s in container.streams if s.type=='video']
   audio=[s for s in container.streams if s.type=='audio']
   out['audio_present']=len(audio)>0
   out['audio_languages']=[s.metadata.get('language') for s in audio]
   out['video_streams']=[{'width':s.codec_context.width,'height':s.codec_context.height,'codec':s.codec_context.name} for s in videos]
   if not videos:return dict(out,error='No video stream')
   fingerprints=set()
   for packet in container.demux(videos[0]):
    for frame in packet.decode():
     fingerprints.add(zlib.crc32(bytes(frame.planes[0])))
     out['frames']+=1
     if out['frames']>=7:break
    if out['frames']>=7:break
   out['unique_frames']=len(fingerprints)
   out['moving_video']=out['frames']>=5 and len(fingerprints)>=3
 except Exception as exc:out['error']=str(exc)[:220]
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool: checks=list(pool.map(inspect,items))
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'notes':'Decoded video frames and stream presence alone do not establish Bengali language or cartoon content or access rights.', 'results':checks}
(root/'bangla_more_cartoon_health.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for x in checks:print(x['name'],x['moving_video'],x['frames'],x.get('video_streams'),x.get('error'))
