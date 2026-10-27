#!/usr/bin/env python3
"""Read-only public Still On Air web-page check for alleged Shinchan Hindi 24/7."""
import json,re,datetime
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.parse import urljoin
url="https://www.stillonair.com/channel/shinchan-247hindi"
res={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"page":url,"warning":"A public watch-page is not itself a direct IPTV media stream or proof of video/rights."}
try:
 with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36"}),timeout=18) as resp:
  html=resp.read(850000).decode("utf8","replace")
  res.update({"http":resp.status,"bytes":len(html),"contains_shinchan":bool(re.search("shinchan",html,re.I))})
  res["public_media_links"]=list(dict.fromkeys(re.findall(r'https?[^"<>\\ ]{5,200}\\.(?:m3u8|mpd|mp4)(?:\\?[^"<> ]*)?',html,re.I)))[:12]
  res["public_js_chunks"]=list(dict.fromkeys(re.findall(r"<script[^>]+src=[\"\x27]([^\"\x27]+)",html,re.I)))[:8]
  res["title"]=re.findall(r'<title>([^<]*)</title>',html,re.I)[:1]
except Exception as e:
 res["error"]=str(e)[:220]
out=Path(__file__).resolve().parent/"cartoon_stillonair_public_health.json"
out.write_text(json.dumps(res,indent=2,ensure_ascii=False)+"\n")
print(res)
