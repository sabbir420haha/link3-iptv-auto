#!/usr/bin/env python3
"""Build a locally hosted, evenly padded square 512x512 PNG for every IPTV channel.
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
    "Nick Bangla":"nick-in.png",
    "Sonic Hindi":"nickelodeon-sonic-in.png",
    "Sonic Bangla":"nickelodeon-sonic-in.png",
    "Super Hungama":"super-hungama-in.png",
    "Sony Yay":"sony-yay-in.png",
    "Nick Jr India":"nick-jr-in.png",
}
# Avoid substituting incorrect logos from similarly named foreign channels.
OTHER={
    "Discovery Bangla":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/India/Discovery-Bangla.png",
    "Disney HD Hindi":"https://xstreamcp-assets-msp.streamready.in/assets/LIVETV/LIVECHANNEL/LIVETV_LIVETVCHANNEL_DISNEY_CHANNEL_HD/images/LOGO_HD/image.png",
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

def card(name, img):
    """Center the *entire* broadcaster artwork in a safe square logo area.

    Artwork occupies the middle 420x248 region, so even an IPTV client's
    horizontal center crop keeps all important logo pixels visible. Source
    alpha-margin is removed before resizing; aspect ratios are never stretched.
    """
    canvas = Image.new("RGBA", (512, 512), (21, 30, 47, 255))
    painter = ImageDraw.Draw(canvas)
    # Subtle edge, not a frame around the logo: prevents a clipped-card look.
    painter.rounded_rectangle((7, 7, 504, 504), radius=28,
                              outline=(57, 71, 94, 255), width=2)
    if img is not None:
        work = img.convert("RGBA")
        # Trim only genuinely transparent margins; do not guess opaque
        # brand background colors or accidentally crop trademark details.
        alpha = work.getchannel("A")
        if alpha.getextrema()[0] < 240:
            mask = alpha.point(lambda x: 255 if x >= 24 else 0)
            bounds = mask.getbbox()
            if bounds and (bounds[2] - bounds[0]) > 12 and (bounds[3] - bounds[1]) > 12:
                work = work.crop(bounds)
        work.thumbnail((418, 248), Image.Resampling.LANCZOS)
        x, y = (512-work.width)//2, (512-work.height)//2
        canvas.alpha_composite(work, (x, y))
        return canvas.convert("RGB"), "brand"
    # Avoid clipped placeholders when artwork is not available.
    parts = textwrap.wrap(name, width=17, break_long_words=False)
    parts = parts[:3]
    if len(parts) == 3 and len(name) > 47:
        parts[2] = parts[2][:13] + "..."
    display = "\n".join(parts)
    chosen = font(43 if len(name) < 20 else 34 if len(name) < 31 else 27)
    bounds = painter.multiline_textbbox((0, 0), display, font=chosen,
                                        spacing=8, align="center")
    height = bounds[3] - bounds[1]
    top = 250 - height // 2
    painter.multiline_text((256, top), display, font=chosen,
                           fill=(245, 249, 255, 255), anchor="ma",
                           spacing=8, align="center")
    return canvas.convert("RGB"), "fallback"

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
            # Versioned URL refreshes IPTV Pro logo cache when image layout changes.
            uri=ROOT_URL+filename+"?v=20261023-centered2"
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
                "clear_name_fallbacks":statuses["fallback"],"size":"512x512 PNG; centered, contain-fit with safe margins",
                "note":"Every M3U logo points to a centered locally cached image. Brand marks keep original proportions; fallback names are not broadcaster originals."}
        STATUS.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Local channel logos:",dict(statuses),"total",len(result))

if __name__=="__main__":
    main()
