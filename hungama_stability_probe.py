#!/usr/bin/env python3
"""Read-only, 3-point audio/video check of Hungama TEST 17.
Never edits playlists or production streams; GitHub runner != Link3.
"""
import datetime as dt, json, re, subprocess, time, urllib.request
from pathlib import Path
URL="http://iptvcasomsapi.jprdigital.in/x-media/C0408/master.m3u8"
ROOT=Path(__file__).resolve().parent

def run(args,timeout=38):
    try:
        p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        return {"exit":p.returncode,"stdout":p.stdout[-3000:],"stderr":p.stderr[-1200:]}
    except subprocess.TimeoutExpired:
        return {"exit":-1,"stdout":"","stderr":"process timed out"}

def check():
    r={"url":URL,"checked_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"scope":"GitHub runner, NOT user's Link3","reliable_link3_playback":None,"confirmed_hindi_audio":None}
    meta=run(["ffprobe","-v","error","-rw_timeout","10000000","-show_entries","stream=codec_type,codec_name,channels","-of","json",URL],40)
    try:
        streams=json.loads(meta["stdout"]).get("streams",[])
    except Exception:streams=[]
    r["stream_types"]=[x.get("codec_type") for x in streams]
    r["audio_tracks_found"]=sum(x.get("codec_type")=="audio" for x in streams)
    r["video_tracks_found"]=sum(x.get("codec_type")=="video" for x in streams)
    r["ffprobe_error"]=meta["stderr"] if meta["exit"] else None
    rounds=[]
    for n in range(3):
        if n:time.sleep(20)
        cmd=["ffmpeg","-hide_banner","-nostdin","-loglevel","error","-rw_timeout","10000000","-i",URL,"-t","8","-map","0:v:0","-map","0:a:0?","-f","null","-","-progress","pipe:1"]
        p=run(cmd,45)
        frames=[int(x) for x in re.findall(r"(?m)^frame=\s*(\d+)",p["stdout"])]
        times=re.findall(r"(?m)^out_time=(\S+)",p["stdout"])
        rounds.append({"point":n+1,"decode_exit":p["exit"],"max_frames":max(frames,default=0),"out_time":times[-1] if times else None,"error":p["stderr"]})
    r["rounds"]=rounds
    r["three_video_checkpoints"]=all(x["decode_exit"]==0 and x["max_frames"]>=12 for x in rounds)
    r["audio_present_and_three_video_checkpoints"]=bool(r["audio_tracks_found"] and r["three_video_checkpoints"])
    r["warning"]="Does not prove uninterrupted audio or Hindi speech over minutes, and cannot establish Link3-specific reliability."
    return r

if __name__=="__main__":
    obj=check()
    (ROOT/"hungama_stability_results.json").write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"video_checks":obj["three_video_checkpoints"],"audio_tracks":obj["audio_tracks_found"],"rounds":obj["rounds"]}))
