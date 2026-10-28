#!/usr/bin/env python3
"""Read-only, runner-only checks of newly discovered public IPTV candidates.
Never changes channels.json, playlist.m3u or pinned user-confirmed streams.
A network-accessible HLS fragment does not establish stream identity,
audio language, broadcast rights, or Link3 IPTV Pro playback.
"""
import concurrent.futures
import datetime
import json
import re
import subprocess
import urllib.parse
from pathlib import Path
from update import fetch_hls_bytes, allowed, direct_media_ok

OUT = Path(__file__).with_name("three_missing_probe.json")
CANDIDATES = [
    # 2026-10-28: source-backed HLS candidates on the same publicly listed
    # ITCN service as a runner-reachable Disney HD feed; not yet viewer-tested.
    {"channel":"Disney HD Hindi","url":"https://s1.itcnbd.live/Disney-D/index.m3u8",
     "evidence":"github.com/eishakilei-bd08/eitv dormns20.m3u labels Disney HD (Tata Play); 2026-10-28 status.json runner audit saw 720p + media segment; Hindi audio and exact Disney identity unconfirmed",
     "expected_audio":"hi","min_height":720},
    {"channel":"Sonic Hindi","url":"https://s2.itcnbd.live/server-3/stream/cGxheWVyLnBocD9zdHJlYW09NDU.m3u8",
     "evidence":"github.com/ShahirTech/Shahir-TV-Playlist ITCN_Fresh_Ultimate.m3u labels SONIC; Hindi vs Bengali not established; audit only",
     "expected_audio":"hi"},
    # 2026-10-28: independent status.json audit previously found a real media fragment
    # at this candidate; check audio metadata/identity separately before any release.
    {"channel":"Sonic Bangla","url":"https://iptvcable.netlify.app/Altogether-007/Cartoon/SONIC.m3u8",
     "evidence":"sabbir420haha/link3-iptv-auto status.json candidate audit 2026-10-28: HLS manifest and media segment reachable from GitHub runner; source title Sonic but Bengali audio/identity unverified",
     "expected_audio":"bn"},
    # 2026-10-28: additional source-backed, non-BDIX-oriented candidates.
    # Public playlist labels alone do not verify channel identity, audio or Link3 playback.
    {"channel":"Sonic Hindi","url":"http://144.217.70.181:9587/hin2/SONIC/tracks-v1a1/mono.m3u8",
     "evidence":"github.com/yash-vardhan-github/public-file-host tv.m3u and public IPTV source index; Sonic Hindi label, Canada-hosted endpoint; independent audio not verified",
     "expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"http://103.229.254.25:7001/play/a0dl/index.m3u8",
     "evidence":"github.com/ttmttm/iptv_2026 streams/in.m3u (iptv-org mirror), Sonic (576p); Hindi language not independently confirmed",
     "expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://playyonogames.in/live.php?id=1345&format=.m3u8",
     "evidence":"github.com/Rapu1/0 0 playlist, explicitly Sonic Bangla Jio ID 1345 with Indian-hosted URL; format= variant not yet audited; no auth bypass",
     "expected_audio":"bn"},
    # 2026-10-27 23:39 Bangladesh time: new source-backed audit-only candidates; no viewer claims.
    {"channel":"Sonic Hindi","url":"https://hey-lookme.shop/live.php?id=815","evidence":"github.com/sm-monirulislam/SM-IPTV jio_tv.m3u, channel 815 explicitly Sonic Hindi; playlist lists HTTP referrer; no authentication bypass","expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://hey-lookme.shop/live.php?id=1345","evidence":"github.com/sm-monirulislam/SM-IPTV jio_tv.m3u, channel 1345 explicitly Sonic Bangla; playlist lists HTTP referrer; no authentication bypass","expected_audio":"bn"},
    {"channel":"Sonic Hindi","url":"https://mini.allinonereborn.fun/jiotv-www/app/ts_live_815.m3u8","evidence":"github.com/eishakilei-bd08/eitv f.m3u, labeled Sonic Hindi, Jio 815","expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://mini.allinonereborn.fun/jiotv-www/app/ts_live_1345.m3u8","evidence":"github.com/eishakilei-bd08/eitv f.m3u, labeled Sonic Bangla, Jio 1345","expected_audio":"bn"},
    {"channel":"Sonic Bangla","url":"http://live.balajibroadband.com:3500/live/1345.m3u8","evidence":"github.com/sm-monirulislam/SM-IPTV Combined_Live_TV.m3u, 2026-10-27 explicitly Sonic Bangla, India-hosted ISP; non-BDIX not proven","expected_audio":"bn"},
    {"channel":"Sonic Hindi","url":"https://ninjatv.host/star/ninjatv.m3u8?id=207.ts","evidence":"github.com/tvbd/m3uplayer m3u/splaylist.m3u, labeled IN: sonic_Hindi; identity unconfirmed","expected_audio":"hi"},
    {"channel":"Disney HD Hindi","url":"http://119.156.26.155:8000/play/a05u/index.m3u8","evidence":"github.com/tvbd/m3uplayer m3u/splaylist.m3u, labeled Disney Channel HD; Indian identity/Hindi/720p unconfirmed","expected_audio":"hi","min_height":720},
    {"channel":"Disney HD Hindi","url":"http://on.deflix.xyz:8880/live/hasan19/hasan1519/3360.m3u8","evidence":"github.com/tvbd/m3uplayer m3u/splaylist.m3u, labeled Disney India; Hindi and 720p unconfirmed","expected_audio":"hi","min_height":720},
    # 2026-10-27 fresh public GitHub candidate references. Audit-only; never promote without identity/audio checks.
    {"channel":"Sonic Hindi","url":"https://jiotv.hadinetbd.tech/jio/v1/Sonic_Hindi/Sonic_Hindi/Sonic_Hindi.m3u8",
     "evidence":"github.com/jongg57ed/jongg57 ip27october, 2026-10-27 Sonic Hindi ID 815", "expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"https://sonamul3535.vercel.app/Sonic-Hindi.m3u8",
     "evidence":"github.com/arafat-anowar/iptv ip.m3u8, specifically Sonic Hindi", "expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://cdn.nayeemparvez.workers.dev/bpk-tv/Sonic_Bangla_MOB/Fallback/index.m3u8",
     "evidence":"github.com/freedish2024/personal-project.sr Sun.m3u, labeled Nick Bangla despite Sonic_Bangla path; identity conflicting, probe only", "expected_audio":"bn"},
    {"channel":"Sonic Bangla","url":"https://techiesneh.in1.bitmana.io/snehapi/jioapi/snehjioxx.php?c=Sonic_Bangla&q=800&e=junk.m3u8",
     "evidence":"github.com/TheSamimMandal/SamimWorld SamimJio.m3u, Sonic Bangla channel label", "expected_audio":"bn"},
    # 2026-10-27 source-backed new public-list entries; independent probe ONLY.
    # Never promote these without HLS segment + channel identity + audio evidence.
    {"channel":"Disney HD Hindi","url":"http://103.153.39.34:8000/play/a04o/index.m3u8",
     "evidence":"github.com/Sonuiptvnew/Sonuiptvnew Sonuiptvfree; labeled Disney (India identity, Hindi and HD still unconfirmed)",
     "expected_audio":"hi","min_height":720},
    {"channel":"Sonic Hindi","url":"http://103.153.39.34:8000/play/a04p/index.m3u8",
     "evidence":"github.com/riyad456/supernetIPTV live; labeled Sonic (2), language unconfirmed",
     "expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"https://allinonereborn.com/tatatv.php?id=11667",
     "evidence":"github.com/Bhavesh0a/Index Index6; explicitly SONIC HINDI",
     "expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"http://mohitweb.zapto.org:7878/live/high/815.m3u8",
     "evidence":"github.com/Bhavesh0a/Index Index6; Jio ID 815 explicitly Sonic Hindi",
     "expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"http://jo123.biz/jweb/m3u8.php?c=sonic_Hindi&q=1200&e=.m3u8",
     "evidence":"github.com/mahmud31132/bdix-tv mahmud.m3u; explicitly Sonic Hindi; host public reachability unknown",
     "expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"http://pkr.cinepex.tv:8278/sonichindikdin/playlist.m3u8",
     "evidence":"github.com/TamannaJain2710/iptv Customised_iptv.m3u; Sonic Hindi label",
     "expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"http://jo123.biz/jweb/m3u8.php?c=Sonic_Bangla&q=400&e=.m3u8",
     "evidence":"github.com/mahmud31132/bdix-tv Expire.m3u; explicitly Sonic Bangla; host public reachability unknown",
     "expected_audio":"bn"},
    # 2026-10-26 newly sourced from public GitHub M3U labels; probe-only.
    # These hosts are not assumed non-BDIX or authorized, and channel identity,
    # audio language and HD must all be independently confirmed before use.
    {"channel":"Disney HD Hindi","url":"https://allinonereborn.tech/doordarshan.m3u8?id=634",
     "evidence":"github.com/Junan02/bdiptvtest all unfiltered.m3u; explicitly DISNEY HINDI HD, identity/720p unconfirmed",
     "expected_audio":"hi","min_height":720},
    {"channel":"Sonic Hindi","url":"https://admin.himel-op.top/Join-Telegram-@HimelOP_Official/tiptop-op.m3u8?id=1134",
     "evidence":"github.com/StarFlixofficial/Personal-File Himel op 2; explicitly Sonic Hindi",
     "expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://fifabangladesh.live/@RANAPKX73/stream.m3u8?id=1345&e=.m3u8",
     "evidence":"github.com/joyesh24/ip.m3u ip.m3u; explicitly Sonic Bangla ID 1345",
     "expected_audio":"bn"},
    # 2026-10-25 fresh public source-backed, read-only HLS/audio probes.
    {"channel":"Disney HD Hindi","url":"https://fifabd.xyz/KIDxRANAPK/play.m3u8?id=167551","evidence":"github.com/BahyOsama/marioo dd.m3u; Disney India 167551 source, not verified Hindi/HD","expected_audio":"hi","min_height":720},
    {"channel":"Disney HD Hindi","url":"https://fifabd.xyz/KID/play.m3u8?id=167551","evidence":"github.com/Mpdishtv/MPDISHTV README.md; Disney Hindi 167551, HD unverified","expected_audio":"hi","min_height":720},
    {"channel":"Sonic Hindi","url":"https://serverbackupchannel.xyz/jiotvchannel/autoq.php?c=sonic_Hindi&e=.m3u8","evidence":"github.com/GhostHostBD/tvlink JIO serverbackupchannel; explicitly Sonic Hindi","expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"https://mini1.allinonereborn.xyz/jiotv-ww192/app/ts_live_815.m3u8","evidence":"github.com/sohelkhan812421/boss SOHELKHAN2025IPTV.m3u; explicitly Sonic Hindi ID 815","expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://serverbackupchannel.xyz/jiotvchannel/autoq.php?c=Sonic_Bangla&e=.m3u8","evidence":"github.com/GhostHostBD/tvlink JIO serverbackupchannel; explicitly Sonic Bangla","expected_audio":"bn"},
    {"channel":"Disney HD Hindi","url":"http://zeestb1.online/dhoom.php?id=11385","evidence":"github.com/swapnilpachare2/tv dhoom.m3u; labeled IN: DISNEY CHANNEL HINDI HD, unverified","expected_audio":"hi","min_height":720},
    {"channel":"Disney HD Hindi","url":"https://sambhavilove1769.000webhostapp.com/Denver/Dhoom.php?id=11385","evidence":"github.com/infinitytechcmp/msx tataplay.m3u; labeled IN: DISNEY CHANNEL HINDI HD, unverified","expected_audio":"hi","min_height":720},
    {"channel":"Sonic Hindi","url":"https://madplay.live/jiotv/app/live/815/null/index.m3u8","evidence":"github.com/hasanmamunctg/hasanmamunctg manik; Jio ID 815 explicitly Sonic Hindi","expected_audio":"hi"},
    {"channel":"Sonic Hindi","url":"https://madplay.live/player/jiotv.php?id=sonic_Hindi_MOB/Fallback/index.m3u8","evidence":"github.com/tvs6/livetv; explicitly Sonic Hindi channel ID","expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://serverbackupchannel.xyz/jiotvchannel/app/live/1345/Sonic_Bangla/index.m3u8","evidence":"github.com/Hasibfy37/Iptv Final.m3u; explicitly Sonic Bangla","expected_audio":"bn"},
    {"channel":"Sonic Bangla","url":"https://jiotv.nayeemparvez.workers.dev/bpk-tv/Sonic_Bangla_MOB/Fallback/index.m3u8","evidence":"github.com/freedish2024/personal-project.sr Kids; explicitly Sonic Bangla MOB","expected_audio":"bn"},
    {"channel":"Sonic Bangla","url":"http://103.135.208.14/live/ibox/bd/58.m3u8","evidence":"github.com/fahadskt/IPTV-Playlists Old/IBOX TV; explicitly Sonic Bangla; may be BDIX-only","expected_audio":"bn"},
    {"channel":"Sonic Bangla","url":"https://madplay.live/jiotv/app/live/1345/null/index.m3u8","evidence":"github.com/hasanmamunctg/hasanmamunctg manik; Jio ID 1345 explicitly Sonic Bangla","expected_audio":"bn"},
    {"channel":"Sonic Bangla","url":"https://tv.googledrivelinks.com/live.php?c=Sonic_Bangla&q=1200&e=junk.m3u8","evidence":"github.com/Nafis495/iptv WOW; Jio ID 1345 Bengali","expected_audio":"bn"},
    {
        "channel": "Disney HD Hindi",
        "url": "http://stream-7b694ce7e.nmbs.top/m3u/Kids/c86abe8bd6.m3u8",
        "evidence": "github.com/technl/Hanssettings - Disney Channel Hindi label (NOT HD evidence)",
        "expected_audio": "hi",
        "min_height": 720,
    },
    {
        "channel": "Sonic Hindi",
        "url": "http://4ce5e2d62ee2c10e43c709f9b87c44d5.streamhost.cc/m3u8/Kids/4415aa98f2f6f59.m3u8",
        "evidence": "github.com/imranemon1/emon - SONIC NICKELODEON SONIC HINDI label",
        "expected_audio": "hi",
    },
    {
        "channel": "Sonic Bangla",
        "url": "https://ott.bingebd.com/live/ngrp:ZXOrtTn-asdt-s78TYU34GTX-03as-f7as-1ffd2-t1682a-sgh32x-zp3e-dsf-3b7aa-ort_621h_sWT564hQW_AQTY1025_sonicPQRT_9653SDE_s9023FGWQ_uiou_f36erxty_fort63_DH/playlist.m3u8",
        "evidence": "github.com/skmasum98/IPTV - Sonic Bangla label",
        "expected_audio": "bn",
    },
    {
        "channel": "Sonic Bangla",
        "url": "http://14.102.123.50:5001/live/1345.m3u",
        "evidence": "github.com/RhqAB/TV - Sonic Bangla label and channel id 1345",
        "expected_audio": "bn",
    },

    # 2026-10-25: Independently listed on public GitHub M3U files, all
    # read-only probes. Not user-confirmed; no changes to the main playlist.
    {"channel":"Disney HD Hindi",
     "url":"https://live.dinesh29.com.np/stream/jiotvplus/disneychannel/master.m3u8",
     "evidence":"github.com/channeliptv0/IPTV Master/jiotvplus.m3u.m3u8; explicitly Disney Channel (not Disney Junior), but Hindi/HD unknown",
     "expected_audio":"hi","min_height":720},
    {"channel":"Disney HD Hindi",
     "url":"https://web.cwabdtv.eu.org/live/disnepchannel/index.m3u8",
     "evidence":"github.com/tvbd/m3uplayer tplay/main.js; Disney server alternative, identity/language/HD unconfirmed",
     "expected_audio":"hi","min_height":720},
    {"channel":"Sonic Hindi",
     "url":"https://live.dinesh29.com.np/stream/jiotvplus/sonichindi/master.m3u8",
     "evidence":"github.com/hardiksaini10/rdp nash.m3u; explicitly Sonic Hindi",
     "expected_audio":"hi"},
    {"channel":"Sonic Hindi",
     "url":"https://snehapi.in1.bitmana.io/jioapi/snehjioxx.php?c=sonic_Hindi&q=800&e=junk.m3u8",
     "evidence":"github.com/arshdeep1112/Indian-IPTV channels/iptv_kids.m3u8; Sonic Hindi Jio 815",
     "expected_audio":"hi"},
    {"channel":"Sonic Hindi",
     "url":"https://jio.drmlive.au/jio/bpk-tv/sonic_Hindi_MOB/Fallback/index.m3u8",
     "evidence":"github.com/MAUSHAMRAJ/Jiotv jio.m3u; Sonic Hindi ID 815, different endpoint from viewer pin",
     "expected_audio":"hi"},
    {"channel":"Sonic Bangla",
     "url":"https://live.dinesh29.com.np/stream/jiotvplus/sonicbangla/master.m3u8",
     "evidence":"github.com/channeliptv0/IPTV Master/jiotvplus.m3u.m3u8; explicitly Sonic Bangla",
     "expected_audio":"bn"},
    {"channel":"Sonic Bangla",
     "url":"https://snehapi.in1.bitmana.io/jioapi/snehjioxx.php?c=Sonic_Bangla&q=800&e=junk.m3u8",
     "evidence":"github.com/arshdeep1112/Indian-IPTV channels/iptv_kids.m3u8; Sonic Bangla Jio 1345",
     "expected_audio":"bn"},
    {"channel":"Sonic Bangla",
     "url":"http://198.195.239.50:8095/sonic/index.m3u8",
     "evidence":"github.com/stablesports711-hue/stable-sports-iptv STABLE-SPORTS TV.m3u; explicitly Sonic Bangla, outside BD IP; header possibly needed",
     "expected_audio":"bn"},
    # 2026-10-25: additional public-source candidates, probe-only; preserve user pins.
    {"channel":"Disney HD Hindi","url":"http://port.denver1769.in/ulpl2.php?tv=4538","evidence":"github.com/mahenkpatel/m3u mahendra.m3u; Disney Channel HD label, India/Hindi unconfirmed","expected_audio":"hi","min_height":720},
    {"channel":"Sonic Hindi","url":"https://tamilultra.tv/api/jiotv.m3u8?id=815","evidence":"github.com/khankimagi23221/okk-1 kids.m3u; Sonic Hindi ID 815, published referer","expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://tamilultra.tv/api/jiotv.m3u8?id=1345","evidence":"github.com/khankimagi23221/okk-1 kids.m3u; Sonic Bangla ID 1345, published referer","expected_audio":"bn"},
    {"channel":"Sonic Hindi","url":"https://tv.001133.xyz/live/815.m3u8","evidence":"github.com/mahenkpatel/m3u raigarh.m3u; Sonic Hindi ID 815","expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://playyonogames.in/live.php?id=1345&extension=.m3u8","evidence":"github.com/Shaharum1010/Cartoon-channel-/Shaharum; Sonic Bangla ID 1345, published referer","expected_audio":"bn"},
    # 2026-10-28 newly discovered public playlist links, independent HLS segment and audio-metadata tests only.
    {"channel":"Sonic Hindi","url":"https://keralamaxtv.com/vt/stream.m3u8?id=Sonic_Nickelodeon","evidence":"github.com/freedish2024/personal-project.sr Allinkids.Com, labeled Sonic; Hindi not independently confirmed","expected_audio":"hi"},
    {"channel":"Sonic Bangla","url":"https://mhdtv.co.in/jio/app/live/1345/Sonic_Bangla/index.m3u8","evidence":"github.com/Hasibfy37/Iptv Final.m3u, explicitly Sonic Bangla 1345","expected_audio":"bn"},
]

def is_media_fragment(data):
    if direct_media_ok(data):
        return True
    # CMAF fMP4 chunks usually start with styp or moof boxes.
    if len(data) > 512 and any(data[4:8] == x for x in (b"moof", b"styp", b"ftyp", b"mdat")):
        return True
    return False

def test(entry):
    result = {**entry, "manifest_ok": False, "media_segment_verified": False,
              "advertised_max_height": 0, "advertised_audio_languages": [],
              "channel_identity_verified": False, "hindi_or_bangla_audio_verified": False,
              "link3_verified": False, "publish_eligible": False,
              "note": "GitHub runner-only test. Playlist is unchanged."}
    current = entry["url"]
    if not allowed(current):
        result["error"] = "URL excluded by existing source-safety filter"
        return result
    try:
        languages = set()
        for _ in range(4):
            body, _ = fetch_hls_bytes(current, 24000, 9)
            text = body.decode("utf-8-sig", "replace")
            if "#EXTM3U" not in text[:500]:
                result["error"] = "No HLS manifest"
                return result
            if "METHOD=SAMPLE-AES" in text or "KEYFORMAT=" in text:
                result["error"] = "Protected/DRM stream is not supported"
                return result
            result["manifest_ok"] = True
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            for line in lines:
                if line.startswith("#EXT-X-MEDIA:") and "TYPE=AUDIO" in line:
                    m = re.search(r'LANGUAGE="([^"]+)"', line, re.I)
                    if m:
                        languages.add(m.group(1).lower())
            result["advertised_audio_languages"] = sorted(languages)
            if "#EXT-X-STREAM-INF" in text:
                variants = []
                for i, line in enumerate(lines[:-1]):
                    if line.startswith("#EXT-X-STREAM-INF") and not lines[i+1].startswith("#"):
                        m = re.search(r'RESOLUTION=\d+x(\d+)', line, re.I)
                        height = int(m.group(1)) if m else 0
                        variants.append((height, urllib.parse.urljoin(current, lines[i+1])))
                if not variants:
                    result["error"] = "Master has no valid variant"
                    return result
                height, current = max(variants, key=lambda x: x[0])
                result["advertised_max_height"] = max(result["advertised_max_height"], height)
                continue
            if "#EXTINF" not in text:
                result["error"] = "No media-segment entries"
                return result
            fragments = [urllib.parse.urljoin(current, x) for x in lines if not x.startswith("#")]
            for uri in reversed(fragments[-3:]):
                try:
                    fragment, ctype = fetch_hls_bytes(uri, 8192, 9)
                    if "text/html" in ctype or "application/json" in ctype:
                        continue
                    if is_media_fragment(fragment):
                        result["media_segment_verified"] = True
                        break
                except Exception:
                    pass
            result["hindi_or_bangla_audio_verified"] = entry["expected_audio"] in languages
            # Inspect codec and embedded language tags only after an actual HLS
            # fragment was fetched. Tags are evidence, NOT proof of spoken audio
            # or channel identity. Never publish automatically from ffprobe.
            if result["media_segment_verified"]:
                try:
                    command = ["ffprobe", "-v", "error", "-rw_timeout", "5000000",
                               "-probesize", "300000", "-analyzeduration", "1200000",
                               "-show_entries", "stream=codec_type,codec_name,width,height:stream_tags=language,title",
                               "-of", "json", entry["url"]]
                    proc = subprocess.run(command, capture_output=True, text=True, timeout=18, check=False)
                    if proc.returncode == 0 and proc.stdout.strip():
                        details = json.loads(proc.stdout)
                        result["ffprobe_streams"] = details.get("streams", [])[:8]
                    else:
                        result["ffprobe_error"] = (proc.stderr or "ffprobe returned no stream data")[:200]
                except Exception as exc:
                    result["ffprobe_error"] = type(exc).__name__ + ": " + str(exc)[:160]
            if entry.get("min_height") and result["advertised_max_height"] < entry["min_height"]:
                result["note"] += " Disney HD requirement not verified."
            if not result["media_segment_verified"]:
                result["note"] += " No valid MPEG-TS/fMP4 fragment fetched."
            # Channel identity requires independently inspected video/audio or
            # an authenticated provider mapping, not merely a public M3U label.
            return result
        result["error"] = "Nested HLS manifest depth exceeded"
    except Exception as exc:
        result["error"] = type(exc).__name__ + ": " + str(exc)[:140]
    return result

def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(test, CANDIDATES))
    report = {
        "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "GitHub Actions network, NOT Link3. No channel identities confirmed.",
        "candidate_count": len(results),
        "verified_media_candidates": sum(bool(x["media_segment_verified"]) for x in results),
        "publication_authorized": False,
        "candidates": results,
    }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Three-channel candidate diagnostics complete:", report["verified_media_candidates"],
          "media candidates of", len(results), "(not published)")

if __name__ == "__main__":
    main()
