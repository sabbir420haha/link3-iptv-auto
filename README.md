# Link3 Auto-Updated IPTV Playlist

IPTV Pro URL: https://raw.githubusercontent.com/sabbir420haha/link3-iptv-auto/main/playlist.m3u

This project maintains a curated M3U playlist for Bangladesh News, BD TV, Indian Bangla, Hindi Kids and Sports, with additional photo-requested channels.

## How updating works
GitHub Actions refreshes candidate stream URLs every six hours (UTC), attempts public HLS manifest checks and commits changes to `playlist.m3u`. IPTV Pro must be configured to reload its M3U URL periodically.

## Known working on user's Link3 Wi-Fi
Channel 24, Independent TV, Sony AATH and Hungama are pinned to the user's working stream URLs.

## Important
A successful HLS manifest check is **not** proof of playback, video quality, language, authorization, or low buffering on Link3. Public playlists may be unreliable. Local/BDIX-only, private-IP and known T-Play placeholder sources are filtered. This project does not bypass subscription restrictions or DRM. Not every requested channel will have an available live stream.

The project publishes a playlist **URL**; it does not provide or host any video streams. Upstream channel URLs remain controlled by their respective providers.
