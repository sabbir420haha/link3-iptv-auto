# Sonic Hindi — deep research and failure ledger (2026-11-02)

## User's goal and constraints
- Channel: **Nickelodeon Sonic India, Hindi audio** (JioTV channel ID 815; Tata Play ID 127 may refer to same TV channel).
- Player: IPTV Pro and VLC. Network: Link3 broadband, Bangladesh.
- **Known positive control:** user confirms `http://103.135.253.32:8080/HUNGAMA/index.m3u8` runs smoothly in VLC.
- **User feedback:** Sonic TEST 1–139 (as tried in preceding batches) has not produced a usable Hindi stream. Most recently 138 and 139 both failed. Do not re-add these URL variants without materially new verification.

## Evidence of why large public lists are misleading
1. **Repeated upstream links:** Most GitHub listings use the same JioTV / JioCinema Sonic 815 feed, copied across many repository files with different relay endpoints. Unique GitHub files are not unique streams.
2. **JioTV India-only terms:** https://www.jio.com/jcms/en-in/zee5-sonyliv-terms-and-conditions/ explicitly limits viewing to India's geographic boundaries. Ordinary Jio relay URLs are not reliable for a Bangladesh Link3 connection, and DRM-protected MPD cannot be treated as normal VLC/IPTV Pro HLS.
3. **Public IPTV channel listing:** https://publiciptv.com/channels/sonicin lists two unverified SD endpoints, notably `http://103.185.24.134:3001/SONIC/index.m3u8` and `http://103.151.60.162:2122/play/a02v/index.m3u8?hls`. Both appear in prior candidate history; do not label as working.
4. **Independent public stream health history:** `saeidrahmanbd/BDIX-IPTV/reports/stream-health-history.json` recorded (as of 2026-11-01T01:12:25Z) **18/18 successful checks for user's Hungama control** and **0/9 successful checks for the common `103.185.24.134:3001/SONIC` endpoint**. These checks were not performed on Link3, and can change.
5. **Verified free IPTV curations:** `gnaidu05/Iptv/playlists/india-active.m3u`, `playlists/india-active-http.m3u`, and `AdeelWajid/iptv_validated_list/playlists/countries/in.m3u` had **no Sonic entries at research time**, despite many Indian channels. Other lists marked `working` included previously failed `https://playyonogames.in/jio/app/ts_live_815.m3u8`.
6. **IPTV Cat 2026-11-01 listing:** https://iptvcat.org/india/s/hindi displayed a green Nickelodeon Sonic Hindi (1080p) item, but this was merely a third-party health indicator; no publicly retrievable unique, authenticated, playable URL was independently obtained. Do not claim success from a green checkmark.
7. **Geo/protected feed:** `Zaman-Topu/Ip-tv-Collection/FINAL_IPTV_GEO.m3u` lists Tata Play Sonic via `botallen.live` using a signed URL in its **GEO** playlist. Do not transplant signed/expiring or geo-restricted credentials into the public test list.

## Last new URLs user tested and rejected
- Sonic TEST 138: `http://144.217.70.181:9587/hin2/SONIC/index.m3u8` (distinct manifest path on a previously unsuccessful server family) — **user says does not play**.
- Sonic TEST 139: `http://66.102.126.10:8000/play/a00p/index.m3u8` (source label Sonic / Tata Play, Hindi uncertain) — **user says does not play**.
- Sonic TEST 134–137 also user-confirmed failed and removed in previous revision. Sonic TEST 111–133, and earlier test batches, similarly failed.

## Validation before future publishing
A candidate should be **sourced, not guessed** and not already in `sonic_hindi_test_index.json`, `sonic_hindi_candidates.json`, past GitHub commits, or this ledger. Keep the user's MAIN `playlist.m3u` and Hungama TEST streams untouched.

A genuinely useful verification needs: 
1. Remote host reachable; not BDIX-only/private LAN or expired signed session.
2. Manifest or TS response verified; for HLS `#EXTM3U` with at least one video segment fetch (not simply HTTP 200 or a channel name).
3. Channel identity **Nickelodeon Sonic (India)** and **Hindi audio** independently confirmed.
4. User confirmation specifically on Link3/IPTV Pro (or VLC). A stream passing GitHub runner tests is not equivalent to Link3 playback.

If 1–3 cannot be verified, label sources UNVERIFIED and refrain from telling the user they work. Never insert expired tokens, account credentials, or DRM circumvention material. No working new Sonic Hindi stream was confirmed in this session.
