#!/usr/bin/env python3
"""Build compact white-card 320x220 PNG for every IPTV channel.
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
    """Reference-TV look: compact white logo cards with centered, uncropped art.

    Keep the whole brand mark inside a 320x220 white tile. Crop only genuinely
    transparent or empty near-white source margins, never the brand artwork.
    """
    canvas = Image.new("RGBA", (320, 220), (255, 255, 255, 255))
    painter = ImageDraw.Draw(canvas)
    painter.rounded_rectangle((1, 1, 318, 218), radius=9,
                              outline=(222, 226, 232, 255), width=2)
    if img is not None:
        work = img.convert("RGBA")
        alpha = work.getchannel("A")
        if alpha.getextrema()[0] < 240:
            # An alpha threshold protects anti-aliased brand edges.
            bounds = alpha.point(lambda v: 255 if v >= 16 else 0).getbbox()
            if bounds and bounds[2]-bounds[0] > 10 and bounds[3]-bounds[1] > 10:
                work = work.crop(bounds)
        else:
            # Trim empty white borders in opaque source logo files.
            # Only do so when its four outer corners are nearly white.
            rgb = work.convert("RGB")
            w, h = rgb.size
            corners = [rgb.getpixel(xy) for xy in
                       [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]]
            if all(min(pixel) >= 245 for pixel in corners):
                from PIL import ImageChops
                delta = ImageChops.difference(
                    rgb, Image.new("RGB", rgb.size, (255, 255, 255)))
                bounds = delta.convert("L").point(
                    lambda v: 255 if v >= 22 else 0).getbbox()
                if bounds and bounds[2]-bounds[0] > 10 and bounds[3]-bounds[1] > 10:
                    work = work.crop(bounds)
        work.thumbnail((272, 168), Image.Resampling.LANCZOS)
        x, y = (320-work.width)//2, (220-work.height)//2
        canvas.alpha_composite(work, (x, y))
        return canvas.convert("RGB"), "brand"

    # Clean dark text on white for stations without a genuine brand logo.
    parts = textwrap.wrap(name, width=19, break_long_words=False)[:3]
    display = "\n".join(parts)
    chosen = font(30 if len(name) < 20 else 25 if len(name) < 31 else 21)
    bounds = painter.multiline_textbbox(
        (0, 0), display, font=chosen, spacing=6, align="center")
    height = bounds[3] - bounds[1]
    painter.multiline_text(
        (160, 106-height//2), display, font=chosen,
        fill=(36, 54, 82, 255), anchor="ma", spacing=6, align="center")
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
    result.quantize(colors=192, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(stream, format="PNG", optimize=True)
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
            uri=ROOT_URL+filename+"?v=whitecard20261023"
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
                "clear_name_fallbacks":statuses["fallback"],"size":"320x220 PNG; white background, centered original-proportion brand marks",
                "note":"Every M3U logo points to a centered locally cached image. Brand marks keep original proportions; fallback names are not broadcaster originals."}
        STATUS.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Local channel logos:",dict(statuses),"total",len(result))

if __name__=="__main__":
    main()
