# Sonic Hindi/Bangla — main-playlist source/CDN audit

Audit date: 2026-10-26 (Bangladesh); automated checks from GitHub Actions **outside Link3**, and viewer reports from IPTV Pro/Link3.

## Conclusions

- Examined **75** main playlist channel URLs across **35 unique hostnames**.
- HLS probe checked **127** total source URLs (including the functioning Hungama baseline and a known wrong-channel control).
- Exact-host CDN/provider cases checked in this labelled subset: **35**. No source was validated as the requested Sonic Hindi/Bangla channel with HLS media.
- One HLS endpoint returned media bytes but was incorrectly labelled Sonic in earlier source registry: **`http://103.151.60.162:2122/play/a00w/index.m3u8?hls` is Star Jalsha**, confirmed by iptv-org channel mapping. It has been corrected to `other-channel`, a negative control, never a Sonic candidate.
- The explicitly labelled Sonic **`http://103.151.60.162:2122/play/a02v/index.m3u8?hls`** returned HTTP 404 from GitHub, despite the same server hosting other Main channels.
- **No independently validated working Sonic Hindi or Sonic Bangla direct HLS URL found.** A manifest/segment alone cannot confirm channel identity/audio, and GitHub checks do not guarantee Link3 playback.
- The 21 previous Sonic TEST channels and all Disney Hindi tests have been removed from `three_channel_test.m3u` after viewer failure. Hungama TEST 29 is kept.

## Main-playlist hostname inventory

| Host/CDN | Main channels | Examples |
|---|---:|---|
| `tvsen6.aynaott.com` | 15 | Zee Bangla HD, ATN News, Channel i, DBC News, Jamuna TV |
| `drk6xq0vhn.gpcdn.net` | 11 | Zee Bangla, Somoy TV, Sony Ten 1 HD, Independent TV, Ekhon TV |
| `app.ncare.live` | 6 | Gazi TV, NAN TV, Channel S, Iqra Bangla, NRB TV |
| `tvsen5.aynaott.com` | 5 | ATN Bangla, BanglaVision, Maasranga TV, Ekushey TV, RTV |
| `103.135.253.32` | 5 | Duronto TV, Hungama, Nat Geo HD Bangla, Nick Bangla, Sony Ten 3 HD |
| `stream.ottplus.live` | 2 | Sony MAX HD, Sony Aath |
| `da86m1sqpm3o0.cloudfront.net` | 2 | Star Jalsha, Ruposhi Bangla |
| `d3qs3d2rkhfqrt.cloudfront.net` | 2 | DD Bangla, DD Sports |
| `live20.bozztv.com` | 1 | Cartoon Network |
| `iptvlive.ahmed-bd-org.workers.dev` | 1 | Channel 24 |
| `app-re.sm-monirul-islam-rs.workers.dev` | 1 | Discovery Bangla |
| `ranapkz.site` | 1 | Disney HD Hindi |
| `2-fss-1.streamhoster.com` | 1 | NTV |
| `btv.hridoytv-channel.workers.dev` | 1 | BTV News |
| `103.190.133.68` | 1 | News 21 Bangla TV |
| `boishakhi.sonarbanglatv.com` | 1 | Boishakhi TV |
| `byphdgllyk.gpcdn.net` | 1 | Deepto TV |
| `j6nfugukcl.gpcdn.net` | 1 | SA TV |
| `deshitv.deshitv24.net` | 1 | Deshi TV |
| `live1.entertv.com.bd` | 1 | Enter TV |
| `dbcanada.sonarbanglatv.com` | 1 | Deshe Bideshe TV |
| `27.124.71.27` | 1 | Sun Bangla |
| `banglajagotv.livebox.co.in` | 1 | Bangla Jago TV |
| `dyjmyiv3bp2ez.cloudfront.net` | 1 | TV9 Bangla |
| `cdn-uw2-prod.tsv2.amagi.tv` | 1 | Zee 24 Ghanta |
| `vglivessai.akamaized.net` | 1 | R Plus Gold |
| `amg01448-samsungin-enterr10bangla-samsungin-ad-gg.amagi.tv` | 1 | Enterr10 Bangla |
| `live-stream.amarbanglatv.in` | 1 | Sananda TV |
| `live-stream.utkalbongo.com` | 1 | Bangla Plus |
| `bein-esp-xumo.amagi.tv` | 1 | beIN Sports XTRA |
| `d4ddgdmj1cvnm.cloudfront.net` | 1 | Sports First TV |
| `rbmn-live.akamaized.net` | 1 | Red Bull TV |
| `103.151.60.162` | 1 | Star Sports 2 |
| `d1nj4u39ja4cn0.cloudfront.net` | 1 | Cricket Gold |
| `d3d85c7qkywguj.cloudfront.net` | 1 | FITE 24/7 |

