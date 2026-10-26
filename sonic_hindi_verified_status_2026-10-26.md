# Sonic Hindi — verified-source search results (2026-10-26)

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
