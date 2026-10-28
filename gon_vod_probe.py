#!/usr/bin/env python3
"""Test whether public Gon 1996 Hindi episodes can be played as direct M3U media.
Only reports URL availability. Does not attempt DRM, geoblocks, downloads, or copying videos.
"""
import concurrent.futures,datetime,json,subprocess
from pathlib import Path
import requests,yt_dlp
base=Path(__file__).resolve().parent
items=json.loads((base/"gon_vod_candidate_pages.json").read_text())["pages"]
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
def check(x):
 r=dict(title=x["title"],page=x["page"],extract_ok=False,media_valid=False,video_decode=False,formats=0)
 try:
  with yt_dlp.YoutubeDL({"skip_download":True,"quiet":True,"no_warnings":True,"socket_timeout":9,"retries":0,
    "extractor_retries":0,"noplaylist":True,"ignoreerrors":False,"http_headers":{"User-Agent":UA}}) as y:
   info=y.extract_info(x["page"],download=False)
  if not info:raise RuntimeError("No video metadata")
  r["actual_title"]=info.get("title","")[:160]
  r["duration_sec"]=info.get("duration")
  formats=info.get("formats",[])
  r["formats"]=len(formats)
  cand=[f for f in formats if f.get("url","").startswith("http") and
    (f.get("protocol") in ("m3u8","m3u8_native") or f.get("ext") in ("mp4","m3u8")) and
    f.get("vcodec") not in ("none",None)]
  cand.sort(key=lambda f:(f.get("protocol") in ("m3u8","m3u8_native"),f.get("height") or 0),reverse=True)
  if not cand:raise RuntimeError("No direct MP4/HLS video formats, likely requires player")
  f=cand[min(1,len(cand)-1)]
  url=f["url"]
  r.update(extract_ok=True,protocol=f.get("protocol"),height=f.get("height"),direct_url=url,
    expires_possible=True,headers=f.get("http_headers") or {})
  headers={"User-Agent":UA}
  headers.update(f.get("http_headers") or {})
  with requests.get(url,headers=headers,timeout=(5,10),stream=True) as resp:
   r["http_status"]=resp.status_code
   r["content_type"]=resp.headers.get("Content-Type","")[:85]
   resp.raise_for_status()
   data=next(resp.iter_content(chunk_size=2048),b"")
   r["media_valid"]=(data.startswith(b"#EXTM3U") or b"ftyp" in data[:50] or (data[:1]==b"\x47"))
  if r["media_valid"]:
   pr=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=codec_name,width,height","-of","json","-rw_timeout","8000000",url],capture_output=True,text=True,timeout=12)
   r["video_decode"]=bool(json.loads(pr.stdout or "{}").get("streams"))
   r["ffprobe_error"]=pr.stderr[:160]
 except Exception as e:r["error"]=str(e)[:240]
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:results=list(pool.map(check,items))
report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "warning":"Playback on GitHub Actions does not prove playback in Bangladesh. Signed URLs expire; video page links do not play in IPTV Pro.",
  "results":results}
(base/"gon_vod_probe_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
for r in results:print(r["title"],"metadata",r["extract_ok"],"media",r["media_valid"],"video",r["video_decode"],"err",r.get("error","")[:130])