## Closest same-provider findings

| Public source / CDN | Source identity | Test result |
|---|---|---|
| `103.135.253.32:8080` | Main Hungama, Nick Bangla, NatGeo Bangla, Duronto, Ten 3 | Sonic, SONIC-BANGLA, Nick-Sonic name variants: 404 |
| `drk6xq0vhn.gpcdn.net` | Main Sony Ten 1, Pogo, Sony Yay, Discovery Kids | Sonic Hindi/Bangla `_abr` variants: 404 |
| `stream.ottplus.live` | Main Sony Aath, Sony MAX HD | Sonic variants: 404 |
| `tvsen6.aynaott.com` / `tvsen7.aynaott.com` | Ayna TV channels in Main | Sonic variants: 404 |
| `app-re.sm-monirul-islam-rs.workers.dev` | Main Discovery Bangla | Sonic Hindi/Bangla variants: 404 |
| `103.151.60.162:2122` | Main Star Sports 2 | Sonic `a02v`: 404. `a00w` is actually Star Jalsha |
| SM-IPTV `vood.m3u` | Named Sonic URL | `shoebinfo.qzz.io/test/hot.php/Sonic.m3u8`: 404 |
| SM-IPTV `SM_bdix.m3u` | `/SONIC/index.m3u8` with timed token in list | Untokened endpoint unavailable; no reusable public URL recovered |

## Source lists cross-checked

- `https://github.com/iptv-org/iptv/blob/master/streams/in.m3u`: Sonic `a02v`, Star Jalsha `a00w`.
- `https://github.com/sm-monirulislam/SM-IPTV/blob/main/Combined_Live_TV.m3u`: labelled Sonic Bangla, same publisher family as Main Discovery Bangla.
- `https://github.com/sm-monirulislam/SM-IPTV/blob/main/vood.m3u`: labelled Sonic stream.
- `https://github.com/sm-monirulislam/SM-IPTV/blob/main/SM_bdix.m3u`: tokenized Sonic stream, not reusable.
- `kids_candidate_sources.json`: provenance and distinction between published and guessed candidates.
- `kids_probe_health.json`: HLS manifest/media probe results, NOT Link3 playback confirmation.

## All current main playlist channel source URLs

