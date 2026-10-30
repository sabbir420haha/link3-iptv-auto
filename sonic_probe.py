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
import subprocess
import urllib.parse as up
from pathlib import Path
from documentary_probe import fetch,manifest

ROOT=Path(__file__).resolve().parent
ALL_CANDIDATES=json.loads((ROOT/"sonic_hindi_candidates.json").read_text(encoding="utf-8"))["candidates"]
PRIOR_PATH=ROOT/"sonic_hindi_probe_results.json"
PRIOR=json.loads(PRIOR_PATH.read_text(encoding="utf-8")) if PRIOR_PATH.exists() else {"results":[]}
FAILED={r["url"] for r in PRIOR.get("results",[]) if r.get("status")=="rejected"}
CANDIDATES=[c for c in ALL_CANDIDATES if c["url"] not in FAILED and not c.get("remote_probe")]
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
                h=re.search(r"RESOLUTION=\d+x(\d+)",line)
                bw=re.search(r"BANDWIDTH=(\d+)",line)
                nxt=next((v for v in lines[i+1:] if not v.startswith("#")),None)
                if nxt:variants.append((int(h.group(1)) if h else 0,
                                        int(bw.group(1)) if bw else 0,up.urljoin(final,nxt)))
        if variants:
            current=max(variants,key=lambda v:(v[0],v[1]))[2]
            continue
        seq=re.search(r"#EXT-X-MEDIA-SEQUENCE:(\d+)",s)
        chunks=[up.urljoin(final,lines[i+1]) for i,l in enumerate(lines[:-1])
                if l.startswith("#EXTINF:") and not lines[i+1].startswith("#")]
        if not chunks:return None
        return {"last_sequence":int(seq.group(1))+len(chunks)-1 if seq else None,
                "segment":chunks[-1],"finished":"#EXT-X-ENDLIST" in s}
    return None

def decoded_frames(url):
    """FFmpeg must actually decode >=8 frames, not merely parse a manifest."""
    cmd=["ffmpeg","-hide_banner","-nostdin","-loglevel","error",
         "-rw_timeout","10000000","-i",url,"-map","0:v:0",
         "-an","-frames:v","12","-f","null","-","-progress","pipe:1"]
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
    except subprocess.TimeoutExpired:
        raise ValueError("ffmpeg_video_decode_timeout")
    nums=[int(x) for x in re.findall(r"(?m)^frame=(\d+)",p.stdout)]
    frames=max(nums,default=0)
    if p.returncode or frames<8:
        raise ValueError("ffmpeg_decode_failed:"+str(frames)+" frames; "+p.stderr[-160:].replace("\n"," "))
    return frames

def validate(item):
    row={k:item[k] for k in ("id","url","feed","source")}
    url=item["url"]
    try:
        if re.search(r"(?:[?&]mac=|/play/live\.php|/stalker/)",url,re.I):
            raise ValueError("credential_bound_portal")
        h,l,kind,size=manifest(url)
        if h<240:
            raise ValueError("no_decodable_video_height:"+str(h))
        frames1=decoded_frames(url)
        # Check a second full real video piece / fetching stream a second time.
        # Playlists 24/7 may reuse a segment briefly; don't mistake it for validated movement.
        first=playlist_window(url)
        time.sleep(14)
        h2,l2,kind2,size2=manifest(url)
        if h2<240:raise ValueError("second_video_check_failed")
        frames2=decoded_frames(url)
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
                   checks=2,decoded_frames_first=frames1,decoded_frames_second=frames2,
                   segment_bytes_first=size,segment_bytes_second=size2,
                   live_playlist_advanced=(first is not None and second is not None),
                   format=kind)
    except Exception as e:row.update(status="rejected",error=str(e)[:240])
    return row

def main():
    with cf.ThreadPoolExecutor(max_workers=15) as pool:
        rows=list(pool.map(validate,CANDIDATES))
    passed=[r for r in rows if r["status"]=="remote_live_video_verified"
            and (r["hindi_audio_tag"] or r["hindi_feed_label"])]
    # Append ONLY newly verified Sonic sources; never clear prior verified tests.
    existing=PLAY.read_text(encoding="utf-8") if PLAY.exists() else "#EXTM3U\n"
    published=[]
    numbers=[int(n) for n in re.findall(r"Sonic Hindi TEST (\d+)",existing)]
    next_number=max(numbers,default=0)+1
    for r in passed:
        if r["url"] in existing:
            continue
        label=f"Sonic Hindi TEST {next_number:02d} ({r['height']}p)"
        existing += (f'#EXTINF:-1 tvg-name="{label}" tvg-logo="{LOGO}" '
                     f'group-title="SONIC HINDI TEST",{label}\n{r["url"]}\n')
        published.append({"test":next_number,"url":r["url"],
                          "height":r["height"],"audio_lang_metadata":r["audio_lang_metadata"],
                          "decoded_frames_first":r["decoded_frames_first"],
                          "decoded_frames_second":r["decoded_frames_second"]})
        next_number+=1
    if published:
        PLAY.write_text(existing,encoding="utf-8")
    history=PRIOR.get("results",[])+rows
    report={"checked_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "newly_checked":len(rows),"total_results":len(history),
            "remote_verified_new":len(passed),"published":published,
            "remote_only_not_Link3":True,
            "audio_note":"Feed label is weaker evidence than HLS/segment Hindi language metadata.",
            "results":history}
    OUT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"newly_checked":len(rows),"published":published}))

if __name__=="__main__":main()
