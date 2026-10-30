#!/usr/bin/env python3
"""Sonic Hindi-only candidate validation. Never change playlist.m3u or other MAIN data.
Only NEW, playable remote video sources are published to documentary_hd_tests.m3u.
Results do NOT prove ISP Link3 playback or that spoken audio is Hindi.
"""
import concurrent.futures as cf
import datetime as dt
import json
import re
import time
import urllib.parse as up
from pathlib import Path
from documentary_probe import fetch,manifest

ROOT=Path(__file__).resolve().parent
CANDIDATES=json.loads((ROOT/"sonic_hindi_candidates.json").read_text(encoding="utf-8"))["candidates"]
PLAY=ROOT/"documentary_hd_tests.m3u"
OUT=ROOT/"sonic_hindi_probe_results.json"
LOGO="https://upload.wikimedia.org/wikipedia/en/2/2b/Nickelodeon_Sonic_logo.png"

def playlist_window(url):
    """Return sequence/segment identifier from a public HLS video manifest."""
    current=url
    for depth in range(5):
        payload,final,_=fetch(current,120000)
        s=payload.decode("utf-8-sig","replace")
        if "#EXTM3U" not in s[:200]:return None
        lines=[x.strip() for x in s.splitlines() if x.strip()]
        variants=[]
        for i,line in enumerate(lines[:-1]):
            if line.startswith("#EXT-X-STREAM-INF"):
                h=re.search(r"RESOLUTION=\\d+x(\\d+)",line)
                bw=re.search(r"BANDWIDTH=(\\d+)",line)
                nxt=next((v for v in lines[i+1:] if not v.startswith("#")),None)
                if nxt:variants.append((int(h.group(1)) if h else 0,
                                        int(bw.group(1)) if bw else 0,up.urljoin(final,nxt)))
        if variants:
            current=max(variants,key=lambda v:(v[0],v[1]))[2]
            continue
        seq=re.search(r"#EXT-X-MEDIA-SEQUENCE:(\\d+)",s)
        chunks=[up.urljoin(final,lines[i+1]) for i,l in enumerate(lines[:-1])
                if l.startswith("#EXTINF:") and not lines[i+1].startswith("#")]
        if not chunks:return None
        return {"last_sequence":int(seq.group(1))+len(chunks)-1 if seq else None,
                "segment":chunks[-1],"finished":"#EXT-X-ENDLIST" in s}
    return None

def validate(item):
    row={k:item[k] for k in ("id","url","feed","source")}
    url=item["url"]
    try:
        if re.search(r"(?:[?&]mac=|/play/live\\.php|/stalker/)",url,re.I):
            raise ValueError("credential_bound_portal")
        h,l,kind,size=manifest(url)
        if h<240:
            raise ValueError("no_decodable_video_height:"+str(h))
        # Check a second full real video piece / fetching stream a second time.
        # Playlists 24/7 may reuse a segment briefly; don't mistake it for validated movement.
        first=playlist_window(url)
        time.sleep(14)
        h2,l2,kind2,size2=manifest(url)
        if h2<240:raise ValueError("second_video_check_failed")
        second=playlist_window(url)
        if first and second:
            advanced=((first["last_sequence"] is not None
                       and second["last_sequence"] is not None
                       and second["last_sequence"]>first["last_sequence"])
                      or first["segment"]!=second["segment"])
            if first["finished"] or second["finished"]:
                raise ValueError("not_live_endlist")
            if not advanced:raise ValueError("live_hls_not_advancing_after_14s")
        lang=sorted(set(x.lower() for x in (l+l2) if x))
        known_hindi=any(x in ("hi","hin","hindi") for x in lang)
        label_hindi=("hindi" in item["feed"].lower()
                     or "/hin2/" in url.lower() or "sonichindi" in url.lower()
                     or "sonic_hindi" in url.lower() or "_hin" in url.lower())
        row.update(status="remote_live_video_verified",height=min(h,h2),
                   audio_lang_metadata=lang,hindi_audio_tag=known_hindi,
                   hindi_feed_label=label_hindi,
                   checks=2,segment_bytes_first=size,segment_bytes_second=size2,
                   live_playlist_advanced=(first is not None and second is not None),
                   format=kind)
    except Exception as e:row.update(status="rejected",error=str(e)[:240])
    return row

def main():
    with cf.ThreadPoolExecutor(max_workers=15) as pool:
        rows=list(pool.map(validate,CANDIDATES))
    passed=[r for r in rows if r["status"]=="remote_live_video_verified"
            and (r["hindi_audio_tag"] or r["hindi_feed_label"])]
    # Publication only into separate TEST. Source URL never copied from MAIN.
    output=["#EXTM3U","# Sonic Hindi TEST sources only. Verified remotely from GitHub runner, not on Link3.",
            "# Spoken Hindi audio NOT established unless HLS/segment language metadata confirms it.",
            "# Existing Discovery/NatGeo searching is disabled. MAIN Playlist never touched."]
    for i,r in enumerate(passed,1):
        label=f"Sonic Hindi TEST {i:02d} ({r['height']}p)"
        output.append(f'#EXTINF:-1 tvg-name="{label}" tvg-logo="{LOGO}" group-title="SONIC HINDI TEST",{label}')
        output.append(r["url"])
    PLAY.write_text("\n".join(output)+"\n",encoding="utf-8")
    report={"checked_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "source_count":len(rows),"remote_verified":len(passed),
            "remote_only_not_Link3":True,
            "audio_note":"Feed label is weaker evidence than actual HLS/segment Hindi language metadata.",
            "results":rows}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"checked":len(rows),"working_sonic_test":len(passed),
                      "verified":list((r["id"],r["height"]) for r in passed)}))
if __name__=="__main__":main()
