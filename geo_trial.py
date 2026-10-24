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
# The user's separate geo_trials.m3u is the opt-in source testing playlist.
# Keep these unverified trials completely separate from the main channel list.
try:
    channel24_trials=json.loads((ROOT/"channel24_geo_candidates.json").read_text(encoding="utf-8"))
    TRIALS["Channel 24"]=[(x["label"],x["url"],x.get("referrer"))
        for x in channel24_trials.get("sources",[])][:20]
except FileNotFoundError:
    pass

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
    # Display numbered TEST entries only. These 20 URLs have NOT been user verified.
    for name,sources in TRIALS.items():
        item=catalog.get(name,{})
        banned=set(item.get("exclude_urls",[]))
        counts=0
        logo=(URL_BASE+"logos/channel-24.png") if name=="Channel 24" else local_logo(name)
        for entry in sources:
            label,uri=entry[:2]
            referer=entry[2] if len(entry)>2 else None
            if not safe(uri) or uri in banned: continue
            title=(name+" TEST "+label.replace(" | ", " - ")).replace('"', "'").replace(",", " -")
            group=("97 | CHANNEL 24 TEST - NOT VERIFIED" if name=="Channel 24"
                   else "99 | BD-GEO TRIAL - Playback NOT verified")
            stable_id=("channel24-test-"+label[:2] if name=="Channel 24" else
                       "bd-geo-"+slug(title))
            output.append(f'#EXTINF:-1 tvg-id="{stable_id}" tvg-name="{title}" tvg-logo="{logo}" group-title="{group}",{title}')
            if referer and referer.startswith("https://"):
                # Some IPTV players honour this optional header, others ignore it.
                output.append("#EXTVLCOPT:http-referrer="+referer)
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
