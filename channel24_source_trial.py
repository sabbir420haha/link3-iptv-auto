#!/usr/bin/env python3
"""Read-only Channel 24 source/rendition trial. Never changes playlist or URLs.

Compare the current pinned HLS feed with independently published Channel 24
CDNs, testing actual video bytes and 9 live HLS windows across ~64 seconds.
The test runs on GitHub's network, NOT on the user's Link3 Wi-Fi.
"""
import concurrent.futures
import datetime
import hashlib
import json
import re
import time
import urllib.parse
from pathlib import Path
from update import fetch_hls_bytes, direct_media_ok

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "channel24_source_trial.json"
CANDIDATES = {
    "existing_gpcdn": "https://drk6xq0vhn.gpcdn.net/live/channel_24_abr/index.m3u8",
    "akash_gpcdn": "https://owrcovcrpy.gpcdn.net/bpk-tv/1703/output/index.m3u8",
    "aynaott": "https://tvsen6.aynaott.com/YrVDF8gu/index.m3u8",
    "ottplus": "https://stream.ottplus.live/live/channel_24_abr/index.m3u8",
    "digijadoo_edge": "https://edge01.iptv.digijadoo.net/live/channel_24/chunks.m3u8",
    "digijadoo_bol": "https://bol.iptv.digijadoo.net/live/channel_24/chunks.m3u8",
    "ayna_scope": "https://tvsen6.aynascope.net/channel24/index.m3u8",
    "jagobd": "https://bdsl.jagobd.com:444/c2VydmVyX6RpbEU8Mi8xNy8yMDE0GIDU6RgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcGVMZEJCTEFWeVN3PTOmdFsaWRtaW51aiPhnPTI/channel24-sg-e8e.stream/chunks.m3u8",
    "bozz_rongo": "https://bozztv.com/rongo/rongo-Channel24HD/index.m3u8",
    "globalbd_mirror": "http://163.172.29.246:8081/globalbd/channel24/chunks.m3u8",
    "jagobd_public_legacy": "http://iptvbd.jagobd.com:1931/live-orgin/channel24-sg-e8e.stream/chunks.m3u8",
    "jagobd_tempskyview": "https://tempskyview.jagobd.com:441/c5V6mmMyX7RpbEU9Mi8xNy8yMDEOGIDU6RgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcGVMZEJCTEFWeVN3PT0mdFsaWRtaW51aiPhnPTI/channel24-sg-e8e.stream/chunks.m3u8",
    "digijadoo_edge_http": "http://edge01.iptv.digijadoo.net/live/channel_24/chunks.m3u8",
    "ottplus_low_bitrate": "https://stream.ottplus.live/live/channel_24_abr/index.m3u8",

}
STEPS = 9
INTERVAL = 8
MAX_MANIFEST = 54000

def manifest(uri):
    t0 = time.monotonic()
    data, content_type = fetch_hls_bytes(uri, MAX_MANIFEST, 9)
    t = data.decode("utf-8-sig", "replace")
    if "#EXTM3U" not in t[:500]:
        raise ValueError("Not an HLS manifest")
    return t, round(time.monotonic()-t0,2)

def resolve_variant(uri):
    manifest_text, latency = manifest(uri)
    variants = []
    for depth in range(3):
        # Ordinary HLS AES-128 can be handled by standard IPTV players.
        # Never attempt protected SAMPLE-AES, DRM key formats or decryption.
        if ("METHOD=SAMPLE-AES" in manifest_text or
                "#EXT-X-SESSION-KEY:" in manifest_text or
                "KEYFORMAT=" in manifest_text):
            raise ValueError("DRM/protected feed cannot be examined")
        lines = [line.strip() for line in manifest_text.splitlines() if line.strip()]
        if "#EXT-X-STREAM-INF" not in manifest_text:
            return uri, variants, latency
        choices = []
        for i, line in enumerate(lines[:-1]):
            if line.startswith("#EXT-X-STREAM-INF:") and not lines[i+1].startswith("#"):
                bm = re.search(r"BANDWIDTH=(\d+)",line)
                hm = re.search(r"RESOLUTION=\d+x(\d+)",line)
                b = int(bm.group(1)) if bm else 0
                h = int(hm.group(1)) if hm else 0
                url = urllib.parse.urljoin(uri, lines[i+1])
                choices.append((b,h,url))
        if not choices:
            raise ValueError("No master variants")
        variants = [{"bandwidth_kbps":round(b/1000),
                     "height":h,
                     "source_path":urllib.parse.urlsplit(u).path.split("/")[-1]}
                    for b,h,u in choices]
        # Keep under ~1.6 Mbps for more resilient viewing on phones/TVs.
        usable = [c for c in choices if (c[0]==0 or c[0] <= 1600000)
                  and (c[1] == 0 or c[1] <= 720)]
        selected = max(usable, key=lambda x:(x[1],x[0])) if usable else min(choices, key=lambda x:(x[0],x[1]))
        uri=selected[2]
        manifest_text, latency = manifest(uri)
    raise ValueError("Nested master playlists")

