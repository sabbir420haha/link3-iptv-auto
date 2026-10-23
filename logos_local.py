#!/usr/bin/env python3
"""Build a locally hosted 512x288 PNG for every IPTV channel.
Never changes stream URLs. Prefer exact Indian broadcaster logos and provider image
sources; otherwise use a clearly labelled custom channel-name placeholder.
"""
import concurrent.futures
import io
import json
import re
import textwrap
import urllib.request
from collections import Counter
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
PLAYLIST=ROOT/"playlist.m3u"
STATUS=ROOT/"status.json"
IMAGES=ROOT/"logos"
IMAGES.mkdir(exist_ok=True)
OWNER="sabbir420haha"
REPO="link3-iptv-auto"
ROOT_URL=f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/logos/"
HEADERS={"User-Agent":"Mozilla/5.0 Link3PlaylistLogoArchive/1.0"}
INDIAN_LOGOS="https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/india/"
# Hand-selected exact channel identity matches from the logo library.
INDIAN={
    "Zee Bangla":"zee-bangla-in.png",
    "Zee Bangla HD":"zee-bangla-hd-in.png",
    "Sony MAX HD":"sony-max-hd-in.png",
    "Sony Ten 1 HD":"sony-ten-1-hd-in.png",
    "Sony Ten 3 HD":"sony-ten-3-hd-in.png",
    "Hungama":"hungama-in.png",
    "Hungama HD":"hungama-in.png",
    "Nick Hindi":"nick-in.png",
    "Sonic Hindi":"nickelodeon-sonic-in.png",
    "Sonic Bangla":"nickelodeon-sonic-in.png",
    "Super Hungama":"super-hungama-in.png",
    "Sony Yay":"sony-yay-in.png",
    "Nick Jr India":"nick-jr-in.png",
}
# Avoid substituting incorrect logos from similarly named foreign channels.
OTHER={
    "Discovery Bangla":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/India/Discovery-Bangla.png",
}
def slug(name):
    return re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-") or "channel"

def read_image(url):
    if not url.startswith("https://") or "?" in url and "api.github.com" in url:
        return None
    req=urllib.request.Request(url,headers=HEADERS)
    try:
        with urllib.request.urlopen(req,timeout=9) as r:
            if r.status!=200:
                return None
            raw=r.read(2800000)
        if len(raw)<120 or len(raw)>=2800000:
            return None
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ("PNG","JPEG","WEBP"):
                return None
            if min(im.size)<55 or max(im.size)<150:
                return None
            im.load()
            return im.convert("RGBA")
    except Exception:
        return None

def font(size):
    for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(path,size)
        except OSError:
            continue
    return ImageFont.load_default()

def card(name,img):
    background=Image.new("RGBA",(512,288),(21,30,47,255))
    p=ImageDraw.Draw(background)
    p.rounded_rectangle((5,5,506,282),radius=22,outline=(76,93,123,255),width=2)
    if img is not None:
        img.thumbnail((445,227),Image.Resampling.LANCZOS)
        x=(512-img.width)//2
        y=(277-img.height)//2
        background.alpha_composite(img,(x,y))
        return background.convert("RGB"),"brand"
    # A visible placeholder is preferable to a broken logo, but not falsely official.
    group_lines=textwrap.wrap(name,width=15,break_long_words=False)
    group_lines=group_lines[:3]
    display="\n".join(group_lines)
    chosen=font(45 if len(name)<20 else 33)
    box=p.multiline_textbbox((0,0),display,font=chosen,spacing=10,align="center")
    yy=124-(box[3]-box[1])/2
    p.multiline_text((256,yy),display,font=chosen,fill=(248,250,255),anchor="ma",spacing=10,align="center")
    p.text((256,259),"CHANNEL NAME · LOGO UNAVAILABLE",font=font(15),fill=(166,187,211),anchor="mm")
    return background.convert("RGB"),"fallback"

def process(line):
    name_match=re.search(r'tvg-name="([^"]+)"',line)
    logo_match=re.search(r'tvg-logo="([^"]*)"',line)
    name=name_match.group(1) if name_match else line.rsplit(",",1)[-1].strip()
    remote=logo_match.group(1) if logo_match else ""
    filename=slug(name)+".png"
    targets=[]
    if name in INDIAN:
        targets.append(INDIAN_LOGOS+INDIAN[name])
    if name in OTHER:
        targets.append(OTHER[name])
    # Regularly maintained provider logo links are secondary to exact brand matches.
    if remote and not remote.startswith(ROOT_URL):
        targets.append(remote)
    # Do not pull a custom placeholder from GitHub; it is regenerated locally.
    selected=None
    for url in list(dict.fromkeys(targets)):
        selected=read_image(url)
        if selected is not None:
            break
    result,kind=card(name,selected)
    path=IMAGES/filename
    stream=io.BytesIO()
    result.save(stream,format="PNG",optimize=True)
    raw=stream.getvalue()
    if not path.exists() or path.read_bytes()!=raw:
        path.write_bytes(raw)
    return (name,filename,kind)

def main():
    lines=PLAYLIST.read_text(encoding="utf-8").splitlines()
    headers=[line for line in lines if line.startswith("#EXTINF")]
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        result=list(pool.map(process,headers))
    mapping={name:(filename,kind) for name,filename,kind in result}
    built=[]
    for line in lines:
        if line.startswith("#EXTINF"):
            name_match=re.search(r'tvg-name="([^"]+)"',line)
            name=name_match.group(1) if name_match else line.rsplit(",",1)[-1].strip()
            filename,_=mapping[name]
            uri=ROOT_URL+filename
            if 'tvg-logo="' in line:
                line=re.sub(r'tvg-logo="[^"]*"',f'tvg-logo="{uri}"',line,count=1)
            else:
                line=line.replace(" group-title=",f' tvg-logo="{uri}" group-title=',1)
        built.append(line)
    PLAYLIST.write_text("\n".join(built)+"\n",encoding="utf-8")
    statuses=Counter(kind for _,_,kind in result)
    if STATUS.exists():
        status=json.loads(STATUS.read_text(encoding="utf-8"))
        status["local_logos"]={"total":len(result),"from_image_sources":statuses["brand"],
                "clear_name_fallbacks":statuses["fallback"],"size":"512x288 PNG",
                "note":"Every M3U logo link points to this repository. Placeholder cards are not original broadcaster logos."}
        STATUS.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Local channel logos:",dict(statuses),"total",len(result))

if __name__=="__main__":
    main()