| # | Channel | Host | URL |
|---:|---|---|---|
| 1 | Zee Bangla HD | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/ZeeBangla/index.m3u8` |
| 2 | Zee Bangla | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/zee_bangla_720/index.m3u8` |
| 3 | ATN Bangla | `tvsen5.aynaott.com` | `https://tvsen5.aynaott.com/atnbangla/index.m3u8` |
| 4 | ATN News | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/da6WMXAk/index.m3u8` |
| 5 | BanglaVision | `tvsen5.aynaott.com` | `https://tvsen5.aynaott.com/banglavision/index.m3u8` |
| 6 | Cartoon Network | `live20.bozztv.com` | `https://live20.bozztv.com/giatvplayout7/giatv-209624/index.m3u8` |
| 7 | Channel 24 | `iptvlive.ahmed-bd-org.workers.dev` | `https://iptvlive.ahmed-bd-org.workers.dev/channel-24-hd-1/index.m3u8` |
| 8 | Channel i | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/FNHpYvGZ7FkCE10PwTHm/index.m3u8` |
| 9 | DBC News | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/pF66Tkz0qFwP2aMMqHyt/index.m3u8` |
| 10 | Discovery Bangla | `app-re.sm-monirul-islam-rs.workers.dev` | `https://app-re.sm-monirul-islam-rs.workers.dev/discovery-bangla/index.m3u8` |
| 11 | Disney HD Hindi | `ranapkz.site` | `http://ranapkz.site/TATABD/play.php?id=167551&format=.m3u8` |
| 12 | Duronto TV | `103.135.253.32` | `http://103.135.253.32:8080/DORONTU-TV/index.m3u8` |
| 13 | Hungama | `103.135.253.32` | `http://103.135.253.32:8080/HUNGAMA/index.m3u8` |
| 14 | Sony MAX HD | `stream.ottplus.live` | `https://stream.ottplus.live/live/max_hd_abr/index.m3u8` |
| 15 | Jamuna TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/KGdZEdA7qQ43dmPkgk1j/index.m3u8` |
| 16 | Maasranga TV | `tvsen5.aynaott.com` | `https://tvsen5.aynaott.com/maasrangatv/index.m3u8` |
| 17 | Nat Geo HD Bangla | `103.135.253.32` | `http://103.135.253.32:8080/NATGEO-HD/index.m3u8` |
| 18 | Nick Bangla | `103.135.253.32` | `http://103.135.253.32:8080/NICK/index.m3u8` |
| 19 | NTV | `2-fss-1.streamhoster.com` | `https://2-fss-1.streamhoster.com/pl_122/201748-1431018-1/chunklist.m3u8` |
| 20 | Somoy TV | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/somoy_tv_abr/index.m3u8` |
| 21 | Sony Aath | `stream.ottplus.live` | `https://stream.ottplus.live/live/sony_aath_abr/index.m3u8` |
| 22 | Sony Ten 1 HD | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/ten_1_hd_abr/index.m3u8` |
| 23 | Sony Ten 3 HD | `103.135.253.32` | `http://103.135.253.32:8080/TEN-3/index.m3u8` |
| 24 | Independent TV | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/independent_tv_abr/index.m3u8` |
| 25 | Ekattor TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/EWDrV5QskgarZEUBb3pU/index.m3u8` |
| 26 | News 24 | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/cdgr3tw6WoG7JyRnLbi0/index.m3u8` |
| 27 | BTV News | `btv.hridoytv-channel.workers.dev` | `https://btv.hridoytv-channel.workers.dev/news.m3u8` |
| 28 | Desh TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/ryFkXfd1a4CQ7mMdc820/index.m3u8` |
| 29 | Ekhon TV | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/ekhon_tv_abr/index.m3u8` |
| 30 | Bijoy TV | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/bijoy_tv_abr/index.m3u8` |
| 31 | Ekushey TV | `tvsen5.aynaott.com` | `https://tvsen5.aynaott.com/SyQuXz8sC3TB/index.m3u8` |
| 32 | News 21 Bangla TV | `103.190.133.68` | `http://103.190.133.68:1935/news21live/live/playlist.m3u8` |
| 33 | BTV Chattogram | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/TjGR1GcxKetHNVcMVxbq/index.m3u8` |
| 34 | Boishakhi TV | `boishakhi.sonarbanglatv.com` | `https://boishakhi.sonarbanglatv.com/boishakhi/boishakhitv/index.m3u8` |
| 35 | Deepto TV | `byphdgllyk.gpcdn.net` | `https://byphdgllyk.gpcdn.net/hls/deeptotv/index.m3u8` |
| 36 | RTV | `tvsen5.aynaott.com` | `https://tvsen5.aynaott.com/RtvHD/index.m3u8` |
| 37 | Gazi TV | `app.ncare.live` | `https://app.ncare.live/c3VydmVyX8RpbEU9Mi8xNy8yMDE0GIDU6RgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcGVMZEJCTEFWeVN3PTOmdFsaWRtaW51aiPhnPTI2/gazibdz.stream/live-orgin/gazibdz.stream/playlist.m3u8` |
| 38 | My TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/XMpHaEf0ANBhv8w6NWR7/index.m3u8` |
| 39 | Asian TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/pKb5k6NnzxsKpWUs6E8M/index.m3u8` |
| 40 | SA TV | `j6nfugukcl.gpcdn.net` | `https://j6nfugukcl.gpcdn.net/tile_5/master.m3u8` |
| 41 | Ananda TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/LeUAm4F1iixYns3s3Non/index.m3u8` |
| 42 | Rajdhani TV | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/rajdhani_tv/index.m3u8` |
| 43 | NAN TV | `app.ncare.live` | `https://app.ncare.live/c3VydmVyX8RpbEU9Mi8xNy8yMDE0GIDU6RgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcGVMZEJCTEFWeVN3PTOmdFsaWRtaW51aiPhnPTI2/nantv.stream/live-orgin/nantv.stream/playlist.m3u8` |
| 44 | Deshi TV | `deshitv.deshitv24.net` | `https://deshitv.deshitv24.net/live/myStream/playlist.m3u8` |
| 45 | Enter TV | `live1.entertv.com.bd` | `https://live1.entertv.com.bd/entertv/tracks-v1a1/mono.m3u8` |
| 46 | Channel S | `app.ncare.live` | `https://app.ncare.live/c3VydmVyX8RpbEU9Mi8xNy8yMDE0GIDU6RgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcGVMZEJCTEFWeVN3PTOmdFsaWRtaW51aiPhnPTI2/channels.stream/live-orgin/channels.stream/playlist.m3u8` |
| 47 | Deshe Bideshe TV | `dbcanada.sonarbanglatv.com` | `https://dbcanada.sonarbanglatv.com/deshebideshe/dbtv/index.m3u8` |
| 48 | Islamic TV | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/islamic_tv/index.m3u8` |
| 49 | Iqra Bangla | `app.ncare.live` | `https://app.ncare.live/c3VydmVyX8RpbEU9Mi8xNy8yMDE0GIDU6RgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcGVMZEJCTEFWeVN3PTOmdFsaWRtaW51aiPhnPTI2/iqrabanglatvoffice.stream/live-orgin/iqrabanglatvoffice.stream/chunks.m3u8` |
| 50 | Mohona TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/AkyX5dunzju4cpo26dr7/index.m3u8` |
| 51 | NRB TV | `app.ncare.live` | `https://app.ncare.live/live-orgin/nrb-eu.stream/playlist.m3u8` |
| 52 | Star Jalsha | `da86m1sqpm3o0.cloudfront.net` | `https://da86m1sqpm3o0.cloudfront.net/28072023/smil:starjalsha.smil/chunklist_b1928000.m3u8` |
| 53 | Sun Bangla | `27.124.71.27` | `http://27.124.71.27/Sun_Bangla/index.m3u8` |
| 54 | Bangla Jago TV | `banglajagotv.livebox.co.in` | `http://banglajagotv.livebox.co.in/banglajagohls/24x7.m3u8` |
| 55 | DD Bangla | `d3qs3d2rkhfqrt.cloudfront.net` | `https://d3qs3d2rkhfqrt.cloudfront.net/out/v1/7ff57cc9046b4c188b51a0d506f36e7f/index_3.m3u8` |
| 56 | TV9 Bangla | `dyjmyiv3bp2ez.cloudfront.net` | `https://dyjmyiv3bp2ez.cloudfront.net/pub-iotv9banaen8yq/liveabr/pub-iotv9banaen8yq/live_480p/chunks.m3u8` |
| 57 | Zee 24 Ghanta | `cdn-uw2-prod.tsv2.amagi.tv` | `https://cdn-uw2-prod.tsv2.amagi.tv/linear/amg01412-xiaomiasia-zee24ghantaa-xiaomi/playlist.m3u8` |
| 58 | Kolkata TV | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/kolkatatv/index.m3u8` |
| 59 | Ruposhi Bangla | `da86m1sqpm3o0.cloudfront.net` | `https://da86m1sqpm3o0.cloudfront.net/28072023/smil:rupashibangla.smil/playlist.m3u8` |
| 60 | Amar Bangla | `app.ncare.live` | `https://app.ncare.live/c3VydmVyX8RpbEU9Mi8xNy8yMDE0GIDU6RgzQ6NTAgdEoaeFzbF92YWxIZTO0U0ezN1IzMyfvcGVMZEJCTEFWeVN3PTOmdFsaWRtaW51aiPhnPTI/amarbanglatv.stream/playlist.m3u8` |
| 61 | R Plus Gold | `vglivessai.akamaized.net` | `https://vglivessai.akamaized.net/sg/v1/master/611d79b11b77e2f571934fd80ca1413453772ac7/cf883da3-f9f5-4c70-b0ef-b3ac2e2ad1e3/index.m3u8` |
| 62 | Enterr10 Bangla | `amg01448-samsungin-enterr10bangla-samsungin-ad-gg.amagi.tv` | `https://amg01448-samsungin-enterr10bangla-samsungin-ad-gg.amagi.tv/playlist/amg01448-samsungin-enterr10bangla-samsungin/playlist.m3u8` |
| 63 | Sananda TV | `live-stream.amarbanglatv.in` | `http://live-stream.amarbanglatv.in:8080/hls/sanandatv/index.m3u8` |
| 64 | Bangla Plus | `live-stream.utkalbongo.com` | `https://live-stream.utkalbongo.com/hls/livebanglatvstream.m3u8` |
| 65 | Sony Yay | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/sony_yay_abr/index.m3u8` |
| 66 | Pogo | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/pogo_sd_abr/index.m3u8` |
| 67 | Discovery Kids | `drk6xq0vhn.gpcdn.net` | `https://drk6xq0vhn.gpcdn.net/live/discovery_kids_abr/index.m3u8` |
| 68 | DD Sports | `d3qs3d2rkhfqrt.cloudfront.net` | `https://d3qs3d2rkhfqrt.cloudfront.net/out/v1/b17adfe543354fdd8d189b110617cddd/index_3.m3u8` |
| 69 | A Sports | `tvsen6.aynaott.com` | `https://tvsen6.aynaott.com/zv68oqPDu7MZZwmHhRxt/index.m3u8` |
| 70 | beIN Sports XTRA | `bein-esp-xumo.amagi.tv` | `https://bein-esp-xumo.amagi.tv/playlistR1080p.m3u8` |
| 71 | Sports First TV | `d4ddgdmj1cvnm.cloudfront.net` | `https://d4ddgdmj1cvnm.cloudfront.net/scheduler/scheduleMaster/409.m3u8` |
| 72 | Red Bull TV | `rbmn-live.akamaized.net` | `https://rbmn-live.akamaized.net/hls/live/590964/BoRB-AT/master_3360.m3u8` |
| 73 | Star Sports 2 | `103.151.60.162` | `http://103.151.60.162:2122/play/a00v/index.m3u8?hls` |
| 74 | Cricket Gold | `d1nj4u39ja4cn0.cloudfront.net` | `https://d1nj4u39ja4cn0.cloudfront.net/v1/master/9d062541f2ff39b5c0f48b743c6411d25f62fc25/FLS-MuxIP-CricketGold/418.m3u8` |
| 75 | FITE 24/7 | `d3d85c7qkywguj.cloudfront.net` | `https://d3d85c7qkywguj.cloudfront.net/scheduler/scheduleMaster/263.m3u8` |

## Integrity

- Main playlist preserved unchanged.
- No credential, token, DRM, license-key or geo-restriction bypass attempted.
- Promote into Main only after correct Sonic identity, playable media and Link3 playback have been confirmed.
