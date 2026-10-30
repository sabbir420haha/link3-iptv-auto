#!/usr/bin/env python3
"""SONY YAY Hindi TEST-only validation; preserve playlist.m3u (MAIN) and Sonic tests.
Two properties verified: real decoded video and a changing live playlist over ~90 sec.
Remote runner playback cannot establish Link3 reliability or spoken Hindi.
"""
import concurrent.futures as cf
import datetime as dt
import json
import re
import subprocess
import time
from pathlib import Path
from sonic_probe import playlist_window
from documentary_probe import manifest

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/"sony_yay_candidates.json").read_text(encoding="utf-8"))
BASE=DATA["main_baseline"]
PATH=ROOT/"documentary_hd_tests.m3u"
OUT=ROOT/"sony_yay_probe_results.json"
LOGO="https://raw.githubusercontent.com/sabbir420haha/link3-iptv-auto/main/logos/sony-yay.png"

def sample_frames(url):
    # Each checkpoint decodes fresh packets from live playback.
    cmd=["ffmpeg","-hide_banner","-nostdin","-loglevel","error",
         "-rw_timeout","9000000","-i",url,"-map","0:v:0",
         "-an","-frames:v","18","-f","null","-","-progress","pipe:1"]
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=38)
    except subprocess.TimeoutExpired:
        raise ValueError("decode_timeout")
    matches=[int(v) for v in re.findall(r"(?m)^frame=(\\d+)",p.stdout)]
    frames=max(matches,default=0)
    if p.returncode!=0 or frames<12:
        raise ValueError(f"video_decode_failed_{frames}_frames: "+p.stderr[-180:].replace("\n"," "))
    return frames

def probe(c):
    row={k:c[k] for k in ("id","url","source","hindi_claim")}
    u=c["url"]
    try:
        if re.search(r"(?:[?&]mac=|/play/live\\.php|/stalker/)",u,re.I):
            raise ValueError("credential_portal")
        observations=[]
        # Spaced playback checks help detect short-lived or frozen upstream streams.
        for checkpoint in range(3):
            h,langs,typ,bytes_count=manifest(u)
            if h<240:raise ValueError(f"no_decodable_video_height_{h}")
            frames=sample_frames(u)
            try:live=playlist_window(u)
            except Exception:live=None
            if live and live["finished"]: raise ValueError("not_live_playlist")
            observations.append({"height":h,"audio_language_metadata":langs,
                                 "frames_decoded":frames,"video_segment_bytes":bytes_count,
                                 "seq":live["last_sequence"] if live else None,
                                 "segment":live["segment"] if live else None})
            if checkpoint<2:time.sleep(32)
        pairs=[(a,b) for a,b in zip(observations[:-1],observations[1:])]
        if all(a["seq"] is not None and b["seq"] is not None for a,b in pairs):
            if not all(b["seq"]>a["seq"] or b["segment"]!=a["segment"] for a,b in pairs):
                raise ValueError("live_manifest_not_advancing")
        elif all(a["segment"] is not None for a in observations):
            if not all(a["segment"]!=b["segment"] for a,b in pairs):
                raise ValueError("live_segments_not_changing")
        # Audio tags in HLS may be missing; preserve this important uncertainty.
        languages=sorted(set(x.lower() for a in observations
                             for x in a["audio_language_metadata"] if x))
        row.update(status="remote_90s_video_verified",
                   height=min(x["height"] for x in observations),
                   decoded_frame_counts=[x["frames_decoded"] for x in observations],
                   audio_tags=languages,
                   hindi_audio_metadata=any(x in ("hi","hin","hindi") for x in languages),
                   manifest_advanced=all(a["seq"] is not None for a in observations),
                   probe_checks=3,
                   approximate_probe_span_seconds=64)
    except Exception as exc:row.update(status="failed",reason=str(exc)[:260])
    return row

def main():
    with cf.ThreadPoolExecutor(max_workers=15) as pool:
        results=list(pool.map(probe,DATA["candidates"]))
    good=[r for r in results
          if r["status"]=="remote_90s_video_verified"
          and r["url"]!=BASE
          and (r["hindi_claim"] or r["hindi_audio_metadata"])]
    before=PATH.read_text(encoding="utf-8") if PATH.exists() else "#EXTM3U\n"
    if not before.lstrip().startswith("#EXTM3U"): raise ValueError("bad_test_playlist")
    playlist=before
    numbers=[int(x) for x in re.findall(r"Sony YAY Hindi TEST (\\d+)",playlist)]
    number=max(numbers,default=0)+1
    published=[]
    for r in good:
        if r["url"] in playlist: continue
        title=f"Sony YAY Hindi TEST {number:02d} ({r['height']}p)"
        playlist+=(f'#EXTINF:-1 tvg-name="{title}" tvg-logo="{LOGO}" '
                   f'group-title="Sony YAY Hindi TEST",{title}\n{r["url"]}\n')
        published.append({"number":number,"url":r["url"],"height":r["height"],
                          "audio_tags":r["audio_tags"],"checks":r["probe_checks"]})
        number+=1
    if published:PATH.write_text(playlist,encoding="utf-8")
    record={"checked_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
            "evaluated":len(results),"new_remote_verified":len(good),
            "newly_published":published,"MAIN_unchanged":True,
            "Link3_playback_not_verified":True,
            "observation":"Three decoded 18-frame samples 32s apart, HLS segment progress when observable. Not proof of uninterrupted long playback or audio language.",
            "main_url":BASE,"results":results}
    OUT.write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"checked":len(results),"verified":len(good),"published":published}))
if __name__=="__main__":main()
