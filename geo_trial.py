#!/usr/bin/env python3
"""Generate an opt-in BD-region trial list, not a 'working channels' claim.
Main playlist.m3u is unchanged. These candidates may be region-/ISP-restricted;
do not take country-restricted access as evidence of a healthy stream.
"""
import json, re, datetime, urllib.parse, ipaddress
from pathlib import Path
from logos_local import read_image, card, slug
ROOT=Path(__file__).resolve().parent
URL_BASE="https://raw.githubusercontent.com/sabbir420haha/link3-iptv-auto/main/"
# User has confirmed every previous geo-trial candidate fails on Link3.
# Publish no misleading old candidates. Populate only after new user-confirmed feeds.
TRIALS={}

LOGO={
 "Nick Hindi":"https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/india/nick-in.png",
 "Sonic Bangla":"https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/india/nickelodeon-sonic-in.png",
}
def safe(uri):
    p=urllib.parse.urlsplit(uri)
    if p.scheme not in ("https","http") or not p.hostname or p.username or p.password:
        return False
    hostname=p.hostname.lower()
    if any(x in uri.lower() for x in ("bdix", "t-play", "tplay")):
        return False
    try:
        if not ipaddress.ip_address(hostname).is_global:
            return False
    except ValueError:
        if hostname in ("localhost",) or hostname.endswith((".local",".lan",".internal")):
            return False
    return True
def local_logo(name):
    # Keep every trial icon in this repository, not an unstable hotlinked server.
    uri=LOGO.get(name,"")
    img=read_image(uri) if uri else None
    frame,_=card(name,img)
    target=ROOT/"logos"/("geo-"+slug(name)+".png")
    target.parent.mkdir(exist_ok=True)
    import io
    buf=io.BytesIO()
    frame.save(buf,format="PNG",optimize=True)
    raw=buf.getvalue()
    if not target.exists() or target.read_bytes()!=raw:
        target.write_bytes(raw)
    return URL_BASE+"logos/"+target.name

def main():
    catalog={x["name"]:x for x in json.loads((ROOT/"channels.json").read_text())}
    status=json.loads((ROOT/"status.json").read_text())
    audit={x["name"]:x for x in status.get("candidate_audit",[])}
    output=["#EXTM3U",
      "# Previous 9 trial streams ALL failed user playback; removed. No confirmed alternate sources yet.",
      "# These may be ISP-only, region restricted, wrong language or offline. No DRM/access bypass."]
    summary={}
    for name,sources in TRIALS.items():
        item=catalog.get(name,{})
        banned=set(item.get("exclude_urls",[]))
        counts=0
        logo=local_logo(name)
        for label,uri in sources:
            if not safe(uri) or uri in banned: continue
            diagnostics=next((c for c in audit.get(name,{}).get("candidates",[]) if c["url"]==uri),None)
            stat= "manifest-checked" if diagnostics and diagnostics.get("manifest_ok") else "unverified"
            title=(name+" - "+label).replace('"', "'").replace(",", " -")
            group="99 | BD-GEO TRIAL - Playback NOT verified"
            output.append(f'#EXTINF:-1 tvg-name="{title}" tvg-logo="{logo}" group-title="{group}",{title}')
            output.append(uri)
            counts+=1
        summary[name]=counts
    (ROOT/"geo_trials.m3u").write_text("\n".join(output)+"\n",encoding="utf-8")
    status["bd_geo_trials"]={
        "entries":sum(summary.values()),"by_name":summary,
        "warning":"These are not certified working or HD and may be ISP-only. Test on your own internet. This is an OPTIONAL playlist, separate from the primary playlist."
    }
    (ROOT/"status.json").write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Optional geo trials",summary)
if __name__=="__main__":main()
