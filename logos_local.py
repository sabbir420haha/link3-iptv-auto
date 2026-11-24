#!/usr/bin/env python3
"""Build tight-fit transparent PNG logos for IPTV Pro (no extra tile).
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
# Use the original 2017-2025 red-circle Zee Bangla logo artwork,
# rather than tiny screenshot crops (which look blurred on a TV).
ZEE_ARCHIVE_SOURCE = "https://upload.wikimedia.org/wikipedia/commons/5/5f/Zee_Bangla_logo.png"
ZEE_ARCHIVE_LOGOS = {
    "Zee Bangla HD": "zee-bangla-legacy-hd.png",
    "Zee Bangla": "zee-bangla-legacy-sd.png",
}

# Only these three user-requested logos get a stronger TV-visible treatment.
# Exact brand artwork is preferred to old plain-name fallback images.
TV_CONTRAST_LOGOS = {
    # These eight entries currently have dark/transparent artwork that blends
    # into IPTV Pro's dark channel tiles. Keep each existing mark and place it
    # on a light, high-contrast branded field; no stream metadata is changed.
    "ATN Bangla": ["https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/atn-bangla-bd.png"],
    "BanglaVision": ["https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/banglavision-bd.png"],
    "Duronto TV": ["https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/duronto-bd.png"],
    "Hungama TEST 113": [INDIAN_LOGOS+"hungama-in.png"],
    "Hungama Backup": [INDIAN_LOGOS+"hungama-in.png"],
    "Maasranga TV": ["https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/maasranga-hd-bd.png", "https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/maasranga-bd.jpg"],
    "NTV": ["https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/n-tv-hd-bd.png", "https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/n-tv-bd.png"],
    "Somoy TV": ["https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/somoy-bd.png"],
    "Discovery Bangla": [
        "https://jiotvimages.cdn.jio.com/dare_images/images/DiscoveryHDBen.png",
        "https://otapp.store/uploads/tv_image/sm/discovery-channel-bengali.png",
        "https://upload.wikimedia.org/wikipedia/commons/4/4e/Discovery_Channel.png",
    ],
    "Jamuna TV": [
        "https://jamuna.tv/assets/images/thumbnail.jpg",
        "https://www.jamuna.tv/uploads/settings/jtv-logo-whitelogo-1-1754573204.png",
    ],
    "Nat Geo HD Bangla": [
        "https://upload.wikimedia.org/wikipedia/commons/2/22/Nat_Geo_HD.png",
        "https://jiotvimages.cdn.jio.com/dare_images/images/Nat_Geo_HD.png",
    ],
}

# Hand-selected exact channel identity matches from the logo library.
INDIAN={
    "Sun Bangla":"sun-bangla-in.png",
    "Cartoon Network":"cartoon-network-in.png",
    "Sony Aath":"sony-aath-in.png",
    "Star Jalsha":"star-jalsha-in.png",
    "Zee 24 Ghanta":"zee-24-ghanta-in.png",
    "Pogo":"pogo-in.png",
    "Discovery Kids":"discovery-kids-in.png",
    "DD Sports":"dd-sports-in.png",
    "Star Sports 2":"star-sports-2-in.png",
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
    "Sun Bangla":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/India/sun-bangla-in.png",
    "ATN News":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/atn-news-bd.png",
    "Channel 24":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/channel-24-bd.png",
    "Channel i":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/channel-i-bd.png",
    "DBC News":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/dbc-news-bd.png",
    "Independent TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/independent-bd.png",
    "Ekattor TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/ekattor-tv-bd.png",
    "News 24":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/news-24-bd.png",
    "BTV News":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/btv-news-bd.png",
    "Desh TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/desh-tv-bd.png",
    "Ekhon TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/ekhon-bd.png",
    "Bijoy TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/bijoy-tv-bd.png",
    "Ekushey TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/ekushey-tv-bd.png",
    "BTV Chattogram":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/btv-chattogram-bd.png",
    "Boishakhi TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/boishakhi-tv-bd.png",
    "Deepto TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/deepto-tv-bd.png",
    "RTV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/r-tv-bd.png",
    "Gazi TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/gtv-bd.png",
    "My TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/my-tv-bd.png",
    "Asian TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/asian-tv-bd.png",
    "SA TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/sa-tv-bd.png",
    "Ananda TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/ananda-tv-bd.png",
    "Rajdhani TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/rajdhani-bd.png",
    "Deshi TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/deshi-tv-bd.png",
    "Channel S":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/channel-s-bd.png",
    "Deshe Bideshe TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/deshebideshe-tv-bd.png",
    "Islamic TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/islamic-tv-bd.png",
    "Mohona TV":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/mohona-tv-bd.png",
    "T Sports":"https://raw.githubusercontent.com/AsimDipto/Logo-box/main/Bangladesh/t-sports-bd.png",
    "beIN Sports XTRA":"https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/international/beinsports/old/stacked/bein-sports-xtra-int.png",
    "Red Bull TV":"https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/international/red-bull-tv-int.png",
    "FITE 24/7":"https://raw.githubusercontent.com/tv-logo/tv-logos/main/countries/international/fite-tv-int.png",
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
    """Export the broadcaster logo itself: no app-within-an-app white card.

    Native-aspect RGBA PNG, closely trimmed, with only four transparent pixels
    of safety around the mark. IPTV Pro is responsible for its own display tile.
    """
    if img is not None:
        artwork = img.convert("RGBA")
        # Bound remote image processing; shrink before scanning its edges.
        artwork.thumbnail((860, 860), Image.Resampling.LANCZOS)
        alpha = artwork.getchannel("A")
        if alpha.getextrema()[0] >= 245:
            # An opaque image can have a large white canvas baked into it.
            # Remove *only edge-connected* near-white, not white enclosed inside
            # an actual channel emblem (such as a Sony roundel).
            w, h = artwork.size
            corners = [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]
            if all(min(artwork.getpixel(xy)[:3]) >= 240 for xy in corners):
                for xy in corners:
                    if artwork.getpixel(xy)[3] > 0:
                        ImageDraw.floodfill(
                            artwork, xy, (255, 255, 255, 0), thresh=24)
        mask = artwork.getchannel("A").point(
            lambda v: 255 if v >= 13 else 0)
        bounds = mask.getbbox()
        if bounds and bounds[2]-bounds[0] >= 12 and bounds[3]-bounds[1] >= 12:
            artwork = artwork.crop(bounds)
            # Do not stretch wide logos to square, or make circular marks wide.
            artwork.thumbnail((308, 188), Image.Resampling.LANCZOS)
            padding = 4
            result = Image.new("RGBA",
                               (artwork.width + 2*padding,
                                artwork.height + 2*padding),
                               (0, 0, 0, 0))
            result.alpha_composite(artwork, (padding, padding))
            return result, "brand"

    # No genuine image? Keep an honest readable text fallback, also tightly
    # cropped and transparent rather than manufacturing a white logo card.
    rows = textwrap.wrap(name, width=18, break_long_words=False)[:3]
    label = "\n".join(rows)
    chosen = font(31 if len(name) < 20 else 24 if len(name) < 31 else 19)
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = measure.multiline_textbbox((0, 0), label, font=chosen,
                                      spacing=5, align="center")
    w = int(max(88, min(314, round(bbox[2]-bbox[0]+14))))
    h = int(max(38, min(198, round(bbox[3]-bbox[1]+14))))
    # Keep unresolved channels visible on IPTV Pro's dark tiles.
    # This is an explicit labelled fallback, NOT represented as official artwork.
    w = min(314, max(132, w + 26))
    h = min(198, max(58, h + 18))
    result = Image.new("RGBA", (w, h), (244, 248, 253, 255))
    painter = ImageDraw.Draw(result)
    painter.rounded_rectangle((1, 1, w-2, h-2), radius=10,
                              fill=(244, 248, 253, 255),
                              outline=(32, 83, 130, 255), width=3)
    painter.multiline_text((w//2, h//2), label, font=chosen,
                            fill=(18, 43, 73, 255), anchor="mm",
                            spacing=5, align="center",
                            stroke_width=0)
    return result, "fallback"


def contrast_brand_logo(name, previous_path):
    """Show real artwork clearly against IPTV app's white logo background.

    This function is ONLY called for Discovery Bangla, Jamuna TV, and
    Nat Geo HD Bangla. It does not affect any stream or other channel logo.
    """
    source = next((pic for uri in TV_CONTRAST_LOGOS[name]
                   if (pic := read_image(uri)) is not None), None)

    if source is None:
        raise RuntimeError(
            f"No genuine broadcaster artwork could be downloaded for {name}; "
            "refusing to publish a text-only placeholder as a channel logo."
        )

    # The channel's native mark is tightly contained, NEVER stretched.
    mark,kind = card(name, source)
    mark = mark.convert("RGBA")

    if name == "Jamuna TV":
        # White Jamuna lettering disappears on white; its channel's own
        # deep red brand field is required for readable contrast.
        backdrop = Image.new("RGBA", (320, 178), (173, 5, 26, 255))
        mark.thumbnail((308, 165), Image.Resampling.LANCZOS)
        backdrop.alpha_composite(mark, ((320-mark.width)//2,
                                        (178-mark.height)//2))
    elif name == "Nat Geo HD Bangla":
        # Original Nat Geo artwork has a yellow portal and dark wordmark.
        # A clean ivory field preserves yellow + black at thumbnail size.
        backdrop = Image.new("RGBA", (320, 178), (251, 252, 247, 255))
        mark.thumbnail((300, 150), Image.Resampling.LANCZOS)
        backdrop.alpha_composite(mark, ((320-mark.width)//2,
                                        (178-mark.height)//2))
    else:
        # A soft pale-blue field lets dark Discovery branding show clearly.
        # Do not use a giant 512px card or oversized blank margins.
        backdrop = Image.new("RGBA", (320, 178), (238, 246, 254, 255))
        mark.thumbnail((306, 158), Image.Resampling.LANCZOS)
        backdrop.alpha_composite(mark, ((320-mark.width)//2,
                                        (178-mark.height)//2))

    # A subtle edge avoids the near-white tile merging with TV's white UI.
    painter = ImageDraw.Draw(backdrop)
    outline = (185, 199, 216, 255) if name != "Jamuna TV" else (132, 11, 25, 255)
    painter.rounded_rectangle((1, 1, 318, 176), radius=10,
                              outline=outline, width=2)
    return backdrop,kind

def process(line):
    name_match=re.search(r'tvg-name="([^"]+)"',line)
    logo_match=re.search(r'tvg-logo="([^"]*)"',line)
    name=name_match.group(1) if name_match else line.rsplit(",",1)[-1].strip()
    remote=logo_match.group(1) if logo_match else ""
    filename=slug(name)+".png"
    if name in TV_CONTRAST_LOGOS:
        path = IMAGES / filename
        output,kind = contrast_brand_logo(name, path)
        encoded = io.BytesIO()
        output.quantize(colors=192, method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE).save(
                            encoded, format="PNG", optimize=True)
        content = encoded.getvalue()
        if not path.exists() or path.read_bytes()!=content:
            path.write_bytes(content)
        return name, filename, kind
    if name in ZEE_ARCHIVE_LOGOS:
        filename = ZEE_ARCHIVE_LOGOS[name]
        path = IMAGES / filename
        original = read_image(ZEE_ARCHIVE_SOURCE)
        if original is None:
            # A network outage must not destroy the last available logo.
            if path.exists():
                with Image.open(path) as old:
                    old.verify()
                return (name, filename, "brand")
            raise RuntimeError("The Zee Bangla archive logo source is unavailable")
        # Use the authentic higher-resolution artwork, not a photograph crop.
        result,kind=card(name, original)
        if name == "Zee Bangla HD":
            # The source graphic has no HD suffix; add a separate crisp badge.
            # Do not touch the circular mark or Bengali wordmark.
            pill_w, pill_h = 74, 42
            output = Image.new("RGBA", (result.width+pill_w, max(result.height, pill_h+12)), (0,0,0,0))
            output.alpha_composite(result, (0, (output.height-result.height)//2))
            drawer = ImageDraw.Draw(output)
            x = result.width+8
            y = (output.height-pill_h)//2
            drawer.rounded_rectangle((x,y,x+54,y+pill_h),radius=10,fill=(181,12,29,255))
            drawer.text((x+27,y+pill_h//2), "HD", anchor="mm",font=font(23),fill=(255,255,255,255))
            result = output
        stream = io.BytesIO()
        result.quantize(colors=192, method=Image.Quantize.FASTOCTREE,
                        dither=Image.Dither.NONE).save(stream,format="PNG",optimize=True)
        data=stream.getvalue()
        if not path.exists() or path.read_bytes()!=data:
            path.write_bytes(data)
        return (name,filename,"brand")
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
    # Palette mode keeps transparency while minimizing download weight.
    result.quantize(colors=192, method=Image.Quantize.FASTOCTREE,
                    dither=Image.Dither.NONE).save(stream, format="PNG", optimize=True)
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
            if name in TV_CONTRAST_LOGOS:
                uri=ROOT_URL+filename+"?v=real-channel-art-20261124b"
            elif name in ZEE_ARCHIVE_LOGOS:
                uri=ROOT_URL+filename+"?v=zee-original-clear-20261023"
            else:
                uri=ROOT_URL+filename+"?v=main-logo-visibility-20261125"
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
                "clear_name_fallbacks":statuses["fallback"],
                "brand_channels":[name for name,filename,kind in result if kind=="brand"],
                "fallback_channels":[name for name,filename,kind in result if kind=="fallback"],
                "size":"variable-aspect transparent PNG; tightly trimmed, 4px safety edge",
                "note":"Brand artwork is sourced from channel/provider logo images; fallback_channels are text-only and must not be represented as official logos."}
        STATUS.write_text(json.dumps(status,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("Local channel logos:",dict(statuses),"total",len(result))

if __name__=="__main__":
    main()
