# Sonic Hindi — verified-source search results (2026-10-26)

## Recovered October 23 user-confirmed source (from actual repo commits)

- The user confirmed **Sonic Hindi TEST 01 working on Link3** on October 23, 2026.
- The historical commit `c00303508de57a427dc1f18247ba94e8eb1b42bd` pins its source in `channels.json` and the commit `d66f9a059552d111526e533b7b7c8a78898dae57` publishes it in `playlist.m3u`: `https://jio.drmlive.net/jio/bpk-tv/sonic_Hindi_MOB/Fallback/index.m3u8`.
- As of October 26 the user reports Sonic Hindi no longer plays. This is a *historically confirmed* feed, NOT currently working.
- A separate old host `http://103.17.193.159:5001/live/815.m3u8` was referenced in a prior answer but was NOT the verified TEST 01 source based on GitHub commits; do not mislabel it as user-confirmed.

## Tata Play-specific research (October 26)

- Sonic Nickelodeon is listed as Tata Play `ts127` in multiple third-party M3U playlists. Three distinct source URLs are now TEST 086–088 in `three_channel_test.m3u`.
- TEST 086: `https://tplay.dinesh29.com.np/live/tataplay-universal/sonic-nickelodeon/index.ts`: GitHub Actions DNS failure.
- TEST 087: `http://103.84.57.155:8000/play/a03y/29711434.m3u8`: GitHub Actions remote timeout (not an HTTP 404; playback on Link3 still unverified).
- TEST 088: `https://playflix.icu/Extra%20Tata%20playlist.m3u/stream.m3u8?id=ts127&e=.m3u8`: GitHub Actions DNS failure.
- Other Tata Play `ts127` `.mpd` listings are DASH/DRM streams, not directly playable as ordinary HLS M3U8 in IPTV Pro. Do not call them working HLS URLs.
- Original user-confirmed working Hungama and other Main channels remain untouched.

---

## What we KNOW

- Viewer checked Sonic Hindi TEST 001–085 in IPTV Pro over Link3 Wi-Fi. **All 85 failed** (viewer report).
- Automated GitHub Action last ran 2026-10-26T14:39:08.382715+00:00; **148 Sonic-Hindi-labelled sources checked; 0 HLS manifest success, 0 verified sample-media success**. This tests from GitHub's network, not Link3.
- `https://garden-tv.mobi/en/channel/Sonic.in` (checked 2026-10-26) currently says 'No working source right now'. It publishes aggregated public IPTV streams, not an official subscription.
- `https://iptv-org.github.io/channels/in/Sonic` lists the channel but listing is not independent proof of playable HLS.
- `https://origin-prod.jiotv.com/live-channel/sonic-hindi/815` is the officially published Sonic Hindi channel page. Streaming needs provider eligibility/authentication and is not a reusable direct M3U8 link.
- `https://nowiretv.com/live-tv/sonic-hindi` advertises a web/app player, but no tested direct link for IPTV Pro was established and service availability on Link3 cannot be confirmed.
- Refreshed public Bangladesh 2026 repositories `abusaeeidx/Mrgify-BDIX-IPTV` and `time2shine/Rokon-IPTV` did not reveal an independent working Sonic Hindi feed. Rokon lists a different Sonic The Hedgehog cartoon channel, not the requested broadcast.

## Do NOT promote a false candidate

- No direct URL has been verified playing both Sonic Hindi content and sound on Link3.
- No additional 403/404, token-expired, DRM-only, guessed endpoint, named-but-not-video-verified URL is appropriate for Main.
- Preserve Main Playlist's confirmed working Hungama URL and the TEST 29 baseline unchanged.
- TEST 001–085 left as-is, since user did not request their deletion; mark all as failed in `sonic_hindi_test_index.json` to prevent repeats.

## Next reliable discovery criterion

Source/ISP operator must supply a currently accessible stream URL. First validate HLS video segments, verify on-screen channel identity and Hindi audio, then viewer must confirm Link3 / IPTV Pro playback. Only then promote a stream to Main.

## Follow-up source trace — 26 October 2026 (second search)

- Viewer confirms TEST087 `http://103.84.57.155:8000/play/a03y/29711434.m3u8` **does not work on Link3**. Keep Main unchanged.
- Alternative path `http://103.84.57.155:8000/play/a03y/index.m3u8` explicitly published in `KMABIDHASAN63/XYZ Website.m3u`; GitHub Runner **timeout**. Not a confirmed playable feed.
- `http://103.17.193.159:5001/live/815.m3u8` inferred from other channels of `maybetv/Jo`, NOT published in that source as Sonic Hindi; GitHub runner returned **HTTP 500**.
- `http://103.154.3.101:5001/live/815.m3u8` explicitly in [iptv-org issue 36782](https://github.com/iptv-org/iptv/issues/36782); GitHub runner **timeout**.
- `http://103.122.249.134:8000/play/a051` explicitly in [iptv-org issue 37823](https://github.com/iptv-org/iptv/issues/37823); checked as an extensionless stream path, GitHub runner **timeout**.
- Latest `kids_probe_health.json` verified **155 Sonic-Hindi-labelled candidates checked, zero successful sample media** (GitHub runner; some ISP-geofenced feeds may behave differently on Link3).
- These four newly traced URLs were queued ONLY for backend examination, **not added to Test 3 or Main playlist**. Do not send user another mass list without positive checks; user has reported 1–85 and TEST 087 failing.
- Historical Jio `jio.drmlive.net` feed is the actual user-confirmed October 23 link; not currently validated.

## Additional source review — 26 October 2026, evening

- Searched further public GitHub M3U/IPTV sources and web indexes including `saeidrahmanbd/BDIX-IPTV`, `ttmttm/iptv_2026`, `Mrdk475/mrdknew`, `MAUSHAMRAJ/Jiotv`, several Gists and the original Sonic source-family references.
- The recently indexed `saeidrahmanbd/BDIX-IPTV/IPTV-Playlist.m3u` points Sonic to `http://103.185.24.134:3001/SONIC/index.m3u8`, a prior failed candidate; the new-indexed 2026 playlists repeat known hosts.
- Search also located `http://hardcore-keldysh.64-227-150-121.plesk.page:80/getm3u8/815/master.m3u8`, but it is **existing TEST035** and its last GitHub probe was HTTP 404.
- Novel URLs in some GitHub snippets were examples (`example.com`), credential-bearing private IPTV endpoints, or URLs with expired `wmsAuthSign` tokens; none can be represented as independently playable, durable Sonic Hindi HLS.
- GitHub Actions latest stored result at 2026-10-26T15:36:51.952621+00:00: `155` Sonic-Hindi-labelled URLs checked and `0` downloaded verified media sample bytes. This does not establish Link3 playback for private/geo-locked sources.
- **No new stream passed the minimum verification standard, so no new Test entry was published.** Main Playlist (75 channels), Hungama and 88 historic Sonic test entries untouched.
