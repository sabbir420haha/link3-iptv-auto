#!/usr/bin/env python3
"""Check newly discovered candidate URLs without modifying the user playlist."""
import concurrent.futures,json,datetime
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.error import HTTPError
from cartoon_stream_probe import probe
p=Path(__file__).resolve().parent
def check(s):
 try:
  if s["url"].endswith(".m3u"):
   req=Request(s["url"],headers={"User-Agent":"Mozilla/5.0"})
   with urlopen(req,timeout=12) as r:
    data=r.read(100000).decode("utf8","replace")
   ls=[{"name":l,"url":data.splitlines()[i+1] if i+1<len(data.splitlines()) else ""} for i,l in enumerate(data.splitlines()) if ("Shinchan" in l or "Gopal" in l or "shinchan" in l.lower())]
   return {**s,"type":"collection","readable":data.startswith("#EXTM3U"),"matching_entries":ls[:20]}
  return {**s,**probe({"name":s["show"],"url":s["url"]})}
 except Exception as e:
  return {**s,"error":str(e)[:200]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 results=list(ex.map(check,json.loads((p/"cartoon_gopal_shinchan_new_leads.json").read_text())["sources"]))
result={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"warning":"HTTP media success alone never proves show identity, Hindi audio, Bangladesh viewing or 24x7 reliability; do not auto-add to test/main.", "results":results}
(p/"cartoon_gopal_shinchan_new_health.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
for r in results: print(r.get("show"),r.get("url"),r.get("manifest_ok"),r.get("media_sample_ok"),r.get("error"),r.get("matching_entries"))