def snapshot(uri):
    text, load_seconds = manifest(uri)
    if ("METHOD=SAMPLE-AES" in text or "KEYFORMAT=" in text or
            "#EXT-X-MAP:" in text):
        raise ValueError("DRM/fMP4 rendition not supported by trial")
    aes128 = ("#EXT-X-KEY:" in text and "METHOD=AES-128" in text)
    lines=[line.strip() for line in text.splitlines() if line.strip()]
    segments=[line for line in lines if not line.startswith("#")]
    if "#EXTINF:" not in text or not segments:
        raise ValueError("No video segment lines")
    m=re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)",text)
    tm=re.search(r"#EXT-X-TARGETDURATION:(\d+)",text)
    latest=urllib.parse.urljoin(uri,segments[-1])
    return {
        "seq":int(m.group(1))+len(segments)-1 if m else None,
        "hash":hashlib.sha256(latest.encode()).hexdigest()[:16],
        "latest_url":latest,
        "target_duration":int(tm.group(1)) if tm else None,
        "request_sec":load_seconds,
        "aes128":aes128,
        "endlist":"#EXT-X-ENDLIST" in text
    }

def segment_bytes(uri, aes128=False):
    t=time.monotonic()
    data,_=fetch_hls_bytes(uri,24576,9)
    # HLS AES-128 segments are encrypted MPEG-TS, so TS sync bytes cannot
    # be seen without decrypting; validate plausible binary only.
    plausible_encrypted=(aes128 and len(data)>=1880 and
                        not data[:100].lstrip().startswith((b"<",b"#EXTM3U",b"{")))
    return {"video_segment_bytes_ok":direct_media_ok(data) or plausible_encrypted,
            "aes128_segment":aes128,
            "segment_sample_bytes":len(data),
            "segment_first_bytes":data[:8].hex(),
            "segment_download_sec":round(time.monotonic()-t,2)}

def inspect(item):
    tag,origin=item
    t0=time.monotonic()
    try:
        media,variants,init_latency=resolve_variant(origin)
        if urllib.parse.urlsplit(media).query:
            public_media="(signed URL hidden)"
        else:
            public_media=media
        trials=[]
        for i in range(STEPS):
            if i:
                time.sleep(max(0, t0+i*INTERVAL-time.monotonic()))
            try:
                s=snapshot(media)
                trials.append({"at_seconds":round(time.monotonic()-t0,1),
                               "seq":s["seq"], "hash":s["hash"],"ok":True,
                               "request_sec":s["request_sec"],
                               "endlist":s["endlist"]})
                if i == 0:
                    initial=s
            except Exception as ex:
                trials.append({"at_seconds":round(time.monotonic()-t0,1),
                               "ok":False,"error":str(ex)[:130]})
        good=[x for x in trials if x.get("ok")]
        changes=0;reversals=0;stale=0;seen=set()
        for a,b in zip(good,good[1:]):
            if a["hash"]!=b["hash"]:
                changes+=1
            else:
                stale+=1
            if a["seq"] is not None and b["seq"] is not None and b["seq"]<a["seq"]:
                reversals+=1
            if a["hash"] not in seen:seen.add(a["hash"])
        for check in good[1:]:
            if check["hash"] in seen and check["hash"] != good[-1]["hash"]:
                pass
        video_test=[]
        for s in (initial if "initial" in locals() else None,
                  snapshot(media) if good else None):
            if s:
                try:video_test.append(segment_bytes(s["latest_url"], s["aes128"]))
                except Exception as e:video_test.append({"video_segment_bytes_ok":False,"error":str(e)[:120]})
        valid_segment=bool(video_test) and all(x.get("video_segment_bytes_ok") for x in video_test)
        return {
            "label":tag, "source":origin, "selected_media_url":public_media,
            "available_variants":variants,"initial_request_sec":init_latency,
            "manifest_polls_ok":len(good),"manifest_polls_total":STEPS,
            "advances":changes,"sequence_reversals":reversals,
            "unchanged_adjacent_polls":stale,
            "manifest_latency_max_sec":max((x["request_sec"] for x in good),default=None),
            "video_samples":video_test,
            "eligible_from_github":len(good)==STEPS and changes>=4
                and reversals==0 and valid_segment and not any(x["endlist"] for x in good),
            "windows":trials,
            "warning":"Server tests only, Link3/IPTV Pro playback NOT independently confirmed",
        }
    except Exception as e:
        return {"label":tag,"source":origin,
                "eligible_from_github":False,"error":(type(e).__name__+": "+str(e))[:170],
                "manifest_polls_ok":0}

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(inspect,CANDIDATES.items()))
    report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "purpose":"Channel24 candidates only; never changes main 77-channel playlist",
            "scope":"GitHub Actions network only; do not infer Link3",
            "sample_window_seconds":64,
            "results":results}
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    for row in results:
        print(row["label"],"eligible=",row["eligible_from_github"],
              "progress=",row.get("advances"),"polls=",row.get("manifest_polls_ok"),
              "reversals=",row.get("sequence_reversals"),"error=",row.get("error"))

if __name__=="__main__":
    main()
