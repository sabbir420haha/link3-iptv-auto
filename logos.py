#!/usr/bin/env python3
"""Update IPTV Pro logos with broadcaster-current public images and legible fallbacks.
This script changes ONLY M3U tvg-logo metadata, never stream URLs.
"""
import json
import re
import textwrap
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parent
M3U = BASE / "playlist.m3u"
STATUS = BASE / "status.json"
LOGO_DIR = BASE / "logos"
CATALOG = BASE / "channels.json"
FALLBACK_BASE = "https://raw.githubusercontent.com/sabbir420haha/link3-iptv-auto/main/logos/"
AGENT = {"User-Agent": "Link3IPTVLogoUpdater/2.0 (GitHub Actions)"}

def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower().replace("&", "and"))

def basename(name):
    return re.sub(r"\s+(HD|SD|FHD|4K)$", "", name or "", flags=re.I).strip()

def fetch_json(url, cap=28000000):
    req = urllib.request.Request(url, headers=AGENT)
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read(cap+1)
    if len(data)>cap:
        raise ValueError("API response too large")
    return json.loads(data)

def load_api():
    try:
        channels = fetch_json("https://iptv-org.github.io/api/channels.json")
        logos = fetch_json("https://iptv-org.github.io/api/logos.json")
    except Exception as exc:
        print("Logo API unavailable:", str(exc)[:150])
        return {}, {}
    by_id = {c["id"]: c for c in channels if isinstance(c,dict) and c.get("id")}
    candidates = defaultdict(list)
    for logo in logos:
        ident=logo.get("channel")
        if ident not in by_id or not logo.get("url","").startswith("https://"):
            continue
        url=logo["url"]
        f=(logo.get("format") or "").lower()
        if f not in ("png","jpeg","jpg","webp") or not logo.get("in_use",False):
            continue
        # Avoid tiny logos and unsupported SVG and animated formats in IPTV Pro.
        width=int(logo.get("width") or 0)
        height=int(logo.get("height") or 0)
        if width < 180 or height < 55:
            continue
        c=by_id[ident]
        for label in [c.get("name",""),*(c.get("alt_names") or []),ident.split(".")[0]]:
            if label:
                candidates[norm(label)].append((url,c.get("country",""),width,height,f))
    print("Current logo candidates:",sum(len(v) for v in candidates.values()))
    return candidates, by_id

def load_india_pngs():
    try:
        listing=fetch_json("https://api.github.com/repos/tv-logo/tv-logos/contents/countries/india",cap=1000000)
    except Exception as exc:
        print("India logo index unavailable:",str(exc)[:120])
        return {}
    logos=defaultdict(list)
    for item in listing:
        filename=item.get("name","")
        if item.get("type")!="file" or not filename.endswith(".png"):
            continue
        stem=filename[:-4]
        label=stem.removesuffix("-in").replace("-hd-in","-hd").replace("-"," ")
        if item.get("download_url"):
            logos[norm(label)].append(item["download_url"])
    return logos

def load_updated_playlist_logos():
    # Supplement newer BD brands absent from the historical IPTV-org logo archive.
    try:
        url="https://raw.githubusercontent.com/sm-monirulislam/SM-IPTV/main/Combined_Live_TV.m3u"
        req=urllib.request.Request(url,headers=AGENT)
        with urllib.request.urlopen(req,timeout=20) as r:
            body=r.read(3000000).decode("utf-8-sig",errors="replace")
    except Exception as exc:
        print("Supplemental logo source unavailable:",str(exc)[:130])
        return {}
    found=defaultdict(list)
    for line in body.splitlines():
        if not line.startswith("#EXTINF:"):
            continue
        m=re.search(r'tvg-logo="([^"]+)"',line)
        if not m or "," not in line:
            continue
        title=line.rsplit(",",1)[-1].strip()
        uri=m.group(1).strip()
        if uri.startswith("https://") and urlsplit(uri).hostname:
            found[norm(title)].append(uri)
    return found

def remote_logo_dimensions(url):
    if not url.startswith("https://"):
        return 0
    try:
        request=urllib.request.Request(url,headers=AGENT)
        with urllib.request.urlopen(request,timeout=7) as response:
            ctype=response.headers.get("Content-Type","").lower()
            if ctype and "image" not in ctype and "octet-stream" not in ctype:
                return 0
            data=response.read(2500000)
        with Image.open(BytesIO(data)) as picture:
            w,h=picture.size
            if picture.format not in ("PNG","JPEG","WEBP") or w<160 or h<70:
                return 0
            return w
    except Exception:
        return 0

