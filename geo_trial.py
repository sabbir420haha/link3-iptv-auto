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
TRIALS={
 "Discovery Bangla":[
   ("KITV TS (Bangla label, old public source)","http://iptv.kitv.live:1935/live/CTGDDN/CTGDDN/61.ts"),
   ("Discovery Bengali (old public HLS)","https://food-dlvr-ott.akamaized.net/primary/4/686a061683e44b518cdf57677e352ef3/index_21.m3u8"),
 ],
 "Disney HD Hindi":[
   ("Disney Channel HD IN (Hindi audio NOT confirmed)","http://66.102.126.10:8000/play/a013/index.m3u8"),
   ("Disney International HD (Hindi audio NOT confirmed)","http://116.90.120.151:8000/play/a0hp/index.m3u8"),
 ],
 "Nat Geo HD Bangla":[
   ("Nat Geo Bangla HD (old published HLS)","http://103.167.167.5:8111/play/a036/index.m3u8"),
 ],
 "Nick Hindi":[
   ("Nick India (Hindi audio NOT confirmed)","http://103.162.136.235:4500/play/a01f/index.m3u8"),
   ("Nick India (second source, audio NOT confirmed)","http://149.71.34.166:8000/play/a00u/index.m3u8"),
 ],
 "Sonic Bangla":[
   ("Bangladesh Sonic, language NOT confirmed","https://edge01.iptv.digijadoo.net/live/sonic/playlist.m3u8"),
   ("Sonic Bangla (alternative, language NOT confirmed)","http://live.balajibroadband.com:3500/live/1345.m3u8"),
 ],
}
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
      "# OPTIONAL Bangladesh/region trial list, NOT confirmed live. Main playlist.m3u is unaffected.",
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
