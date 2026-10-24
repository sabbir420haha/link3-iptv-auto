# Cartoon Episodes — Official On-Demand Watch Guide

This is **not** an IPTV Pro VOD M3U: the providers below supply playback through YouTube / ZEE5 / JioHotstar / Tata Play Binge and typically do **not** provide permanent, independently licensed direct MP4/M3U8 episode links. A `watch?v=` URL is a website link, **not an HLS stream**.

The companion **Cartoon LIVE TEST** playlist is [cartoon_live.m3u](./cartoon_live.m3u). Its channels may show different cartoons according to the broadcaster's schedule. No TV live stream is asserted to be 24/7 dedicated to a requested series unless it is specifically labelled as the Mr Bean FAST channel. Location, language and Link3 playback are not verified.

## Gopal Bhar (Bengali)
* [Gopal Bhar — Episode 16 (official Sony AATH / YouTube)](https://www.youtube.com/watch?v=jwV5GoJBs6M)
* [Gopal Bhar — Episode 1027 (official Sony AATH / YouTube)](https://www.youtube.com/watch?v=yEQXmIfzxXY)
* Live-TV fallback in M3U: Sony AATH, **only when scheduled**.

## Tom and Jerry
* [Tom and Jerry Singapore — official WB Kids episodes 1–4 (YouTube)](https://www.youtube.com/watch?v=vcRorKK_uBM)
* [WB Kids official Tom and Jerry Tales 24/7 **YouTube** broadcast page](https://www.youtube.com/watch?v=COVffL_E9wI) — YouTube live status may change; this is **not a direct HLS source**.
* Live-TV fallback in M3U: Cartoon Network, **only when scheduled**.

## Bantul the Great (Bengali)
* [Bantul the Great — Bengali episodes (official ZEE5)](https://www.zee5.com/tv-shows/details/bantul-the-great/0-6-231) — app/region/subscription may apply.
* [Bantul the Great — official Zee Bangla YouTube webisode 279](https://www.youtube.com/watch?v=hwj1He5Xxkg)
* Live-TV fallback in M3U: Zee Bangla, **only when scheduled**.
* Do not substitute the ZEE5 **Odia** series (/0-6-2858) for the intended Bengali audio.

## Mr Bean Animated
* [Mr Bean Animated Season 1 — official Mr Bean full-episode compilation](https://www.youtube.com/watch?v=ze3cICcTM_E)
* [Scientist Bean — official Mr Bean animated episode](https://www.youtube.com/watch?v=6qD6-zSsmy8)
* Three regional 24/7 English-labelled Banijay Mr Bean Animated FAST feeds are in the live M3U (availability can be region-limited).

## Ninja Hattori (Hindi selectable)
* [Ninja Hattori — New, Hindi is an available audio option (Tata Play Binge / JioHotstar)](https://www.tataplaybinge.com/watch/shows/ninja-hattori-new/32168) — select **Hindi** in the provider's audio selector; may require eligible account/region.
* [Ninja Hattori — Classic (Tata Play Binge)](https://www.tataplaybinge.com/watch/series/ninja-hattori-classic-season-2/51913) — explicitly offers Hindi among audio tracks.
* Sonic Hindi live in the M3U is **not** a guaranteed Ninja Hattori-only channel.

## Shinchan — **HINDI AUDIO ONLY**
* [Shin-chan — official Tata Play Binge / JioHotstar show page (Hindi listed)](https://www.tataplaybinge.com/watch/shows/shin-chan/3483). **Choose Hindi audio**; do not choose Tamil/Telugu versions.
* [Shin-chan — Sony YAY **Hindi** JioTV episode example (Hindi confirmed on page)](https://www.jiotv.com/live-channel/sony-yay-hindi/872/sony-yay-hindi/episode-31/260803872087). Login and region restrictions may apply; archived programme pages may not replay.
* Only Hindi-labelled Sony YAY and Hungama linear feeds are included in the live TEST M3U, **and they are not guaranteed to show Shinchan now**. Their actual audio was **not** separately checked. Japanese/Tamil/Telugu stream variants were **not** included.

---

## Why there is no six-show `cartoon_vod.m3u` yet

A playable VOD playlist must refer to permitted, **actual media URLs** (direct MP4/HLS), not watch pages. No stable licensed direct episode media URLs were verified for these six shows. It would be misleading to turn the watch pages into `#EXTINF` entries. The links above work as **official viewing-page shortcuts in a browser or supported app**, not as IPTV Pro videos. These URLs and availability may change.

## Existing user playlists

* Main playlist and `favorites_best.m3u` untouched.
* Cartoon live stream list: [cartoon_live.m3u](./cartoon_live.m3u).
* For future direct VOD: provide media files you own or authorized direct downloadable URLs; a VOD M3U can then be built without copying platform-only video streams.

Compiled: 2026-10-25.
