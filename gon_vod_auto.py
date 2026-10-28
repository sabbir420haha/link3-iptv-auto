#!/usr/bin/env python3
"""Refresh Gon Hindi on-demand streams in both standalone VOD and TEST playlists.
No DRM circumvention, no video downloads, and no edits to playlist.m3u (MAIN).
Public Dailymotion direct HLS URLs are signed/temporary; this regenerates them hourly.
"""
from __future__ import annotations
import concurrent.futures,datetime,json,zlib
from pathlib import Path
import av,requests,yt_dlp
base=Path(__file__).resolve().parent
UA="Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
items=[
 ("Clip A","https://www.dailymotion.com/video/x8ozzbx"),
 ("Clip B","https://www.dailymotion.com/video/x8p38pt"),
 ("Clip C","https://www.dailymotion.com/video/x8ozzbr"),
]
def check(item):
 label,page=item
 result={"label":label,"page":page,"playable":False}
 try:
  with yt_dlp.YoutubeDL({"quiet":True,"skip_download":True,"no_warnings":True,
    "socket_timeout":10,"retries":0,"extractor_retries":0,
    "http_headers":{"User-Agent":UA}}) as y:
    info=y.extract_info(page,download=False)
  result["video_title"]=info.get("title")
  result["duration"]=info.get("duration")
  media=[f for f in info.get("formats",[]) if f.get("url","").startswith("https://") and
    f.get("protocol") in ("m3u8_native","m3u8") and f.get("vcodec")!="none"]
  if not media:raise RuntimeError("No HLS video rendition")
  media.sort(key=lambda f:f.get("height") or 0,reverse=True)
  f=media[0]
  url=f["url"]
  result["resolution"]=f.get("height")
  headers={"User-Agent":UA}
  headers.update(f.get("http_headers") or {})
  with requests.get(url,headers=headers,timeout=(6,12)) as resp:
   result["status"]=resp.status_code
   resp.raise_for_status()
   if not resp.content.lstrip().startswith(b"#EXTM3U"):raise RuntimeError("Not HLS manifest")
   result["manifest_type"]="VOD" if b"#EXT-X-ENDLIST" in resp.content else "HLS"
  opts={"headers":"User-Agent: "+UA+"\r\nReferer: https://www.dailymotion.com/\r\n"}
  with av.open(url,mode="r",options=opts,timeout=(8,15)) as c:
   v=next((x for x in c.streams if x.type=="video"),None)
   a=[x for x in c.streams if x.type=="audio"]
   if not v or not a:raise RuntimeError("Video or audio stream missing")
   result["audio_tracks"]=[x.metadata.get("language") for x in a]
   result["codec"]=v.codec_context.name
   result["width"]=v.codec_context.width
   result["height"]=v.codec_context.height
   fingerprints=set()
   frames=0
   for pkt in c.demux(v):
    for frame in pkt.decode():
     fingerprints.add(zlib.crc32(bytes(frame.planes[0])))
     frames+=1
     if frames>=6:break
    if frames>=6:break
   result["frames"]=frames
   result["distinct_frames"]=len(fingerprints)
   if frames<4 or len(fingerprints)<2:raise RuntimeError("No moving playable video")
  result.update(playable=True,url=url)
 except Exception as e: result["error"]=str(e)[:240]
 return result
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex: results=list(ex.map(check,items))
now=datetime.datetime.now(datetime.timezone.utc)
report={"generated_utc":now.isoformat(),"assumptions":"Public third-party uploads; Hindi dubbing claimed by publisher, not independently listening verified. Link3/IPTV Pro playback needs local check. Signed HLS may expire early.","results":results}
(base/"gon_vod_health.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
passed=[x for x in results if x["playable"]]
lines=["#EXTM3U","# Gon The Stone Age Boy (1996) Hindi VOD-style TEST playlist",
 "# Authoritative episode numbers unknown; these are separately hosted video clips, not verified numbered episodes.",
 "# SOURCE: public video pages; URLs are time-limited; refreshed hourly when GitHub Actions succeeds.",
 "# Player: IPTV Pro entries look like channels but are on-demand recorded videos.",
 "# Generated UTC: "+now.isoformat()]
for r in passed:
 title="Gon 1996 Hindi VOD - "+r["label"]
 # VOD via finite-duration HLS media URL; no website links.
 lines.extend([
   '#EXTINF:-1 tvg-name="'+title+'" group-title="GON 1996 | HINDI VOD TEST",'+title,
   '#EXTVLCOPT:http-user-agent='+UA,
   '#EXTVLCOPT:http-referrer=https://www.dailymotion.com/',
   r["url"],""
 ])
(base/"gon_vod.m3u").write_text("\n".join(lines)+"\n",encoding="utf-8")

# Synchronize the playable VOD clips into the existing user's TEST playlist;
# retain ALL non-Gon entries, existing order, group metadata, and original URLs.
# The auto-generated marker block makes hourly refresh idempotent.
start="# BEGIN GON 1996 HINDI VOD AUTO"
end="# END GON 1996 HINDI VOD AUTO"
test_file=base/"three_channel_test.m3u"
original=test_file.read_text(encoding="utf-8")
if not original.startswith("#EXTM3U") or ((start in original)!=(end in original)):
 raise RuntimeError("Refusing to modify malformed TEST playlist or unbalanced Gon block")
if passed:
 block_lines=[
   start,
   "# On-demand Gon 1996 clips; HLS CDN links expire and are regenerated hourly.",
   "# Language, exact episode numbers, and playback on user's Link3 are not independently confirmed.",
 ]
 for r in passed:
  title="Gon 1996 Hindi VOD - "+r["label"]
  block_lines.extend([
    '#EXTINF:-1 tvg-name="'+title+'" group-title="29 | GON 1996 - HINDI VOD TEST",'+title,
    '#EXTVLCOPT:http-user-agent='+UA,
    '#EXTVLCOPT:http-referrer=https://www.dailymotion.com/',
    r["url"],""
  ])
 block_lines.append(end)
 block="\n".join(block_lines)+"\n"
 if start in original:
  before=original[:original.index(start)]
  after=original[original.index(end)+len(end):]
  modified=before+block+after.lstrip("\n")
 else:
  modified=original.rstrip("\n")+"\n\n"+block
 modified=modified.rstrip("\n")+"\n"
 old_non_gon=[l for l in original.splitlines() if l.startswith("#EXTINF") and "Gon 1996 Hindi VOD" not in l]
 new_non_gon=[l for l in modified.splitlines() if l.startswith("#EXTINF") and "Gon 1996 Hindi VOD" not in l]
 if old_non_gon!=new_non_gon:
  raise RuntimeError("Refusing to change existing non-Gon TEST entries")
 if modified.count(start)!=1 or modified.count(end)!=1:
  raise RuntimeError("Gon block markers repeated")
 if modified.count("group-title=\"29 | GON 1996 - HINDI VOD TEST\"")!=len(passed):
  raise RuntimeError("Incorrect Gon entry count")
 test_file.write_text(modified,encoding="utf-8")
 print("Updated three_channel_test.m3u: added/refreshed",len(passed),"Gon VOD clips")
else:
 print("0 Gon clips passed fresh media validation; existing TEST Gon block retained without altering other channels")

print(json.dumps({"tested":len(results),"passed":len(passed),"labels":[r["label"] for r in passed],
  "failures":[{"label":r["label"],"error":r.get("error")} for r in results if not r["playable"]]}))
