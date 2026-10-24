#!/usr/bin/env python3
"""Read-only diagnostics for newly sourced Bangladesh ATN News TEST URLs.
Remote GitHub success does not establish Link3 playback or channel identity.
Never edits the main playlist, candidate registry or M3U files.
"""
import concurrent.futures
import datetime
import json
from pathlib import Path
from update import probe, segment_probe
ROOT=Path(__file__).resolve().parent
CANDIDATES=ROOT/"favorites_test_registry.json"
REPORT=ROOT/"atn_news_test_health.json"

def check(entry):
    url=entry["url"]
    reachable=probe(url)
    media=segment_probe(url) if reachable else False
    return {"test":entry["number"],
            "manifest":bool(reachable),
            "media_segment":bool(media),
            "link3":"NOT_VERIFIED",
            "source":entry.get("origin","GitHub"),
            "note":"No claim of correct broadcaster or buffer-free playback"}

def main():
    registry=json.loads(CANDIDATES.read_text(encoding="utf-8"))
    entries=registry["channels"]["ATN News"]["candidates"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(check,entries))
    report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sources":len(results),
            "segment_passed":sum(item["media_segment"] for item in results),
            "warning":"GitHub runner != Link3. Test each stream in IPTV Pro. Previously user-rejected 30 links excluded.",
            "results":results}
    REPORT.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    for result in results:
        print("ATN News TEST "+result["test"],"manifest",result["manifest"],"segment",result["media_segment"])
if __name__=="__main__":
    main()
