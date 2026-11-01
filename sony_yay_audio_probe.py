#!/usr/bin/env python3
"""TEST-only speech-language verification of Sony YAY live streams.

Only a source that already passed three spaced FFmpeg video/segment checks can
be promoted. Two fresh audio excerpts must independently be recognized as Hindi.
No recordings are committed or retained. MAIN playlists are never opened.
"""
import datetime as dt
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "sony_yay_probe_results.json"
AUDIO_RESULTS = ROOT / "sony_yay_audio_probe_results.json"
TEST = ROOT / "documentary_hd_tests.m3u"
LOGO = "https://raw.githubusercontent.com/sabbir420haha/link3-iptv-auto/main/logos/sony-yay.png"

def record_audio(url, seconds=20, referer=None, user_agent=None):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
           "-rw_timeout", "15000000"]
    if user_agent:
        cmd += ["-user_agent", user_agent]
    if referer:
        cmd += ["-referer", referer]
    cmd += ["-i", url, "-map", "0:a:0",
            "-vn", "-ac", "1", "-ar", "16000", "-t", str(seconds),
            "-y", path]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=65)
        if p.returncode != 0 or os.path.getsize(path) < 16000 * 2 * 8:
            raise RuntimeError("no 8-second decodable audio: " + p.stderr[-180:])
        return path
    except Exception:
        os.unlink(path)
        raise

def main():
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    candidates = [r for r in data["results"]
                  if r.get("status") == "remote_90s_video_verified"
                  and r.get("live_advancement_confirmed")
                  and not r.get("hindi_audio_metadata")
                  and r.get("hindi_claim")]
    results = []
    published = []
    model = None
    for row in candidates:
        entry = {"id": row["id"], "url": row["url"], "video_verified": True,
                 "audio_checks": [], "hindi_spoken_confirmed": False}
        try:
            if model is None:
                from faster_whisper import WhisperModel
                model = WhisperModel("base", device="cpu", compute_type="int8")
            for i in range(2):
                wav = record_audio(row["url"], referer=row.get("referer"),
                                   user_agent=row.get("user_agent"))
                try:
                    segments, info = model.transcribe(
                        wav, beam_size=2, vad_filter=True,
                        condition_on_previous_text=False, task="transcribe")
                    transcript = " ".join(s.text.strip() for s in segments).strip()
                    devanagari = len(re.findall(r"[\u0900-\u097F]", transcript))
                    entry["audio_checks"].append({
                        "language": info.language,
                        "language_probability": round(info.language_probability, 3),
                        "speech_text_excerpt": transcript[:150],
                        "devanagari_characters": devanagari})
                finally:
                    os.unlink(wav)
                if i == 0:
                    time.sleep(15)
            entry["hindi_spoken_confirmed"] = (
                len(entry["audio_checks"]) == 2
                and all(s["language"] == "hi"
                        and s["language_probability"] >= 0.80
                        and s["devanagari_characters"] >= 10
                        for s in entry["audio_checks"]))
            if entry["hindi_spoken_confirmed"]:
                before = TEST.read_text(encoding="utf-8")
                if not before.lstrip().startswith("#EXTM3U"):
                    raise ValueError("Invalid TEST playlist")
                if row["url"] not in before:
                    nums = [int(x) for x in re.findall(
                        r"Sony YAY Hindi TEST (\d+)", before)]
                    number = max(nums, default=0) + 1
                    title = f"Sony YAY Hindi TEST {number:02d} ({row['height']}p; speech-checked)"
                    with TEST.open("a", encoding="utf-8") as f:
                        f.write(f'#EXTINF:-1 tvg-name="{title}" tvg-logo="{LOGO}" '
                                f'group-title="Sony YAY Hindi TEST",{title}\n'
                                f'{row["url"]}\n')
                    published.append({"url": row["url"], "number": number,
                                      "height": row["height"],
                                      "audio_checks": entry["audio_checks"]})
        except Exception as exc:
            entry["error"] = str(exc)[:300]
        results.append(entry)
    report = {"checked_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "video_report": "sony_yay_probe_results.json",
              "tested_audio_count": len(results),
              "newly_published": published,
              "method": "Two independent 20-second audio excerpts, 15 seconds apart; faster-whisper base int8 language identification. Require both hi >=0.80 and >=10 Devanagari characters. Video already decoded at three spaced intervals.",
              "Link3_not_verified": True, "MAIN_unchanged": True,
              "results": results}
    AUDIO_RESULTS.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n",
                             encoding="utf-8")
    print(json.dumps({"audio_tested": len(results), "published": len(published),
                      "results": results}, ensure_ascii=False))
if __name__ == "__main__":
    main()
