#!/usr/bin/env python3
"""Non-invasive public HLS and FFprobe audits for Bangla cartoon candidates."""
import concurrent.futures
import datetime
import json
import subprocess
from pathlib import Path
from cartoon_stream_probe import probe
ROOT=Path(__file__).resolve().parent
CAND=ROOT/"bangla_animation_candidate_sources.json"
OUT=ROOT/"bangla_animation_candidate_health.json"
def check(item):
 out=probe({"name":item["label"],"url":item["url"]})
 out.update({"slug":item["slug"],"category":item["category"],"source_resolution_claim":item.get("source_resolution_claim"),"may_publish_if_media":item["may_publish_if_media"]})
 if out.get("media_sample_ok"):
  try:
   cmd=["ffprobe","-v","error","-probesize","1500000","-analyzeduration","2000000","-show_entries","stream=codec_type,codec_name,width,height,channels:format=bit_rate","-of","json",item["url"]]
   r=subprocess.run(cmd,capture_output=True,text=True,timeout=22)
   if r.returncode==0:
    js=json.loads(r.stdout or "{}")
    out["stream_info"]=js.get("streams",[])[:6]
    out["format_info"]=js.get("format")
   else:out["ffprobe_error"]=r.stderr[-300:]
  except Exception as e: out["ffprobe_error"]=str(e)[:220]
 return out
def main():
 items=json.loads(CAND.read_text())["sources"]
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
  r=list(executor.map(check,items))
 report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"warning":"Only Link3 viewer can confirm video identity/language/buffering. FFprobe dimensions do not verify cartoon episodes or licence.","results":r}
 OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
 for x in r:
  print(x["label"],x.get("manifest_ok"),x.get("media_sample_ok"),x.get("stream_info"),x.get("error"),x.get("ffprobe_error"))
if __name__=="__main__":main()