def best_official_logo(name, group, aliases, api, india, supplemental, checked):
    names=[name,basename(name)]+list(aliases)
    names=[x for x in names if x]
    expected="BD" if group.startswith(("01","02","05")) else "IN" if group.startswith(("03","04","08")) else ""
    best=None
    for n in names:
        for u,country,width,height,fmt in api.get(norm(n),[]):
            if expected and country != expected:
                continue
            score=width + min(height, 900)*0.3 +(450 if fmt=="png" else 0)
            if not best or score>best[0]:
                best=(score,u)
    if best:
        return best[1],"current-broadcaster"
    if not expected or expected=="IN":
        for n in names:
            choices=india.get(norm(n),[])
            if choices:
                return choices[0],"indian-png-library"
    # Fallback to a newer independent index, but only after checking image bytes
    # and minimum dimensions, rather than trusting a random logo URL.
    for n in names:
        for uri in supplemental.get(norm(n),[])[:3]:
            if uri not in checked:
                checked[uri]=remote_logo_dimensions(uri)
            if checked[uri]>=225:
                return uri,"verified-recent-provider-logo"
    return None,"text-fallback"

def slug(name):
    label=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")
    return label or "channel"

def generate_fallback(name, group, filename):
    LOGO_DIR.mkdir(exist_ok=True)
    palette={
      "01":(32,61,93), "02":(37,73,66), "03":(73,48,100),
      "04":(36,90,142), "05":(36,90,142), "06":(110,57,36),
      "07":(37,79,74), "08":(89,51,87)
    }
    colour=palette.get(group[:2],(43,52,69))
    canvas=Image.new("RGB",(512,288),colour)
    draw=ImageDraw.Draw(canvas)
    try:
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 43)
        little=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18)
    except OSError:
        font=ImageFont.load_default()
        little=font
    parts=textwrap.wrap(name, width=16,break_long_words=False)
    if len(parts)>3:
        parts=parts[:3];parts[-1]=parts[-1]+"..."
    size=draw.multiline_textbbox((0,0),"\n".join(parts),font=font,spacing=10,align="center")
    h=size[3]-size[1]
    draw.multiline_text((256,133-h/2),"\n".join(parts),font=font,fill=(245,247,251),anchor="ma",spacing=10,align="center")
    draw.rounded_rectangle((23,18,489,270),radius=20,outline=(158,170,184),width=3)
    draw.text((256,258),"CHANNEL NAME • FALLBACK",font=little,anchor="mm",fill=(200,213,222))
    path=LOGO_DIR/filename
    canvas.save(path,format="PNG",optimize=True)
    return FALLBACK_BASE+filename

def main():
    known={c["name"]:c for c in json.loads(CATALOG.read_text(encoding="utf-8"))}
    api,_=load_api()
    india=load_india_pngs()
    supplemental=load_updated_playlist_logos()
    checked={}
    content=M3U.read_text(encoding="utf-8").splitlines()
    counts=defaultdict(int)
    new=[]
    for line in content:
        if not line.startswith("#EXTINF"):
            new.append(line)
            continue
        m=re.search(r'tvg-name="([^"]+)"',line)
        name=m.group(1) if m else line.rsplit(",",1)[-1].strip()
        channel=known.get(name,{})
        url,method=best_official_logo(name,channel.get("group",""),channel.get("aliases",[]),api,india,supplemental,checked)
        if not url:
            filename=slug(name)+".png"
            url=generate_fallback(name,channel.get("group",""),filename)
        counts[method]+=1
        if 'tvg-logo="' in line:
            line=re.sub(r'tvg-logo="[^"]*"',f'tvg-logo="{url}"',line,count=1)
        else:
            line=line.replace("#EXTINF:",f'#EXTINF:-1 tvg-logo="{url}" x-orig-extinf=',1)
        new.append(line)
    M3U.write_text("\n".join(new)+"\n",encoding="utf-8")
    if STATUS.exists():
        data=json.loads(STATUS.read_text(encoding="utf-8"))
        data["logos"]={"logo_count":sum(counts.values()),"methods":dict(counts),
            "note":"Text fallback logos are custom labels, not official broadcaster logos."}
        STATUS.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Applied logos:",dict(counts))

if __name__=="__main__":
    main()
